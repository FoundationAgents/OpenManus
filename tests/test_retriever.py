"""Unit tests for the hybrid retriever system."""

import asyncio
import time
import unittest
from typing import List

from app.memory import (
    HybridRetriever,
    KnowledgeGraph,
    GraphNode,
    GraphEdge,
    NodeType,
    EdgeType,
    VectorStore,
    Document,
    MockEmbeddingProvider,
    RetrievalStrategy,
    get_retriever_service
)


class TestVectorStore(unittest.TestCase):
    """Test cases for vector store."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.provider = MockEmbeddingProvider()
        self.store = VectorStore(embedding_dim=768)
    
    def test_add_document(self):
        """Test adding documents."""
        text = "Machine learning is great"
        embedding = self.provider.embed_text(text)
        doc = Document(id="doc1", content=text, embedding=embedding)
        
        self.store.add_document(doc)
        self.assertEqual(self.store.size(), 1)
        self.assertEqual(self.store.get_document("doc1"), doc)
    
    def test_remove_document(self):
        """Test removing documents."""
        embedding = self.provider.embed_text("test")
        doc = Document(id="doc1", content="test", embedding=embedding)
        
        self.store.add_document(doc)
        self.assertTrue(self.store.remove_document("doc1"))
        self.assertEqual(self.store.size(), 0)
        self.assertFalse(self.store.remove_document("doc1"))
    
    def test_search(self):
        """Test vector search."""
        docs = [
            ("machine learning", "Machine learning is a subset of AI"),
            ("deep learning", "Deep learning uses neural networks"),
            ("natural language", "NLP processes text data"),
        ]
        
        for doc_id, content in docs:
            embedding = self.provider.embed_text(content)
            doc = Document(id=doc_id, content=content, embedding=embedding)
            self.store.add_document(doc)
        
        # Search for similar content with lower threshold
        query_embedding = self.provider.embed_text("artificial intelligence and ML")
        results = self.store.search(query_embedding, top_k=2, threshold=0.0)
        
        self.assertGreater(len(results), 0)
        # Results should be sorted by similarity
        self.assertEqual(len(results), min(2, self.store.size()))
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        vec3 = [0.0, 1.0, 0.0]
        
        # Same vectors should have similarity 1.0
        sim = VectorStore._cosine_similarity(vec1, vec2)
        self.assertAlmostEqual(sim, 1.0, places=5)
        
        # Orthogonal vectors should have similarity 0.0
        sim = VectorStore._cosine_similarity(vec1, vec3)
        self.assertAlmostEqual(sim, 0.0, places=5)


class TestKnowledgeGraph(unittest.TestCase):
    """Test cases for knowledge graph."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.graph = KnowledgeGraph()
    
    def test_add_node(self):
        """Test adding nodes."""
        node = GraphNode(
            id="n1",
            node_type=NodeType.CONCEPT,
            content="Machine Learning"
        )
        
        self.graph.add_node(node)
        self.assertEqual(self.graph.size()[0], 1)
        self.assertEqual(self.graph.get_node("n1"), node)
    
    def test_remove_node(self):
        """Test removing nodes."""
        node = GraphNode(id="n1", node_type=NodeType.CONCEPT, content="ML")
        
        self.graph.add_node(node)
        self.assertTrue(self.graph.remove_node("n1"))
        self.assertEqual(self.graph.size()[0], 0)
    
    def test_add_edge(self):
        """Test adding edges."""
        n1 = GraphNode(id="n1", node_type=NodeType.CONCEPT, content="ML")
        n2 = GraphNode(id="n2", node_type=NodeType.CONCEPT, content="AI")
        
        self.graph.add_node(n1)
        self.graph.add_node(n2)
        
        edge = GraphEdge(
            source_id="n1",
            target_id="n2",
            edge_type=EdgeType.RELATED_TO
        )
        self.graph.add_edge(edge)
        
        self.assertEqual(self.graph.size()[1], 1)
        self.assertIn("n2", self.graph.adjacency_list["n1"])
    
    def test_get_neighbors(self):
        """Test getting neighbors."""
        n1 = GraphNode(id="n1", node_type=NodeType.CONCEPT, content="ML")
        n2 = GraphNode(id="n2", node_type=NodeType.CONCEPT, content="AI")
        n3 = GraphNode(id="n3", node_type=NodeType.CONCEPT, content="DL")
        
        self.graph.add_node(n1)
        self.graph.add_node(n2)
        self.graph.add_node(n3)
        
        self.graph.add_edge(GraphEdge("n1", "n2", EdgeType.RELATED_TO))
        self.graph.add_edge(GraphEdge("n1", "n3", EdgeType.RELATED_TO))
        
        neighbors = self.graph.get_neighbors("n1")
        self.assertEqual(len(neighbors), 2)
    
    def test_bfs_traversal(self):
        """Test BFS traversal."""
        # Create chain: n1 -> n2 -> n3 -> n4
        for i in range(1, 5):
            node = GraphNode(
                id=f"n{i}",
                node_type=NodeType.CONCEPT,
                content=f"Concept {i}"
            )
            self.graph.add_node(node)
        
        for i in range(1, 4):
            self.graph.add_edge(
                GraphEdge(f"n{i}", f"n{i+1}", EdgeType.RELATED_TO)
            )
        
        # BFS from n1 with max_depth=2
        traversed = self.graph.bfs_traversal("n1", max_depth=2)
        
        # Should get n1, n2, n3
        self.assertGreaterEqual(len(traversed), 2)
    
    def test_find_path(self):
        """Test path finding."""
        # Create graph: n1 -> n2 -> n3
        #               n1 -> n4
        for i in range(1, 5):
            node = GraphNode(id=f"n{i}", node_type=NodeType.CONCEPT, content=f"C{i}")
            self.graph.add_node(node)
        
        self.graph.add_edge(GraphEdge("n1", "n2", EdgeType.RELATED_TO))
        self.graph.add_edge(GraphEdge("n2", "n3", EdgeType.RELATED_TO))
        self.graph.add_edge(GraphEdge("n1", "n4", EdgeType.RELATED_TO))
        
        path = self.graph.find_path("n1", "n3")
        self.assertIsNotNone(path)
        self.assertEqual(path[0], "n1")
        self.assertEqual(path[-1], "n3")


