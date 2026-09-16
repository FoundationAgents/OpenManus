"""Model discovery and capability filtering for OrcaRouter.

The model list comes from ``GET {api_base}/models`` on the OrcaRouter relay.
Live discovery is authoritative; when it fails, a small verified seed keeps a
fresh installation usable. The seed is never merged into a successful live
result.

Capability filters are derived from catalog metadata only - never from a model
name. A record that does not explicitly declare the modality an entry point
uploads is excluded (fail closed), because a text-only model that silently
receives an image is a broken request, not a degraded one.
"""

import json
import threading
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from app.orcarouter.constants import OrcaOrigins, resolve_origins
from app.orcarouter.errors import OrcaCatalogError


# Supported endpoint types this integration can actually speak (OpenAI wire
# format). Anything outside the set is dropped rather than advertised.
TEXT_ENDPOINT_TYPES = frozenset({"openai", "anthropic", "gemini", "openai-response"})
EMBEDDING_ENDPOINT_TYPES = frozenset({"embedding", "embeddings"})
IMAGE_ENDPOINT_TYPES = frozenset({"image-generation"})
VIDEO_ENDPOINT_TYPES = frozenset({"openai-video"})
RERANK_ENDPOINT_TYPES = frozenset({"jina-rerank"})

# Models whose only job is a non-text output must never appear in a chat
# selector, even when they also advertise an OpenAI-compatible route.
CHAT_EXCLUDED_ENDPOINT_TYPES = frozenset(
    {"image-generation", "openai-video", "jina-rerank"}
)

MAX_MODELS = 2000
MAX_BODY_BYTES = 4 * 1024 * 1024
CATALOG_TIMEOUT = 20.0

_REQUIRED_FIELDS = ("id",)


def _reasoning_efforts(model_id: str, metadata: Optional[dict]) -> List[str]:
    if metadata and isinstance(metadata.get("reasoning_efforts"), list):
        return [str(x) for x in metadata["reasoning_efforts"]]
    if model_id in VERIFIED_SEED:
        return list(VERIFIED_SEED[model_id].get("reasoning_efforts", []))
    return []


class ModelRecord:
    """One entry of the OrcaRouter catalog, normalised and bounded."""

    __slots__ = (
        "id",
        "name",
        "context_length",
        "max_completion_tokens",
        "input_modalities",
        "output_modalities",
        "supported_endpoint_types",
        "reasoning_efforts",
        "source",
    )

    def __init__(
        self,
        id: str,
        name: Optional[str] = None,
        context_length: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        input_modalities: Optional[Iterable[str]] = None,
        output_modalities: Optional[Iterable[str]] = None,
        supported_endpoint_types: Optional[Iterable[str]] = None,
        reasoning_efforts: Optional[Iterable[str]] = None,
        source: str = "live",
    ):
        self.id = id
        self.name = name or id
        self.context_length = context_length
        self.max_completion_tokens = max_completion_tokens
        self.input_modalities = tuple(input_modalities or ())
        self.output_modalities = tuple(output_modalities or ())
        self.supported_endpoint_types = tuple(supported_endpoint_types or ())
        self.reasoning_efforts = tuple(reasoning_efforts or ())
        self.source = source

    @property
    def vendor(self) -> str:
        return self.id.split("/", 1)[0] if "/" in self.id else ""

    def supports_endpoint(self, endpoint_types: Iterable[str]) -> bool:
        return bool(set(self.supported_endpoint_types) & set(endpoint_types))

    def accepts_input(self, modality: str) -> bool:
        """True only when the catalog explicitly declares the modality."""
        return modality in self.input_modalities

    def to_metadata(self) -> Dict[str, object]:
        """The minimum a selector needs; never carries a credential."""
        return {
            "id": self.id,
            "name": self.name,
            "context_length": self.context_length,
            "max_completion_tokens": self.max_completion_tokens,
            "input_modalities": list(self.input_modalities),
            "output_modalities": list(self.output_modalities),
            "supported_endpoint_types": list(self.supported_endpoint_types),
            "reasoning_efforts": list(self.reasoning_efforts),
            "source": self.source,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ModelRecord({self.id!r}, source={self.source!r})"

    def __eq__(self, other) -> bool:
        return isinstance(other, ModelRecord) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)


