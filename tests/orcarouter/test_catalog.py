"""Model discovery, capability filtering, fail-closed modality handling."""

import json

import pytest

from app.orcarouter.catalog import (
    ENTRY_POINTS,
    MAX_MODELS,
    SEED_CATALOG_SOURCE,
    VERIFIED_SEED,
    ModelCatalog,
    capability_options,
    catalog_options,
    entry_point_options,
    filter_for_inputs,
    filter_models,
    matches_capability,
    model_accepts,
    parse_catalog,
    reset_shared_catalog,
    seed_records,
    shared_catalog,
)
from app.orcarouter.errors import OrcaCatalogError
from tests.orcarouter.conftest import (
    FAKE_KEY,
    FakeCatalogServer,
    chat_record,
    model_payload,
)


TEXT_ONLY = chat_record("vendor/text-only")
VISION_CHAT = chat_record(
    "vendor/vision-chat",
    architecture={
        "input_modalities": ["text", "image"],
        "output_modalities": ["text"],
    },
)
AUDIO_CHAT = chat_record(
    "vendor/audio-chat",
    architecture={
        "input_modalities": ["text", "audio"],
        "output_modalities": ["text"],
    },
)
EMBEDDING = {
    "id": "vendor/embed-1",
    "object": "model",
    "supported_endpoint_types": ["embeddings"],
    "architecture": {"input_modalities": ["text"], "output_modalities": ["embedding"]},
}
IMAGE_GEN = {
    "id": "vendor/image-gen",
    "object": "model",
    "supported_endpoint_types": ["image-generation"],
    "architecture": {"input_modalities": ["text"], "output_modalities": ["image"]},
}
VIDEO_GEN = {
    "id": "vendor/video-gen",
    "object": "model",
    "supported_endpoint_types": ["openai-video"],
    "architecture": {"input_modalities": ["text"], "output_modalities": ["video"]},
}
RERANK = {
    "id": "vendor/rerank-1",
    "object": "model",
    "supported_endpoint_types": ["jina-rerank"],
    "architecture": {"input_modalities": ["text"], "output_modalities": ["score"]},
}
ANTHROPIC_CHAT = chat_record(
    "vendor/claude", supported_endpoint_types=["openai", "anthropic"]
)
GEMINI_CHAT = chat_record("vendor/gemini", supported_endpoint_types=["gemini"])
UNKNOWN_ROUTE = chat_record(
    "vendor/exotic", supported_endpoint_types=["some-future-api"]
)
MULTI_ROUTE_CHAT = chat_record(
    "vendor/multi",
    supported_endpoint_types=["openai", "image-generation"],
    architecture={
        "input_modalities": ["text", "image"],
        "output_modalities": ["text", "image"],
    },
)


ALL = [
    TEXT_ONLY,
    VISION_CHAT,
    AUDIO_CHAT,
    EMBEDDING,
    IMAGE_GEN,
    VIDEO_GEN,
    RERANK,
    ANTHROPIC_CHAT,
    GEMINI_CHAT,
    UNKNOWN_ROUTE,
    MULTI_ROUTE_CHAT,
]


def records():
    return parse_catalog(model_payload(*ALL))


# ------------------------------------------------------------------ parsing


def test_parses_records_and_keeps_the_vendor_namespace():
    parsed = records()
    assert "vendor/text-only" in [r.id for r in parsed]
    assert parsed[0].vendor == "vendor"
    assert all(r.source == "live" for r in parsed)


def test_preserves_context_and_modality_metadata():
    parsed = {r.id: r for r in records()}
    assert parsed["vendor/vision-chat"].context_length == 128000
    assert parsed["vendor/vision-chat"].accepts_input("image")
    assert not parsed["vendor/text-only"].accepts_input("image")


def test_reads_context_from_top_provider_when_absent_at_the_top_level():
    payload = model_payload(
        {
            "id": "vendor/nested",
            "supported_endpoint_types": ["openai"],
            "top_provider": {"context_length": 200000, "max_completion_tokens": 4096},
        }
    )
    record = parse_catalog(payload)[0]
    assert record.context_length == 200000
    assert record.max_completion_tokens == 4096


def test_records_without_an_id_are_dropped():
    payload = model_payload({"name": "no id"}, {"id": "  "}, chat_record("vendor/ok"))
    assert [r.id for r in parse_catalog(payload)] == ["vendor/ok"]


def test_duplicate_ids_are_collapsed():
    payload = model_payload(chat_record("vendor/dup"), chat_record("vendor/dup"))
    assert len(parse_catalog(payload)) == 1


