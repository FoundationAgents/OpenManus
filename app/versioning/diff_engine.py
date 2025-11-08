"""
Diff Engine
Generates and processes file differences
"""

import difflib
from typing import Dict, List, Any, Tuple


class DiffEngine:
    """Engine for generating and processing file differences"""
    
    def __init__(self):
        self.context_lines = 3
    
    async def compare_text(self, text1: str, text2: str) -> Dict[str, Any]:
        """Compare two text strings and return diff information"""
        try:
            lines1 = text1.splitlines(keepends=True)
            lines2 = text2.splitlines(keepends=True)
            
            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                lines1, lines2,
                fromfile="version1",
                tofile="version2",
                n=self.context_lines,
                lineterm=""
            ))
            
            # Generate HTML diff
            html_diff = self._generate_html_diff(lines1, lines2)
            
            # Calculate statistics
            added_lines = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
            removed_lines = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
            modified_lines = max(added_lines, removed_lines)
            
            # Find changed sections
            changed_sections = self._find_changed_sections(diff_lines)
            
            return {
                "unified_diff": ''.join(diff_lines),
                "html_diff": html_diff,
                "statistics": {
                    "added_lines": added_lines,
                    "removed_lines": removed_lines,
                    "modified_lines": modified_lines,
                    "total_changes": added_lines + removed_lines
                },
                "changed_sections": changed_sections,
                "similarity_score": self._calculate_similarity(text1, text2)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_html_diff(self, lines1: List[str], lines2: List[str]) -> str:
        """Generate HTML diff"""
        differ = difflib.HtmlDiff(
            tabsize=4,
            wrapcolumn=80,
            linejunk=lambda x: x.strip() == '',
            charjunk=lambda x: x.isspace()
        )
        
        return differ.make_file(
            lines1, lines2,
            fromdesc="Version 1",
            todesc="Version 2",
            context=True,
            numlines=self.context_lines
        )
    
    def _find_changed_sections(self, diff_lines: List[str]) -> List[Dict[str, Any]]:
        """Find sections with changes"""
        sections = []
        current_section = None
        
        for i, line in enumerate(diff_lines):
            if line.startswith('@@'):
                # Parse hunk header
                if current_section:
                    sections.append(current_section)
                
                # Extract line numbers
                import re
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    start1 = int(match.group(1))
                    len1 = int(match.group(2) or 1)
                    start2 = int(match.group(3))
                    len2 = int(match.group(4) or 1)
                    
                    current_section = {
                        "type": "change",
                        "old_start": start1,
                        "old_length": len1,
                        "new_start": start2,
                        "new_length": len2,
                        "diff_index": i
                    }
            
            elif current_section and (line.startswith('+') or line.startswith('-')):
                if "changes" not in current_section:
                    current_section["changes"] = []
                
                current_section["changes"].append({
                    "line": line,
                    "type": "added" if line.startswith('+') else "removed"
                })
        
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity score between two texts"""
        if not text1 and not text2:
            return 1.0
        
        if not text1 or not text2:
            return 0.0
        
        # Use SequenceMatcher for similarity
        matcher = difflib.SequenceMatcher(None, text1, text2)
        return matcher.ratio()
    
    async def compare_binary(self, data1: bytes, data2: bytes) -> Dict[str, Any]:
        """Compare binary data"""
        try:
            if len(data1) != len(data2):
                return {
                    "identical": False,
                    "size_difference": abs(len(data1) - len(data2)),
                    "size1": len(data1),
                    "size2": len(data2)
                }
            
            if data1 == data2:
                return {
                    "identical": True,
                    "size": len(data1)
                }
            
            # Find differing bytes
            differences = []
            min_len = min(len(data1), len(data2))
            
            for i in range(min_len):
                if data1[i] != data2[i]:
                    differences.append({
                        "offset": i,
                        "byte1": data1[i],
                        "byte2": data2[i]
                    })
            
            return {
                "identical": False,
                "size": len(data1),
                "differences": differences[:100],  # Limit to first 100 differences
                "total_differences": len(differences)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def generate_patch(self, text1: str, text2: str) -> str:
        """Generate a patch that can convert text1 to text2"""
        try:
            lines1 = text1.splitlines(keepends=True)
            lines2 = text2.splitlines(keepends=True)
            
            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                lines1, lines2,
                fromfile="original",
                tofile="modified",
                n=0,  # No context for patch
                lineterm=""
            ))
            
            return ''.join(diff_lines)
            
        except Exception as e:
            return f"Error generating patch: {str(e)}"
    
    async def apply_patch(self, original_text: str, patch_text: str) -> str:
        """Apply a patch to original text"""
        try:
            original_lines = original_text.splitlines(keepends=True)
            
            # Parse patch and apply changes
            result_lines = original_lines.copy()
            offset = 0
            
            for line in patch_text.splitlines():
                if line.startswith('@@'):
                    # Parse hunk header
                    import re
                    match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                    if match:
                        old_start = int(match.group(1)) - 1  # Convert to 0-based
                        # Apply offset from previous hunks
                        current_line = old_start + offset
                        
                elif line.startswith(' '):
                    # Unchanged line - skip
                    pass
                elif line.startswith('-'):
                    # Removed line
                    result_lines.pop(current_line)
                    offset -= 1
                elif line.startswith('+'):
                    # Added line
                    result_lines.insert(current_line + 1, line[1:] + '\n')
                    offset += 1
                    current_line += 1
            
            return ''.join(result_lines)
            
        except Exception as e:
            return f"Error applying patch: {str(e)}"
    
    async def get_line_changes(self, text1: str, text2: str) -> List[Dict[str, Any]]:
        """Get detailed line-by-line changes"""
        try:
            lines1 = text1.splitlines()
            lines2 = text2.splitlines()
            
            # Use SequenceMatcher to get detailed changes
            matcher = difflib.SequenceMatcher(None, lines1, lines2)
            
            changes = []
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'replace':
                    changes.append({
                        "type": "replace",
                        "old_lines": list(range(i1, i2)),
                        "new_lines": list(range(j1, j2)),
                        "old_content": lines1[i1:i2],
                        "new_content": lines2[j1:j2]
                    })
                elif tag == 'delete':
                    changes.append({
                        "type": "delete",
                        "old_lines": list(range(i1, i2)),
                        "old_content": lines1[i1:i2]
                    })
                elif tag == 'insert':
                    changes.append({
                        "type": "insert",
                        "new_lines": list(range(j1, j2)),
                        "new_content": lines2[j1:j2]
                    })
                elif tag == 'equal':
                    # No changes
                    pass
            
            return changes
            
        except Exception as e:
            return [{"error": str(e)}]
    
    async def merge_versions(self, base_text: str, version1_text: str, version2_text: str) -> Dict[str, Any]:
        """Attempt to merge two versions of a file"""
        try:
            # This is a simplified merge - in practice, you'd want a more sophisticated algorithm
            base_lines = base_text.splitlines()
            v1_lines = version1_text.splitlines()
            v2_lines = version2_text.splitlines()
            
            # Compare each version with base
            matcher1 = difflib.SequenceMatcher(None, base_lines, v1_lines)
            matcher2 = difflib.SequenceMatcher(None, base_lines, v2_lines)
            
            conflicts = []
            merged_lines = base_lines.copy()
            
            # Simple three-way merge logic
            # In a real implementation, this would be much more sophisticated
            merge_result = {
                "merged": True,
                "conflicts": conflicts,
                "merged_text": '\n'.join(merged_lines),
                "conflict_count": len(conflicts)
            }
            
            return merge_result
            
        except Exception as e:
            return {
                "merged": False,
                "error": str(e),
                "conflicts": [],
                "merged_text": ""
            }
