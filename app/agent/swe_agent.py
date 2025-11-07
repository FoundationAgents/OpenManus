"""
Enhanced Software Engineering Agent for complex development tasks.
Provides advanced code analysis, debugging, testing, and project management capabilities.
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    from pydantic import Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Create dummy Field decorator
    def Field(default=None, **kwargs):
        return default

from app.agent.manus import Manus
from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.logger import logger
from app.prompt.swe import SYSTEM_PROMPT, ANALYSIS_PROMPT
from app.tool import ToolCollection
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.python_execute import PythonExecute
from app.tool.ask_human import AskHuman
from app.tool.terminate import Terminate


class CodeAnalyzer:
    """Advanced code analysis utilities."""
    
    @staticmethod
    def analyze_python_file(file_path: Path) -> Dict[str, Any]:
        """Analyze a Python file and extract structural information."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            analysis = {
                "file_path": str(file_path),
                "functions": [],
                "classes": [],
                "imports": [],
                "complexity_metrics": {},
                "dependencies": [],
                "docstrings": [],
                "type_hints": [],
                "potential_issues": []
            }
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        analysis["imports"].append(f"{module}.{alias.name}")
                        
            # Extract functions and classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "line_number": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "returns": ast.unparse(node.returns) if node.returns else None,
                        "docstring": ast.get_docstring(node),
                        "decorators": [ast.unparse(d) for d in node.decorator_list],
                        "is_async": isinstance(node, ast.AsyncFunctionDef)
                    }
                    analysis["functions"].append(func_info)
                    
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line_number": node.lineno,
                        "bases": [ast.unparse(base) for base in node.bases],
                        "methods": [],
                        "docstring": ast.get_docstring(node),
                        "decorators": [ast.unparse(d) for d in node.decorator_list]
                    }
                    
                    # Extract methods
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_info = {
                                "name": item.name,
                                "line_number": item.lineno,
                                "args": [arg.arg for arg in item.args.args],
                                "returns": ast.unparse(item.returns) if item.returns else None,
                                "docstring": ast.get_docstring(item),
                                "is_async": isinstance(item, ast.AsyncFunctionDef)
                            }
                            class_info["methods"].append(method_info)
                            
                    analysis["classes"].append(class_info)
                    
            # Calculate complexity metrics
            analysis["complexity_metrics"] = CodeAnalyzer.calculate_complexity(content)
            
            # Find potential issues
            analysis["potential_issues"] = CodeAnalyzer.find_issues(content, tree)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing Python file {file_path}: {e}")
            return {"error": str(e)}
            
    @staticmethod
    def calculate_complexity(content: str) -> Dict[str, int]:
        """Calculate basic complexity metrics."""
        lines = content.split('\n')
        code_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
        
        return {
            "total_lines": len(lines),
            "code_lines": len(code_lines),
            "comment_lines": len(lines) - len(code_lines),
            "functions": content.count('def '),
            "classes": content.count('class '),
            "imports": content.count('import ') + content.count('from '),
        }
        
    @staticmethod
    def find_issues(content: str, tree: ast.AST) -> List[str]:
        """Find potential issues in the code."""
        issues = []
        
        # Check for common issues
        if 'eval(' in content:
            issues.append("Use of eval() detected - potential security risk")
            
        if 'exec(' in content:
            issues.append("Use of exec() detected - potential security risk")
            
        if 'TODO:' in content or 'FIXME:' in content:
            issues.append("TODO/FIXME comments found - incomplete implementation")
            
        # Check for long functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                end_line = node.end_lineno or node.lineno
                if end_line - node.lineno > 50:
                    issues.append(f"Function '{node.name}' is too long ({end_line - node.lineno} lines)")
                    
        return issues