def test_non_list_payloads_are_refused():
    with pytest.raises(OrcaCatalogError):
        parse_catalog({"data": "nope"})
    with pytest.raises(OrcaCatalogError):
        parse_catalog({"object": "list"})


def test_catalog_size_is_bounded():
    payload = model_payload(
        *[chat_record(f"vendor/m{i}") for i in range(MAX_MODELS + 1)]
    )
    with pytest.raises(OrcaCatalogError):
        parse_catalog(payload)


# -------------------------------------------------------------- capabilities


def test_chat_filter_keeps_only_speakable_text_endpoints():
    ids = [r.id for r in filter_models(records(), "chat")]
    assert "vendor/text-only" in ids
    assert "vendor/vision-chat" in ids
    assert "vendor/claude" in ids
    assert "vendor/gemini" in ids
    assert "vendor/exotic" not in ids


def test_chat_filter_excludes_non_text_output_models():
    ids = [r.id for r in filter_models(records(), "chat")]
    assert "vendor/image-gen" not in ids
    assert "vendor/video-gen" not in ids
    assert "vendor/rerank-1" not in ids
    # A model that speaks OpenAI *and* generates images is still not a chat pick.
    assert "vendor/multi" not in ids


def test_embedding_filter_matches_only_the_embeddings_endpoint():
    ids = [r.id for r in filter_models(records(), "embedding")]
    assert ids == ["vendor/embed-1"]


def test_image_video_and_rerank_filters():
    image_ids = [r.id for r in filter_models(records(), "image")]
    # Both models that genuinely declare image-generation, and nothing else.
    assert set(image_ids) == {"vendor/image-gen", "vendor/multi"}
    assert [r.id for r in filter_models(records(), "video")] == ["vendor/video-gen"]
    assert [r.id for r in filter_models(records(), "rerank")] == ["vendor/rerank-1"]


def test_multimodal_filter_requires_an_explicit_declared_modality():
    ids = [r.id for r in filter_models(records(), "chat_multimodal")]
    assert "vendor/vision-chat" in ids
    assert "vendor/audio-chat" in ids
    assert "vendor/text-only" not in ids  # fail closed


def test_vision_filter_is_image_specific():
    ids = [r.id for r in filter_models(records(), "chat_vision")]
    assert ids == ["vendor/vision-chat"]


def test_unknown_capability_is_an_error_not_a_silent_pass():
    with pytest.raises(OrcaCatalogError):
        matches_capability(records()[0], "telepathy")


def test_entry_point_modalities_are_all_required():
    parsed = records()
    # An entry point that uploads image and audio needs both declared.
    assert [r.id for r in filter_for_inputs(parsed, ["text", "image"])] == [
        "vendor/vision-chat"
    ]
    assert [r.id for r in filter_for_inputs(parsed, ["text", "audio"])] == [
        "vendor/audio-chat"
    ]
    assert filter_for_inputs(parsed, ["text", "image", "audio"]) == []


# ------------------------------------------------------------- option lists


def test_options_are_records_not_free_text():
    options = capability_options(records(), "chat")
    assert options["ids"]
    assert all(set(o) >= {"id", "name", "source"} for o in options["options"])
    assert all("api_key" not in json.dumps(o) for o in options["options"])


def test_an_incompatible_selected_model_is_invalidated():
    result = capability_options(
        records(), "chat_vision", selected_model="vendor/text-only"
    )
    assert result["invalidated"] is True
    assert result["selected"] is None
    result = capability_options(
        records(), "chat_vision", selected_model="vendor/vision-chat"
    )
    assert result["invalidated"] is False
    assert result["selected"] == "vendor/vision-chat"


def test_attaching_an_image_narrows_the_option_list_and_drops_the_text_model():
    records_all = records()
    before = capability_options(records_all, "chat", selected_model="vendor/text-only")
    after = capability_options(
        records_all, "chat_vision", selected_model="vendor/text-only"
    )
    assert "vendor/text-only" in before["ids"]
    assert "vendor/text-only" not in after["ids"]
    assert after["invalidated"] is True
    assert after["selected"] is None


# ------------------------------------------------------------------- catalog


def test_live_discovery_is_authoritative():
    server = FakeCatalogServer(payload=model_payload(*ALL))
    catalog = ModelCatalog(fetcher=server, origins=_origins())
    catalog.refresh(api_key=FAKE_KEY)
    assert catalog.source == "live"
    assert catalog.status()["degraded"] is False
    assert catalog.error is None
    assert catalog.model_count == len(ALL)
    url, headers = server.calls[-1]
    assert url == "https://api.orcarouter.ai/v1/models"
    assert headers["Authorization"] == f"Bearer {FAKE_KEY}"


