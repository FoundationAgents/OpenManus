"""Knowledge Base Management Module

Handles document storage, retrieval, and semantic search for FreEco.AI.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class DocumentType(Enum):
    """Document type enumeration."""

    TEXT = "text"
    MARKDOWN = "markdown"
    PDF = "pdf"
    CODE = "code"


class DocumentCategory(Enum):
    """Document category enumeration."""

    GENERAL = "general"
    RESEARCH = "research"
    NOTES = "notes"
    GUIDES = "guides"
    CODE = "code"
    OTHER = "other"


@dataclass
class Document:
    """Document data class."""

    id: str
    title: str
    content: str
    category: DocumentCategory = DocumentCategory.GENERAL
    doc_type: DocumentType = DocumentType.MARKDOWN
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    size: int = 0

    def __post_init__(self):
        """Calculate document size."""
        self.size = len(self.content.encode("utf-8"))

    def to_dict(self):
        """Convert document to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category.value,
            "doc_type": self.doc_type.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create document from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            category=DocumentCategory(data.get("category", "general")),
            doc_type=DocumentType(data.get("doc_type", "markdown")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            tags=data.get("tags", []),
            size=data.get("size", 0),
        )


class KnowledgeBaseManager:
    """Manages knowledge base operations."""

    def __init__(self, storage_path: str = ".freeco/knowledge_base.json"):
        """Initialize knowledge base manager.

        Args:
            storage_path: Path to store documents JSON file.
        """
        self.storage_path = storage_path
        self.documents: Dict[str, Document] = {}
        self._ensure_storage()
        self._load_documents()

    def _ensure_storage(self):
        """Ensure storage directory exists."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_documents(self):
        """Load documents from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self.documents = {
                        doc_id: Document.from_dict(doc_data)
                        for doc_id, doc_data in data.items()
                    }
            except Exception as e:
                print(f"Error loading documents: {e}")
                self.documents = {}

    def _save_documents(self):
        """Save documents to storage."""
        try:
            with open(self.storage_path, "w") as f:
                data = {doc_id: doc.to_dict() for doc_id, doc in self.documents.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving documents: {e}")

    def add_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        category: str = "general",
        doc_type: str = "markdown",
        tags: Optional[List[str]] = None,
    ) -> Document:
        """Add a document to knowledge base.

        Args:
            doc_id: Unique document identifier.
            title: Document title.
            content: Document content.
            category: Document category.
            doc_type: Document type.
            tags: Optional list of tags.

        Returns:
            Created Document object.
        """
        doc = Document(
            id=doc_id,
            title=title,
            content=content,
            category=DocumentCategory(category),
            doc_type=DocumentType(doc_type),
            tags=tags or [],
        )
        self.documents[doc_id] = doc
        self._save_documents()
        return doc

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID.

        Args:
            doc_id: Document identifier.

        Returns:
            Document object or None if not found.
        """
        return self.documents.get(doc_id)

    def list_documents(
        self,
        category: Optional[str] = None,
        doc_type: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Document]:
        """List documents with optional filtering.

        Args:
            category: Filter by category.
            doc_type: Filter by document type.
            tag: Filter by tag.

        Returns:
            List of filtered documents.
        """
        docs = list(self.documents.values())

        if category:
            docs = [d for d in docs if d.category.value == category]
        if doc_type:
            docs = [d for d in docs if d.doc_type.value == doc_type]
        if tag:
            docs = [d for d in docs if tag in d.tags]

        return sorted(docs, key=lambda d: d.created_at, reverse=True)

    def search_documents(self, query: str) -> List[Document]:
        """Search documents by title and content.

        Args:
            query: Search query string.

        Returns:
            List of matching documents sorted by relevance.
        """
        query_lower = query.lower()
        results = []

        for doc in self.documents.values():
            # Title match (higher relevance)
            if query_lower in doc.title.lower():
                results.append((doc, 2))
            # Content match (lower relevance)
            elif query_lower in doc.content.lower():
                results.append((doc, 1))

        # Sort by relevance score (descending) then by date (descending)
        results.sort(key=lambda x: (-x[1], -x[0].created_at.timestamp()))
        return [doc for doc, _ in results]

    def update_document(
        self,
        doc_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Document]:
        """Update a document.

        Args:
            doc_id: Document identifier.
            title: New title (optional).
            content: New content (optional).
            category: New category (optional).
            tags: New tags (optional).

        Returns:
            Updated Document object or None if not found.
        """
        doc = self.documents.get(doc_id)
        if not doc:
            return None

        if title:
            doc.title = title
        if content:
            doc.content = content
            doc.size = len(content.encode("utf-8"))
        if category:
            doc.category = DocumentCategory(category)
        if tags is not None:
            doc.tags = tags

        doc.updated_at = datetime.now()
        self._save_documents()
        return doc

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document.

        Args:
            doc_id: Document identifier.

        Returns:
            True if deleted, False if not found.
        """
        if doc_id in self.documents:
            del self.documents[doc_id]
            self._save_documents()
            return True
        return False

    def get_statistics(self) -> dict:
        """Get knowledge base statistics.

        Returns:
            Dictionary with statistics.
        """
        docs = list(self.documents.values())
        total_size = sum(doc.size for doc in docs)

        category_counts = {}
        for doc in docs:
            cat = doc.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "total_documents": len(docs),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "categories": category_counts,
            "document_types": {
                dt.value: len([d for d in docs if d.doc_type == dt])
                for dt in DocumentType
            },
            "average_doc_size": (round(total_size / len(docs), 2) if docs else 0),
        }

    def export_knowledge_base(self, export_path: str):
        """Export knowledge base to file.

        Args:
            export_path: Path to export to.
        """
        try:
            with open(export_path, "w") as f:
                data = {doc_id: doc.to_dict() for doc_id, doc in self.documents.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error exporting knowledge base: {e}")

    def import_knowledge_base(self, import_path: str):
        """Import knowledge base from file.

        Args:
            import_path: Path to import from.
        """
        try:
            with open(import_path, "r") as f:
                data = json.load(f)
                for doc_id, doc_data in data.items():
                    self.documents[doc_id] = Document.from_dict(doc_data)
                self._save_documents()
        except Exception as e:
            print(f"Error importing knowledge base: {e}")
