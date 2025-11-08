"""
Vector Store for Knowledge Graph
Handles vector embeddings and similarity search
"""

import pickle
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

import faiss
import numpy as np
from pydantic import BaseModel

from app.logger import logger
from app.config import config


class VectorStore:
    """Vector store using FAISS for similarity search"""
    
    def __init__(self):
        self.index: Optional[faiss.Index] = None
        self.id_map: Dict[int, int] = {}  # node_id -> index_id
        self.reverse_id_map: Dict[int, int] = {}  # index_id -> node_id
        self.dimension = 1536  # Default for text-embedding-ada-002
        self._initialized = False
    
    async def initialize(self):
        """Initialize the vector store"""
        try:
            logger.info("Initializing vector store...")
            
            # Determine vector dimension from config
            embedding_model = config.knowledge_graph.embedding_model
            if "ada-002" in embedding_model:
                self.dimension = 1536
            elif "small" in embedding_model:
                self.dimension = 1536
            else:
                self.dimension = 768  # Default fallback
            
            # Initialize FAISS index
            self.index = faiss.IndexFlatL2(self.dimension)
            
            # Load existing vectors if available
            if config.knowledge_graph.persist_to_disk:
                await self._load_from_disk()
            
            self._initialized = True
            logger.info(f"Vector store initialized with dimension {self.dimension}")
            
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
            raise
    
    async def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text"""
        try:
            # This would integrate with actual embedding service
            # For now, return a random vector as placeholder
            if text in self._embedding_cache:
                return self._embedding_cache[text]
            
            # Placeholder embedding generation
            # In production, this would call OpenAI/embedding service
            embedding = np.random.random(self.dimension).astype('float32')
            
            # Normalize the embedding
            embedding = embedding / np.linalg.norm(embedding)
            
            # Cache the embedding
            self._embedding_cache[text] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return np.zeros(self.dimension, dtype='float32')
    
    async def add_vector(self, node_id: int, embedding: np.ndarray) -> bool:
        """Add a vector to the store"""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Convert to correct format
            if isinstance(embedding, list):
                embedding = np.array(embedding, dtype='float32')
            
            # Ensure correct dimension
            if embedding.shape[0] != self.dimension:
                logger.error(f"Embedding dimension mismatch: expected {self.dimension}, got {embedding.shape[0]}")
                return False
            
            # Add to FAISS index
            index_id = self.index.ntotal
            self.index.add(embedding.reshape(1, -1))
            
            # Update mappings
            self.id_map[node_id] = index_id
            self.reverse_id_map[index_id] = node_id
            
            # Persist to disk if enabled
            if config.knowledge_graph.persist_to_disk:
                await self._save_to_disk()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding vector for node {node_id}: {e}")
            return False
    
    async def update_vector(self, node_id: int, embedding: np.ndarray) -> bool:
        """Update a vector in the store"""
        try:
            if node_id not in self.id_map:
                # Add as new vector
                return await self.add_vector(node_id, embedding)
            
            # FAISS doesn't support direct updates, so we need to rebuild
            await self._remove_vector(node_id)
            return await self.add_vector(node_id, embedding)
            
        except Exception as e:
            logger.error(f"Error updating vector for node {node_id}: {e}")
            return False
    
    async def delete_vector(self, node_id: int) -> bool:
        """Delete a vector from the store"""
        try:
            return await self._remove_vector(node_id)
            
        except Exception as e:
            logger.error(f"Error deleting vector for node {node_id}: {e}")
            return False
    
    async def _remove_vector(self, node_id: int) -> bool:
        """Remove a vector from the store"""
        try:
            if node_id not in self.id_map:
                return False
            
            index_id = self.id_map[node_id]
            
            # FAISS doesn't support direct removal, so we need to rebuild
            await self._rebuild_index_excluding([index_id])
            
            # Update mappings
            del self.id_map[node_id]
            if index_id in self.reverse_id_map:
                del self.reverse_id_map[index_id]
            
            # Persist to disk if enabled
            if config.knowledge_graph.persist_to_disk:
                await self._save_to_disk()
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing vector for node {node_id}: {e}")
            return False
    
    async def search_similar(self, query_embedding: np.ndarray, 
                           limit: int = 10) -> List[Tuple[int, float]]:
        """Search for similar vectors"""
        try:
            if not self._initialized or self.index.ntotal == 0:
                return []
            
            # Convert to correct format
            if isinstance(query_embedding, list):
                query_embedding = np.array(query_embedding, dtype='float32')
            
            # Normalize query embedding
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            
            # Search in FAISS
            k = min(limit, self.index.ntotal)
            distances, indices = self.index.search(query_embedding.reshape(1, -1), k)
            
            # Convert to node_ids and similarity scores
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx >= 0 and idx in self.reverse_id_map:
                    node_id = self.reverse_id_map[idx]
                    # Convert L2 distance to similarity score
                    similarity = 1.0 / (1.0 + dist)
                    results.append((node_id, similarity))
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar vectors: {e}")
            return []
    
    async def _rebuild_index_excluding(self, exclude_indices: List[int]):
        """Rebuild the FAISS index excluding certain indices"""
        try:
            # Get all vectors except excluded ones
            all_vectors = []
            new_id_map = {}
            new_reverse_id_map = {}
            
            for node_id, index_id in self.id_map.items():
                if index_id not in exclude_indices:
                    # Get vector from current index
                    vector = self.index.reconstruct(int(index_id))
                    all_vectors.append(vector)
                    
                    new_index_id = len(all_vectors) - 1
                    new_id_map[node_id] = new_index_id
                    new_reverse_id_map[new_index_id] = node_id
            
            # Rebuild index
            if all_vectors:
                vectors_array = np.vstack(all_vectors)
                self.index = faiss.IndexFlatL2(self.dimension)
                self.index.add(vectors_array)
            else:
                self.index = faiss.IndexFlatL2(self.dimension)
            
            # Update mappings
            self.id_map = new_id_map
            self.reverse_id_map = new_reverse_id_map
            
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            raise
    
    async def _save_to_disk(self):
        """Save vector store to disk"""
        try:
            storage_path = Path(config.knowledge_graph.graph_storage_path)
            storage_path.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            index_file = storage_path / "vectors.faiss"
            faiss.write_index(self.index, str(index_file))
            
            # Save mappings
            mappings_file = storage_path / "mappings.pkl"
            with open(mappings_file, 'wb') as f:
                pickle.dump({
                    'id_map': self.id_map,
                    'reverse_id_map': self.reverse_id_map,
                    'dimension': self.dimension
                }, f)
            
            logger.debug(f"Vector store saved to {storage_path}")
            
        except Exception as e:
            logger.error(f"Error saving vector store to disk: {e}")
    
    async def _load_from_disk(self):
        """Load vector store from disk"""
        try:
            storage_path = Path(config.knowledge_graph.graph_storage_path)
            
            # Check if files exist
            index_file = storage_path / "vectors.faiss"
            mappings_file = storage_path / "mappings.pkl"
            
            if not index_file.exists() or not mappings_file.exists():
                logger.info("No existing vector store found, starting fresh")
                return
            
            # Load FAISS index
            self.index = faiss.read_index(str(index_file))
            
            # Load mappings
            with open(mappings_file, 'rb') as f:
                data = pickle.load(f)
                self.id_map = data['id_map']
                self.reverse_id_map = data['reverse_id_map']
                self.dimension = data['dimension']
            
            logger.info(f"Loaded vector store with {self.index.ntotal} vectors")
            
        except Exception as e:
            logger.error(f"Error loading vector store from disk: {e}")
            # Start fresh on error
            self.index = faiss.IndexFlatL2(self.dimension)
            self.id_map = {}
            self.reverse_id_map = {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self._initialized:
            return {"initialized": False}
        
        return {
            "initialized": True,
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "id_mappings": len(self.id_map),
            "cache_size": len(self._embedding_cache)
        }
    
    # Cache for embeddings to avoid recomputation
    _embedding_cache: Dict[str, np.ndarray] = {}