def test_capability_query_is_passed_through():
    server = FakeCatalogServer(payload=model_payload(*ALL))
    catalog = ModelCatalog(fetcher=server, origins=_origins())
    catalog.refresh(api_key=FAKE_KEY, capability="chat")
    assert server.calls[-1][0].endswith("/models?capability=chat")


def test_models_url_never_points_at_the_auth_origin():
    server = FakeCatalogServer(payload=model_payload(*ALL))
    catalog = ModelCatalog(fetcher=server, origins=_origins())
    catalog.refresh(api_key=FAKE_KEY)
    url = server.calls[-1][0]
    assert "www.orcarouter.ai" not in url
    assert "/auth" not in url


def test_network_failure_falls_back_to_the_verified_seed():
    def boom(url, headers, timeout):
        raise OSError("connection refused")

    catalog = ModelCatalog(fetcher=boom, origins=_origins())
    catalog.refresh(api_key=FAKE_KEY)
    assert catalog.source == SEED_CATALOG_SOURCE
    assert catalog.status()["degraded"] is True
    assert catalog.status()["error"]
    assert set(catalog.chat_models()) >= {
        "openai/gpt-5.5",
        "anthropic/claude-opus-4.8",
        "deepseek/deepseek-v4-pro",
        "orcarouter/auto",
    }


def test_http_error_falls_back_to_the_verified_seed():
    catalog = ModelCatalog(
        fetcher=FakeCatalogServer(status=500, body="oops"), origins=_origins()
    )
    catalog.refresh(api_key=FAKE_KEY)
    assert catalog.source == SEED_CATALOG_SOURCE


def test_seed_keeps_reasoning_and_modality_metadata():
    catalog = ModelCatalog(
        fetcher=FakeCatalogServer(status=503, body=""), origins=_origins()
    )
    catalog.refresh()
    by_id = {r.id: r for r in catalog.records}
    gpt = by_id["openai/gpt-5.5"]
    assert list(gpt.reasoning_efforts) == ["low", "medium", "high", "xhigh"]
    assert gpt.accepts_input("image")
    assert gpt.context_length == 400000
    gemini = by_id["google/gemini-3.5-flash"]
    assert gemini.accepts_input("image") and gemini.accepts_input("video")
    assert not by_id["deepseek/deepseek-v4-pro"].accepts_input("image")


def test_an_empty_catalog_is_a_failure_not_an_empty_selector():
    catalog = ModelCatalog(
        fetcher=FakeCatalogServer(payload=model_payload()), origins=_origins()
    )
    catalog.refresh(api_key=FAKE_KEY)
    assert catalog.source == SEED_CATALOG_SOURCE
    assert catalog.chat_models()


def test_the_seed_is_never_merged_into_a_live_result():
    catalog = ModelCatalog(
        fetcher=FakeCatalogServer(payload=model_payload(*ALL)), origins=_origins()
    )
    catalog.refresh(api_key=FAKE_KEY)
    sources = {r.source for r in catalog.records}
    assert sources == {"live"}
    assert all("openai/gpt-5.5" != r.id for r in catalog.records)


def test_a_last_known_good_catalog_survives_a_later_outage():
    catalog = ModelCatalog(
        fetcher=FakeCatalogServer(payload=model_payload(*ALL)), origins=_origins()
    )
    catalog.refresh(api_key=FAKE_KEY)
    assert catalog.source == "live"

    def boom(url, headers, timeout):
        raise OSError("down")

    catalog._fetcher = boom
    catalog.refresh(api_key=FAKE_KEY)
    assert catalog.source == "last_known_good"
    assert catalog.status()["degraded"] is True
    assert "vendor/text-only" in catalog.chat_models()


def test_oversized_catalog_response_is_refused():
    catalog = ModelCatalog(
        fetcher=FakeCatalogServer(body="x" * (5 * 1024 * 1024)), origins=_origins()
    )
    catalog.refresh(api_key=FAKE_KEY)
    assert catalog.source == SEED_CATALOG_SOURCE


def test_malformed_catalog_json_is_refused():
    catalog = ModelCatalog(
        fetcher=FakeCatalogServer(body="{not json"), origins=_origins()
    )
    catalog.refresh(api_key=FAKE_KEY)
    assert catalog.source == SEED_CATALOG_SOURCE


def test_catalog_never_exposes_the_credential_in_its_status():
    catalog = ModelCatalog(
        fetcher=FakeCatalogServer(payload=model_payload(*ALL)), origins=_origins()
    )
    catalog.refresh(api_key=FAKE_KEY)
    assert FAKE_KEY not in json.dumps(catalog.status())
    assert FAKE_KEY not in json.dumps(catalog.capabilities("chat"))


