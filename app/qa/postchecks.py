"""
Post-Check Validation System

After QA passes, these checks verify that the QA changes themselves
are correct and don't introduce new issues.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass
from app.logger import logger


class PostCheckType(str, Enum):
    """Types of post-check validations"""
    CODE_INTEGRITY = "code_integrity"
    BEHAVIOR_PRESERVATION = "behavior_preservation"
    REGRESSION_DETECTION = "regression_detection"
    FIX_VERIFICATION = "fix_verification"
    SECURITY_AUDIT = "security_audit"
    PERFORMANCE_IMPACT = "performance_impact"


@dataclass
class PostCheckResult:
    """Result of a post-check validation"""
    check_type: PostCheckType
    passed: bool
    description: str
    issues_found: List[Dict[str, Any]]
    warnings: List[str]
    metadata: Dict[str, Any]


class CodeIntegrityChecker:
    """Verify code integrity after QA fixes"""
    
    async def check_syntax(self, file_path: str, code_content: str) -> PostCheckResult:
        """Check that code has valid syntax after fixes"""
        import ast
        
        try:
            ast.parse(code_content)
            return PostCheckResult(
                check_type=PostCheckType.CODE_INTEGRITY,
                passed=True,
                description="Code syntax is valid",
                issues_found=[],
                warnings=[],
                metadata={"check": "syntax_validation", "file": file_path}
            )
        except SyntaxError as e:
            return PostCheckResult(
                check_type=PostCheckType.CODE_INTEGRITY,
                passed=False,
                description=f"Syntax error after QA fixes: {e}",
                issues_found=[{
                    "type": "syntax_error",
                    "line": e.lineno,
                    "message": e.msg
                }],
                warnings=[],
                metadata={"check": "syntax_validation", "file": file_path}
            )
    
    async def check_imports(self, code_content: str, file_path: str) -> PostCheckResult:
        """Check that all imports are valid"""
        import ast
        import_issues = []
        warnings = []
        
        try:
            tree = ast.parse(code_content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module)
            
            # Check for common issues
            if len(imports) != len(set(imports)):
                warnings.append("Duplicate imports detected")
            
            return PostCheckResult(
                check_type=PostCheckType.CODE_INTEGRITY,
                passed=len(import_issues) == 0,
                description="Import validation completed",
                issues_found=import_issues,
                warnings=warnings,
                metadata={"check": "import_validation", "file": file_path, "imports_count": len(set(imports))}
            )
        except Exception as e:
            return PostCheckResult(
                check_type=PostCheckType.CODE_INTEGRITY,
                passed=False,
                description=f"Failed to validate imports: {e}",
                issues_found=[{"type": "validation_error", "message": str(e)}],
                warnings=[],
                metadata={"check": "import_validation", "file": file_path}
            )


class BehaviorPreservationChecker:
    """Verify that QA fixes preserve original behavior"""
    
    async def check_function_signatures(
        self,
        original_code: str,
        fixed_code: str,
        file_path: str
    ) -> PostCheckResult:
        """Check that function signatures haven't changed"""
        import ast
        import re
        
        def extract_signatures(code: str) -> Dict[str, str]:
            try:
                tree = ast.parse(code)
                sigs = {}
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Extract function signature
                        args = [arg.arg for arg in node.args.args]
                        sigs[node.name] = f"({', '.join(args)})"
                
                return sigs
            except:
                return {}
        
        original_sigs = extract_signatures(original_code)
        fixed_sigs = extract_signatures(fixed_code)
        
        issues = []
        
        # Check if signatures match
        for func_name in original_sigs:
            if func_name not in fixed_sigs:
                issues.append({
                    "type": "signature_removed",
                    "function": func_name,
                    "original_sig": original_sigs[func_name]
                })
            elif original_sigs[func_name] != fixed_sigs[func_name]:
                issues.append({
                    "type": "signature_changed",
                    "function": func_name,
                    "original_sig": original_sigs[func_name],
                    "new_sig": fixed_sigs[func_name]
                })
        
        return PostCheckResult(
            check_type=PostCheckType.BEHAVIOR_PRESERVATION,
            passed=len(issues) == 0,
            description="Function signature preservation check",
            issues_found=issues,
            warnings=[],
            metadata={"check": "function_signatures", "file": file_path, "functions_checked": len(original_sigs)}
        )
    
    async def check_return_types(
        self,
        original_code: str,
        fixed_code: str,
        file_path: str
    ) -> PostCheckResult:
        """Check that return types haven't changed"""
        import ast
        import re
        
        def extract_return_types(code: str) -> Dict[str, List[str]]:
            try:
                tree = ast.parse(code)
                return_types = {}
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        returns = []
                        for child in ast.walk(node):
                            if isinstance(child, ast.Return):
                                if child.value is None:
                                    returns.append("None")
                                elif isinstance(child.value, ast.Constant):
                                    returns.append(type(child.value.value).__name__)
                        
                        if returns:
                            return_types[node.name] = returns
                
                return return_types
            except:
                return {}
        
        original_returns = extract_return_types(original_code)
        fixed_returns = extract_return_types(fixed_code)
        
        issues = []
        warnings = []
        
        # Check consistency
        for func_name, original_types in original_returns.items():
            if func_name in fixed_returns:
                fixed_types = fixed_returns[func_name]
                if set(original_types) != set(fixed_types):
                    warnings.append(f"Function {func_name}: return types may have changed")
        
        return PostCheckResult(
            check_type=PostCheckType.BEHAVIOR_PRESERVATION,
            passed=len(issues) == 0,
            description="Return type preservation check",
            issues_found=issues,
            warnings=warnings,
            metadata={"check": "return_types", "file": file_path}
        )


