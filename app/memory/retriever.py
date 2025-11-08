"""Hybrid retriever combining graph traversal and vector similarity search."""

import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field

from app.logger import logger
from app.memory.graph import KnowledgeGraph, GraphNode, NodeType, EdgeType
from app.memory.vector_store import VectorStore, Document, EmbeddingProvider, MockEmbeddingProvider
from app.memory.cache import RetrievalCache, EmbeddingCache


class RetrievalStrategy(str, Enum):
    """Strategies for merging graph and vector results."""
    GRAPH_FIRST = "graph_first"  # Prioritize graph results
    VECTOR_FIRST = "vector_first"  # Prioritize vector results
    BALANCED = "balanced"  # Equal weight
    ADAPTIVE = "adaptive"  # Adapt based on query characteristics


@dataclass
class RetrievalResult:
    """Single retrieved item with scoring information."""
    node_id: str
    content: str
    source: Optional[str]
    score: float  # Composite score [0, 1]
    graph_score: float = 0.0  # Graph traversal score
    vector_score: float = 0.0  # Vector similarity score
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "content": self.content,
            "source": self.source,
            "score": self.score,
            "graph_score": self.graph_score,
            "vector_score": self.vector_score,
            "metadata": self.metadata
        }


@dataclass
class RetrievalContext:
    """Context bundle returned from retrieval."""
    query: str
    results: List[RetrievalResult]
    total_time: float = 0.0
    strategy_used: str = ""
    graph_nodes_searched: int = 0
    documents_searched: int = 0
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_time": self.total_time,
            "strategy_used": self.strategy_used,
            "graph_nodes_searched": self.graph_nodes_searched,
            "documents_searched": self.documents_searched,
            "metadata": self.metadata
        }


