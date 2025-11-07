# Language Registry Documentation

## Overview

The Language Registry is a service for managing programming language definitions and syntax highlighting configurations. It provides CRUD operations, schema validation, and persistence for language definitions.

## Key Features

- **Default Language Definitions**: Pre-configured definitions for Python, JavaScript, TypeScript, Go, Rust, SQL, and Bash
- **CRUD Operations**: Add, retrieve, update, and remove language definitions
- **File Extension Mapping**: Map file extensions to languages for automatic detection
- **Schema Validation**: Validate language definition schemas before persistence
- **Import/Export**: Load and save language definitions from/to JSON files
- **Thread-Safe**: Uses threading locks for safe concurrent access
- **Disk Persistence**: Automatically saves language definitions to `config/languages/` directory

## Language Definition Schema

Each language definition is a JSON file with the following structure:

```json
{
  "id": "python",
  "name": "Python",
  "file_extensions": [".py", ".pyw"],
  "keywords": ["def", "class", "if", "else", "for", "while", ...],
  "comments": {
    "line": "#",
    "block": ["\"\"\"", "\"\"\""]
  },
  "strings": {
    "single": "'",
    "double": "\"",
    "triple": "\"\"\""
  },
  "indentation": "spaces",
  "indent_size": 4,
  "color_scheme": "default",
  "syntax_rules": [
    {
      "pattern": "\\b\\d+\\b",
      "color": "#0066ff",
      "bold": false,
      "italic": false,
      "underline": false
    }
  ]
}
```

### Schema Fields

- **id** (required): Unique identifier for the language
- **name** (required): Human-readable name
- **file_extensions**: List of file extensions associated with the language
- **keywords**: List of language keywords for highlighting
- **comments**: Comment syntax (line and/or block)
- **strings**: String delimiters (single, double, triple, backtick, etc.)
- **indentation**: "spaces" or "tabs"
- **indent_size**: Number of spaces/tabs for indentation
- **color_scheme**: Color scheme identifier
- **syntax_rules**: List of syntax highlighting rules

## API Reference

### LanguageRegistry

Main service class for managing language definitions.

#### Methods

##### `get_language(language_id: str) -> Optional[Language]`

Get a language definition by ID.

```python
python_lang = registry.get_language("python")
if python_lang:
    print(f"Language: {python_lang.name}")
    print(f"Extensions: {python_lang.file_extensions}")
```

##### `get_language_by_extension(extension: str) -> Optional[Language]`

Get a language definition by file extension.

```python
lang = registry.get_language_by_extension(".py")
if lang:
    print(f"Language for .py files: {lang.name}")
```

##### `add_language(language: Language) -> bool`

Add or update a language definition.

```python
from app.languages.registry import Language

custom_lang = Language(
    id="custom",
    name="Custom Language",
    file_extensions=[".custom"],
    keywords=["key1", "key2"],
    comments={"line": "#"}
)

if registry.add_language(custom_lang):
    print("Language added successfully")
```

##### `remove_language(language_id: str) -> bool`

Remove a language definition.

```python
if registry.remove_language("custom"):
    print("Language removed")
```

##### `list_languages() -> List[Language]`

List all registered languages.

```python
all_languages = registry.list_languages()
for lang in all_languages:
    print(f"{lang.id}: {lang.name}")
```

##### `validate_language_schema(language_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]`

Validate a language definition schema.

```python
lang_data = {
    "id": "test",
    "name": "Test Language"
}

is_valid, error = registry.validate_language_schema(lang_data)
if not is_valid:
    print(f"Schema validation failed: {error}")
```

##### `import_language_from_json(json_path: str) -> bool`

Import a language definition from a JSON file.

```python
if registry.import_language_from_json("path/to/lang.json"):
    print("Language imported")
```

##### `export_language_to_json(language_id: str, output_path: str) -> bool`

Export a language definition to a JSON file.

```python
if registry.export_language_to_json("python", "output/python.json"):
    print("Language exported")
```

### Language Model

Represents a single language definition.

#### Fields

- `id`: Language identifier
- `name`: Human-readable name
- `file_extensions`: List of file extensions
- `keywords`: List of keywords
- `comments`: Comment syntax configuration
- `strings`: String delimiter configuration
- `indentation`: Indentation type
- `indent_size`: Indentation size
- `color_scheme`: Color scheme identifier
- `syntax_rules`: List of syntax highlighting rules

#### Methods

- `model_dump()`: Convert to dictionary
- `model_validate()`: Create from dictionary

## Usage Examples

### Creating a New Language

```python
from app.languages.registry import Language, get_language_registry

registry = get_language_registry()

ruby_lang = Language(
    id="ruby",
    name="Ruby",
    file_extensions=[".rb"],
    keywords=["def", "class", "if", "unless", "end", "require"],
    comments={"line": "#"},
    strings={"single": "'", "double": '"'},
    indentation="spaces",
    indent_size=2
)

registry.add_language(ruby_lang)
```

### Updating an Existing Language

```python
registry = get_language_registry()

python_lang = registry.get_language("python")
if python_lang:
    python_lang.keywords.append("walrus")
    registry.add_language(python_lang)
```

### Bulk Import Languages

```python
from pathlib import Path

registry = get_language_registry()

lang_dir = Path("path/to/language/definitions")
for json_file in lang_dir.glob("*.json"):
    registry.import_language_from_json(str(json_file))
```

### List All Supported File Extensions

```python
registry = get_language_registry()

extensions = {}
for lang in registry.list_languages():
    for ext in lang.file_extensions:
        extensions[ext] = lang.id

for ext, lang_id in sorted(extensions.items()):
    print(f"{ext} -> {lang_id}")
```

## Global Registry Instance

Use `get_language_registry()` to access the global singleton instance:

```python
from app.languages.registry import get_language_registry

registry = get_language_registry()

# Use registry...
```

The registry is thread-safe and can be safely accessed from multiple threads.

## Default Languages

The registry is pre-loaded with definitions for these languages:

| ID | Name | Extensions |
|---|---|---|
| python | Python | .py, .pyw |
| javascript | JavaScript | .js, .jsx, .mjs |
| typescript | TypeScript | .ts, .tsx |
| go | Go | .go |
| rust | Rust | .rs |
| sql | SQL | .sql |
| bash | Bash | .sh, .bash |

## Persistence

Language definitions are automatically persisted to the `config/languages/` directory as JSON files. Each language definition is saved in a separate file named `{language_id}.json`.

When the registry is initialized, it automatically loads all language definitions from the disk.

## Error Handling

The registry handles errors gracefully:

- Invalid JSON files are logged but don't crash the application
- Schema validation failures return error messages
- File I/O errors are caught and logged

## Performance Considerations

- The registry uses lazy loading for language definitions from disk
- Thread locks are used to ensure safe concurrent access
- Language lookups are O(1) operations using dictionaries

## Integration with Editor

The language registry is integrated with the CodeEditor component for automatic syntax highlighting:

```python
from app.ui.editor.code_editor import CodeEditor

editor = CodeEditor()
editor.set_file_path("script.py")  # Language detected automatically

# Or explicitly set language
editor.set_language("javascript")
```

## Future Enhancements

- LSP (Language Server Protocol) integration
- Custom color scheme definitions
- Advanced syntax rules with regex patterns
- Language inheritance for similar languages
- Plugin system for loading languages dynamically
- Web UI for language definition management
