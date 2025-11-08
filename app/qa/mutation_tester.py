"""
Mutation Testing

Advanced test quality verification through mutation testing.
Intentionally introduces bugs in code and checks if tests catch them.
"""

import ast
import subprocess
import random
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from copy import deepcopy
from datetime import datetime
from app.logger import logger


class MutationType(str, Enum):
    """Types of mutations"""
    CONSTANT_REPLACEMENT = "constant_replacement"
    OPERATOR_REPLACEMENT = "operator_replacement"
    CONDITIONAL_REPLACEMENT = "conditional_replacement"
    RETURN_REPLACEMENT = "return_replacement"
    ASSIGNMENT_REPLACEMENT = "assignment_replacement"


@dataclass
class Mutant:
    """Represents a code mutation"""
    id: str
    file_path: str
    mutation_type: MutationType
    line_number: int
    original_code: str
    mutated_code: str
    survived: bool = False  # True if tests didn't catch the mutation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "file_path": self.file_path,
            "mutation_type": self.mutation_type.value,
            "line_number": self.line_number,
            "original_code": self.original_code,
            "mutated_code": self.mutated_code,
            "survived": self.survived,
        }


@dataclass
class MutationTestResult:
    """Results from mutation testing"""
    timestamp: datetime
    total_mutants: int
    killed_mutants: int
    survived_mutants: int
    mutant_coverage_percentage: float
    coverage_gaps: List[str] = field(default_factory=list)
    survived_mutants_details: List[Mutant] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_mutants": self.total_mutants,
            "killed_mutants": self.killed_mutants,
            "survived_mutants": self.survived_mutants,
            "mutation_score": self.mutant_coverage_percentage,
            "coverage_gaps": self.coverage_gaps,
            "survived_details": [m.to_dict() for m in self.survived_mutants_details],
        }


