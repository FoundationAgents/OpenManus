"""
Code Quality Analyzer

Comprehensive code analysis for detecting:
- Stubs/placeholders
- Hacks/workarounds (халтура)
- Anti-patterns & code smells
- Incomplete implementations
- Planning quality issues
"""

import ast
import re
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from app.logger import logger


class IssueSeverity(str, Enum):
    """Issue severity levels"""
    CRITICAL = "CRITICAL"  # Blocks production
    HIGH = "HIGH"  # Should be fixed before merge
    MEDIUM = "MEDIUM"  # Should be fixed soon
    LOW = "LOW"  # Nice to fix


@dataclass
class CodeIssue:
    """Represents a code quality issue"""
    id: str
    type: str
    severity: IssueSeverity
    file_path: str
    line_number: int
    column: Optional[int]
    message: str
    root_cause: str
    suggestion: str
    auto_fixable: bool
    context: Optional[str] = None
    fix_snippet: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "location": f"{self.file_path}:{self.line_number}" + (f":{self.column}" if self.column else ""),
            "line_number": self.line_number,
            "column": self.column,
            "message": self.message,
            "root_cause": self.root_cause,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable,
            "context": self.context,
            "fix_snippet": self.fix_snippet
        }


class CodeAnalyzer:
    """Analyzes code for quality issues"""
    
    def __init__(self, qa_level: str = "standard"):
        self.qa_level = qa_level
        self.issue_counter = 0
        
        # Stub/placeholder patterns
        self.stub_patterns = [
            (r'\bpass\s*$', "Empty pass statement", IssueSeverity.HIGH),
            (r'^\s*\.\.\.\s*$', "Ellipsis placeholder", IssueSeverity.HIGH),
            (r'#\s*TODO:', "TODO comment", IssueSeverity.MEDIUM),
            (r'#\s*FIXME:', "FIXME comment", IssueSeverity.HIGH),
            (r'\bNotImplemented\b', "NotImplemented constant", IssueSeverity.HIGH),
            (r'raise\s+NotImplementedError', "NotImplementedError raised", IssueSeverity.CRITICAL),
        ]
        
        # Hack/workaround patterns (халтура)
        self.hack_patterns = [
            (r'#\s*HACK:', "Hack comment", IssueSeverity.HIGH),
            (r'#\s*XXX:', "XXX warning", IssueSeverity.HIGH),
            (r'while\s+True:\s*break', "Infinite loop with immediate break", IssueSeverity.HIGH),
            (r'if\s+False:', "Dead code (if False)", IssueSeverity.MEDIUM),
            (r'if\s+True:', "Always-true condition", IssueSeverity.MEDIUM),
            (r'except:\s*pass', "Silent exception catching", IssueSeverity.HIGH),
            (r'except\s+Exception:\s*pass', "Silent broad exception catching", IssueSeverity.HIGH),
        ]
        
        # Security patterns
        self.security_patterns = [
            (r'f["\']SELECT.*{', "Potential SQL injection (f-string)", IssueSeverity.CRITICAL),
            (r'\.format\(.*SELECT', "Potential SQL injection (.format)", IssueSeverity.CRITICAL),
            (r'%\s*\(.*SELECT', "Potential SQL injection (% formatting)", IssueSeverity.CRITICAL),
            (r'eval\(', "Use of eval() - code injection risk", IssueSeverity.CRITICAL),
            (r'exec\(', "Use of exec() - code injection risk", IssueSeverity.CRITICAL),
            (r'pickle\.loads?\(', "Pickle usage - deserialization risk", IssueSeverity.HIGH),
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password", IssueSeverity.CRITICAL),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key", IssueSeverity.CRITICAL),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret", IssueSeverity.CRITICAL),
        ]
        
        # Resource leak patterns
        self.resource_leak_patterns = [
            (r'open\([^)]+\)(?!.*with)', "File opened without with statement", IssueSeverity.HIGH),
            (r'requests\.(get|post|put|delete)\(', "HTTP request without timeout", IssueSeverity.MEDIUM),
        ]
    
    async def analyze_file(self, file_path: str, checks: List[str]) -> List[Dict[str, Any]]:
        """Analyze a single file for quality issues"""
        issues = []
        
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return issues
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Syntax validation
            if "syntax_validation" in checks:
                issues.extend(self._check_syntax(file_path, content))
            
            # Import check
            if "import_check" in checks:
                issues.extend(self._check_imports(file_path, content, lines))
            
            # Basic linting
            if "basic_linting" in checks:
                issues.extend(self._basic_lint(file_path, lines))
            
            # Code smell detection
            if "code_smell_detection" in checks:
                issues.extend(self._detect_code_smells(file_path, content, lines))
            
            # Naming convention check
            if "naming_convention_check" in checks:
                issues.extend(self._check_naming_conventions(file_path, content))
            
            # Error handling validation
            if "error_handling_validation" in checks:
                issues.extend(self._check_error_handling(file_path, content, lines))
            
            # Performance analysis
            if "performance_analysis" in checks:
                issues.extend(self._analyze_performance(file_path, content, lines))
            
            # Security scan
            if "security_scan" in checks:
                issues.extend(self._security_scan(file_path, content, lines))
            
            # Architectural pattern check
            if "architectural_pattern_check" in checks:
                issues.extend(self._check_architecture(file_path, content))
            
            # Documentation completeness
            if "documentation_completeness" in checks:
                issues.extend(self._check_documentation(file_path, content))
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            issues.append(self._create_issue(
                "analysis_error",
                IssueSeverity.MEDIUM,
                file_path,
                0,
                f"Analysis error: {str(e)}",
                "File could not be analyzed",
                "Check file encoding and syntax",
                False
            ).to_dict())
        
        return issues
    
    def _check_syntax(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Check Python syntax"""
        issues = []
        
        try:
            ast.parse(content)
        except SyntaxError as e:
            issues.append(self._create_issue(
                "syntax_error",
                IssueSeverity.CRITICAL,
                file_path,
                e.lineno or 0,
                f"Syntax error: {e.msg}",
                "Invalid Python syntax",
                "Fix syntax error before proceeding",
                False
            ).to_dict())
        
        return issues
    
    def _check_imports(self, file_path: str, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Check import statements"""
        issues = []
        
        try:
            tree = ast.parse(content)
            
            # Check for unused imports (simple check)
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imports.add(alias.name)
            
            # Check import order
            import_lines = [i for i, line in enumerate(lines) if line.strip().startswith('import ') or line.strip().startswith('from ')]
            if import_lines:
                # Check if imports are sorted
                import_strs = [lines[i].strip() for i in import_lines]
                sorted_imports = sorted(import_strs)
                if import_strs != sorted_imports:
                    issues.append(self._create_issue(
                        "import_order",
                        IssueSeverity.LOW,
                        file_path,
                        import_lines[0] + 1,
                        "Imports are not sorted",
                        "Unsorted imports reduce readability",
                        "Sort imports alphabetically",
                        True,
                        fix_snippet="Use isort or sort imports manually"
                    ).to_dict())
        
        except Exception as e:
            logger.debug(f"Import check error: {e}")
        
        return issues
    
    def _basic_lint(self, file_path: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Basic linting checks"""
        issues = []
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Line too long
            if len(line) > 120:
                issues.append(self._create_issue(
                    "line_too_long",
                    IssueSeverity.LOW,
                    file_path,
                    line_num,
                    f"Line too long ({len(line)} > 120 characters)",
                    "Long lines reduce readability",
                    "Split line into multiple lines",
                    True
                ).to_dict())
            
            # Trailing whitespace
            if line.endswith(' ') or line.endswith('\t'):
                issues.append(self._create_issue(
                    "trailing_whitespace",
                    IssueSeverity.LOW,
                    file_path,
                    line_num,
                    "Trailing whitespace",
                    "Trailing whitespace is unnecessary",
                    "Remove trailing whitespace",
                    True
                ).to_dict())
            
            # Multiple statements on one line
            if ';' in line and not line.strip().startswith('#'):
                issues.append(self._create_issue(
                    "multiple_statements",
                    IssueSeverity.MEDIUM,
                    file_path,
                    line_num,
                    "Multiple statements on one line",
                    "Multiple statements reduce readability",
                    "Put each statement on its own line",
                    True
                ).to_dict())
        
        return issues
    
    def _detect_code_smells(self, file_path: str, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Detect code smells and anti-patterns"""
        issues = []
        
        # Check for stubs/placeholders
        for i, line in enumerate(lines):
            line_num = i + 1
            for pattern, description, severity in self.stub_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Check if it's in a valid context (e.g., abstract method)
                    context_valid = self._is_valid_stub_context(lines, i)
                    if not context_valid:
                        issues.append(self._create_issue(
                            "stub_detected",
                            severity,
                            file_path,
                            line_num,
                            f"Stub/placeholder detected: {description}",
                            "Incomplete implementation",
                            "Implement the missing functionality",
                            False,
                            context=line.strip()
                        ).to_dict())
        
        # Check for hacks/workarounds
        for i, line in enumerate(lines):
            line_num = i + 1
            for pattern, description, severity in self.hack_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(self._create_issue(
                        "hack_detected",
                        severity,
                        file_path,
                        line_num,
                        f"Hack/workaround detected: {description}",
                        "Quick fix that should be refactored",
                        "Refactor to proper implementation",
                        False,
                        context=line.strip()
                    ).to_dict())
        
        # Check for magic numbers
        for i, line in enumerate(lines):
            line_num = i + 1
            # Skip comments and strings
            if not line.strip().startswith('#'):
                numbers = re.findall(r'\b(\d{2,})\b', line)
                for num in numbers:
                    if int(num) not in [0, 1, 10, 100, 1000]:  # Common acceptable numbers
                        issues.append(self._create_issue(
                            "magic_number",
                            IssueSeverity.MEDIUM,
                            file_path,
                            line_num,
                            f"Magic number detected: {num}",
                            "Unexplained numeric constant",
                            "Extract to named constant with explanation",
                            True,
                            context=line.strip()
                        ).to_dict())
        
        # Check for deep nesting
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    max_depth = self._calculate_nesting_depth(node)
                    if max_depth > 4:
                        issues.append(self._create_issue(
                            "deep_nesting",
                            IssueSeverity.MEDIUM,
                            file_path,
                            node.lineno,
                            f"Deep nesting detected (depth: {max_depth})",
                            "Excessive nesting reduces readability",
                            "Refactor to reduce nesting (early returns, extract methods)",
                            False,
                            context=f"Function: {node.name}"
                        ).to_dict())
        except Exception as e:
            logger.debug(f"Nesting check error: {e}")
        
        # Check for long functions
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_length = self._get_function_length(node, lines)
                    if func_length > 50:
                        issues.append(self._create_issue(
                            "long_function",
                            IssueSeverity.MEDIUM,
                            file_path,
                            node.lineno,
                            f"Long function detected ({func_length} lines)",
                            "Long functions are hard to understand and maintain",
                            "Break into smaller functions",
                            False,
                            context=f"Function: {node.name}"
                        ).to_dict())
        except Exception as e:
            logger.debug(f"Function length check error: {e}")
        
        # Check for God classes
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_length = self._get_class_length(node, lines)
                    if class_length > 500:
                        issues.append(self._create_issue(
                            "god_class",
                            IssueSeverity.HIGH,
                            file_path,
                            node.lineno,
                            f"God class detected ({class_length} lines)",
                            "Large classes violate Single Responsibility Principle",
                            "Break into smaller, focused classes",
                            False,
                            context=f"Class: {node.name}"
                        ).to_dict())
        except Exception as e:
            logger.debug(f"Class size check error: {e}")
        
        return issues
    
    def _check_naming_conventions(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Check naming conventions"""
        issues = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Check function names (should be snake_case)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not re.match(r'^[a-z_][a-z0-9_]*$', node.name) and not node.name.startswith('_'):
                        issues.append(self._create_issue(
                            "naming_convention",
                            IssueSeverity.LOW,
                            file_path,
                            node.lineno,
                            f"Function name '{node.name}' should be snake_case",
                            "Inconsistent naming reduces code readability",
                            "Rename to snake_case",
                            True,
                            context=f"Function: {node.name}"
                        ).to_dict())
                
                # Check class names (should be PascalCase)
                elif isinstance(node, ast.ClassDef):
                    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                        issues.append(self._create_issue(
                            "naming_convention",
                            IssueSeverity.LOW,
                            file_path,
                            node.lineno,
                            f"Class name '{node.name}' should be PascalCase",
                            "Inconsistent naming reduces code readability",
                            "Rename to PascalCase",
                            True,
                            context=f"Class: {node.name}"
                        ).to_dict())
        
        except Exception as e:
            logger.debug(f"Naming check error: {e}")
        
        return issues
    
    def _check_error_handling(self, file_path: str, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Check error handling"""
        issues = []
        
        # Check for bare except
        for i, line in enumerate(lines):
            line_num = i + 1
            if re.search(r'except\s*:', line):
                issues.append(self._create_issue(
                    "bare_except",
                    IssueSeverity.HIGH,
                    file_path,
                    line_num,
                    "Bare except clause",
                    "Catches all exceptions including system exits",
                    "Specify exception types",
                    True,
                    context=line.strip()
                ).to_dict())
        
        # Check for missing error handling on risky operations
        for i, line in enumerate(lines):
            line_num = i + 1
            for pattern in self.resource_leak_patterns:
                if re.search(pattern[0], line):
                    # Check if inside try-except
                    in_try_block = self._is_in_try_block(lines, i)
                    if not in_try_block:
                        issues.append(self._create_issue(
                            "missing_error_handling",
                            pattern[2],
                            file_path,
                            line_num,
                            pattern[1],
                            "Operation may fail without proper handling",
                            "Wrap in try-except or use with statement",
                            False,
                            context=line.strip()
                        ).to_dict())
        
        return issues
    
    def _analyze_performance(self, file_path: str, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Analyze performance issues"""
        issues = []
        
        # Check for inefficient operations
        performance_patterns = [
            (r'for\s+\w+\s+in\s+range\(len\(\w+\)\):', "Use enumerate() instead of range(len())", IssueSeverity.LOW),
            (r'\+\s*=.*\[', "String concatenation in loop (use list and join)", IssueSeverity.MEDIUM),
        ]
        
        for i, line in enumerate(lines):
            line_num = i + 1
            for pattern, message, severity in performance_patterns:
                if re.search(pattern, line):
                    issues.append(self._create_issue(
                        "performance_issue",
                        severity,
                        file_path,
                        line_num,
                        message,
                        "Inefficient operation",
                        "Use recommended alternative",
                        True,
                        context=line.strip()
                    ).to_dict())
        
        return issues
    
    def _security_scan(self, file_path: str, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Scan for security issues"""
        issues = []
        
        for i, line in enumerate(lines):
            line_num = i + 1
            for pattern, description, severity in self.security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(self._create_issue(
                        "security_issue",
                        severity,
                        file_path,
                        line_num,
                        f"Security issue: {description}",
                        "Potential security vulnerability",
                        "Use parameterized queries or secure alternatives",
                        False,
                        context=line.strip()
                    ).to_dict())
        
        return issues
    
    def _check_architecture(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Check architectural patterns"""
        issues = []
        
        # Check for tight coupling (excessive imports from same module)
        try:
            tree = ast.parse(content)
            imports_from = {}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imports_from[node.module] = imports_from.get(node.module, 0) + 1
            
            for module, count in imports_from.items():
                if count > 5:
                    issues.append(self._create_issue(
                        "tight_coupling",
                        IssueSeverity.MEDIUM,
                        file_path,
                        0,
                        f"Tight coupling detected: {count} imports from {module}",
                        "Excessive dependencies indicate tight coupling",
                        "Consider dependency injection or facade pattern",
                        False
                    ).to_dict())
        
        except Exception as e:
            logger.debug(f"Architecture check error: {e}")
        
        return issues
    
    def _check_documentation(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Check documentation completeness"""
        issues = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Check if has docstring
                    docstring = ast.get_docstring(node)
                    if not docstring:
                        node_type = "Function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "Class"
                        issues.append(self._create_issue(
                            "missing_docstring",
                            IssueSeverity.LOW,
                            file_path,
                            node.lineno,
                            f"{node_type} '{node.name}' missing docstring",
                            "Undocumented code is hard to understand",
                            "Add docstring describing purpose and parameters",
                            True,
                            context=f"{node_type}: {node.name}"
                        ).to_dict())
        
        except Exception as e:
            logger.debug(f"Documentation check error: {e}")
        
        return issues
    
    # Helper methods
    
    def _create_issue(
        self,
        issue_type: str,
        severity: IssueSeverity,
        file_path: str,
        line_number: int,
        message: str,
        root_cause: str,
        suggestion: str,
        auto_fixable: bool,
        column: Optional[int] = None,
        context: Optional[str] = None,
        fix_snippet: Optional[str] = None
    ) -> CodeIssue:
        """Create a code issue"""
        self.issue_counter += 1
        return CodeIssue(
            id=f"QA-{self.issue_counter:04d}",
            type=issue_type,
            severity=severity,
            file_path=file_path,
            line_number=line_number,
            column=column,
            message=message,
            root_cause=root_cause,
            suggestion=suggestion,
            auto_fixable=auto_fixable,
            context=context,
            fix_snippet=fix_snippet
        )
    
    def _is_valid_stub_context(self, lines: List[str], line_index: int) -> bool:
        """Check if stub is in valid context (e.g., abstract method)"""
        # Look backwards for decorator or class definition
        for i in range(max(0, line_index - 5), line_index):
            line = lines[i].strip()
            if '@abstractmethod' in line or '@abc.abstractmethod' in line:
                return True
            if 'class ' in line and 'ABC' in line:
                return True
        return False
    
    def _is_in_try_block(self, lines: List[str], line_index: int) -> bool:
        """Check if line is inside try block"""
        indent_level = len(lines[line_index]) - len(lines[line_index].lstrip())
        
        for i in range(line_index - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith('try:'):
                try_indent = len(lines[i]) - len(lines[i].lstrip())
                if try_indent < indent_level:
                    return True
        return False
    
    def _calculate_nesting_depth(self, node: ast.AST, depth: int = 0) -> int:
        """Calculate maximum nesting depth"""
        max_depth = depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _get_function_length(self, node: ast.FunctionDef, lines: List[str]) -> int:
        """Get function length in lines"""
        # Find end of function
        end_line = node.lineno
        for child in ast.walk(node):
            if hasattr(child, 'lineno'):
                end_line = max(end_line, child.lineno)
        
        return end_line - node.lineno + 1
    
    def _get_class_length(self, node: ast.ClassDef, lines: List[str]) -> int:
        """Get class length in lines"""
        end_line = node.lineno
        for child in ast.walk(node):
            if hasattr(child, 'lineno'):
                end_line = max(end_line, child.lineno)
        
        return end_line - node.lineno + 1
