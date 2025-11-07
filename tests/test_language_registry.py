"""Unit tests for the LanguageRegistry module."""

import json
import tempfile
import unittest
from pathlib import Path

from app.languages.registry import (
    Language, LanguageRegistry, SyntaxRule, get_language_registry
)


class TestLanguageModel(unittest.TestCase):
    """Test cases for the Language model."""
    
    def test_create_language(self):
        """Test creating a language definition."""
        lang = Language(
            id="test",
            name="Test Language",
            file_extensions=[".test"],
            keywords=["if", "else", "def"],
            comments={"line": "#"},
            strings={"single": "'", "double": '"'}
        )
        
        self.assertEqual(lang.id, "test")
        self.assertEqual(lang.name, "Test Language")
        self.assertEqual(lang.file_extensions, [".test"])
        self.assertEqual(len(lang.keywords), 3)
    
    def test_language_serialization(self):
        """Test language serialization to dict."""
        lang = Language(
            id="python",
            name="Python",
            file_extensions=[".py"],
            keywords=["def", "class"]
        )
        
        data = lang.model_dump()
        self.assertEqual(data["id"], "python")
        self.assertEqual(data["name"], "Python")


class TestLanguageRegistry(unittest.TestCase):
    """Test cases for the LanguageRegistry."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.registry = LanguageRegistry(self.temp_dir)
    
    def tearDown(self):
        """Clean up after tests."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_registry_initialization(self):
        """Test registry initialization with default languages."""
        self.assertIsNotNone(self.registry.get_language("python"))
        self.assertIsNotNone(self.registry.get_language("javascript"))
        self.assertIsNotNone(self.registry.get_language("go"))
        self.assertIsNotNone(self.registry.get_language("rust"))
    
    def test_get_language_by_id(self):
        """Test getting a language by ID."""
        lang = self.registry.get_language("python")
        self.assertIsNotNone(lang)
        self.assertEqual(lang.name, "Python")
        self.assertIn(".py", lang.file_extensions)
    
    def test_get_language_by_extension(self):
        """Test getting a language by file extension."""
        lang = self.registry.get_language_by_extension(".py")
        self.assertIsNotNone(lang)
        self.assertEqual(lang.id, "python")
        
        lang = self.registry.get_language_by_extension(".js")
        self.assertIsNotNone(lang)
        self.assertEqual(lang.id, "javascript")
    
    def test_add_language(self):
        """Test adding a new language."""
        lang = Language(
            id="custom",
            name="Custom Language",
            file_extensions=[".custom"],
            keywords=["test"]
        )
        
        result = self.registry.add_language(lang)
        self.assertTrue(result)
        
        retrieved = self.registry.get_language("custom")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Custom Language")
    
    def test_remove_language(self):
        """Test removing a language."""
        lang = Language(
            id="removable",
            name="Removable",
            file_extensions=[".rmv"]
        )
        
        self.registry.add_language(lang)
        self.assertIsNotNone(self.registry.get_language("removable"))
        
        result = self.registry.remove_language("removable")
        self.assertTrue(result)
        self.assertIsNone(self.registry.get_language("removable"))
    
    def test_list_languages(self):
        """Test listing all languages."""
        languages = self.registry.list_languages()
        self.assertTrue(len(languages) > 0)
        
        lang_ids = [lang.id for lang in languages]
        self.assertIn("python", lang_ids)
        self.assertIn("javascript", lang_ids)
    
    def test_validate_language_schema(self):
        """Test language schema validation."""
        valid_data = {
            "id": "test",
            "name": "Test",
            "file_extensions": [".test"]
        }
        
        is_valid, error = self.registry.validate_language_schema(valid_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        invalid_data = {"name": "Test"}
        
        is_valid, error = self.registry.validate_language_schema(invalid_data)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_persist_language(self):
        """Test persisting a language to disk."""
        lang = Language(
            id="persistent",
            name="Persistent Language",
            file_extensions=[".persist"],
            keywords=["key1", "key2"]
        )
        
        self.registry.add_language(lang)
        
        json_file = Path(self.temp_dir) / "persistent.json"
        self.assertTrue(json_file.exists())
        
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["id"], "persistent")
        self.assertEqual(data["name"], "Persistent Language")
    
    def test_import_language_from_json(self):
        """Test importing a language from a JSON file."""
        lang_data = {
            "id": "imported",
            "name": "Imported Language",
            "file_extensions": [".imp"],
            "keywords": ["import", "export"]
        }
        
        json_file = Path(self.temp_dir) / "import.json"
        with open(json_file, 'w') as f:
            json.dump(lang_data, f)
        
        result = self.registry.import_language_from_json(str(json_file))
        self.assertTrue(result)
        
        lang = self.registry.get_language("imported")
        self.assertIsNotNone(lang)
        self.assertEqual(lang.name, "Imported Language")
    
    def test_export_language_to_json(self):
        """Test exporting a language to a JSON file."""
        output_file = Path(self.temp_dir) / "export.json"
        
        result = self.registry.export_language_to_json("python", str(output_file))
        self.assertTrue(result)
        self.assertTrue(output_file.exists())
        
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["id"], "python")
        self.assertEqual(data["name"], "Python")
    
    def test_get_language_registry_singleton(self):
        """Test that get_language_registry returns a singleton."""
        registry1 = get_language_registry(self.temp_dir)
        registry2 = get_language_registry(self.temp_dir)
        
        self.assertIs(registry1, registry2)


class TestSyntaxRule(unittest.TestCase):
    """Test cases for the SyntaxRule model."""
    
    def test_create_syntax_rule(self):
        """Test creating a syntax rule."""
        rule = SyntaxRule(
            pattern=r"\b\d+\b",
            color="#0066ff",
            bold=True
        )
        
        self.assertEqual(rule.pattern, r"\b\d+\b")
        self.assertEqual(rule.color, "#0066ff")
        self.assertTrue(rule.bold)


if __name__ == '__main__':
    unittest.main()