class MutationTester:
    """Perform mutation testing to verify test quality"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.mutants: List[Mutant] = []
        self.result: Optional[MutationTestResult] = None
        
        # Configuration
        self.num_mutants_per_function = self.config.get("num_mutants_per_function", 5)
        self.mutation_timeout = self.config.get("mutation_timeout", 30)
        self.coverage_gap_threshold = self.config.get("coverage_gap_threshold", 10)
    
    async def generate_mutants(self, file_path: str, max_mutants: int = 50) -> List[Mutant]:
        """Generate mutations for a file"""
        try:
            with open(file_path) as f:
                source = f.read()
            
            tree = ast.parse(source)
            mutations = []
            
            # Walk AST and find mutation opportunities
            for node in ast.walk(tree):
                # Constant replacement
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, str, bool)):
                    mutations.extend(self._generate_constant_mutations(node, file_path))
                
                # Operator replacement
                elif isinstance(node, ast.BinOp):
                    mutations.extend(self._generate_operator_mutations(node, file_path))
                
                # Conditional replacement
                elif isinstance(node, ast.Compare):
                    mutations.extend(self._generate_conditional_mutations(node, file_path))
                
                # Return replacement
                elif isinstance(node, ast.Return):
                    mutations.extend(self._generate_return_mutations(node, file_path))
                
                # Limit mutants
                if len(mutations) >= max_mutants:
                    break
            
            self.mutants.extend(mutations[:max_mutants])
            return mutations[:max_mutants]
        
        except Exception as e:
            logger.error(f"Failed to generate mutants: {e}")
            return []
    
    def _generate_constant_mutations(self, node: ast.Constant, file_path: str) -> List[Mutant]:
        """Generate constant replacement mutations"""
        mutations = []
        
        if isinstance(node.value, bool):
            mutated = not node.value
        elif isinstance(node.value, int):
            mutated = node.value + 1
        elif isinstance(node.value, str):
            mutated = ""
        else:
            return []
        
        mutation = Mutant(
            id=f"mutant_{len(self.mutants)}",
            file_path=file_path,
            mutation_type=MutationType.CONSTANT_REPLACEMENT,
            line_number=node.lineno if hasattr(node, 'lineno') else 0,
            original_code=repr(node.value),
            mutated_code=repr(mutated),
        )
        mutations.append(mutation)
        
        return mutations
    
    def _generate_operator_mutations(self, node: ast.BinOp, file_path: str) -> List[Mutant]:
        """Generate operator replacement mutations"""
        mutations = []
        
        operator_map = {
            ast.Add: ast.Sub,
            ast.Sub: ast.Add,
            ast.Mult: ast.Div,
            ast.Div: ast.Mult,
            ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq,
            ast.Lt: ast.Gt,
            ast.Gt: ast.Lt,
        }
        
        original_op = type(node.op).__name__
        mutated_op_class = operator_map.get(type(node.op))
        
        if mutated_op_class:
            mutated_op = mutated_op_class.__name__
            
            mutation = Mutant(
                id=f"mutant_{len(self.mutants)}",
                file_path=file_path,
                mutation_type=MutationType.OPERATOR_REPLACEMENT,
                line_number=node.lineno if hasattr(node, 'lineno') else 0,
                original_code=original_op,
                mutated_code=mutated_op,
            )
            mutations.append(mutation)
        
        return mutations
    
    def _generate_conditional_mutations(self, node: ast.Compare, file_path: str) -> List[Mutant]:
        """Generate conditional replacement mutations"""
        mutations = []
        
        comparator_map = {
            ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq,
            ast.Lt: ast.Gt,
            ast.Gt: ast.Lt,
            ast.LtE: ast.GtE,
            ast.GtE: ast.LtE,
        }
        
        for comp in node.ops:
            original_comp = type(comp).__name__
            mutated_comp_class = comparator_map.get(type(comp))
            
            if mutated_comp_class:
                mutated_comp = mutated_comp_class.__name__
                
                mutation = Mutant(
                    id=f"mutant_{len(self.mutants)}",
                    file_path=file_path,
                    mutation_type=MutationType.CONDITIONAL_REPLACEMENT,
                    line_number=node.lineno if hasattr(node, 'lineno') else 0,
                    original_code=original_comp,
                    mutated_code=mutated_comp,
                )
                mutations.append(mutation)
        
        return mutations
    
    def _generate_return_mutations(self, node: ast.Return, file_path: str) -> List[Mutant]:
        """Generate return value mutations"""
        mutations = []
        
        # Return None instead of value
        mutation = Mutant(
            id=f"mutant_{len(self.mutants)}",
            file_path=file_path,
            mutation_type=MutationType.RETURN_REPLACEMENT,
            line_number=node.lineno if hasattr(node, 'lineno') else 0,
            original_code="return <value>",
            mutated_code="return None",
        )
        mutations.append(mutation)
        
        return mutations
    
    async def run_mutation_tests(
        self,
        test_command: str = "python -m pytest tests/ -q",
        timeout: int = 300,
    ) -> MutationTestResult:
        """Run tests against all mutants"""
        killed = 0
        survived = []
        
        for mutant in self.mutants:
            # Apply mutation
            backup_path = self._backup_file(mutant.file_path)
            
            try:
                self._apply_mutation(mutant)
                
                # Run tests
                result = subprocess.run(
                    test_command.split(),
                    capture_output=True,
                    text=True,
                    timeout=min(self.mutation_timeout, timeout),
                )
                
                # If tests fail, mutation was killed
                if result.returncode != 0:
                    killed += 1
                    mutant.survived = False
                else:
                    mutant.survived = True
                    survived.append(mutant)
            
            except subprocess.TimeoutExpired:
                # Timeout = tests hung, consider mutation killed
                killed += 1
                mutant.survived = False
            
            except Exception as e:
                logger.warning(f"Error testing mutant {mutant.id}: {e}")
                killed += 1
                mutant.survived = False
            
            finally:
                # Restore file
                self._restore_file(mutant.file_path, backup_path)
        
        # Calculate mutation score
        mutation_score = (killed / len(self.mutants) * 100) if self.mutants else 0
        
        # Identify coverage gaps
        coverage_gaps = []
        if mutation_score < (100 - self.coverage_gap_threshold):
            for mutant in survived:
                coverage_gaps.append(f"{mutant.file_path}:{mutant.line_number} - {mutant.mutation_type.value}")
        
        self.result = MutationTestResult(
            timestamp=datetime.now(),
            total_mutants=len(self.mutants),
            killed_mutants=killed,
            survived_mutants=len(survived),
            mutant_coverage_percentage=mutation_score,
            coverage_gaps=coverage_gaps,
            survived_mutants_details=survived,
        )
        
        return self.result
    
    def _backup_file(self, file_path: str) -> str:
        """Create backup of file"""
        backup_path = f"{file_path}.mutant_backup"
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def _restore_file(self, file_path: str, backup_path: str):
        """Restore file from backup"""
        try:
            shutil.move(backup_path, file_path)
        except Exception as e:
            logger.warning(f"Failed to restore file: {e}")
    
    def _apply_mutation(self, mutant: Mutant):
        """Apply mutation to file"""
        try:
            with open(mutant.file_path) as f:
                lines = f.readlines()
            
            # Simple string replacement (not ideal but works)
            if mutant.line_number > 0 and mutant.line_number <= len(lines):
                line = lines[mutant.line_number - 1]
                if mutant.original_code in line:
                    lines[mutant.line_number - 1] = line.replace(
                        mutant.original_code,
                        mutant.mutated_code
                    )
                    
                    with open(mutant.file_path, 'w') as f:
                        f.writelines(lines)
        
        except Exception as e:
            logger.error(f"Failed to apply mutation: {e}")
    
    def export_result(self, format: str = "json") -> str:
        """Export mutation test results"""
        if not self.result:
            return "{}"
        
        if format == "json":
            import json
            return json.dumps(self.result.to_dict(), indent=2)
        else:
            return self._generate_text_report()
    
    def _generate_text_report(self) -> str:
        """Generate text format report"""
        if not self.result:
            return ""
        
        report = ["=" * 80]
        report.append("MUTATION TEST REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Total Mutants: {self.result.total_mutants}")
        report.append(f"Killed Mutants: {self.result.killed_mutants}")
        report.append(f"Survived Mutants: {self.result.survived_mutants}")
        report.append(f"Mutation Score: {self.result.mutant_coverage_percentage:.1f}%")
        report.append("")
        
        if self.result.survived_mutants_details:
            report.append("SURVIVED MUTANTS (Test Quality Issues):")
            for mutant in self.result.survived_mutants_details[:10]:
                report.append(f"  {mutant.file_path}:{mutant.line_number}")
                report.append(f"    Type: {mutant.mutation_type.value}")
                report.append(f"    Original: {mutant.original_code}")
                report.append(f"    Mutated:  {mutant.mutated_code}")
                report.append("")
            
            if len(self.result.survived_mutants_details) > 10:
                report.append(f"  ... and {len(self.result.survived_mutants_details) - 10} more")
        
        if self.result.coverage_gaps:
            report.append("TEST COVERAGE GAPS:")
            for gap in self.result.coverage_gaps[:10]:
                report.append(f"  - {gap}")
        
        report.append("=" * 80)
        
        return "\n".join(report)