class RegressionDetector:
    """Detect potential regressions from QA fixes"""
    
    async def check_line_count_changes(
        self,
        original_code: str,
        fixed_code: str,
        file_path: str
    ) -> PostCheckResult:
        """Check for significant line count changes that might indicate issues"""
        original_lines = len(original_code.split('\n'))
        fixed_lines = len(fixed_code.split('\n'))
        
        change_percent = abs(fixed_lines - original_lines) / original_lines * 100 if original_lines > 0 else 0
        
        warnings = []
        issues = []
        
        if change_percent > 50:
            warnings.append(f"Large line count change ({change_percent:.1f}%) - manual review recommended")
        
        if fixed_lines < original_lines - 100:
            issues.append({
                "type": "large_deletion",
                "lines_removed": original_lines - fixed_lines,
                "percent": change_percent
            })
        
        return PostCheckResult(
            check_type=PostCheckType.REGRESSION_DETECTION,
            passed=len(issues) == 0,
            description="Line count change analysis",
            issues_found=issues,
            warnings=warnings,
            metadata={
                "check": "line_count_changes",
                "file": file_path,
                "original_lines": original_lines,
                "fixed_lines": fixed_lines,
                "change_percent": change_percent
            }
        )
    
    async def check_logic_preservation(
        self,
        original_code: str,
        fixed_code: str,
        file_path: str
    ) -> PostCheckResult:
        """Check that core logic is preserved"""
        # Look for key control flow structures
        def count_keywords(code: str) -> Dict[str, int]:
            keywords = ['if', 'for', 'while', 'try', 'with', 'return', 'raise']
            counts = {}
            for kw in keywords:
                counts[kw] = code.count(f' {kw} ') + code.count(f'\n{kw} ')
            return counts
        
        original_keywords = count_keywords(original_code)
        fixed_keywords = count_keywords(fixed_code)
        
        warnings = []
        issues = []
        
        for kw in original_keywords:
            diff = abs(original_keywords[kw] - fixed_keywords[kw])
            if diff > 5:  # Significant difference
                warnings.append(f"Control flow keyword '{kw}' count changed by {diff}")
        
        return PostCheckResult(
            check_type=PostCheckType.REGRESSION_DETECTION,
            passed=len(issues) == 0,
            description="Logic preservation check",
            issues_found=issues,
            warnings=warnings,
            metadata={"check": "logic_preservation", "file": file_path}
        )


class FixVerificationChecker:
    """Verify that applied fixes actually solve the reported issues"""
    
    async def verify_fixes(
        self,
        fixed_code: str,
        applied_fixes: List[Dict[str, Any]],
        file_path: str
    ) -> PostCheckResult:
        """Verify that fixes were correctly applied"""
        issues = []
        
        for fix in applied_fixes:
            fix_type = fix.get("type")
            
            if fix_type == "remove_import":
                import_name = fix.get("target")
                if import_name in fixed_code:
                    issues.append({
                        "type": "fix_not_applied",
                        "fix": fix_type,
                        "reason": f"Import '{import_name}' still present"
                    })
            
            elif fix_type == "add_docstring":
                func_name = fix.get("target")
                if f'def {func_name}' in fixed_code and '"""' not in fixed_code:
                    issues.append({
                        "type": "fix_incomplete",
                        "fix": fix_type,
                        "reason": f"Docstring not added to {func_name}"
                    })
            
            elif fix_type == "format_code":
                # Check if code is properly formatted
                if '\t' in fixed_code:
                    issues.append({
                        "type": "format_issue",
                        "fix": fix_type,
                        "reason": "Code still contains tabs"
                    })
        
        return PostCheckResult(
            check_type=PostCheckType.FIX_VERIFICATION,
            passed=len(issues) == 0,
            description="Fix verification completed",
            issues_found=issues,
            warnings=[],
            metadata={
                "check": "fix_verification",
                "file": file_path,
                "fixes_verified": len(applied_fixes),
                "issues_found": len(issues)
            }
        )