def test_seed_records_are_labelled_as_a_fallback():
    seed = seed_records()
    assert {r.id for r in seed} == set(VERIFIED_SEED)
    assert all(r.source == SEED_CATALOG_SOURCE for r in seed)
    options = capability_options(seed, "chat")
    assert options["degraded"] is True


def _origins():
    from app.orcarouter.constants import OrcaOrigins

    return OrcaOrigins("https://www.orcarouter.ai", "https://api.orcarouter.ai/v1")


# --------------------------------------------------------------- entry points


def test_every_entry_point_maps_to_a_known_capability():
    assert set(ENTRY_POINTS) == {
        "chat",
        "vision",
        "embedding",
        "image",
        "video",
        "rerank",
    }
    for name, spec in ENTRY_POINTS.items():
        assert spec["capability"] in {
            "chat",
            "embedding",
            "image",
            "video",
            "rerank",
        }, name


def test_the_vision_entry_point_is_chat_narrowed_to_declared_image_input():
    result = entry_point_options(records(), "vision")
    assert "vendor/vision-chat" in result["ids"]
    assert "vendor/text-only" not in result["ids"]
    assert "vendor/audio-chat" not in result["ids"]
    assert result["required_modalities"] == ["image"]


def test_entry_point_options_never_leak_a_credential():
    options = entry_point_options(records(), "chat")
    assert FAKE_KEY not in json.dumps(options)


def test_a_text_model_selected_before_an_image_is_invalidated_by_the_entry_point():
    """The exact sequence the agent takes: text chat, then a screenshot."""
    catalog = ModelCatalog(
        fetcher=FakeCatalogServer(payload=model_payload(*ALL)), origins=_origins()
    )
    catalog.refresh(api_key=FAKE_KEY)
    text = entry_point_options(
        catalog.records, "chat", selected_model="vendor/text-only"
    )
    assert text["selected"] == "vendor/text-only"
    assert text["invalidated"] is False
    vision = entry_point_options(
        catalog.records, "vision", selected_model=text["selected"]
    )
    assert "vendor/text-only" not in vision["ids"]
    assert vision["invalidated"] is True
    assert vision["selected"] is None


def test_an_unknown_entry_point_is_an_error_not_a_default():
    with pytest.raises(OrcaCatalogError):
        entry_point_options(records(), "audio")


def test_model_accepts_reads_the_catalog_and_fails_closed_on_a_stranger():
    catalog = shared_catalog(origins=_origins())
    catalog.refresh  # the shared instance is populated below through the fetcher
    reset_shared_catalog()
    catalog = shared_catalog(origins=_origins(), api_key=FAKE_KEY)
    catalog._fetcher = FakeCatalogServer(payload=model_payload(*ALL))
    catalog._records = None
    assert model_accepts(
        "vendor/vision-chat", "image", origins=_origins(), api_key=FAKE_KEY
    )
    assert not model_accepts(
        "vendor/text-only", "image", origins=_origins(), api_key=FAKE_KEY
    )
    assert not model_accepts(
        "vendor/not-in-catalog", "image", origins=_origins(), api_key=FAKE_KEY
    )
    assert not model_accepts(None, "image", origins=_origins(), api_key=FAKE_KEY)
    reset_shared_catalog()


def test_catalog_options_carries_the_live_status_alongside_the_options():
    reset_shared_catalog()
    catalog = shared_catalog(origins=_origins(), api_key=FAKE_KEY)
    catalog._fetcher = FakeCatalogServer(payload=model_payload(*ALL))
    catalog._records = None
    result = catalog_options(
        api_key=FAKE_KEY, entry_point="chat", origins=_origins(), refresh=True
    )
    assert result["status"]["source"] == "live"
    assert result["ids"]
    assert FAKE_KEY not in json.dumps(result)
    reset_shared_catalog()


def test_the_shared_catalog_is_reused_for_one_origin_and_never_per_selector():
    reset_shared_catalog()
    server = FakeCatalogServer(payload=model_payload(*ALL))
    catalog = shared_catalog(origins=_origins(), api_key=FAKE_KEY)
    catalog._fetcher = server
    catalog._records = None
    first = shared_catalog(origins=_origins(), refresh=True)
    second = shared_catalog(origins=_origins(), refresh=True)
    assert first is second
    assert len(server.calls) == 1
    assert all("orcarouter.ai/v1/models" in url for url, _ in server.calls)
    reset_shared_catalog()
    assert shared_catalog(origins=_origins()) is not first
    reset_shared_catalog()
