import os
import json
import tempfile
import pytest
from app.memory.agentmemory import AgentMemoryClient


@pytest.fixture
def temp_memory_client(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_memory.db")
        faiss_path = os.path.join(tmpdir, "test_memory.faiss")
        meta_path = os.path.join(tmpdir, "test_memory_vectors.json")

        client = AgentMemoryClient()
        client.enabled_in_config = True
        client.db_path = db_path
        client.settings.vector_backend = "faiss"
        client.settings.vector_index_path = faiss_path
        client.settings.vector_meta_path = meta_path
        client.settings.hybrid_search = True
        client._init_db()

        # Mock embedding function to return deterministic vectors
        def mock_embedding(text: str):
            # Simple pseudo-embedding based on length and characters
            val = float(len(text))
            if "apple" in text.lower():
                return [1.0, 0.0, 0.0, 0.0]
            elif "banana" in text.lower():
                return [0.0, 1.0, 0.0, 0.0]
            elif "region" in text.lower() or "frankfurt" in text.lower() or "eu" in text.lower():
                return [0.0, 0.0, 1.0, 0.0]
            return [val, val, val, val]

        monkeypatch.setattr(client, "_get_embedding", mock_embedding)
        yield client


def test_remember_and_search_hybrid(temp_memory_client):
    client = temp_memory_client
    cid = "conv-1"

    success = client.remember(
        conversation_id=cid,
        title="Server location",
        content="Our primary deployment region is Frankfurt.",
    )
    assert success is True

    # Verify FAISS index file and meta file were created
    assert os.path.exists(client.settings.vector_index_path)
    assert os.path.exists(client.settings.vector_meta_path)

    # Search with query that matches vector similarity (mock returns [0, 0, 1, 0] for 'eu')
    hits = client.search(conversation_id=cid, query="Which EU data center is used?")
    assert len(hits) > 0
    assert "Frankfurt" in hits[0].content


def test_faiss_fallback_on_error(temp_memory_client, monkeypatch):
    client = temp_memory_client
    cid = "conv-2"

    client.remember(
        conversation_id=cid,
        title="Keyword Test",
        content="UniqueWordXYZZY is present in this memory.",
    )

    # Force FAISS index read error
    def failing_read(*args, **kwargs):
        raise RuntimeError("Mock FAISS error")

    import faiss
    monkeypatch.setattr(faiss, "read_index", failing_read)

    hits = client.search(conversation_id=cid, query="UniqueWordXYZZY")
    assert len(hits) > 0
    assert "UniqueWordXYZZY" in hits[0].content
    assert client.last_vector_error is not None


def test_rebuild_vector_index(temp_memory_client):
    client = temp_memory_client
    cid = "conv-3"

    # Insert directly via SQLite to bypass remember vector indexing
    with client._get_conn() as conn:
        conn.execute(
            """
            INSERT INTO memories (conversation_id, project, title, content)
            VALUES (?, ?, ?, ?)
            """,
            (cid, client.project, "Fruit", "Apple is delicious."),
        )
        conn.commit()

    if os.path.exists(client.settings.vector_index_path):
        os.remove(client.settings.vector_index_path)

    count = client.rebuild_vector_index()
    assert count == 1
    assert os.path.exists(client.settings.vector_index_path)


def test_vector_health(temp_memory_client):
    client = temp_memory_client
    health = client.get_vector_health()
    assert health["vector_backend"] == "faiss"
    assert health["vector_live"] is True
