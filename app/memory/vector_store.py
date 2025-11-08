"""Vector store implementation for embedding-based similarity search."""

import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


@dataclass
class Document:
    """Represents a document with embedding."""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict = field(default_factory=dict)
    source: Optional[str] = None
    
    def __hash__(self):
        return hash(self.id)


class VectorStore(BaseModel):
    """In-memory vector store with similarity search capabilities."""
    
    documents: Dict[str, Document] = Field(default_factory=dict)
    embedding_dim: int = Field(default=768, description="Dimension of embeddings")
    
    class Config:
        arbitrary_types_allowed = True
    
    def add_document(self, doc: Document) -> None:
        """Add a document to the store."""
        if len(doc.embedding) != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.embedding_dim}, "
                f"got {len(doc.embedding)}"
            )
        self.documents[doc.id] = doc
    
    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the store."""
        if doc_id in self.documents:
            del self.documents[doc_id]
            return True
        return False
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self.documents.get(doc_id)
    
    def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        threshold: float = 0.5
    ) -> List[Tuple[Document, float]]:
        """Search for similar documents using cosine similarity."""
        if len(query_embedding) != self.embedding_dim:
            raise ValueError(
                f"Query embedding dimension mismatch: expected {self.embedding_dim}, "
                f"got {len(query_embedding)}"
            )
        
        similarities = []
        for doc in self.documents.values():
            similarity = self._cosine_similarity(query_embedding, doc.embedding)
            if similarity >= threshold:
                similarities.append((doc, similarity))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a ** 2 for a in vec1) ** 0.5
        magnitude2 = sum(b ** 2 for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def batch_search(
        self,
        query_embeddings: List[List[float]],
        top_k: int = 5,
        threshold: float = 0.5
    ) -> List[List[Tuple[Document, float]]]:
        """Search for multiple queries in batch."""
        return [
            self.search(qe, top_k=top_k, threshold=threshold)
            for qe in query_embeddings
        ]
    
    def clear(self) -> None:
        """Clear all documents from the store."""
        self.documents.clear()
    
    def size(self) -> int:
        """Get the number of documents in the store."""
        return len(self.documents)


class EmbeddingProvider(BaseModel):
    """Base class for embedding providers."""
    
    model_name: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    embedding_dim: int = Field(default=768)
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text. Should be overridden by subclasses."""
        raise NotImplementedError
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [self.embed_text(text) for text in texts]


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing that generates deterministic embeddings."""
    
    def embed_text(self, text: str) -> List[float]:
        """Generate deterministic mock embedding based on text hash."""
        # Create deterministic embedding based on hash
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert hash bytes to normalized float vector
        embedding = []
        for i in range(self.embedding_dim):
            byte_val = hash_bytes[i % len(hash_bytes)]
            # Normalize to [-1, 1]
            normalized = (byte_val / 255.0) * 2 - 1
            embedding.append(normalized)
        
        # Normalize to unit vector
        norm = sum(x ** 2 for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