# --------------------------------------------------------------------- seed

# A small, verified cold-start seed, used only when live discovery fails. Every
# entry keeps the metadata this project relies on (context window, input
# modalities, reasoning-effort ladder), so an outage never silently downgrades
# a model's advertised capabilities.
VERIFIED_SEED: Dict[str, Dict[str, object]] = {
    "openai/gpt-5.5": {
        "name": "OpenAI: GPT-5.5",
        "context_length": 400000,
        "max_completion_tokens": 128000,
        "input_modalities": ("text", "image"),
        "output_modalities": ("text",),
        "supported_endpoint_types": ("openai", "openai-response"),
        "reasoning_efforts": ("low", "medium", "high", "xhigh"),
    },
    "anthropic/claude-opus-4.8": {
        "name": "Anthropic: Claude Opus 4.8",
        "context_length": 200000,
        "max_completion_tokens": 64000,
        "input_modalities": ("text", "image"),
        "output_modalities": ("text",),
        "supported_endpoint_types": ("openai", "anthropic"),
        "reasoning_efforts": ("low", "medium", "high"),
    },
    "google/gemini-3.5-flash": {
        "name": "Google: Gemini 3.5 Flash",
        "context_length": 1000000,
        "max_completion_tokens": 65536,
        "input_modalities": ("text", "image", "audio", "video"),
        "output_modalities": ("text",),
        "supported_endpoint_types": ("openai", "gemini"),
        "reasoning_efforts": ("low", "medium", "high"),
    },
    "deepseek/deepseek-v4-pro": {
        "name": "DeepSeek: DeepSeek V4 Pro",
        "context_length": 1048576,
        "max_completion_tokens": 384000,
        "input_modalities": ("text",),
        "output_modalities": ("text",),
        "supported_endpoint_types": ("openai", "openai-response", "anthropic"),
        "reasoning_efforts": ("low", "medium", "high"),
    },
    "orcarouter/auto": {
        "name": "OrcaRouter: Auto",
        "context_length": 1000000,
        "max_completion_tokens": 128000,
        "input_modalities": ("text", "image"),
        "output_modalities": ("text",),
        "supported_endpoint_types": ("openai", "openai-response"),
        "reasoning_efforts": (),
    },
}

SEED_CATALOG_SOURCE = "verified_seed"
LIVE_CATALOG_SOURCE = "live"


def seed_records() -> List[ModelRecord]:
    """The verified fallback catalog, clearly labelled as such."""
    records = []
    for model_id, meta in VERIFIED_SEED.items():
        records.append(
            ModelRecord(
                id=model_id,
                name=str(meta.get("name") or model_id),
                context_length=meta.get("context_length"),
                max_completion_tokens=meta.get("max_completion_tokens"),
                input_modalities=meta.get("input_modalities", ()),
                output_modalities=meta.get("output_modalities", ()),
                supported_endpoint_types=meta.get("supported_endpoint_types", ()),
                reasoning_efforts=meta.get("reasoning_efforts", ()),
                source=SEED_CATALOG_SOURCE,
            )
        )
    return records


# ------------------------------------------------------------------ parsing


def parse_catalog(payload: object) -> List[ModelRecord]:
    """Turn a ``GET /models`` payload into bounded, validated records."""
    if isinstance(payload, dict):
        items = payload.get("data")
    else:
        items = payload
    if not isinstance(items, list):
        raise OrcaCatalogError("OrcaRouter model catalog was not a list of models.")
    if len(items) > MAX_MODELS:
        raise OrcaCatalogError(
            f"OrcaRouter model catalog exceeded the {MAX_MODELS} model bound."
        )

    records: List[ModelRecord] = []
    seen = set()
    for item in items:
        record = _parse_record(item)
        if record is None or record.id in seen:
            continue
        seen.add(record.id)
        records.append(record)
    return records