class TestHybridRetriever(unittest.TestCase):
    """Test cases for hybrid retriever."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.retriever = HybridRetriever()
        self.provider = MockEmbeddingProvider()
    
    def test_ingest_document(self):
        """Test document ingestion."""
        self.retriever.ingest_document(
            doc_id="doc1",
            content="Machine learning basics",
            metadata={"topic": "ML"}
        )
        
        self.assertEqual(self.retriever.vector_store.size(), 1)
        self.assertEqual(self.retriever.graph.size()[0], 1)
    
    def test_retrieve_basic(self):
        """Test basic retrieval."""
        docs = [
            ("doc1", "Machine learning is great"),
            ("doc2", "Deep learning uses neural networks"),
            ("doc3", "Python is a programming language"),
        ]
        
        for doc_id, content in docs:
            self.retriever.ingest_document(doc_id, content)
        
        context = self.retriever.retrieve("machine learning")
        
        self.assertGreater(len(context.results), 0)
        self.assertGreater(context.results[0].score, 0)
    
    def test_caching(self):
        """Test retrieval caching."""
        self.retriever.ingest_document("doc1", "test content")
        
        # First retrieval
        context1 = self.retriever.retrieve("test")
        time1 = context1.total_time
        
        # Second retrieval (should be cached)
        context2 = self.retriever.retrieve("test")
        time2 = context2.total_time
        
        # Cached retrieval should be faster
        self.assertLessEqual(time2, time1)
    
    def test_iterative_retrieval(self):
        """Test iterative retrieval with refinement."""
        docs = [
            ("doc1", "Machine learning is a subset of AI"),
            ("doc2", "Deep learning uses neural networks"),
            ("doc3", "Neural networks are inspired by biology"),
            ("doc4", "Biological systems are complex"),
        ]
        
        for doc_id, content in docs:
            self.retriever.ingest_document(doc_id, content)
        
        contexts = self.retriever.retrieve_iterative(
            "machine learning",
            max_iterations=2
        )
        
        self.assertGreater(len(contexts), 0)
    
    def test_add_relationship(self):
        """Test adding relationships."""
        self.retriever.ingest_document("doc1", "Machine Learning")
        self.retriever.ingest_document("doc2", "Neural Networks")
        
        self.retriever.add_context_relationship(
            "doc1",
            "doc2",
            EdgeType.RELATED_TO,
            weight=0.8
        )
        
        # Check edge was added
        edges = self.retriever.graph.edges
        self.assertEqual(len(edges), 1)
    
    def test_retrieval_strategies(self):
        """Test different retrieval strategies."""
        docs = [
            ("doc1", "Machine learning"),
            ("doc2", "Deep learning"),
            ("doc3", "Neural networks"),
        ]
        
        for doc_id, content in docs:
            self.retriever.ingest_document(doc_id, content)
        
        strategies = [
            RetrievalStrategy.GRAPH_FIRST,
            RetrievalStrategy.VECTOR_FIRST,
            RetrievalStrategy.BALANCED,
            RetrievalStrategy.ADAPTIVE
        ]
        
        for strategy in strategies:
            context = self.retriever.retrieve(
                "learning networks",
                strategy=strategy
            )
            self.assertIsNotNone(context)
            self.assertEqual(context.strategy_used, strategy.value)


class TestRetrieverService(unittest.TestCase):
    """Test cases for retriever service."""
    
    def test_singleton(self):
        """Test that service is a singleton."""
        service1 = get_retriever_service()
        service2 = get_retriever_service()
        
        self.assertIs(service1, service2)
    
    def test_retrieve_with_service(self):
        """Test retrieval through service."""
        service = get_retriever_service()
        
        # Clear previous state
        service.clear_all()
        
        # Ingest document
        service.ingest_document("doc1", "Test content")
        
        # Retrieve
        context = service.retrieve("agent1", "test")
        
        self.assertGreater(len(context.results), 0)
    
    def test_agent_preferences(self):
        """Test agent preferences."""
        service = get_retriever_service()
        service.clear_all()
        
        prefs = {"retrieval_strategy": "vector_first"}
        service.set_agent_preferences("agent1", prefs)
        
        self.assertEqual(service.agent_preferences["agent1"], prefs)
    
    def test_session_context(self):
        """Test session context management."""
        service = get_retriever_service()
        service.clear_all()
        
        service.ingest_document("doc1", "content")
        service.retrieve("agent1", "content")
        
        contexts = service.get_session_contexts("agent1")
        self.assertGreater(len(contexts), 0)
    
    def test_clear_operations(self):
        """Test clear operations."""
        service = get_retriever_service()
        
        service.ingest_document("doc1", "content")
        service.retrieve("agent1", "content")
        
        # Clear agent session
        service.clear_session("agent1")
        contexts = service.get_session_contexts("agent1")
        self.assertEqual(len(contexts), 0)
        
        # Clear all
        service.clear_all()
        stats = service.get_stats()
        self.assertEqual(stats["vector_documents"], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for the retrieval system."""
    
    def test_hybrid_retrieval_workflow(self):
        """Test a complete hybrid retrieval workflow."""
        retriever = HybridRetriever()
        
        # Ingest knowledge base
        knowledge_base = [
            ("concept_ml", "Machine Learning - algorithms that learn from data"),
            ("concept_dl", "Deep Learning - multiple layers of neural networks"),
            ("concept_nn", "Neural Networks - inspired by biological neurons"),
            ("tool_pytorch", "PyTorch - framework for deep learning"),
            ("tool_sklearn", "Scikit-learn - machine learning library"),
            ("task_classification", "Classification - predicting discrete categories"),
        ]
        
        for doc_id, content in knowledge_base:
            retriever.ingest_document(doc_id, content)
        
        # Add relationships
        retriever.add_context_relationship(
            "concept_ml", "concept_dl", EdgeType.CONTAINS, weight=0.9
        )
        retriever.add_context_relationship(
            "concept_dl", "concept_nn", EdgeType.IMPLEMENTS, weight=0.8
        )
        retriever.add_context_relationship(
            "concept_ml", "tool_sklearn", EdgeType.PRODUCES, weight=0.7
        )
        
        # Retrieve with different strategies
        contexts = []
        for strategy in RetrievalStrategy:
            context = retriever.retrieve(
                "neural networks for classification",
                top_k=3,
                strategy=strategy
            )
            contexts.append(context)
            self.assertGreater(len(context.results), 0)
        
        # Verify we got results
        total_results = sum(len(c.results) for c in contexts)
        self.assertGreater(total_results, 0)
    
    def test_retrieval_with_agent_scenario(self):
        """Test retrieval in a simulated agent scenario."""
        service = get_retriever_service()
        service.clear_all()
        
        # Simulate developer documentation
        docs = [
            ("api_rest", "REST API best practices and design patterns"),
            ("api_graphql", "GraphQL query language and advantages"),
            ("db_sql", "SQL database fundamentals and optimization"),
            ("db_nosql", "NoSQL databases for scalable applications"),
            ("arch_microservices", "Microservices architecture patterns"),
        ]
        
        for doc_id, content in docs:
            service.ingest_document(doc_id, content)
        
        # Agent queries
        agent_queries = [
            ("developer1", "What's the best approach for building APIs?"),
            ("architect1", "How should I design scalable systems?"),
            ("devops1", "What database solutions are available?"),
        ]
        
        for agent_id, query in agent_queries:
            context = service.retrieve(agent_id, query)
            self.assertGreater(len(context.results), 0)
        
        # Verify agent contexts are separate
        contexts_dev = service.get_session_contexts("developer1")
        contexts_arch = service.get_session_contexts("architect1")
        
        self.assertNotEqual(len(contexts_dev), 0)
        self.assertNotEqual(len(contexts_arch), 0)


if __name__ == "__main__":
    unittest.main()
