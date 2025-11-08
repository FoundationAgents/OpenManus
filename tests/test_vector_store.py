"""Unit tests for the VectorStore module."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from app.memory.vector_store import VectorStore, VectorStoreEntry


class TestVectorStoreEntry(unittest.TestCase):
    """Test cases for VectorStoreEntry model."""
    
    def test_create_entry(self):
        """Test creating a vector store entry."""
        embedding = [0.1] * 10
        entry = VectorStoreEntry(
            entity_id="doc1",
            entity_type="document",
            embedding=embedding,
            text="Test document",
        )
        
        self.assertEqual(entry.entity_id, "doc1")
        self.assertEqual(entry.entity_type, "document")
        self.assertEqual(len(entry.embedding), 10)
        self.assertEqual(entry.text, "Test document")


class TestVectorStore(unittest.TestCase):
    """Test cases for VectorStore."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.vs = VectorStore(
            dimension=128,
            index_type="Flat",
            storage_path=self.temp_dir,
        )
    
    def tearDown(self):
        """Clean up after tests."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_random_embedding(self, dim: int = 128) -> list:
        """Create a random embedding."""
        return np.random.randn(dim).astype(np.float32).tolist()
    
    def test_add_embedding(self):
        """Test adding an embedding."""
        embedding = self._create_random_embedding()
        idx = self.vs.add_embedding(
            entity_id="doc1",
            entity_type="document",
            embedding=embedding,
            text="Test document",
        )
        
        self.assertIsInstance(idx, (int, np.integer))
    
    def test_get_embedding(self):
        """Test retrieving an embedding."""
        embedding = self._create_random_embedding()
        self.vs.add_embedding(
            entity_id="doc1",
            entity_type="document",
            embedding=embedding,
            text="Test document",
        )
        
        entry = self.vs.get_embedding("doc1", "document")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.entity_id, "doc1")
        self.assertEqual(entry.entity_type, "document")
        self.assertEqual(entry.text, "Test document")
    
    def test_get_nonexistent_embedding(self):
        """Test retrieving a nonexistent embedding."""
        entry = self.vs.get_embedding("nonexistent", "document")
        self.assertIsNone(entry)
    
    def test_search_similar(self):
        """Test searching for similar embeddings."""
        embedding1 = np.random.randn(128).astype(np.float32).tolist()
        embedding2 = np.random.randn(128).astype(np.float32).tolist()
        embedding3 = embedding1.copy()
        
        self.vs.add_embedding("doc1", "document", embedding1, "Document 1")
        self.vs.add_embedding("doc2", "document", embedding2, "Document 2")
        self.vs.add_embedding("doc3", "document", embedding3, "Document 3 (similar to 1)")
        
        results = self.vs.search_similar(embedding1, k=2)
        
        self.assertEqual(len(results), 2)
        self.assertIsNotNone(results[0])
    
    def test_delete_embedding(self):
        """Test deleting an embedding."""
        embedding = self._create_random_embedding()
        self.vs.add_embedding("doc1", "document", embedding)
        
        result = self.vs.delete_embedding("doc1", "document")
        self.assertTrue(result)
        
        entry = self.vs.get_embedding("doc1", "document")
        self.assertIsNone(entry)
    
    def test_batch_add_embeddings(self):
        """Test adding embeddings in batch."""
        entries = [
            VectorStoreEntry(
                entity_id=f"doc{i}",
                entity_type="document",
                embedding=self._create_random_embedding(),
                text=f"Document {i}",
            )
            for i in range(5)
        ]
        
        indices = self.vs.batch_add_embeddings(entries)
        
        self.assertEqual(len(indices), 5)
    
    def test_batch_search_similar(self):
        """Test searching for similar embeddings in batch."""
        for i in range(5):
            self.vs.add_embedding(
                entity_id=f"doc{i}",
                entity_type="document",
                embedding=self._create_random_embedding(),
            )
        
        query_embeddings = [self._create_random_embedding() for _ in range(2)]
        results = self.vs.batch_search_similar(query_embeddings, k=3)
        
        self.assertEqual(len(results), 2)
    
    def test_search_by_entity_type(self):
        """Test searching by entity type filter."""
        self.vs.add_embedding("node1", "node", self._create_random_embedding())
        self.vs.add_embedding("doc1", "document", self._create_random_embedding())
        self.vs.add_embedding("doc2", "document", self._create_random_embedding())
        
        query = self._create_random_embedding()
        results = self.vs.search_similar(query, k=10, entity_type="document")
        
        for entity_id, entity_type, distance in results:
            self.assertEqual(entity_type, "document")
    
    def test_persistence(self):
        """Test that embeddings are persisted."""
        embedding = self._create_random_embedding()
        self.vs.add_embedding("doc1", "document", embedding, "Test document")
        
        vs2 = VectorStore(
            dimension=128,
            index_type="Flat",
            storage_path=self.temp_dir,
        )
        
        entry = vs2.get_embedding("doc1", "document")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.text, "Test document")
    
    def test_update_embedding(self):
        """Test updating an embedding."""
        embedding1 = self._create_random_embedding()
        self.vs.add_embedding("doc1", "document", embedding1, "Version 1")
        
        embedding2 = self._create_random_embedding()
        self.vs.add_embedding("doc1", "document", embedding2, "Version 2")
        
        entry = self.vs.get_embedding("doc1", "document")
        self.assertEqual(entry.text, "Version 2")
    
    def test_get_statistics(self):
        """Test getting vector store statistics."""
        for i in range(5):
            self.vs.add_embedding(
                entity_id=f"node{i}",
                entity_type="node",
                embedding=self._create_random_embedding(),
            )
        
        stats = self.vs.get_statistics()
        
        self.assertIn("total_vectors", stats)
        self.assertIn("dimension", stats)
        self.assertEqual(stats["dimension"], 128)


if __name__ == "__main__":
    unittest.main()