def _parse_record(item: object) -> Optional[ModelRecord]:
    if not isinstance(item, dict):
        return None
    for field in _REQUIRED_FIELDS:
        if not isinstance(item.get(field), str) or not item[field].strip():
            return None
    model_id = item["id"].strip()

    architecture = item.get("architecture")
    if not isinstance(architecture, dict):
        architecture = {}
    top_provider = item.get("top_provider")
    if not isinstance(top_provider, dict):
        top_provider = {}

    endpoints = item.get("supported_endpoint_types")
    if not isinstance(endpoints, list):
        endpoints = []
    endpoints = [str(e) for e in endpoints if isinstance(e, str)]

    context_length = _as_int(item.get("context_length"))
    if context_length is None:
        context_length = _as_int(top_provider.get("context_length"))
    max_completion = _as_int(item.get("max_completion_tokens"))
    if max_completion is None:
        max_completion = _as_int(top_provider.get("max_completion_tokens"))

    name = item.get("name")
    return ModelRecord(
        id=model_id,
        name=name if isinstance(name, str) and name.strip() else model_id,
        context_length=context_length,
        max_completion_tokens=max_completion,
        input_modalities=_as_str_list(architecture.get("input_modalities")),
        output_modalities=_as_str_list(architecture.get("output_modalities")),
        supported_endpoint_types=endpoints,
        reasoning_efforts=_reasoning_efforts(model_id, item),
        source=LIVE_CATALOG_SOURCE,
    )


def _as_int(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _as_str_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if isinstance(v, str)]


# --------------------------------------------------------------- capabilities


def filter_models(records: Sequence[ModelRecord], capability: str) -> List[ModelRecord]:
    """Filter a catalog for one entry point's capability.

    ``capability`` is one of ``chat``, ``chat_multimodal``, ``embedding``,
    ``image``, ``video`` or ``rerank``.
    """
    return [r for r in records if matches_capability(r, capability)]


def matches_capability(record: ModelRecord, capability: str) -> bool:
    """Whether one record is usable by one entry point. Fails closed."""
    endpoints = set(record.supported_endpoint_types)

    if capability == "chat":
        if endpoints & CHAT_EXCLUDED_ENDPOINT_TYPES:
            return False
        return bool(endpoints & TEXT_ENDPOINT_TYPES)

    if capability == "chat_multimodal":
        if not matches_capability(record, "chat"):
            return False
        # Only modalities the catalog explicitly declares; no name guessing.
        return any(record.accepts_input(m) for m in ("image", "audio", "video"))

    if capability == "chat_vision":
        return matches_capability(record, "chat") and record.accepts_input("image")

    if capability == "embedding":
        return bool(endpoints & EMBEDDING_ENDPOINT_TYPES)

    if capability == "image":
        return bool(endpoints & IMAGE_ENDPOINT_TYPES)

    if capability == "video":
        return bool(endpoints & VIDEO_ENDPOINT_TYPES)

    if capability == "rerank":
        return bool(endpoints & RERANK_ENDPOINT_TYPES)

    raise OrcaCatalogError(f"Unknown model capability {capability!r}.")


def required_modalities(modalities: Iterable[str]) -> Tuple[str, ...]:
    """The non-text input modalities an entry point actually uploads."""
    return tuple(m for m in modalities if m and m != "text")


def filter_for_inputs(
    records: Sequence[ModelRecord], modalities: Iterable[str]
) -> List[ModelRecord]:
    """Chat models that accept every non-text modality an entry point sends."""
    needed = required_modalities(modalities)
    out = []
    for record in records:
        if not matches_capability(record, "chat"):
            continue
        # An entry point that uploads image + audio needs both declared.
        if all(record.accepts_input(m) for m in needed):
            out.append(record)
    return out


def capability_options(
    records: Sequence[ModelRecord],
    capability: str,
    selected_model: Optional[str] = None,
) -> Dict[str, object]:
    """The option list a model selector receives, plus its status.

    Returning the filtered list (rather than a free-text box) is what makes an
    incompatible attachment impossible to submit: when the attachment changes,
    the list is recomputed and an already-selected model that no longer
    qualifies is dropped and reported as such.
    """
    return _options(
        matching=filter_models(records, capability),
        records=records,
        label=capability,
        selected_model=selected_model,
        required=(),
    )


