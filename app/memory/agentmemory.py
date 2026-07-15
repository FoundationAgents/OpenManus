from __future__ import annotations

import json
import os
import sqlite3
import threading
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from app.config import config
from app.utils.logger import logger


@dataclass
class MemoryHit:
    title: str
    content: str
    score: float
    memory_id: Optional[int] = None


class AgentMemoryClient:
    """Robust local SQLite + FAISS AgentMemory implementation."""

    def __init__(self) -> None:
        self.settings = config.agentmemory
        self.enabled_in_config = self.settings.enabled
        self.project = self.settings.project
        self.db_path = "/app/workspace/agentmemory.db"
        self._vector_lock = threading.Lock()
        self.last_vector_error: Optional[str] = None
        self._init_db()

    @property
    def enabled(self) -> bool:
        return bool(self.enabled_in_config)

    def _get_conn(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        if not self.enabled:
            return
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT NOT NULL,
                        project TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        concepts TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                try:
                    conn.execute(
                        """
                        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                            title, content, tokenize="unicode61"
                        )
                    """
                    )
                    conn.execute(
                        """
                        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                            INSERT INTO memories_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
                        END
                    """
                    )
                    conn.execute(
                        """
                        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                            INSERT INTO memories_fts(memories_fts, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
                        END
                    """
                    )
                    conn.execute(
                        """
                        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                            INSERT INTO memories_fts(memories_fts, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
                            INSERT INTO memories_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
                        END
                    """
                    )
                except Exception as fts_exc:
                    logger.warning(
                        f"SQLite FTS5 not available, falling back to substring matching: {fts_exc}"
                    )
        except Exception as exc:
            logger.error(f"Failed to initialize local AgentMemory DB: {exc}")

    def _get_embedding(self, text: str) -> list[float]:
        base_url = getattr(self.settings, "embedding_base_url", "").strip()
        api_key = getattr(self.settings, "embedding_api_key", "").strip()

        if not base_url or not api_key:
            default_llm = (
                config.llm.get("default") if isinstance(config.llm, dict) else None
            )
            if not base_url:
                base_url = (
                    getattr(default_llm, "base_url", "http://localhost:1234/v1")
                    if default_llm
                    else "http://localhost:1234/v1"
                )
            if not api_key:
                api_key = (
                    getattr(default_llm, "api_key", "lm-studio")
                    if default_llm
                    else "lm-studio"
                )

        url = base_url.rstrip("/") + "/embeddings"
        model = getattr(
            self.settings, "embedding_model", "text-embedding-nomic-embed-text-v1.5"
        )
        payload = {
            "model": model,
            "input": text[:8000],
        }
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(
            req, timeout=getattr(self.settings, "timeout_seconds", 8)
        ) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            data = res.get("data", [])
            if not data or "embedding" not in data[0]:
                raise ValueError("Invalid embeddings response format")
            return [float(x) for x in data[0]["embedding"]]

    def _index_memory_vector(
        self, memory_id: int, title: str, content: str, conversation_id: str
    ) -> bool:
        if getattr(self.settings, "vector_backend", "none") != "faiss":
            return False
        try:
            import faiss
            import numpy as np
        except ImportError as exc:
            self.last_vector_error = f"Missing FAISS or numpy: {exc}"
            logger.warning(self.last_vector_error)
            return False

        try:
            vec = self._get_embedding(f"{title}\n{content}")
            arr = np.array([vec], dtype=np.float32)
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm

            with self._vector_lock:
                index_path = self.settings.vector_index_path
                os.makedirs(os.path.dirname(index_path), exist_ok=True)
                if os.path.exists(index_path):
                    index = faiss.read_index(index_path)
                else:
                    dim = arr.shape[1]
                    index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))

                ids = np.array([memory_id], dtype=np.int64)
                try:
                    index.remove_ids(np.array([memory_id], dtype=np.int64))
                except Exception:
                    pass
                index.add_with_ids(arr, ids)
                faiss.write_index(index, index_path)

                meta_path = self.settings.vector_meta_path
                meta = {}
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                    except Exception:
                        meta = {}
                meta[str(memory_id)] = {
                    "memory_id": int(memory_id),
                    "conversation_id": conversation_id,
                    "project": self.project,
                    "title": title,
                    "content": content,
                }
                os.makedirs(os.path.dirname(meta_path), exist_ok=True)
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
            self.last_vector_error = None
            return True
        except Exception as exc:
            self.last_vector_error = str(exc)
            logger.warning(f"Failed to index memory vector for id={memory_id}: {exc}")
            return False

    def remember(
        self,
        *,
        conversation_id: str,
        content: str,
        title: str = "OpenManus memory",
        concepts: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        if not self.enabled or not content.strip():
            return False

        memory_id: Optional[int] = None
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO memories (conversation_id, project, title, content, concepts, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        conversation_id,
                        self.project,
                        title,
                        content,
                        json.dumps(concepts or []),
                        json.dumps(metadata or {}),
                    ),
                )
                conn.commit()
                memory_id = cursor.lastrowid
        except Exception as exc:
            logger.error(f"Local AgentMemory remember failed: {exc}")
            return False

        if (
            getattr(self.settings, "vector_backend", "none") == "faiss"
            and memory_id is not None
        ):
            self._index_memory_vector(
                memory_id=int(memory_id),
                title=title,
                content=content,
                conversation_id=conversation_id,
            )
        return True

    def search(
        self,
        *,
        conversation_id: str,
        query: str,
        limit: Optional[int] = None,
    ) -> list[MemoryHit]:
        if not self.enabled or not query.strip():
            return []

        limit_val = int(limit or self.settings.top_k)
        kw_hits: dict[int, MemoryHit] = {}

        try:
            with self._get_conn() as conn:
                try:
                    sanitized_words = [
                        f'"{word}"' for word in query.split() if len(word) > 1
                    ]
                    if not sanitized_words:
                        sanitized_words = [f'"{query}"']
                    sanitized_query = " OR ".join(sanitized_words)

                    cursor = conn.execute(
                        """
                        SELECT m.id, m.title, m.content, bm25(memories_fts) as score
                        FROM memories m
                        JOIN memories_fts f ON m.id = f.rowid
                        WHERE m.conversation_id = ? AND m.project = ? AND memories_fts MATCH ?
                        ORDER BY score ASC
                        LIMIT ?
                        """,
                        (conversation_id, self.project, sanitized_query, limit_val * 2),
                    )
                    rows = cursor.fetchall()
                    for row in rows:
                        score = abs(float(row["score"]))
                        mid = int(row["id"])
                        kw_hits[mid] = MemoryHit(
                            title=row["title"],
                            content=row["content"],
                            score=score,
                            memory_id=mid,
                        )
                except Exception as fts_err:
                    logger.debug(f"FTS5 search query failed, using fallback: {fts_err}")
                    words = [w.lower() for w in query.split() if len(w) > 1]
                    if not words:
                        words = [query.lower()]

                    cursor = conn.execute(
                        """
                        SELECT id, title, content
                        FROM memories
                        WHERE conversation_id = ? AND project = ?
                        """,
                        (conversation_id, self.project),
                    )
                    rows = cursor.fetchall()

                    scored_rows = []
                    for row in rows:
                        title_lower = row["title"].lower()
                        content_lower = row["content"].lower()
                        score = 0.0
                        for word in words:
                            if word in title_lower:
                                score += 2.0
                            if word in content_lower:
                                score += 1.0
                        if score > 0:
                            scored_rows.append(
                                (int(row["id"]), row["title"], row["content"], score)
                            )

                    scored_rows.sort(key=lambda x: x[3], reverse=True)
                    for r_id, r_title, r_content, r_score in scored_rows[
                        : limit_val * 2
                    ]:
                        kw_hits[r_id] = MemoryHit(
                            title=r_title,
                            content=r_content,
                            score=r_score,
                            memory_id=r_id,
                        )
        except Exception as exc:
            logger.error(f"Local AgentMemory search failed: {exc}")

        if getattr(self.settings, "vector_backend", "none") != "faiss":
            hits = list(kw_hits.values())
            hits.sort(key=lambda h: h.score, reverse=True)
            return hits[:limit_val]

        vec_hits: dict[int, tuple[str, str, float]] = {}
        try:
            import faiss
            import numpy as np

            index_path = self.settings.vector_index_path
            meta_path = self.settings.vector_meta_path
            if os.path.exists(index_path) and os.path.exists(meta_path):
                with self._vector_lock:
                    index = faiss.read_index(index_path)
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta_dict = json.load(f)

                if index.ntotal > 0:
                    q_vec = self._get_embedding(query)
                    arr = np.array([q_vec], dtype=np.float32)
                    norm = np.linalg.norm(arr)
                    if norm > 0:
                        arr = arr / norm

                    k_search = min(int(index.ntotal), max(limit_val * 10, 50))
                    distances, ids = index.search(arr, k_search)
                    for dist, mid in zip(distances[0], ids[0]):
                        mid_int = int(mid)
                        if mid_int < 0:
                            continue
                        meta = meta_dict.get(str(mid_int))
                        if not meta:
                            continue
                        if str(meta.get("conversation_id")) == str(
                            conversation_id
                        ) and str(meta.get("project")) == str(self.project):
                            vec_hits[mid_int] = (
                                meta.get("title", ""),
                                meta.get("content", ""),
                                float(dist),
                            )
            self.last_vector_error = None
        except Exception as exc:
            self.last_vector_error = str(exc)
            logger.warning(f"FAISS vector search failed, falling back to SQLite: {exc}")
            hits = list(kw_hits.values())
            hits.sort(key=lambda h: h.score, reverse=True)
            return hits[:limit_val]

        all_ids = set(kw_hits.keys()) | set(vec_hits.keys())
        if not all_ids:
            return []

        max_kw = max([h.score for h in kw_hits.values()] + [1e-6])
        hybrid_enabled = getattr(self.settings, "hybrid_search", True)
        kw_w = getattr(self.settings, "keyword_weight", 0.35)
        vec_w = getattr(self.settings, "vector_weight", 0.65)

        merged: list[MemoryHit] = []
        for mid in all_ids:
            kw_hit = kw_hits.get(mid)
            vec_hit = vec_hits.get(mid)

            title = kw_hit.title if kw_hit else (vec_hit[0] if vec_hit else "")
            content = kw_hit.content if kw_hit else (vec_hit[1] if vec_hit else "")

            norm_kw = (kw_hit.score / max_kw) if kw_hit else 0.0
            norm_vec = max(0.0, vec_hit[2]) if vec_hit else 0.0

            if hybrid_enabled:
                combined_score = kw_w * norm_kw + vec_w * norm_vec
            else:
                combined_score = norm_vec if vec_hit else norm_kw

            merged.append(
                MemoryHit(
                    title=title, content=content, score=combined_score, memory_id=mid
                )
            )

        merged.sort(key=lambda h: h.score, reverse=True)
        return merged[:limit_val]

    def rebuild_vector_index(self) -> int:
        if getattr(self.settings, "vector_backend", "none") != "faiss":
            return 0
        try:
            import faiss
            import numpy as np
        except ImportError as exc:
            self.last_vector_error = str(exc)
            logger.warning(f"Missing dependencies for rebuild_vector_index: {exc}")
            return 0

        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, conversation_id, project, title, content
                    FROM memories
                    """
                )
                rows = cursor.fetchall()
        except Exception as exc:
            logger.error(f"Failed to fetch memories for vector index rebuild: {exc}")
            return 0

        if not rows:
            with self._vector_lock:
                index_path = self.settings.vector_index_path
                meta_path = self.settings.vector_meta_path
                if os.path.exists(index_path):
                    try:
                        os.remove(index_path)
                    except Exception:
                        pass
                if os.path.exists(meta_path):
                    try:
                        os.remove(meta_path)
                    except Exception:
                        pass
            return 0

        embeddings = []
        ids = []
        meta_dict = {}

        for row in rows:
            mid = int(row["id"])
            title = row["title"]
            content = row["content"]
            cid = row["conversation_id"]
            proj = row["project"]
            try:
                vec = self._get_embedding(f"{title}\n{content}")
                arr = np.array(vec, dtype=np.float32)
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
                embeddings.append(arr)
                ids.append(mid)
                meta_dict[str(mid)] = {
                    "memory_id": mid,
                    "conversation_id": cid,
                    "project": proj,
                    "title": title,
                    "content": content,
                }
            except Exception as exc:
                logger.warning(
                    f"Failed embedding for memory id={mid} during rebuild: {exc}"
                )

        if not embeddings:
            return 0

        emb_matrix = np.array(embeddings, dtype=np.float32)
        id_array = np.array(ids, dtype=np.int64)
        dim = emb_matrix.shape[1]

        with self._vector_lock:
            index_path = self.settings.vector_index_path
            meta_path = self.settings.vector_meta_path
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            os.makedirs(os.path.dirname(meta_path), exist_ok=True)

            base_index = faiss.IndexFlatIP(dim)
            index = faiss.IndexIDMap(base_index)
            index.add_with_ids(emb_matrix, id_array)
            faiss.write_index(index, index_path)

            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta_dict, f, ensure_ascii=False, indent=2)

        self.last_vector_error = None
        return len(ids)

    def get_vector_health(self) -> dict[str, Any]:
        backend = getattr(self.settings, "vector_backend", "none")
        provider = getattr(self.settings, "embedding_provider", "openai_compatible")
        res = {
            "vector_backend": backend,
            "embedding_provider": provider,
            "vector_live": False,
            "vector_count": 0,
            "last_vector_error": getattr(self, "last_vector_error", None),
        }
        if not self.enabled or backend != "faiss":
            return res
        try:
            import faiss

            index_path = self.settings.vector_index_path
            if os.path.exists(index_path):
                with self._vector_lock:
                    index = faiss.read_index(index_path)
                    res["vector_count"] = int(index.ntotal)
                res["vector_live"] = True
            else:
                res["vector_count"] = 0
                res["vector_live"] = True
        except Exception as exc:
            res["vector_live"] = False
            res["last_vector_error"] = str(exc)
        return res

    def format_context(
        self,
        *,
        conversation_id: str,
        query: str,
        limit: Optional[int] = None,
    ) -> str:
        hits = self.search(conversation_id=conversation_id, query=query, limit=limit)
        if not hits:
            return ""
        lines = [
            "AgentMemory recall context:",
            "- Relevant long-term memory snippets for this conversation:",
        ]
        for idx, hit in enumerate(hits, start=1):
            lines.append(
                f"  {idx}. {hit.title} (score={hit.score:.3f}): {hit.content[:700]}"
            )
        return "\n".join(lines)


agentmemory = AgentMemoryClient()