class HybridRetriever(BaseModel):
    """Hybrid retriever combining graph and vector search."""
    
    graph: KnowledgeGraph = Field(default_factory=KnowledgeGraph)
    vector_store: VectorStore = Field(default_factory=VectorStore)
    embedding_provider: EmbeddingProvider = Field(
        default_factory=MockEmbeddingProvider
    )
    cache: RetrievalCache = Field(default_factory=RetrievalCache)
    embedding_cache: EmbeddingCache = Field(default_factory=EmbeddingCache)
    
    strategy: RetrievalStrategy = Field(
        default=RetrievalStrategy.BALANCED,
        description="Default retrieval strategy"
    )
    graph_weight: float = Field(default=0.5, description="Weight for graph results [0, 1]")
    vector_weight: float = Field(default=0.5, description="Weight for vector results [0, 1]")
    
    max_graph_depth: int = Field(default=3, description="Max depth for graph traversal")
    max_results: int = Field(default=10, description="Max results to return")
    similarity_threshold: float = Field(
        default=0.3,
        description="Minimum similarity score [0, 1]"
    )
    
    class Config:
        arbitrary_types_allowed = True
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        strategy: Optional[RetrievalStrategy] = None,
        refine_query: bool = False
    ) -> RetrievalContext:
        """
        Retrieve contextual knowledge using hybrid approach.
        
        Args:
            query: Search query
            top_k: Number of results to return (uses max_results if None)
            strategy: Retrieval strategy (uses default if None)
            refine_query: Whether to refine the query for recursive search
        
        Returns:
            RetrievalContext with merged results
        """
        import time
        start_time = time.time()
        
        top_k = top_k or self.max_results
        strategy = strategy or self.strategy
        
        # Check cache first
        cache_key = self._cache_key(query, top_k, strategy)
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for query: {query}")
            return cached_result
        
        # Get query embedding
        query_embedding = self._get_query_embedding(query)
        
        # Perform retrieval based on strategy
        if strategy == RetrievalStrategy.GRAPH_FIRST:
            results = self._retrieve_graph_first(query, query_embedding, top_k)
        elif strategy == RetrievalStrategy.VECTOR_FIRST:
            results = self._retrieve_vector_first(query, query_embedding, top_k)
        elif strategy == RetrievalStrategy.ADAPTIVE:
            results = self._retrieve_adaptive(query, query_embedding, top_k)
        else:  # BALANCED
            results = self._retrieve_balanced(query, query_embedding, top_k)
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:top_k]
        
        elapsed_time = time.time() - start_time
        
        # Create context
        context = RetrievalContext(
            query=query,
            results=results,
            total_time=elapsed_time,
            strategy_used=strategy.value,
            graph_nodes_searched=self.graph.size()[0],
            documents_searched=self.vector_store.size(),
            metadata={
                "embedding_dim": self.embedding_provider.embedding_dim,
                "similarity_threshold": self.similarity_threshold
            }
        )
        
        # Cache the result
        self.cache.put(cache_key, context, ttl=3600)
        
        logger.info(
            f"Retrieved {len(results)} results for query '{query}' "
            f"using {strategy.value} strategy in {elapsed_time:.2f}s"
        )
        
        return context
    
    def retrieve_iterative(
        self,
        initial_query: str,
        max_iterations: int = 3,
        strategy: Optional[RetrievalStrategy] = None
    ) -> List[RetrievalContext]:
        """
        Iteratively refine queries based on prior results.
        
        Args:
            initial_query: Initial search query
            max_iterations: Maximum refinement iterations
            strategy: Retrieval strategy
        
        Returns:
            List of retrieval contexts from each iteration
        """
        contexts = []
        current_query = initial_query
        
        for i in range(max_iterations):
            logger.debug(f"Iteration {i+1}/{max_iterations}: query='{current_query}'")
            
            context = self.retrieve(
                current_query,
                strategy=strategy,
                refine_query=i > 0
            )
            contexts.append(context)
            
            # If no results, stop
            if not context.results:
                logger.debug("No results found, stopping iteration")
                break
            
            # Refine query based on best result
            top_result = context.results[0]
            refined_query = self._refine_query(current_query, top_result)
            
            if refined_query == current_query:
                logger.debug("Query refinement converged, stopping iteration")
                break
            
            current_query = refined_query
        
        return contexts
    
    def ingest_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict] = None,
        source: Optional[str] = None
    ) -> None:
        """
        Ingest a document into both graph and vector store.
        
        Args:
            doc_id: Unique document ID
            content: Document content
            metadata: Optional metadata
            source: Optional source identifier
        """
        metadata = metadata or {}
        
        # Create graph node
        graph_node = GraphNode(
            id=doc_id,
            node_type=NodeType.DOCUMENT,
            content=content,
            metadata=metadata
        )
        self.graph.add_node(graph_node)
        
        # Get embedding and store in vector store
        embedding = self._get_query_embedding(content)
        doc = Document(
            id=doc_id,
            content=content,
            embedding=embedding,
            metadata=metadata,
            source=source
        )
        self.vector_store.add_document(doc)
        
        logger.debug(f"Ingested document {doc_id}")
    
    def ingest_batch(
        self,
        documents: List[Tuple[str, str, Optional[Dict]]],
        source: Optional[str] = None
    ) -> None:
        """
        Ingest multiple documents.
        
        Args:
            documents: List of (doc_id, content, metadata) tuples
            source: Optional common source
        """
        for doc_id, content, metadata in documents:
            self.ingest_document(doc_id, content, metadata, source)
    
    def add_context_relationship(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        weight: float = 1.0
    ) -> None:
        """
        Add a relationship between entities in the graph.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            edge_type: Type of relationship
            weight: Edge weight (importance)
        """
        from app.memory.graph import GraphEdge
        
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight
        )
        self.graph.add_edge(edge)
        logger.debug(f"Added edge: {source_id} -{edge_type.value}-> {target_id}")
    
    def update_from_context(
        self,
        context: RetrievalContext,
        auto_ingest: bool = False
    ) -> None:
        """
        Update graph/vector store based on retrieval context.
        
        Args:
            context: Retrieval context to learn from
            auto_ingest: Whether to auto-ingest new nodes
        """
        for result in context.results:
            # Update node weights based on retrieval scores
            node = self.graph.get_node(result.node_id)
            if node:
                # Increase weight based on retrieval score
                node.weight = min(2.0, node.weight + (result.score * 0.1))
                logger.debug(f"Updated node weight: {result.node_id} -> {node.weight}")
    
    def clear(self) -> None:
        """Clear all stores and caches."""
        self.graph.clear()
        self.vector_store.clear()
        self.cache.clear()
        self.embedding_cache.clear()
        logger.info("Cleared all retrieval stores and caches")
    
    # Private methods
    
    def _cache_key(
        self,
        query: str,
        top_k: int,
        strategy: RetrievalStrategy
    ) -> str:
        """Generate cache key for a retrieval request."""
        key_parts = [query, str(top_k), strategy.value]
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Get embedding for query with caching."""
        cached = self.embedding_cache.get(query)
        if cached is not None:
            return cached
        
        embedding = self.embedding_provider.embed_text(query)
        self.embedding_cache.put(query, embedding)
        return embedding
    
    def _retrieve_graph_first(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int
    ) -> List[RetrievalResult]:
        """Retrieve using graph traversal first."""
        results = []
        
        # Find starting nodes matching query keywords
        start_nodes = self._find_query_nodes(query)
        
        if not start_nodes:
            # Fall back to vector search
            return self._search_vector(query_embedding, top_k)
        
        # Traverse from each starting node
        all_traversed = {}
        for start_node in start_nodes:
            traversed = self.graph.weighted_traversal(
                start_node.id,
                max_depth=self.max_graph_depth
            )
            
            for node, weight in traversed:
                if node.id not in all_traversed:
                    all_traversed[node.id] = (node, weight)
        
        # Convert to results
        for node_id, (node, graph_score) in all_traversed.items():
            # Boost score for direct matches
            if node_id in [n.id for n in start_nodes]:
                graph_score = min(1.0, graph_score + 0.3)
            
            result = RetrievalResult(
                node_id=node_id,
                content=node.content,
                source=node.metadata.get("source"),
                score=graph_score * self.graph_weight,
                graph_score=graph_score,
                metadata=node.metadata
            )
            results.append(result)
        
        # Supplement with vector search if needed
        if len(results) < top_k:
            vector_results = self._search_vector(
                query_embedding,
                top_k - len(results)
            )
            for vr in vector_results:
                if vr.node_id not in [r.node_id for r in results]:
                    results.append(vr)
        
        return results
    
    def _retrieve_vector_first(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int
    ) -> List[RetrievalResult]:
        """Retrieve using vector search first."""
        results = self._search_vector(query_embedding, top_k)
        
        # Enhance with graph context
        for result in results:
            node = self.graph.get_node(result.node_id)
            if node:
                # Add neighbors as context
                neighbors = self.graph.get_neighbors(result.node_id)
                result.metadata["neighbors"] = [n.id for n in neighbors]
        
        return results
    
    def _retrieve_balanced(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int
    ) -> List[RetrievalResult]:
        """Retrieve using balanced graph and vector approach."""
        graph_results = self._retrieve_graph_first(query, query_embedding, top_k)
        vector_results = self._search_vector(query_embedding, top_k)
        
        # Merge results with balanced scoring
        merged = {}
        
        for result in graph_results:
            merged[result.node_id] = result
        
        for vr in vector_results:
            if vr.node_id in merged:
                # Combine scores
                merged[vr.node_id].vector_score = vr.vector_score
                merged[vr.node_id].score = (
                    merged[vr.node_id].graph_score * self.graph_weight +
                    vr.vector_score * self.vector_weight
                )
            else:
                # Add new result
                vr.score = vr.vector_score * self.vector_weight
                merged[vr.node_id] = vr
        
        return list(merged.values())
    
    def _retrieve_adaptive(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int
    ) -> List[RetrievalResult]:
        """Retrieve using adaptive strategy based on query characteristics."""
        # Analyze query to determine best strategy
        query_length = len(query.split())
        
        if query_length < 3:
            # Short queries: use keyword matching in graph
            graph_weight = 0.7
            vector_weight = 0.3
        elif query_length > 10:
            # Long queries: use more vector search
            graph_weight = 0.3
            vector_weight = 0.7
        else:
            # Medium queries: balanced
            graph_weight = 0.5
            vector_weight = 0.5
        
        # Temporarily adjust weights
        old_graph_weight = self.graph_weight
        old_vector_weight = self.vector_weight
        
        self.graph_weight = graph_weight
        self.vector_weight = vector_weight
        
        results = self._retrieve_balanced(query, query_embedding, top_k)
        
        # Restore weights
        self.graph_weight = old_graph_weight
        self.vector_weight = old_vector_weight
        
        return results
    
    def _search_vector(
        self,
        query_embedding: List[float],
        top_k: int
    ) -> List[RetrievalResult]:
        """Search vector store."""
        matches = self.vector_store.search(
            query_embedding,
            top_k=top_k,
            threshold=self.similarity_threshold
        )
        
        results = []
        for doc, similarity in matches:
            result = RetrievalResult(
                node_id=doc.id,
                content=doc.content,
                source=doc.source,
                score=similarity * self.vector_weight,
                vector_score=similarity,
                metadata=doc.metadata
            )
            results.append(result)
        
        return results
    
    def _find_query_nodes(self, query: str) -> List[GraphNode]:
        """Find graph nodes matching query keywords."""
        keywords = query.lower().split()
        matching_nodes = []
        
        for node in self.graph.nodes.values():
            # Simple keyword matching
            content_lower = node.content.lower()
            matches = sum(1 for kw in keywords if kw in content_lower)
            
            if matches > 0:
                matching_nodes.append(node)
        
        # Sort by number of matches
        matching_nodes.sort(
            key=lambda n: sum(1 for kw in keywords if kw in n.content.lower()),
            reverse=True
        )
        
        return matching_nodes[:5]  # Return top 5 matches
    
    def _refine_query(
        self,
        original_query: str,
        best_result: RetrievalResult
    ) -> str:
        """Refine query based on best result."""
        # Extract key terms from result
        result_words = best_result.content.lower().split()
        original_words = original_query.lower().split()
        
        # Find new high-frequency words
        new_words = [
            w for w in result_words
            if w not in original_words and len(w) > 3
        ]
        
        if new_words:
            # Add top new words to query
            refined = f"{original_query} {' '.join(new_words[:2])}"
            return refined
        
        return original_query
