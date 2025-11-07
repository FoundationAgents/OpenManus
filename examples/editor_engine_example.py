"""
Example usage of the Editor Engine components.

This example demonstrates how to use the code editor, language registry,
terminal widget, and diff viewer together.
"""

import sys
import tempfile
from pathlib import Path

try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget
    from PyQt6.QtCore import Qt
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    print("PyQt6 is not available. Install it with: pip install PyQt6")
    sys.exit(1)

from app.languages.registry import get_language_registry, Language
from app.ui.editor.code_editor import CodeEditor
from app.ui.editor.editor_container import EditorContainer
from app.ui.editor.terminal_widget import TerminalWidget
from app.ui.editor.diff_viewer import DiffViewer


class EditorEngineDemo(QMainWindow):
    """Main window for the Editor Engine demo."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editor Engine Demo")
        self.setGeometry(100, 100, 1400, 800)
        
        self.setup_ui()
        self.create_sample_files()
    
    def setup_ui(self):
        """Set up the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        tabs = QTabWidget()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            self.workspace_dir = temp_dir
            
            editor_container = EditorContainer(workspace_dir=self.workspace_dir)
            tabs.addTab(editor_container, "Editor")
            
            terminal = TerminalWidget(workspace_dir=self.workspace_dir)
            tabs.addTab(terminal, "Terminal")
            
            diff_viewer = DiffViewer()
            tabs.addTab(diff_viewer, "Diff Viewer")
            
            layout.addWidget(tabs)
    
    def create_sample_files(self):
        """Create sample files to demonstrate the editor."""
        workspace = Path(self.workspace_dir)
        
        python_file = workspace / "hello.py"
        python_file.write_text(
            '''def hello(name):
    """Say hello to someone."""
    print(f"Hello, {name}!")

if __name__ == "__main__":
    hello("World")
'''
        )
        
        js_file = workspace / "script.js"
        js_file.write_text(
            '''function greet(name) {
    console.log(`Hello, ${name}!`);
}

greet("JavaScript");
'''
        )
        
        sql_file = workspace / "query.sql"
        sql_file.write_text(
            '''SELECT id, name, email
FROM users
WHERE status = 'active'
ORDER BY created_at DESC;
'''
        )


def demonstrate_language_registry():
    """Demonstrate the language registry functionality."""
    print("\n=== Language Registry Demo ===\n")
    
    registry = get_language_registry()
    
    print("1. Available Languages:")
    for lang in registry.list_languages():
        print(f"   - {lang.name} ({lang.id}): {', '.join(lang.file_extensions)}")
    
    print("\n2. Language by Extension:")
    for ext in [".py", ".js", ".ts", ".go"]:
        lang = registry.get_language_by_extension(ext)
        if lang:
            print(f"   {ext} -> {lang.name}")
    
    print("\n3. Adding a Custom Language:")
    custom_lang = Language(
        id="custom",
        name="Custom Language",
        file_extensions=[".custom"],
        keywords=["keyword1", "keyword2"],
        comments={"line": "//"},
        strings={"single": "'", "double": '"'},
        indentation="spaces",
        indent_size=4
    )
    
    if registry.add_language(custom_lang):
        print(f"   ✓ Added {custom_lang.name}")
        
        retrieved = registry.get_language("custom")
        print(f"   ✓ Retrieved {retrieved.name}")
    
    print("\n4. Language Schema Validation:")
    valid_schema = {
        "id": "test",
        "name": "Test Language",
        "file_extensions": [".test"]
    }
    
    is_valid, error = registry.validate_language_schema(valid_schema)
    print(f"   Valid schema: {is_valid}")
    
    invalid_schema = {"name": "Test"}
    is_valid, error = registry.validate_language_schema(invalid_schema)
    print(f"   Invalid schema: {not is_valid}")
    if error:
        print(f"   Error: {error}")


def demonstrate_code_editor():
    """Demonstrate the code editor functionality."""
    print("\n=== Code Editor Demo ===\n")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("# Python code\ndef hello():\n    pass\n")
        temp_file = f.name
    
    try:
        editor = CodeEditor(file_path=temp_file)
        
        print("1. Loading file:")
        if editor.load_content():
            print(f"   ✓ Loaded {temp_file}")
        
        print("\n2. File properties:")
        print(f"   File path: {editor.file_path}")
        print(f"   Language: {editor.language_id}")
        print(f"   Modified: {editor.is_modified()}")
        
        print("\n3. Content operations:")
        content = editor.get_content()
        print(f"   Content length: {len(content)} chars")
        
        editor.insert_snippet("\n# New line")
        print(f"   ✓ Inserted snippet")
        
        print("\n4. Setting language:")
        editor.set_language("javascript")
        print(f"   ✓ Set language to {editor.language_id}")
    
    finally:
        import os
        os.unlink(temp_file)


def demonstrate_diff_viewer():
    """Demonstrate the diff viewer functionality."""
    print("\n=== Diff Viewer Demo ===\n")
    
    original = """def hello():
    print("Hello")
    return True
"""
    
    current = """def hello():
    print("Hello, World!")
    return False
"""
    
    print("1. Original content:")
    print(original)
    
    print("2. Current content:")
    print(current)
    
    print("\n3. Diff summary:")
    added, removed, changed = 0, 0, 0
    
    for i, (orig_line, curr_line) in enumerate(zip(original.split('\n'), current.split('\n'))):
        if orig_line != curr_line:
            changed += 1
            print(f"   - {orig_line}")
            print(f"   + {curr_line}")
    
    print(f"\n   Changed lines: {changed}")


def main():
    """Run the example."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Editor Engine Example")
    parser.add_argument("--demo", choices=["registry", "editor", "diff", "gui"],
                       default="gui", help="Which demo to run")
    
    args = parser.parse_args()
    
    if args.demo == "registry":
        demonstrate_language_registry()
    
    elif args.demo == "editor":
        demonstrate_code_editor()
    
    elif args.demo == "diff":
        demonstrate_diff_viewer()
    
    elif args.demo == "gui":
        if PYQT6_AVAILABLE:
            app = QApplication(sys.argv)
            window = EditorEngineDemo()
            window.show()
            sys.exit(app.exec())
        else:
            print("PyQt6 is required for GUI demo")
            demonstrate_language_registry()
            demonstrate_code_editor()
            demonstrate_diff_viewer()


if __name__ == "__main__":
    main()
