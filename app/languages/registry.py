"""Language Registry service for managing language definitions and syntax highlighting."""

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

from app.logger import logger


class SyntaxRule(BaseModel):
    """Represents a single syntax highlighting rule."""
    pattern: str
    color: str = "#000000"
    bold: bool = False
    italic: bool = False
    underline: bool = False


class Language(BaseModel):
    """Represents a programming language definition."""
    id: str
    name: str
    file_extensions: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    comments: Dict[str, Union[str, List[str]]] = Field(default_factory=dict)  # e.g., {"line": "//", "block": ["/*", "*/"]}
    strings: Dict[str, str] = Field(default_factory=dict)  # e.g., {"single": "'", "double": '"'}
    syntax_rules: List[SyntaxRule] = Field(default_factory=list)
    indentation: str = "spaces"  # "spaces" or "tabs"
    indent_size: int = 4
    color_scheme: str = "default"
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "python",
                "name": "Python",
                "file_extensions": [".py", ".pyw"],
                "keywords": ["def", "class", "if", "else", "for", "while", "import"],
                "comments": {"line": "#"},
                "strings": {"single": "'", "double": '"'},
                "indentation": "spaces",
                "indent_size": 4
            }
        }


class LanguageRegistry:
    """Manages language definitions and provides CRUD operations."""
    
    def __init__(self, config_dir: str = "config/languages"):
        """Initialize the language registry.
        
        Args:
            config_dir: Directory path where language definitions are stored.
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self._languages: Dict[str, Language] = {}
        self._lock = threading.RLock()
        
        self._load_default_languages()
        self._load_from_disk()
        
    def _load_default_languages(self) -> None:
        """Load default language definitions."""
        defaults = {
            "python": {
                "id": "python",
                "name": "Python",
                "file_extensions": [".py", ".pyw"],
                "keywords": ["def", "class", "if", "elif", "else", "for", "while", "try", "except", "finally", "import", "from", "as", "return", "yield", "with", "lambda"],
                "comments": {"line": "#"},
                "strings": {"single": "'", "double": '"', "triple": '"""'},
                "indentation": "spaces",
                "indent_size": 4,
            },
            "javascript": {
                "id": "javascript",
                "name": "JavaScript",
                "file_extensions": [".js", ".jsx", ".mjs"],
                "keywords": ["function", "class", "if", "else", "for", "while", "do", "switch", "case", "try", "catch", "finally", "return", "const", "let", "var", "async", "await", "import", "export"],
                "comments": {"line": "//", "block": ["/*", "*/"]},
                "strings": {"single": "'", "double": '"', "template": "`"},
                "indentation": "spaces",
                "indent_size": 2,
            },
            "typescript": {
                "id": "typescript",
                "name": "TypeScript",
                "file_extensions": [".ts", ".tsx"],
                "keywords": ["function", "class", "interface", "type", "if", "else", "for", "while", "do", "switch", "case", "try", "catch", "finally", "return", "const", "let", "var", "async", "await", "import", "export"],
                "comments": {"line": "//", "block": ["/*", "*/"]},
                "strings": {"single": "'", "double": '"', "template": "`"},
                "indentation": "spaces",
                "indent_size": 2,
            },
            "go": {
                "id": "go",
                "name": "Go",
                "file_extensions": [".go"],
                "keywords": ["func", "package", "import", "if", "else", "for", "switch", "case", "default", "return", "defer", "go", "chan", "select", "interface", "struct", "type", "const", "var"],
                "comments": {"line": "//", "block": ["/*", "*/"]},
                "strings": {"single": "'", "double": '"', "backtick": "`"},
                "indentation": "tabs",
                "indent_size": 1,
            },
            "rust": {
                "id": "rust",
                "name": "Rust",
                "file_extensions": [".rs"],
                "keywords": ["fn", "let", "mut", "const", "static", "struct", "enum", "trait", "impl", "if", "else", "for", "while", "loop", "match", "return", "use", "mod", "crate", "pub", "async", "await"],
                "comments": {"line": "//", "block": ["/*", "*/"]},
                "strings": {"single": "'", "double": '"'},
                "indentation": "spaces",
                "indent_size": 4,
            },
            "sql": {
                "id": "sql",
                "name": "SQL",
                "file_extensions": [".sql"],
                "keywords": ["SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "TABLE", "INDEX", "VIEW", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "GROUP", "BY", "ORDER", "ASC", "DESC"],
                "comments": {"line": "--", "block": ["/*", "*/"]},
                "strings": {"single": "'", "double": '"'},
                "indentation": "spaces",
                "indent_size": 2,
            },
            "bash": {
                "id": "bash",
                "name": "Bash",
                "file_extensions": [".sh", ".bash"],
                "keywords": ["if", "then", "else", "elif", "fi", "for", "do", "done", "while", "case", "esac", "function", "return", "export", "local", "readonly", "declare"],
                "comments": {"line": "#"},
                "strings": {"single": "'", "double": '"'},
                "indentation": "spaces",
                "indent_size": 4,
            },
        }
        
        with self._lock:
            for lang_id, lang_data in defaults.items():
                if lang_id not in self._languages:
                    self._languages[lang_id] = Language(**lang_data)
    
    def _load_from_disk(self) -> None:
        """Load language definitions from disk."""
        with self._lock:
            for json_file in self.config_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        lang_data = json.load(f)
                        language = Language(**lang_data)
                        self._languages[language.id] = language
                        logger.info(f"Loaded language definition: {language.name}")
                except Exception as e:
                    logger.error(f"Error loading language definition from {json_file}: {e}")
    
    def get_language(self, language_id: str) -> Optional[Language]:
        """Get a language definition by ID.
        
        Args:
            language_id: The language identifier.
            
        Returns:
            Language definition or None if not found.
        """
        with self._lock:
            return self._languages.get(language_id)
    
    def get_language_by_extension(self, extension: str) -> Optional[Language]:
        """Get a language definition by file extension.
        
        Args:
            extension: File extension (e.g., ".py", ".js").
            
        Returns:
            Language definition or None if not found.
        """
        with self._lock:
            for language in self._languages.values():
                if extension.lower() in [ext.lower() for ext in language.file_extensions]:
                    return language
        return None
    
    def add_language(self, language: Language) -> bool:
        """Add or update a language definition.
        
        Args:
            language: Language definition to add.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            with self._lock:
                self._languages[language.id] = language
                self._persist_language(language)
                logger.info(f"Added language: {language.name}")
                return True
        except Exception as e:
            logger.error(f"Error adding language {language.id}: {e}")
            return False
    
    def remove_language(self, language_id: str) -> bool:
        """Remove a language definition.
        
        Args:
            language_id: The language identifier to remove.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            with self._lock:
                if language_id in self._languages:
                    del self._languages[language_id]
                    
                    json_file = self.config_dir / f"{language_id}.json"
                    if json_file.exists():
                        json_file.unlink()
                    
                    logger.info(f"Removed language: {language_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error removing language {language_id}: {e}")
            return False
    
    def list_languages(self) -> List[Language]:
        """List all registered languages.
        
        Returns:
            List of Language definitions.
        """
        with self._lock:
            return list(self._languages.values())
    
    def validate_language_schema(self, language_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate a language definition schema.
        
        Args:
            language_data: Dictionary containing language definition data.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            required_fields = ["id", "name"]
            for field in required_fields:
                if field not in language_data:
                    return False, f"Missing required field: {field}"
            
            Language(**language_data)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def _persist_language(self, language: Language) -> None:
        """Persist a language definition to disk.
        
        Args:
            language: Language definition to persist.
        """
        json_file = self.config_dir / f"{language.id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(language.model_dump(), f, indent=2)
    
    def import_language_from_json(self, json_path: str) -> bool:
        """Import a language definition from a JSON file.
        
        Args:
            json_path: Path to the JSON file.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                lang_data = json.load(f)
            
            is_valid, error = self.validate_language_schema(lang_data)
            if not is_valid:
                logger.error(f"Invalid language schema: {error}")
                return False
            
            language = Language(**lang_data)
            return self.add_language(language)
        except Exception as e:
            logger.error(f"Error importing language from {json_path}: {e}")
            return False
    
    def export_language_to_json(self, language_id: str, output_path: str) -> bool:
        """Export a language definition to a JSON file.
        
        Args:
            language_id: The language identifier.
            output_path: Path where to save the JSON file.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            language = self.get_language(language_id)
            if not language:
                return False
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(language.model_dump(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error exporting language {language_id}: {e}")
            return False


# Global registry instance
_registry_instance: Optional[LanguageRegistry] = None
_registry_lock = threading.Lock()


def get_language_registry(config_dir: str = "config/languages") -> LanguageRegistry:
    """Get or create the global language registry instance.
    
    Args:
        config_dir: Directory path where language definitions are stored.
        
    Returns:
        The global LanguageRegistry instance.
    """
    global _registry_instance
    
    if _registry_instance is None:
        with _registry_lock:
            if _registry_instance is None:
                _registry_instance = LanguageRegistry(config_dir)
    
    return _registry_instance