class ProjectManager:
    """Project management and analysis utilities."""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        
    def analyze_project_structure(self) -> Dict[str, Any]:
        """Analyze the overall project structure."""
        structure = {
            "root": str(self.workspace_root),
            "directories": [],
            "files": {},
            "languages": {},
            "dependencies": {},
            "entry_points": [],
            "test_files": [],
            "config_files": []
        }
        
        # Scan project structure
        for item in self.workspace_root.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(self.workspace_root)
                file_info = {
                    "path": str(rel_path),
                    "size": item.stat().st_size,
                    "extension": item.suffix,
                    "language": self.detect_language(item)
                }
                
                structure["files"][str(rel_path)] = file_info
                
                # Categorize files
                if item.suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c']:
                    lang = file_info["language"]
                    structure["languages"][lang] = structure["languages"].get(lang, 0) + 1
                    
                if any(name in rel_path.name.lower() for name in ['test', 'spec']):
                    structure["test_files"].append(str(rel_path))
                    
                if any(name in rel_path.name.lower() for name in ['main', 'app', 'index']):
                    structure["entry_points"].append(str(rel_path))
                    
                if any(name in rel_path.name.lower() for name in ['config', 'settings', 'env']):
                    structure["config_files"].append(str(rel_path))
                    
            elif item.is_dir():
                rel_path = item.relative_to(self.workspace_root)
                structure["directories"].append(str(rel_path))
                
        return structure
        
    def detect_language(self, file_path: Path) -> str:
        """Detect the programming language of a file."""
        suffix_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.html': 'HTML',
            '.css': 'CSS',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.xml': 'XML',
            '.md': 'Markdown',
            '.txt': 'Text'
        }
        
        return suffix_map.get(file_path.suffix.lower(), 'Unknown')
        
    def find_dependencies(self) -> Dict[str, List[str]]:
        """Find project dependencies."""
        dependencies = {}
        
        # Python dependencies
        requirements_files = list(self.workspace_root.glob("requirements*.txt"))
        for req_file in requirements_files:
            try:
                with open(req_file, 'r') as f:
                    deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    dependencies[f"requirements_{req_file.name}"] = deps
            except Exception as e:
                logger.error(f"Error reading {req_file}: {e}")
                
        # Package.json for Node.js
        package_json = self.workspace_root / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    deps = []
                    if 'dependencies' in data:
                        deps.extend(data['dependencies'].keys())
                    if 'devDependencies' in data:
                        deps.extend(data['devDependencies'].keys())
                    dependencies['package.json'] = deps
            except Exception as e:
                logger.error(f"Error reading package.json: {e}")
                
        return dependencies