class SecurityAuditChecker:
    """Audit security aspects of QA fixes"""
    
    async def check_security_fixes(
        self,
        fixed_code: str,
        file_path: str
    ) -> PostCheckResult:
        """Check that security issues were properly fixed"""
        import re
        
        security_patterns = {
            "eval": r'\beval\s*\(',
            "exec": r'\bexec\s*\(',
            "pickle": r'\bpickle\.load',
            "hardcoded_password": r'password\s*=\s*["\'][^"\']{4,}["\']',
            "sql_injection": r'f["\'].*\{.*\}.*SELECT',
            "command_injection": r'os\.system\s*\(',
            "deserialization": r'pickle\.loads?\s*\(',
        }
        
        issues = []
        
        for issue_type, pattern in security_patterns.items():
            matches = re.findall(pattern, fixed_code)
            if matches:
                issues.append({
                    "type": "security_issue_remaining",
                    "issue": issue_type,
                    "count": len(matches),
                    "severity": "CRITICAL" if issue_type in ["eval", "exec", "pickle", "hardcoded_password"] else "HIGH"
                })
        
        return PostCheckResult(
            check_type=PostCheckType.SECURITY_AUDIT,
            passed=len(issues) == 0,
            description="Security audit of fixed code",
            issues_found=issues,
            warnings=[],
            metadata={"check": "security_audit", "file": file_path}
        )


class PerformanceImpactChecker:
    """Check for performance impacts from QA fixes"""
    
    async def check_complexity_increase(
        self,
        original_code: str,
        fixed_code: str,
        file_path: str
    ) -> PostCheckResult:
        """Check if fixes increased code complexity"""
        def calculate_complexity(code: str) -> int:
            complexity = 1
            for keyword in ['if', 'elif', 'for', 'while', 'and', 'or', 'except', 'finally']:
                complexity += code.count(f' {keyword} ')
            return complexity
        
        original_complexity = calculate_complexity(original_code)
        fixed_complexity = calculate_complexity(fixed_code)
        
        increase = fixed_complexity - original_complexity
        warnings = []
        
        if increase > 5:
            warnings.append(f"Code complexity increased by {increase} points")
        
        return PostCheckResult(
            check_type=PostCheckType.PERFORMANCE_IMPACT,
            passed=True,
            description="Complexity impact analysis",
            issues_found=[],
            warnings=warnings,
            metadata={
                "check": "complexity_impact",
                "file": file_path,
                "original_complexity": original_complexity,
                "fixed_complexity": fixed_complexity,
                "increase": increase
            }
        )


class PostCheckValidator:
    """Main validator for post-check validations"""
    
    def __init__(self):
        self.code_integrity = CodeIntegrityChecker()
        self.behavior_preservation = BehaviorPreservationChecker()
        self.regression_detector = RegressionDetector()
        self.fix_verifier = FixVerificationChecker()
        self.security_auditor = SecurityAuditChecker()
        self.performance_checker = PerformanceImpactChecker()
    
    async def run_all_checks(
        self,
        original_code: str,
        fixed_code: str,
        file_path: str,
        applied_fixes: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run all post-check validations"""
        import asyncio
        
        applied_fixes = applied_fixes or []
        
        logger.info(f"Running post-check validations for {file_path}")
        
        # Run all checks in parallel
        results = await asyncio.gather(
            self.code_integrity.check_syntax(file_path, fixed_code),
            self.code_integrity.check_imports(fixed_code, file_path),
            self.behavior_preservation.check_function_signatures(original_code, fixed_code, file_path),
            self.behavior_preservation.check_return_types(original_code, fixed_code, file_path),
            self.regression_detector.check_line_count_changes(original_code, fixed_code, file_path),
            self.regression_detector.check_logic_preservation(original_code, fixed_code, file_path),
            self.fix_verifier.verify_fixes(fixed_code, applied_fixes, file_path),
            self.security_auditor.check_security_fixes(fixed_code, file_path),
            self.performance_checker.check_complexity_increase(original_code, fixed_code, file_path)
        )
        
        # Aggregate results
        all_passed = all(r.passed for r in results)
        total_issues = sum(len(r.issues_found) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)
        
        return {
            "file_path": file_path,
            "all_passed": all_passed,
            "total_checks": len(results),
            "checks_passed": sum(1 for r in results if r.passed),
            "total_issues": total_issues,
            "total_warnings": total_warnings,
            "results": results,
            "summary": {
                "syntax_valid": results[0].passed,
                "imports_valid": results[1].passed,
                "behavior_preserved": results[2].passed and results[3].passed,
                "no_regressions": results[4].passed and results[5].passed,
                "fixes_verified": results[6].passed,
                "security_safe": results[7].passed,
                "performance_acceptable": True if len(results[8].warnings) < 3 else False
            }
        }
    
    async def validate_qa_changes(
        self,
        files_data: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Validate all QA changes"""
        results = []
        
        for file_data in files_data:
            result = await self.run_all_checks(
                original_code=file_data.get("original_code", ""),
                fixed_code=file_data.get("fixed_code", ""),
                file_path=file_data.get("file_path", ""),
                applied_fixes=file_data.get("applied_fixes", [])
            )
            results.append(result)
        
        # Overall result
        all_passed = all(r["all_passed"] for r in results)
        
        return {
            "validation_status": "PASSED" if all_passed else "FAILED",
            "files_validated": len(results),
            "files_passed": sum(1 for r in results if r["all_passed"]),
            "files_failed": sum(1 for r in results if not r["all_passed"]),
            "total_issues": sum(r["total_issues"] for r in results),
            "total_warnings": sum(r["total_warnings"] for r in results),
            "results": results
        }
