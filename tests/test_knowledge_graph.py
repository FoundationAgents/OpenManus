"""Unit tests for the KnowledgeGraph module."""

import json
import tempfile
import unittest
from pathlib import Path

from app.memory.knowledge_graph import GraphEdge, GraphNode, KnowledgeGraph


class TestGraphNode(unittest.TestCase):
    """Test cases for GraphNode model."""
    
    def test_create_graph_node(self):
        """Test creating a graph node."""
        node = GraphNode(
            node_id="node1",
            node_type="concept",
            name="Test Concept",
            content="This is a test concept",
        )
        
        self.assertEqual(node.node_id, "node1")
        self.assertEqual(node.node_type, "concept")
        self.assertEqual(node.name, "Test Concept")
        self.assertEqual(node.content, "This is a test concept")
    
    def test_graph_node_with_metadata(self):
        """Test graph node with metadata."""
        metadata = {
            "source": "test_source",
            "version": 1,
            "tags": ["test", "example"],
        }
        
        node = GraphNode(
            node_id="node2",
            node_type="document",
            name="Test Document",
            metadata=metadata,
        )
        
        self.assertEqual(node.metadata["source"], "test_source")
        self.assertEqual(node.metadata["version"], 1)
        self.assertIn("test", node.metadata["tags"])


class TestGraphEdge(unittest.TestCase):
    """Test cases for GraphEdge model."""
    
    def test_create_graph_edge(self):
        """Test creating a graph edge."""
        edge = GraphEdge(
            source_id="node1",
            target_id="node2",
            edge_type="related_to",
            weight=1.5,
        )
        
        self.assertEqual(edge.source_id, "node1")
        self.assertEqual(edge.target_id, "node2")
        self.assertEqual(edge.edge_type, "related_to")
        self.assertEqual(edge.weight, 1.5)