# --------------------------------------------------------------- entry points

# Every place OpenManus can send a request, and the catalog evidence a model
# needs before it may appear in that entry point's selector. ``inputs`` holds
# the non-text modalities the entry point actually uploads; the browser and
# toolcall agents attach screenshots, which is the ``vision`` entry point.
ENTRY_POINTS: Dict[str, Dict[str, object]] = {
    "chat": {"capability": "chat", "inputs": ()},
    "vision": {"capability": "chat", "inputs": ("image",)},
    "embedding": {"capability": "embedding", "inputs": ()},
    "image": {"capability": "image", "inputs": ()},
    "video": {"capability": "video", "inputs": ()},
    "rerank": {"capability": "rerank", "inputs": ()},
}


def entry_point_options(
    records: Sequence[ModelRecord],
    entry_point: str,
    selected_model: Optional[str] = None,
) -> Dict[str, object]:
    """The option list one OpenManus entry point is allowed to offer.

    ``vision`` is chat narrowed to models that explicitly declare image input,
    so attaching an image recomputes the list: a text-only model that was
    selected is dropped and reported instead of being kept and guarded later.
    """
    spec = ENTRY_POINTS.get(entry_point)
    if spec is None:
        raise OrcaCatalogError(
            f"Unknown model entry point {entry_point!r}; expected one of "
            + ", ".join(sorted(ENTRY_POINTS))
            + "."
        )
    inputs = tuple(spec["inputs"])  # type: ignore[arg-type]
    matching = (
        filter_for_inputs(records, inputs)
        if inputs
        else filter_models(records, str(spec["capability"]))
    )
    return _options(
        matching=matching,
        records=records,
        label=entry_point,
        selected_model=selected_model,
        required=inputs,
    )


def _options(
    matching: Sequence[ModelRecord],
    records: Sequence[ModelRecord],
    label: str,
    selected_model: Optional[str],
    required: Tuple[str, ...],
) -> Dict[str, object]:
    ids = [r.id for r in matching]
    invalidated = bool(selected_model) and selected_model not in ids
    return {
        "options": [r.to_metadata() for r in matching],
        "ids": ids,
        "capability": label,
        "required_modalities": list(required),
        "selected": None if invalidated else selected_model,
        "invalidated": invalidated,
        "degraded": any(r.source == SEED_CATALOG_SOURCE for r in records)
        if records
        else False,
    }


# -------------------------------------------------------------------- fetch


class ModelCatalog:
    """Bounded live model discovery with a verified cold-start fallback."""

    def __init__(
        self,
        origins: Optional[OrcaOrigins] = None,
        fetcher: Optional[Callable[[str, Dict[str, str], float], tuple]] = None,
        timeout: float = CATALOG_TIMEOUT,
    ):
        self.origins = origins or resolve_origins()
        self._fetcher = fetcher or _http_fetch
        self.timeout = timeout
        self._records: Optional[List[ModelRecord]] = None
        self.source = "unresolved"
        self.error: Optional[str] = None
        self.model_count = 0

    def _headers(self, api_key: Optional[str]) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def refresh(
        self, api_key: Optional[str] = None, capability: Optional[str] = None
    ) -> List[ModelRecord]:
        """Fetch the catalog. On failure, keep the verified seed usable."""
        url = self.origins.models_url
        if capability:
            url = f"{url}?capability={capability}"
        try:
            status, text = self._fetcher(url, self._headers(api_key), self.timeout)
        except Exception as exc:
            return self._fallback(f"{type(exc).__name__}: {exc}")

        if status != 200:
            return self._fallback(f"catalog request returned HTTP {status}")
        if len(text) > MAX_BODY_BYTES:
            return self._fallback("catalog response exceeded the size bound")
        try:
            payload = json.loads(text)
        except ValueError as exc:
            return self._fallback(f"catalog response was not JSON: {exc}")
        try:
            records = parse_catalog(payload)
        except OrcaCatalogError as exc:
            return self._fallback(str(exc))

        if not records:
            return self._fallback("catalog returned no usable models")

        self._records = records
        self.source = LIVE_CATALOG_SOURCE
        self.error = None
        self.model_count = len(records)
        return records

    def _fallback(self, reason: str) -> List[ModelRecord]:
        from app.orcarouter.errors import redact

        self.error = redact(reason)
        if self._records:
            # A last-known-good catalog beats a seed; neither is free text.
            self.source = "last_known_good"
            self.model_count = len(self._records)
            return self._records
        self._records = seed_records()
        self.source = SEED_CATALOG_SOURCE
        self.model_count = len(self._records)
        return self._records

    @property
    def records(self) -> List[ModelRecord]:
        if self._records is None:
            return seed_records()
        return self._records

    def capabilities(self, capability: str) -> Dict[str, object]:
        return capability_options(self.records, capability)

    def chat_models(self) -> List[str]:
        return [r.id for r in filter_models(self.records, "chat")]

    def multimodal_models(self) -> List[str]:
        return [r.id for r in filter_models(self.records, "chat_multimodal")]

    def status(self) -> Dict[str, object]:
        """Display state for a selector: live, degraded, or last-known-good."""
        return {
            "source": self.source,
            "degraded": self.source != LIVE_CATALOG_SOURCE,
            "error": self.error,
            "model_count": self.model_count,
            "refresh_url": self.origins.models_url,
        }


