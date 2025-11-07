# Editor Engine Documentation

## Overview

The Editor Engine provides a rich code editing experience with syntax highlighting, language registration, terminal integration, and diff viewing capabilities.

## Components

### 1. CodeEditor

A feature-rich code editor based on QPlainTextEdit with the following features:

- **Syntax Highlighting**: Language-aware syntax highlighting using QSyntaxHighlighter
- **Line Numbers**: Visual line numbering with automatic width calculation
- **Text Operations**: Load, save, and manage file content
- **Language Detection**: Automatic language detection based on file extension
- **Content Tracking**: Tracks modifications to content

#### Usage

```python
from app.ui.editor.code_editor import CodeEditor

editor = CodeEditor()
editor.set_file_path("script.py")
editor.load_content()

# Get content
content = editor.get_content()

# Save content
editor.save_content()

# Set language for syntax highlighting
editor.set_language("javascript")
```

### 2. EditorContainer

Manages multiple editor tabs with file tree integration:

- **Tab Management**: Open multiple files in tabs
- **File Tree**: Visual file browser for the workspace
- **Save/Close Operations**: Handle file lifecycle
- **Workspace Integration**: Seamless integration with workspace directory

#### Usage

```python
from app.ui.editor.editor_container import EditorContainer

container = EditorContainer(workspace_dir="./workspace")
container.open_file("path/to/file.py")
container.save_current_file()

editor = container.get_current_editor()
content = editor.get_content()
```

### 3. LanguageRegistry

Service for managing language definitions:

- **Language Definitions**: Register and manage language syntax rules
- **CRUD Operations**: Add, update, remove, and retrieve languages
- **File Extension Mapping**: Map file extensions to languages
- **Schema Validation**: Validate language definition schemas
- **Import/Export**: Load and save language definitions from/to JSON

#### Usage

```python
from app.languages.registry import get_language_registry

registry = get_language_registry()

# Get a language by ID
python_lang = registry.get_language("python")

# Get a language by file extension
lang = registry.get_language_by_extension(".js")

# Add a custom language
from app.languages.registry import Language

custom = Language(
    id="custom",
    name="Custom Language",
    file_extensions=[".custom"],
    keywords=["keyword1", "keyword2"]
)
registry.add_language(custom)

# List all languages
all_languages = registry.list_languages()
```

### 4. TerminalWidget

Integrated terminal widget for executing commands:

- **Command Execution**: Execute commands via LocalService
- **Output Display**: Color-coded stdout/stderr/info output
- **Process Management**: Kill and manage running processes
- **Async Execution**: Non-blocking command execution

#### Usage

```python
from app.ui.editor.terminal_widget import TerminalWidget

terminal = TerminalWidget(workspace_dir="./workspace")
terminal.execute_command("python script.py")
terminal.set_workspace_dir("/new/path")
```

### 5. DiffViewer

Diff viewer for comparing file versions:

- **Diff Computation**: Compare current vs original content
- **Visualization**: Color-coded diff display
- **Summary Statistics**: Get added/removed/changed line counts
- **Export**: Save diffs to files

#### Usage

```python
from app.ui.editor.diff_viewer import DiffViewer

viewer = DiffViewer()
viewer.set_content(current_content, original_content)

added, removed, changed = viewer.get_diff_summary()
viewer.export_diff("output.diff")
```

## Language Registry

### Default Languages

The registry comes with default language definitions for:

- **Python** (.py, .pyw)
- **JavaScript** (.js, .jsx, .mjs)
- **TypeScript** (.ts, .tsx)
- **Go** (.go)
- **Rust** (.rs)
- **SQL** (.sql)
- **Bash** (.sh, .bash)

### Language Definition Schema

```python
{
    "id": "python",
    "name": "Python",
    "file_extensions": [".py", ".pyw"],
    "keywords": ["def", "class", "if", ...],
    "comments": {
        "line": "#"
    },
    "strings": {
        "single": "'",
        "double": "\"",
        "triple": "\"\"\""
    },
    "indentation": "spaces",
    "indent_size": 4,
    "color_scheme": "default"
}
```

## Configuration

### Persist Settings

Language registry persists definitions in `config/languages/` directory as JSON files.

### UISettings

Add to `app/config.py`:

```python
class EditorSettings(BaseModel):
    enable_editor: bool = Field(True, description="Enable code editor")
    default_language: str = Field("python", description="Default language")
    default_theme: str = Field("default", description="Default theme")
    auto_save: bool = Field(True, description="Auto-save files")
    auto_save_interval: int = Field(60, description="Auto-save interval in seconds")
```

## Architecture

### Threading

- Terminal command execution uses QThread for non-blocking operations
- Language registry uses threading.RLock for thread-safe operations
- Syntax highlighting is performed on the main Qt thread

### Signals

- `CodeEditor.content_changed`: Emitted when editor content changes
- `CodeEditor.file_path_changed`: Emitted when file path is changed
- `EditorContainer.file_opened`: Emitted when a file is opened
- `EditorContainer.file_saved`: Emitted when a file is saved
- `EditorContainer.file_closed`: Emitted when a file is closed
- `DiffViewer.file_reverted`: Emitted when changes are reverted

## Testing

Run the unit tests:

```bash
python -m pytest tests/test_language_registry.py
python -m pytest tests/test_code_editor.py
python -m pytest tests/test_diff_viewer.py
python -m pytest tests/test_terminal_widget.py
```

## Future Enhancements

- LSP (Language Server Protocol) integration for IntelliSense
- More syntax highlighters for additional languages
- Bracket matching and auto-completion
- Code folding visualization
- Theme customization UI
- Plugin system for language definitions
- Terminal tab management
- Search and replace functionality
- Code formatting integration