class SWEAgent(ToolCallAgent):
    """Enhanced Software Engineering Agent."""
    
    name: str = "SWEAgent"
    description: str = "Advanced software engineering agent for complex development tasks"
    
    system_prompt: str = SYSTEM_PROMPT
    analysis_prompt: str = ANALYSIS_PROMPT
    
    max_observe: int = 15000
    max_steps: int = 30
    
    # Enhanced tool collection for SWE tasks
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            StrReplaceEditor(),
            PythonExecute(),
            AskHuman(),
            Terminate(),
        )
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        self.code_analyzer = CodeAnalyzer()
        self.project_manager = ProjectManager(config.workspace_root)
        
    async def analyze_codebase(self, directory: str = ".") -> Dict[str, Any]:
        """Analyze the entire codebase."""
        try:
            target_dir = config.workspace_root / directory
            
            if not target_dir.exists():
                return {"error": f"Directory {directory} does not exist"}
                
            analysis = {
                "project_structure": self.project_manager.analyze_project_structure(),
                "code_analysis": {},
                "recommendations": []
            }
            
            # Analyze Python files
            py_files = list(target_dir.rglob("*.py"))
            for py_file in py_files:
                file_analysis = self.code_analyzer.analyze_python_file(py_file)
                analysis["code_analysis"][str(py_file.relative_to(config.workspace_root))] = file_analysis
                
            # Generate recommendations
            analysis["recommendations"] = self.generate_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing codebase: {e}")
            return {"error": str(e)}
            
    def generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations based on analysis."""
        recommendations = []
        
        # Check for missing tests
        code_files = len([f for f in analysis["project_structure"]["files"].values() 
                         if f["language"] == "Python"])
        test_files = len(analysis["project_structure"]["test_files"])
        
        if test_files < code_files * 0.3:  # Less than 30% test coverage
            recommendations.append("Consider adding more unit tests - current test coverage appears low")
            
        # Check for complexity issues
        total_complexity = 0
        for file_analysis in analysis["code_analysis"].values():
            if "complexity_metrics" in file_analysis:
                total_complexity += file_analysis["complexity_metrics"].get("code_lines", 0)
                
        if total_complexity > 10000:  # Large codebase
            recommendations.append("Consider breaking down large modules into smaller, more focused ones")
            
        # Check for potential issues
        issues_found = 0
        for file_analysis in analysis["code_analysis"].values():
            if "potential_issues" in file_analysis:
                issues_found += len(file_analysis["potential_issues"])
                
        if issues_found > 0:
            recommendations.append(f"Address {issues_found} potential code issues found during analysis")
            
        return recommendations
        
    async def create_test_file(self, source_file: str, test_type: str = "unit") -> bool:
        """Create a test file for a given source file."""
        try:
            source_path = config.workspace_root / source_file
            
            if not source_path.exists():
                return False
                
            # Analyze the source file
            analysis = self.code_analyzer.analyze_python_file(source_path)
            
            if "error" in analysis:
                return False
                
            # Generate test file content
            test_content = self.generate_test_content(analysis, test_type)
            
            # Determine test file path
            test_path = self.get_test_file_path(source_path)
            
            # Write test file
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(test_content)
                
            return True
            
        except Exception as e:
            logger.error(f"Error creating test file: {e}")
            return False
            
    def generate_test_content(self, analysis: Dict[str, Any], test_type: str) -> str:
        """Generate test content based on code analysis."""
        content = [
            "import unittest",
            "import sys",
            "from pathlib import Path",
            "",
            "# Add the project root to the Python path",
            "sys.path.insert(0, str(Path(__file__).parent.parent))",
            ""
        ]
        
        # Import the module
        if "functions" in analysis or "classes" in analysis:
            module_name = Path(analysis["file_path"]).stem
            content.append(f"from {module_name} import *")
            content.append("")
            
        # Create test class
        content.append("class TestGenerated(unittest.TestCase):")
        content.append('    """Auto-generated test class."""')
        content.append("")
        
        # Add test methods for functions
        for func in analysis.get("functions", []):
            if not func["name"].startswith("_"):  # Don't test private functions
                test_method = self.generate_function_test(func)
                content.extend(test_method)
                content.append("")
                
        # Add test methods for classes
        for cls in analysis.get("classes", []):
            test_methods = self.generate_class_tests(cls)
            content.extend(test_methods)
            content.append("")
            
        content.extend([
            "",
            "if __name__ == '__main__':",
            "    unittest.main()"
        ])
        
        return "\n".join(content)
        
    def generate_function_test(self, func_info: Dict[str, Any]) -> List[str]:
        """Generate test method for a function."""
        func_name = func_info["name"]
        test_name = f"test_{func_name}"
        
        test_lines = [
            f"    def {test_name}(self):",
            f'        """Test the {func_name} function."""',
            "        # TODO: Implement test logic",
            "        pass"
        ]
        
        return test_lines
        
    def generate_class_tests(self, class_info: Dict[str, Any]) -> List[str]:
        """Generate test methods for a class."""
        class_name = class_info["name"]
        test_lines = [
            f"    def test_{class_name.lower()}_instantiation(self):",
            f'        """Test {class_name} class instantiation."""',
            "        # TODO: Implement test logic",
            "        pass",
            ""
        ]
        
        # Add tests for public methods
        for method in class_info.get("methods", []):
            if not method["name"].startswith("_"):
                method_test = f"    def test_{class_name.lower()}_{method['name'].lower()}(self):"
                test_lines.extend([
                    method_test,
                    f'        """Test {class_name}.{method["name"]} method."""',
                    "        # TODO: Implement test logic",
                    "        pass",
                    ""
                ])
                
        return test_lines
        
    def get_test_file_path(self, source_path: Path) -> Path:
        """Determine the appropriate test file path."""
        # Check for common test directory structures
        test_dirs = ["tests", "test"]
        
        for test_dir in test_dirs:
            test_path = config.workspace_root / test_dir
            if test_path.exists():
                # Mirror the source directory structure
                relative_path = source_path.relative_to(config.workspace_root)
                test_file_path = test_path / relative_path.with_name(f"{relative_path.stem}_test.py")
                test_file_path.parent.mkdir(parents=True, exist_ok=True)
                return test_file_path
                
        # If no test directory found, create test alongside source
        return source_path.with_name(f"{source_path.stem}_test.py")