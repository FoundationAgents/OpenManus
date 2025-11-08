"""Retrieval service for agent integration."""

from typing import Dict, List, Optional, Any

from app.logger import logger
from app.memory.retriever import HybridRetriever, RetrievalContext, RetrievalStrategy
from app.memory.graph import NodeType, EdgeType, GraphNode


class RetrieverService:
    """Singleton service for managing retrieval across agents."""
    
    _instance = None
    _lock = __import__('threading').Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.retriever = HybridRetriever()
        self.session_contexts: Dict[str, RetrievalContext] = {}
        self.agent_preferences: Dict[str, Dict[str, Any]] = {}
        self._initialized = True
        
        logger.info("RetrieverService initialized")
    
    def retrieve(
        self,
        agent_id: str,
        query: str,
        top_k: Optional[int] = None,
        strategy: Optional[str] = None
    ) -> RetrievalContext:
        """
        Retrieve contextual knowledge for an agent.
        
        Args:
            agent_id: ID of requesting agent
            query: Search query
            top_k: Number of results
            strategy: Retrieval strategy
        
        Returns:
            RetrievalContext with results
        """
        # Get agent preferences
        prefs = self.agent_preferences.get(agent_id, {})
        
        # Use provided strategy or agent preference
        if strategy is None:
            strategy = prefs.get("retrieval_strategy", "balanced")
        
        try:
            strategy_enum = RetrievalStrategy[strategy.upper()]
        except (KeyError, AttributeError):
            strategy_enum = RetrievalStrategy.BALANCED
        
        # Retrieve
        context = self.retriever.retrieve(
            query=query,
            top_k=top_k,
            strategy=strategy_enum
        )
        
        # Store in session context
        session_key = f"{agent_id}:{query}"
        self.session_contexts[session_key] = context
        
        logger.debug(
            f"Agent {agent_id} retrieved {len(context.results)} results for query: {query}"
        )
        
        return context
    
    def retrieve_iterative(
        self,
        agent_id: str,
        query: str,
        max_iterations: int = 3,
        strategy: Optional[str] = None
    ) -> List[RetrievalContext]:
        """
        Iterative retrieval with query refinement.
        
        Args:
            agent_id: ID of requesting agent
            query: Initial query
            max_iterations: Max refinement iterations
            strategy: Retrieval strategy
        
        Returns:
            List of RetrievalContext from each iteration
        """
        # Get agent preferences
        prefs = self.agent_preferences.get(agent_id, {})
        
        if strategy is None:
            strategy = prefs.get("retrieval_strategy", "balanced")
        
        try:
            strategy_enum = RetrievalStrategy[strategy.upper()]
        except (KeyError, AttributeError):
            strategy_enum = RetrievalStrategy.BALANCED
        
        contexts = self.retriever.retrieve_iterative(
            initial_query=query,
            max_iterations=max_iterations,
            strategy=strategy_enum
        )
        
        # Store all contexts
        for i, context in enumerate(contexts):
            session_key = f"{agent_id}:{query}:iter_{i}"
            self.session_contexts[session_key] = context
        
        logger.debug(f"Agent {agent_id} completed {len(contexts)} retrieval iterations")
        
        return contexts
    
    def ingest_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict] = None,
        source: Optional[str] = None
    ) -> None:
        """Ingest a document."""
        self.retriever.ingest_document(
            doc_id=doc_id,
            content=content,
            metadata=metadata,
            source=source
        )
    
    def ingest_batch(
        self,
        documents: List[tuple],
        source: Optional[str] = None
    ) -> None:
        """Ingest multiple documents."""
        self.retriever.ingest_batch(documents, source)
    
    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        weight: float = 1.0
    ) -> None:
        """
        Add relationship between nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship_type: Type of relationship
            weight: Edge weight
        """
        try:
            edge_type = EdgeType[relationship_type.upper()]
        except KeyError:
            edge_type = EdgeType.RELATED_TO
        
        self.retriever.add_context_relationship(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight
        )
    
    def set_agent_preferences(
        self,
        agent_id: str,
        preferences: Dict[str, Any]
    ) -> None:
        """Set retrieval preferences for an agent."""
        self.agent_preferences[agent_id] = preferences
        logger.debug(f"Set preferences for agent {agent_id}: {preferences}")
    
    def get_agent_context(
        self,
        agent_id: str,
        include_all: bool = False
    ) -> Dict[str, Any]:
        """
        Get retrieval context for an agent.
        
        Args:
            agent_id: Agent ID
            include_all: Include all session contexts or just recent
        
        Returns:
            Agent context data
        """
        agent_contexts = {}
        
        for key, context in self.session_contexts.items():
            if key.startswith(agent_id):
                agent_contexts[key] = context.to_dict()
        
        return {
            "agent_id": agent_id,
            "preferences": self.agent_preferences.get(agent_id, {}),
            "contexts": agent_contexts,
            "retriever_stats": {
                "graph_size": self.retriever.graph.size(),
                "vector_store_size": self.retriever.vector_store.size(),
                "cache_size": self.retriever.cache.size()
            }
        }
    
    def get_session_contexts(self, agent_id: Optional[str] = None) -> Dict[str, RetrievalContext]:
        """Get session contexts."""
        if agent_id is None:
            return self.session_contexts
        
        return {
            k: v for k, v in self.session_contexts.items()
            if k.startswith(agent_id)
        }
    
    def update_from_context(
        self,
        context: RetrievalContext,
        auto_ingest: bool = False
    ) -> None:
        """Update retriever based on context."""
        self.retriever.update_from_context(context, auto_ingest=auto_ingest)
    
    def clear_session(self, agent_id: Optional[str] = None) -> None:
        """Clear session contexts."""
        if agent_id is None:
            self.session_contexts.clear()
        else:
            keys_to_remove = [
                k for k in self.session_contexts.keys()
                if k.startswith(agent_id)
            ]
            for key in keys_to_remove:
                del self.session_contexts[key]
    
    def clear_all(self) -> None:
        """Clear everything."""
        self.retriever.clear()
        self.session_contexts.clear()
        self.agent_preferences.clear()
        logger.info("Cleared all retriever service data")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        graph_nodes, graph_edges = self.retriever.graph.size()
        return {
            "graph_nodes": graph_nodes,
            "graph_edges": graph_edges,
            "vector_documents": self.retriever.vector_store.size(),
            "cache_entries": self.retriever.cache.size(),
            "embedding_cache_size": self.retriever.embedding_cache.size(),
            "session_contexts": len(self.session_contexts),
            "agents_with_prefs": len(self.agent_preferences)
        }


def get_retriever_service() -> RetrieverService:
    """Get the singleton retriever service instance."""
    return RetrieverService()
