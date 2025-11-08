"""
Automatic Code Remediation Engine

Applies automatic fixes to code quality issues where safe to do so.
"""

import ast
import re
import os
from typing import Dict, List, Optional, Any
from app.logger import logger


class CodeRemediator:
    """Automatically fixes code quality issues"""
    
    def __init__(self):
        self.fixes_applied = 0
        self.fixes_failed = 0
    
    async def apply_fix(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Apply automatic fix for an issue"""
        if not issue.get("auto_fixable", False):
            return {"success": False, "reason": "Issue not auto-fixable"}
        
        issue_type = issue.get("type")
        file_path = issue.get("file_path")
        
        try:
            if issue_type == "import_order":
                return await self._fix_import_order(file_path)
            elif issue_type == "trailing_whitespace":
                return await self._fix_trailing_whitespace(file_path)
            elif issue_type == "line_too_long":
                return await self._fix_line_length(file_path, issue.get("line_number"))
            elif issue_type == "multiple_statements":
                return await self._fix_multiple_statements(file_path, issue.get("line_number"))
            elif issue_type == "naming_convention":
                return await self._fix_naming_convention(file_path, issue)
            elif issue_type == "bare_except":
                return await self._fix_bare_except(file_path, issue.get("line_number"))
            elif issue_type == "magic_number":
                return await self._fix_magic_number(file_path, issue)
            elif issue_type == "missing_docstring":
                return await self._add_docstring(file_path, issue)
            elif issue_type == "performance_issue":
                return await self._fix_performance_issue(file_path, issue)
            else:
                return {"success": False, "reason": f"No fix handler for {issue_type}"}
        
        except Exception as e:
            logger.error(f"Failed to apply fix for {issue_type}: {e}")
            self.fixes_failed += 1
            return {"success": False, "reason": str(e)}
    
    async def _fix_import_order(self, file_path: str) -> Dict[str, Any]:
        """Sort imports"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find import section
            import_start = None
            import_end = None
            
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    if import_start is None:
                        import_start = i
                    import_end = i
                elif import_start is not None and line.strip() and not line.strip().startswith('#'):
                    break
            
            if import_start is not None and import_end is not None:
                # Extract and sort imports
                imports = lines[import_start:import_end + 1]
                sorted_imports = sorted(imports, key=lambda x: (
                    0 if x.strip().startswith('from ') else 1,  # 'from' imports first
                    x.strip()
                ))
                
                # Replace in file
                new_lines = lines[:import_start] + sorted_imports + lines[import_end + 1:]
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                
                self.fixes_applied += 1
                return {"success": True, "message": "Imports sorted"}
            
            return {"success": False, "reason": "No imports found"}
        
        except Exception as e:
            return {"success": False, "reason": str(e)}
    
    async def _fix_trailing_whitespace(self, file_path: str) -> Dict[str, Any]:
        """Remove trailing whitespace"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_lines = [line.rstrip() + '\n' if line.endswith('\n') else line.rstrip() for line in lines]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            self.fixes_applied += 1
            return {"success": True, "message": "Trailing whitespace removed"}
        
        except Exception as e:
            return {"success": False, "reason": str(e)}
    
    async def _fix_line_length(self, file_path: str, line_number: int) -> Dict[str, Any]:
        """Fix line that's too long (basic approach)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if 0 <= line_number - 1 < len(lines):
                line = lines[line_number - 1]
                
                # Simple fix: if line contains commas, split on commas
                if ',' in line and len(line) > 120:
                    indent = len(line) - len(line.lstrip())
                    parts = line.split(',')
                    
                    if len(parts) > 1:
                        new_lines = []
                        for i, part in enumerate(parts):
                            if i == 0:
                                new_lines.append(part + ',\n')
                            elif i < len(parts) - 1:
                                new_lines.append(' ' * (indent + 4) + part.strip() + ',\n')
                            else:
                                new_lines.append(' ' * (indent + 4) + part.strip())
                        
                        lines[line_number - 1:line_number] = new_lines
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        
                        self.fixes_applied += 1
                        return {"success": True, "message": "Long line split"}
            
            return {"success": False, "reason": "Could not split line safely"}
        
        except Exception as e:
            return {"success": False, "reason": str(e)}
    
    async def _fix_multiple_statements(self, file_path: str, line_number: int) -> Dict[str, Any]:
        """Split multiple statements on one line"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if 0 <= line_number - 1 < len(lines):
                line = lines[line_number - 1]
                indent = len(line) - len(line.lstrip())
                
                # Split on semicolon
                statements = [s.strip() for s in line.split(';') if s.strip()]
                
                if len(statements) > 1:
                    new_lines = [' ' * indent + stmt + '\n' for stmt in statements]
                    lines[line_number - 1:line_number] = new_lines
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    self.fixes_applied += 1
                    return {"success": True, "message": "Statements split"}
            
            return {"success": False, "reason": "Could not split statements"}
        
        except Exception as e:
            return {"success": False, "reason": str(e)}
    
    async def _fix_naming_convention(self, file_path: str, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Fix naming convention (conservative approach)"""
        # This is complex and risky, so we'll only suggest for now
        return {"success": False, "reason": "Naming fixes require manual review"}
    
    async def _fix_bare_except(self, file_path: str, line_number: int) -> Dict[str, Any]:
        """Fix bare except clause"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if 0 <= line_number - 1 < len(lines):
                line = lines[line_number - 1]
                
                # Replace 'except:' with 'except Exception:'
                new_line = re.sub(r'except\s*:', 'except Exception:', line)
                
                if new_line != line:
                    lines[line_number - 1] = new_line
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    self.fixes_applied += 1
                    return {"success": True, "message": "Bare except fixed"}
            
            return {"success": False, "reason": "Could not fix bare except"}
        
        except Exception as e:
            return {"success": False, "reason": str(e)}
    
    async def _fix_magic_number(self, file_path: str, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Extract magic number to constant"""
        # This requires understanding context, so suggest only
        return {"success": False, "reason": "Magic number extraction requires manual review"}
    
    async def _add_docstring(self, file_path: str, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Add template docstring"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_number = issue.get("line_number", 0)
            
            if 0 <= line_number - 1 < len(lines):
                # Get indent of the definition line
                def_line = lines[line_number - 1]
                indent = len(def_line) - len(def_line.lstrip())
                
                # Create template docstring
                if 'Function' in issue.get("message", ""):
                    docstring = f'{" " * (indent + 4)}"""TODO: Add function description"""\n'
                else:
                    docstring = f'{" " * (indent + 4)}"""TODO: Add class description"""\n'
                
                # Insert after definition line
                lines.insert(line_number, docstring)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                self.fixes_applied += 1
                return {"success": True, "message": "Docstring template added"}
            
            return {"success": False, "reason": "Could not add docstring"}
        
        except Exception as e:
            return {"success": False, "reason": str(e)}
    
    async def _fix_performance_issue(self, file_path: str, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Fix performance issue"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_number = issue.get("line_number", 0)
            
            if 0 <= line_number - 1 < len(lines):
                line = lines[line_number - 1]
                
                # Fix range(len()) pattern
                if 'enumerate' in issue.get("message", ""):
                    # Replace range(len(x)) with enumerate(x)
                    new_line = re.sub(
                        r'for\s+(\w+)\s+in\s+range\(len\((\w+)\)\):',
                        r'for \1, item in enumerate(\2):',
                        line
                    )
                    
                    if new_line != line:
                        lines[line_number - 1] = new_line
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        
                        self.fixes_applied += 1
                        return {"success": True, "message": "Performance issue fixed"}
            
            return {"success": False, "reason": "Could not fix performance issue"}
        
        except Exception as e:
            return {"success": False, "reason": str(e)}
    
    def get_stats(self) -> Dict[str, int]:
        """Get remediation statistics"""
        return {
            "fixes_applied": self.fixes_applied,
            "fixes_failed": self.fixes_failed
        }
