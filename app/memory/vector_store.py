"""Vector Store module for managing embeddings using FAISS."""

import json
import pickle
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np
from pydantic import BaseModel, Field


class VectorStoreEntry(BaseModel):
    """Represents an entry in the vector store."""
    entity_id: str = Field(..., description="ID of the entity (node, document, etc.)")
    entity_type: str = Field(..., description="Type of entity: node, document, chunk")
    embedding: List[float] = Field(..., description="The embedding vector")
    text: Optional[str] = Field(None, description="Original text for reference")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        arbitrary_types_allowed = True


class VectorStore:
    """Manages embeddings using FAISS with SQLite persistence."""
    
    def __init__(
        self,
        dimension: int = 1536,
        index_type: str = "IVFFlat",
        storage_path: str = "data/vectors",
        nprobe: int = 10,
        use_gpu: bool = False,
    ):
        """Initialize the vector store.
        
        Args:
            dimension: Dimension of embeddings
            index_type: Type of FAISS index (IVFFlat, Flat, etc.)
            storage_path: Path for persistence
            nprobe: Number of probes for IVFFlat index
            use_gpu: Whether to use GPU (if available)
        """
        self.dimension = dimension
        self.index_type = index_type
        self.storage_path = Path(storage_path)
        self.nprobe = nprobe
        self.use_gpu = use_gpu
        self._lock = threading.RLock()
        self._embeddings_cache: Dict[int, List[float]] = {}
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_path / "index.faiss"
        self.db_path = self.storage_path / "vectors.db"
        self.id_map_path = self.storage_path / "id_map.json"
        self.embeddings_path = self.storage_path / "embeddings.json"
        
        self._init_database()
        self._init_index()
        self._load_id_map()
        self._load_embeddings()
        self._next_id = 0
    
    def _init_database(self):
        """Initialize SQLite database for metadata storage."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vector_entries (
                    entry_id INTEGER PRIMARY KEY,
                    entity_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    text TEXT,
                    metadata TEXT,
                    embedding_saved_at TEXT,
                    UNIQUE(entity_id, entity_type)
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_id ON vector_entries(entity_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON vector_entries(entity_type)")
            
            conn.commit()
    
    def _init_index(self):
        """Initialize or load the FAISS index."""
        if self.index_path.exists():
            self._load_index()
        else:
            self._create_index()
    
    def _create_index(self):
        """Create a new FAISS index."""
        if self.index_type == "IVFFlat":
            nlist = 100
            quantizer = faiss.IndexFlatL2(self.dimension)
            flat_index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            flat_index.nprobe = self.nprobe
            self.index = faiss.IndexIDMap(flat_index)
        elif self.index_type == "Flat":
            flat_index = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIDMap(flat_index)
        else:
            flat_index = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIDMap(flat_index)
        
        self.id_to_entity: Dict[int, str] = {}
        self.entity_to_id: Dict[str, int] = {}
    
    def _load_index(self):
        """Load the FAISS index from disk."""
        self.index = faiss.read_index(str(self.index_path))
        if hasattr(self.index, 'index') and hasattr(self.index.index, 'nprobe'):
            self.index.index.nprobe = self.nprobe
    
    def _save_index(self):
        """Save the FAISS index to disk."""
        faiss.write_index(self.index, str(self.index_path))
    
    def _load_id_map(self):
        """Load the entity ID mapping from disk."""
        if self.id_map_path.exists():
            with open(self.id_map_path, "r") as f:
                data = json.load(f)
                self.id_to_entity = {int(k): v for k, v in data.get("id_to_entity", {}).items()}
                self.entity_to_id = data.get("entity_to_id", {})
                self._next_id = max([int(k) for k in self.id_to_entity.keys()], default=0) + 1
        else:
            self.id_to_entity = {}
            self.entity_to_id = {}
            self._next_id = 0
    
    def _save_id_map(self):
        """Save the entity ID mapping to disk."""
        data = {
            "id_to_entity": self.id_to_entity,
            "entity_to_id": self.entity_to_id,
        }
        with open(self.id_map_path, "w") as f:
            json.dump(data, f)
    
    def _load_embeddings(self):
        """Load embeddings from disk."""
        if self.embeddings_path.exists():
            with open(self.embeddings_path, "r") as f:
                data = json.load(f)
                self._embeddings_cache = {int(k): v for k, v in data.items()}
    
    def _save_embeddings(self):
        """Save embeddings to disk."""
        with open(self.embeddings_path, "w") as f:
            json.dump(self._embeddings_cache, f)
    
    def add_embedding(
        self,
        entity_id: str,
        entity_type: str,
        embedding: List[float],
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add an embedding to the vector store.
        
        Args:
            entity_id: ID of the entity
            entity_type: Type of entity (node, document, chunk)
            embedding: Embedding vector
            text: Optional original text
            metadata: Optional metadata
            
        Returns:
            Index ID of the added embedding
        """
        with self._lock:
            if metadata is None:
                metadata = {}
            
            embedding_array = np.array([embedding], dtype=np.float32)
            
            entity_key = f"{entity_type}:{entity_id}"
            
            if entity_key in self.entity_to_id:
                idx = self.entity_to_id[entity_key]
                self.index.remove_ids(np.array([idx]))
            else:
                idx = self._next_id
                self._next_id += 1
                self.entity_to_id[entity_key] = idx
                self.id_to_entity[idx] = entity_key
            
            self.index.add_with_ids(embedding_array, np.array([idx]))
            self._embeddings_cache[idx] = embedding
            
            metadata["added_at"] = metadata.get("added_at", datetime.now(timezone.utc).isoformat())
            
            self._save_embedding_metadata(idx, entity_id, entity_type, text, metadata)
            self._save_index()
            self._save_id_map()
            self._save_embeddings()
            
            return idx
    
    def get_embedding(self, entity_id: str, entity_type: str) -> Optional[VectorStoreEntry]:
        """Get an embedding from the vector store.
        
        Args:
            entity_id: ID of the entity
            entity_type: Type of entity
            
        Returns:
            VectorStoreEntry or None if not found
        """
        with self._lock:
            entity_key = f"{entity_type}:{entity_id}"
            
            if entity_key not in self.entity_to_id:
                return None
            
            idx = self.entity_to_id[entity_key]
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT text, metadata FROM vector_entries WHERE entry_id = ?",
                    (idx,),
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                text, metadata_json = row
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                embedding = self._embeddings_cache.get(idx)
                if embedding is None:
                    return None
                
                return VectorStoreEntry(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    embedding=embedding,
                    text=text,
                    metadata=metadata,
                )
    
    def search_similar(
        self,
        query_embedding: List[float],
        k: int = 10,
        entity_type: Optional[str] = None,
    ) -> List[Tuple[str, str, float]]:
        """Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            entity_type: Optional filter by entity type
            
        Returns:
            List of (entity_id, entity_type, distance) tuples
        """
        with self._lock:
            query_array = np.array([query_embedding], dtype=np.float32)
            
            distances, indices = self.index.search(query_array, min(k * 2, self.index.ntotal))
            
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx == -1:
                    continue
                
                if idx not in self.id_to_entity:
                    continue
                
                entity_key = self.id_to_entity[idx]
                stored_entity_type, entity_id = entity_key.split(":", 1)
                
                if entity_type is not None and stored_entity_type != entity_type:
                    continue
                
                results.append((entity_id, stored_entity_type, float(distance)))
                
                if len(results) >= k:
                    break
            
            return results
    
    def delete_embedding(self, entity_id: str, entity_type: str) -> bool:
        """Delete an embedding from the vector store.
        
        Args:
            entity_id: ID of the entity
            entity_type: Type of entity
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            entity_key = f"{entity_type}:{entity_id}"
            
            if entity_key not in self.entity_to_id:
                return False
            
            idx = self.entity_to_id[entity_key]
            self.index.remove_ids(np.array([idx]))
            
            del self.entity_to_id[entity_key]
            del self.id_to_entity[idx]
            if idx in self._embeddings_cache:
                del self._embeddings_cache[idx]
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM vector_entries WHERE entry_id = ?", (idx,))
                conn.commit()
            
            self._save_index()
            self._save_id_map()
            self._save_embeddings()
            
            return True
    
    def batch_add_embeddings(
        self,
        entries: List[VectorStoreEntry],
    ) -> List[int]:
        """Add multiple embeddings in batch.
        
        Args:
            entries: List of VectorStoreEntry objects
            
        Returns:
            List of index IDs
        """
        with self._lock:
            indices = []
            embeddings_array = []
            faiss_indices = []
            
            for entry in entries:
                entity_key = f"{entry.entity_type}:{entry.entity_id}"
                
                if entity_key in self.entity_to_id:
                    idx = self.entity_to_id[entity_key]
                    self.index.remove_ids(np.array([idx]))
                else:
                    idx = self._next_id
                    self._next_id += 1
                    self.entity_to_id[entity_key] = idx
                    self.id_to_entity[idx] = entity_key
                
                indices.append(idx)
                embeddings_array.append(entry.embedding)
                faiss_indices.append(idx)
                self._embeddings_cache[idx] = entry.embedding
                
                entry.metadata["added_at"] = entry.metadata.get("added_at", datetime.now(timezone.utc).isoformat())
                self._save_embedding_metadata(idx, entry.entity_id, entry.entity_type, entry.text, entry.metadata)
            
            if embeddings_array:
                embeddings_np = np.array(embeddings_array, dtype=np.float32)
                faiss_indices_np = np.array(faiss_indices)
                self.index.add_with_ids(embeddings_np, faiss_indices_np)
                
                self._save_index()
                self._save_id_map()
                self._save_embeddings()
            
            return indices
    
    def batch_search_similar(
        self,
        query_embeddings: List[List[float]],
        k: int = 10,
        entity_type: Optional[str] = None,
    ) -> List[List[Tuple[str, str, float]]]:
        """Search for similar embeddings in batch.
        
        Args:
            query_embeddings: List of query embeddings
            k: Number of results per query
            entity_type: Optional filter by entity type
            
        Returns:
            List of result lists, each containing (entity_id, entity_type, distance) tuples
        """
        with self._lock:
            query_array = np.array(query_embeddings, dtype=np.float32)
            
            distances, indices = self.index.search(query_array, min(k * 2, self.index.ntotal))
            
            batch_results = []
            
            for batch_idx, (dist_row, idx_row) in enumerate(zip(distances, indices)):
                results = []
                
                for idx, distance in zip(idx_row, dist_row):
                    if idx == -1:
                        continue
                    
                    if idx not in self.id_to_entity:
                        continue
                    
                    entity_key = self.id_to_entity[idx]
                    stored_entity_type, entity_id = entity_key.split(":", 1)
                    
                    if entity_type is not None and stored_entity_type != entity_type:
                        continue
                    
                    results.append((entity_id, stored_entity_type, float(distance)))
                    
                    if len(results) >= k:
                        break
                
                batch_results.append(results)
            
            return batch_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vector store statistics.
        
        Returns:
            Dictionary containing statistics
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM vector_entries")
                total_entries = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT entity_type) FROM vector_entries")
                entity_types = cursor.fetchone()[0]
            
            return {
                "total_vectors": self.index.ntotal,
                "total_entries": total_entries,
                "dimension": self.dimension,
                "index_type": self.index_type,
                "entity_types": entity_types,
            }
    
    def _save_embedding_metadata(
        self,
        entry_id: int,
        entity_id: str,
        entity_type: str,
        text: Optional[str],
        metadata: Dict[str, Any],
    ):
        """Save embedding metadata to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata)
            now = datetime.now(timezone.utc).isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO vector_entries
                (entry_id, entity_id, entity_type, text, metadata, embedding_saved_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (entry_id, entity_id, entity_type, text, metadata_json, now))
            
            conn.commit()
    
    def export_to_file(self, file_path: str):
        """Export the vector store to a file.
        
        Args:
            file_path: Path to save the export
        """
        with self._lock:
            export_data = {
                "index_type": self.index_type,
                "dimension": self.dimension,
                "id_to_entity": self.id_to_entity,
                "entity_to_id": self.entity_to_id,
                "next_id": self._next_id,
            }
            
            with open(file_path, "wb") as f:
                pickle.dump(export_data, f)
            
            faiss.write_index(self.index, f"{file_path}.index")
    
    def import_from_file(self, file_path: str):
        """Import the vector store from a file.
        
        Args:
            file_path: Path to the export file
        """
        with self._lock:
            with open(file_path, "rb") as f:
                export_data = pickle.load(f)
            
            self.index_type = export_data["index_type"]
            self.dimension = export_data["dimension"]
            self.id_to_entity = export_data["id_to_entity"]
            self.entity_to_id = export_data["entity_to_id"]
            self._next_id = export_data["next_id"]
            
            self.index = faiss.read_index(f"{file_path}.index")
            
            self._save_index()
            self._save_id_map()