class TestKnowledgeGraph(unittest.TestCase):
    """Test cases for KnowledgeGraph."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.kg = KnowledgeGraph(storage_path=self.temp_dir, enable_persistence=True)
    
    def tearDown(self):
        """Clean up after tests."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_add_node(self):
        """Test adding a node to the graph."""
        node = self.kg.add_node(
            node_id="concept1",
            node_type="concept",
            name="Test Concept",
            content="Test content",
        )
        
        self.assertEqual(node.node_id, "concept1")
        self.assertEqual(node.node_type, "concept")
        self.assertEqual(node.name, "Test Concept")
    
    def test_get_node(self):
        """Test retrieving a node."""
        self.kg.add_node(
            node_id="concept1",
            node_type="concept",
            name="Test Concept",
        )
        
        node = self.kg.get_node("concept1")
        self.assertIsNotNone(node)
        self.assertEqual(node.name, "Test Concept")
    
    def test_get_nonexistent_node(self):
        """Test retrieving a nonexistent node."""
        node = self.kg.get_node("nonexistent")
        self.assertIsNone(node)
    
    def test_update_node(self):
        """Test updating a node."""
        self.kg.add_node(
            node_id="concept1",
            node_type="concept",
            name="Original Name",
        )
        
        updated_node = self.kg.update_node(
            "concept1",
            name="Updated Name",
            content="New content",
        )
        
        self.assertEqual(updated_node.name, "Updated Name")
        self.assertEqual(updated_node.content, "New content")
        self.assertGreater(updated_node.metadata["version"], 1)
    
    def test_delete_node(self):
        """Test deleting a node."""
        self.kg.add_node(
            node_id="concept1",
            node_type="concept",
            name="Test Concept",
        )
        
        result = self.kg.delete_node("concept1")
        self.assertTrue(result)
        
        retrieved = self.kg.get_node("concept1")
        self.assertIsNone(retrieved)
    
    def test_add_edge(self):
        """Test adding an edge."""
        self.kg.add_node("node1", "concept", "Concept 1")
        self.kg.add_node("node2", "concept", "Concept 2")
        
        edge = self.kg.add_edge("node1", "node2", "related_to", weight=2.0)
        
        self.assertIsNotNone(edge)
        self.assertEqual(edge.source_id, "node1")
        self.assertEqual(edge.target_id, "node2")
        self.assertEqual(edge.edge_type, "related_to")
        self.assertEqual(edge.weight, 2.0)
    
    def test_add_edge_nonexistent_nodes(self):
        """Test adding edge with nonexistent nodes."""
        edge = self.kg.add_edge("nonexistent1", "nonexistent2", "related_to")
        self.assertIsNone(edge)
    
    def test_get_edge(self):
        """Test retrieving an edge."""
        self.kg.add_node("node1", "concept", "Concept 1")
        self.kg.add_node("node2", "concept", "Concept 2")
        self.kg.add_edge("node1", "node2", "related_to")
        
        edge = self.kg.get_edge("node1", "node2")
        self.assertIsNotNone(edge)
        self.assertEqual(edge.edge_type, "related_to")
    
    def test_delete_edge(self):
        """Test deleting an edge."""
        self.kg.add_node("node1", "concept", "Concept 1")
        self.kg.add_node("node2", "concept", "Concept 2")
        self.kg.add_edge("node1", "node2", "related_to")
        
        result = self.kg.delete_edge("node1", "node2")
        self.assertTrue(result)
        
        retrieved = self.kg.get_edge("node1", "node2")
        self.assertIsNone(retrieved)
    
    def test_get_nodes_by_type(self):
        """Test getting nodes by type."""
        self.kg.add_node("node1", "concept", "Concept 1")
        self.kg.add_node("node2", "concept", "Concept 2")
        self.kg.add_node("node3", "document", "Document 1")
        
        concepts = self.kg.get_nodes_by_type("concept")
        self.assertEqual(len(concepts), 2)
        
        documents = self.kg.get_nodes_by_type("document")
        self.assertEqual(len(documents), 1)
    
    def test_get_neighbors(self):
        """Test getting neighbors of a node."""
        self.kg.add_node("node1", "concept", "Concept 1")
        self.kg.add_node("node2", "concept", "Concept 2")
        self.kg.add_node("node3", "concept", "Concept 3")
        self.kg.add_edge("node1", "node2", "related_to")
        self.kg.add_edge("node1", "node3", "depends_on")
        
        neighbors = self.kg.get_neighbors("node1")
        self.assertEqual(len(neighbors), 2)
    
    def test_find_path(self):
        """Test finding a path between nodes."""
        self.kg.add_node("node1", "concept", "Concept 1")
        self.kg.add_node("node2", "concept", "Concept 2")
        self.kg.add_node("node3", "concept", "Concept 3")
        self.kg.add_edge("node1", "node2", "related_to")
        self.kg.add_edge("node2", "node3", "related_to")
        
        path = self.kg.find_path("node1", "node3")
        self.assertIsNotNone(path)
        self.assertEqual(len(path), 3)
    
    def test_find_nonexistent_path(self):
        """Test finding path when no path exists."""
        self.kg.add_node("node1", "concept", "Concept 1")
        self.kg.add_node("node2", "concept", "Concept 2")
        
        path = self.kg.find_path("node1", "node2")
        self.assertIsNone(path)
    
    def test_search_nodes_by_name(self):
        """Test searching nodes by name."""
        self.kg.add_node("node1", "concept", "Machine Learning")
        self.kg.add_node("node2", "concept", "Deep Learning")
        self.kg.add_node("node3", "document", "Python Guide")
        
        results = self.kg.search_nodes("Learning", search_type="name")
        self.assertGreaterEqual(len(results), 2)
    
    def test_search_nodes_by_content(self):
        """Test searching nodes by content."""
        self.kg.add_node("node1", "document", "Test Doc", content="This is about machine learning")
        self.kg.add_node("node2", "document", "Another Doc", content="This is about databases")
        
        results = self.kg.search_nodes("machine", search_type="content")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].node_id, "node1")
    
    def test_export_to_json(self):
        """Test exporting graph to JSON."""
        self.kg.add_node("node1", "concept", "Concept 1")
        self.kg.add_node("node2", "concept", "Concept 2")
        self.kg.add_edge("node1", "node2", "related_to")
        
        export_path = Path(self.temp_dir) / "export.json"
        self.kg.export_to_json(str(export_path))
        
        self.assertTrue(export_path.exists())
        
        with open(export_path, "r") as f:
            data = json.load(f)
        
        self.assertEqual(len(data["nodes"]), 2)
        self.assertEqual(len(data["edges"]), 1)
    
    def test_import_from_json(self):
        """Test importing graph from JSON."""
        export_data = {
            "nodes": [
                {
                    "id": "node1",
                    "type": "concept",
                    "name": "Concept 1",
                    "content": None,
                    "metadata": {},
                    "attributes": {},
                },
                {
                    "id": "node2",
                    "type": "concept",
                    "name": "Concept 2",
                    "content": None,
                    "metadata": {},
                    "attributes": {},
                },
            ],
            "edges": [
                {
                    "source": "node1",
                    "target": "node2",
                    "type": "related_to",
                    "weight": 1.0,
                    "metadata": {},
                },
            ],
            "exported_at": "2024-01-01T00:00:00",
        }
        
        import_path = Path(self.temp_dir) / "import.json"
        with open(import_path, "w") as f:
            json.dump(export_data, f)
        
        kg2 = KnowledgeGraph(storage_path=self.temp_dir + "_import", enable_persistence=True)
        kg2.import_from_json(str(import_path))
        
        node1 = kg2.get_node("node1")
        self.assertIsNotNone(node1)
        self.assertEqual(node1.name, "Concept 1")
        
        edge = kg2.get_edge("node1", "node2")
        self.assertIsNotNone(edge)
    
    def test_export_to_graphml(self):
        """Test exporting graph to GraphML."""
        self.kg.add_node("node1", "concept", "Concept 1")
        self.kg.add_node("node2", "concept", "Concept 2")
        self.kg.add_edge("node1", "node2", "related_to")
        
        export_path = Path(self.temp_dir) / "export.graphml"
        self.kg.export_to_graphml(str(export_path))
        
        self.assertTrue(export_path.exists())
    
    def test_persistence(self):
        """Test that graph is persisted to database."""
        self.kg.add_node("node1", "concept", "Concept 1")
        self.kg.add_node("node2", "concept", "Concept 2")
        self.kg.add_edge("node1", "node2", "related_to")
        
        kg2 = KnowledgeGraph(storage_path=self.temp_dir, enable_persistence=True)
        
        node1 = kg2.get_node("node1")
        self.assertIsNotNone(node1)
        self.assertEqual(node1.name, "Concept 1")
        
        edge = kg2.get_edge("node1", "node2")
        self.assertIsNotNone(edge)
    
    def test_get_statistics(self):
        """Test getting graph statistics."""
        self.kg.add_node("node1", "concept", "Concept 1")
        self.kg.add_node("node2", "concept", "Concept 2")
        self.kg.add_node("node3", "document", "Document 1")
        self.kg.add_edge("node1", "node2", "related_to")
        self.kg.add_edge("node2", "node3", "references")
        
        stats = self.kg.get_statistics()
        
        self.assertEqual(stats["total_nodes"], 3)
        self.assertEqual(stats["total_edges"], 2)
        self.assertIn("concept", stats["nodes_by_type"])
        self.assertIn("document", stats["nodes_by_type"])


if __name__ == "__main__":
    unittest.main()
