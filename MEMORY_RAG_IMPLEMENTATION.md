# Memory RAG Implementation Guide

## Overview

The Memory RAG (Retrieval-Augmented Generation) system provides hybrid retrieval capabilities combining knowledge graph traversal with vector similarity search. This system enables agents to retrieve contextual knowledge and iteratively refine queries based on prior results.

## Architecture

### Components

1. **Vector Store** (`app/memory/vector_store.py`)
   - In-memory vector storage for document embeddings
   - Cosine similarity search
   - Document management (add, remove, search)
   - Embedding providers (mock for testing, extensible for real embeddings)

2. **Knowledge Graph** (`app/memory/graph.py`)
   - Hierarchical memory organization
   - Graph traversal (BFS, weighted traversal)
   - Path finding between nodes
   - Node and edge management
   - Multiple relationship types (REFERENCES, DEPENDS_ON, CONTAINS, RELATED_TO, PRODUCES, CONSUMES, IMPLEMENTS)

3. **Hybrid Retriever** (`app/memory/retriever.py`)
   - Combines graph and vector search
   - Multiple retrieval strategies (GRAPH_FIRST, VECTOR_FIRST, BALANCED, ADAPTIVE)
   - Query refinement and iterative retrieval
   - Scoring heuristics for merging results
   - Result caching

4. **Caching Layer** (`app/memory/cache.py`)
   - TTL-based retrieval caching
   - Embedding caching
   - LRU eviction
   - Expired entry cleanup

5. **Retriever Service** (`app/memory/service.py`)
   - Singleton service for agent integration
   - Session context management
   - Agent preferences
   - Service statistics

## Usage

### Basic Retrieval

```python
from app.memory import HybridRetriever

# Initialize retriever
retriever = HybridRetriever()

# Ingest documents
retriever.ingest_document(
    doc_id="doc1",
    content="Machine learning is a subset of AI",
    metadata={"category": "ML"}
)

# Retrieve
context = retriever.retrieve("machine learning", top_k=5)
for result in context.results:
    print(f"Score: {result.score}, Content: {result.content}")
```

### Retrieval in Agents

```python
from app.memory import get_retriever_service

service = get_retriever_service()

# In agent code
context = service.retrieve(
    agent_id="developer_1",
    query="REST API design patterns",
    top_k=5,
    strategy="balanced"
)

# Inject into agent reasoning
agent.inject_context([r.to_dict() for r in context.results])
```

### Iterative Retrieval

```python
# Refine queries based on prior results
contexts = service.retrieve_iterative(
    agent_id="agent_1",
    query="neural networks for classification",
    max_iterations=3,
    strategy="balanced"
)

for i, context in enumerate(contexts):
    print(f"Iteration {i+1}: {len(context.results)} results")
```

### Graph Operations

```python
from app.memory import GraphNode, NodeType, EdgeType

# Add nodes
node1 = GraphNode(
    id="concept_ml",
    node_type=NodeType.CONCEPT,
    content="Machine Learning"
)
retriever.graph.add_node(node1)

# Add relationships
retriever.add_context_relationship(
    source_id="concept_ml",
    target_id="concept_dl",
    edge_type=EdgeType.CONTAINS,
    weight=0.9
)

# Traverse
neighbors = retriever.graph.get_neighbors("concept_ml")
traversed = retriever.graph.bfs_traversal("concept_ml", max_depth=3)
```

## Retrieval Strategies

### GRAPH_FIRST
- Prioritizes knowledge graph traversal
- Finds keyword matches in graph nodes
- Supplements with vector search if needed
- Best for: Structured knowledge, hierarchical relationships

### VECTOR_FIRST
- Prioritizes vector similarity search
- Enhances results with graph context
- Adds neighbor information to results
- Best for: Semantic similarity, unstructured data

### BALANCED
- Combines graph and vector results
- Equal weight for both approaches
- Merges and ranks results
- Best for: General purpose queries

### ADAPTIVE
- Analyzes query characteristics
- Adjusts strategy based on query length
- Short queries: more graph (70%), less vector (30%)
- Long queries: more vector (70%), less graph (30%)
- Medium queries: balanced
- Best for: Unknown query types

## UI Integration

### Retrieval Insights Panel

The `RetrievalInsightsPanel` provides a visual interface for:

1. **Query Search**
   - Enter queries
   - Select retrieval strategy
   - Execute search and refinement

2. **Results Display**
   - Tabular results view
   - Composite, graph, and vector scores
   - Content preview

3. **Knowledge Graph Visualization**
   - Tree view of graph nodes
   - Relationship display
   - Node details

4. **Context Actions**
   - Accept and inject results
   - Reject results
   - Copy to clipboard

**Usage:**
```python
from app.ui.panels import RetrievalInsightsPanel

panel = RetrievalInsightsPanel()
# Connect signals
panel.result_accepted.connect(on_result_accepted)
panel.result_rejected.connect(on_result_rejected)
```

## Integration with SpecializedAgent

The `SpecializedAgent` class includes three new methods:

### retrieve_knowledge(query, top_k=5, strategy="balanced")
Retrieves contextual knowledge using hybrid RAG.

```python
results = await agent.retrieve_knowledge(
    "Design patterns for distributed systems",
    top_k=10,
    strategy="balanced"
)
```