def _http_fetch(url: str, headers: Dict[str, str], timeout: float) -> tuple:
    import httpx

    response = httpx.get(url, headers=headers, timeout=timeout)
    return response.status_code, response.text


# ------------------------------------------------------------ shared service

_SHARED: Dict[str, ModelCatalog] = {}
_SHARED_LOCK = threading.Lock()


def shared_catalog(
    origins: Optional[OrcaOrigins] = None,
    api_key: Optional[str] = None,
    refresh: bool = False,
) -> ModelCatalog:
    """One catalog per inference origin, reused by every selector.

    Discovery is a single bounded request per origin rather than one per agent
    profile, and a selector that asks again reads the snapshot already in
    memory. The catalog holds model metadata only - never a credential.
    """
    resolved = origins or resolve_origins()
    with _SHARED_LOCK:
        catalog = _SHARED.get(resolved.api_base)
        if catalog is None:
            catalog = ModelCatalog(origins=resolved)
            _SHARED[resolved.api_base] = catalog
        if refresh and catalog.source == "unresolved":
            catalog.refresh(api_key=api_key)
        return catalog


def reset_shared_catalog() -> None:
    """Drop the cached catalogs (used by tests and after a credential change)."""
    with _SHARED_LOCK:
        _SHARED.clear()


def catalog_options(
    api_key: Optional[str] = None,
    entry_point: str = "chat",
    selected_model: Optional[str] = None,
    origins: Optional[OrcaOrigins] = None,
    refresh: bool = True,
) -> Dict[str, object]:
    """The options a selector shows for one entry point, from the live catalog.

    This is the single place every OpenManus entry point resolves its model
    choices through, so no page or command re-implements the capability rules.
    ``status`` is carried alongside the options so a caller can show whether the
    list is live, last-known-good or the verified cold-start seed.
    """
    catalog = shared_catalog(origins=origins, api_key=api_key, refresh=refresh)
    result = entry_point_options(catalog.records, entry_point, selected_model)
    result["status"] = catalog.status()
    return result


def model_accepts(
    model_id: Optional[str],
    modality: str,
    origins: Optional[OrcaOrigins] = None,
    api_key: Optional[str] = None,
) -> bool:
    """Whether the catalog vouches for ``model_id`` accepting ``modality``.

    Fails closed: a model the catalog does not list, or lists without the
    declared modality, is not treated as capable. Nothing here guesses from a
    model name.
    """
    if not model_id:
        return False
    catalog = shared_catalog(origins=origins, api_key=api_key, refresh=True)
    for record in catalog.records:
        if record.id == model_id:
            return record.accepts_input(modality)
    return False