### refine_knowledge(query, max_iterations=3, strategy="balanced")
Iteratively refines knowledge retrieval with query refinement.

```python
iteration_results = await agent.refine_knowledge(
    "API security best practices",
    max_iterations=3
)
```

### inject_context(context_items)
Injects retrieved context into the agent's reasoning.

```python
agent.inject_context(results)
# Context is now part of agent's memory
```

## Testing

Run the comprehensive test suite:

```bash
python -m pytest tests/test_retriever.py -v
```

Tests cover:
- Vector store operations (add, remove, search)
- Knowledge graph operations (nodes, edges, traversal)
- Hybrid retriever (all strategies, caching, iterative retrieval)
- Service integration
- Agent integration scenarios

**Test Results:**
- 23 tests
- Coverage: Vector store, Graph, Retriever, Service, Integration

## Performance Considerations

### Caching
- Results cached with configurable TTL (default: 3600s)
- Embeddings cached separately
- LRU eviction when cache exceeds max size (default: 1000 entries)

### Graph Traversal
- BFS for breadth-first exploration
- Weighted traversal for importance-based ranking
- Max depth configurable (default: 3)

### Vector Search
- Cosine similarity for distance metric
- Configurable similarity threshold (default: 0.3)
- O(n) complexity, suitable for <100k documents

### Optimization Tips
- Set appropriate similarity threshold to filter noise
- Use graph_weight and vector_weight to balance strategies
- Clear cache periodically for long-running agents
- Use ADAPTIVE strategy for varied query types

## Extension Points

### Custom Embedding Providers
```python
from app.memory import EmbeddingProvider

class OpenAIEmbeddingProvider(EmbeddingProvider):
    def embed_text(self, text: str) -> List[float]:
        # Implementation using OpenAI API
        pass

retriever = HybridRetriever(
    embedding_provider=OpenAIEmbeddingProvider()
)
```

### Custom Node and Edge Types
Add to `NodeType` and `EdgeType` enums as needed:

```python
class NodeType(str, Enum):
    # Existing types...
    CUSTOM = "custom"
```

### Result Scoring Customization
Override scoring in retriever strategies:

```python
class CustomRetriever(HybridRetriever):
    def _score_result(self, result, query):
        # Custom scoring logic
        pass
```

## API Reference

### HybridRetriever

**Methods:**
- `retrieve(query, top_k, strategy, refine_query)` - Main retrieval method
- `retrieve_iterative(initial_query, max_iterations, strategy)` - Iterative retrieval
- `ingest_document(doc_id, content, metadata, source)` - Add single document
- `ingest_batch(documents, source)` - Add multiple documents
- `add_context_relationship(source_id, target_id, edge_type, weight)` - Add edges
- `update_from_context(context, auto_ingest)` - Learn from results
- `clear()` - Clear all stores

### RetrieverService

**Methods:**
- `retrieve(agent_id, query, top_k, strategy)` - Agent retrieval
- `retrieve_iterative(agent_id, query, max_iterations, strategy)` - Iterative retrieval
- `ingest_document(doc_id, content, metadata, source)` - Document ingestion
- `ingest_batch(documents, source)` - Batch ingestion
- `add_relationship(source_id, target_id, relationship_type, weight)` - Add relationship
- `set_agent_preferences(agent_id, preferences)` - Set agent preferences
- `get_agent_context(agent_id, include_all)` - Get agent context
- `get_session_contexts(agent_id)` - Get session contexts
- `clear_session(agent_id)` - Clear agent session
- `clear_all()` - Clear everything
- `get_stats()` - Get service statistics

## Best Practices

1. **Knowledge Base Organization**
   - Use meaningful node IDs
   - Add metadata for filtering
   - Create relationships explicitly

2. **Query Formulation**
   - Use specific keywords
   - Longer queries for semantic search
   - Short queries for keyword matching

3. **Result Evaluation**
   - Check both graph and vector scores
   - Review metadata
   - Accept high-quality results for injection

4. **Performance**
   - Monitor cache size
   - Batch operations when possible
   - Use appropriate retrieval strategy

5. **Error Handling**
   - Handle embedding provider failures
   - Manage cache eviction
   - Log retrieval operations

## Troubleshooting

### No results returned
- Lower similarity threshold
- Use different retrieval strategy
- Check if documents are properly ingested
- Verify embedding provider is working

### Slow queries
- Check cache configuration
- Reduce max_depth for traversal
- Use vector_first strategy for large graphs
- Check embedding cache hit rate

### Memory usage
- Monitor cache size
- Clear old session contexts
- Reduce max_messages in cache
- Use session-specific retrieval

## Future Enhancements

1. **Persistent Storage**
   - Store graph and vector data to disk
   - Enable cross-session persistence

2. **Real Embeddings**
   - Integration with OpenAI embeddings
   - Hugging Face transformers support

3. **Advanced Ranking**
   - Learning-to-rank approaches
   - Personalized scoring

4. **Distributed Retrieval**
   - Multi-node graph traversal
   - Distributed vector search

5. **Security**
   - Guardian oversight for sensitive data
   - Access control on context injection

## References

- Retrieval-Augmented Generation: https://arxiv.org/abs/2005.11401
- Knowledge Graphs: https://en.wikipedia.org/wiki/Knowledge_graph
- Vector Databases: https://en.wikipedia.org/wiki/Vector_database
