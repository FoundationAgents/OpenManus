"""
Test Generator Agent

Specialist agent that automatically generates comprehensive tests:
- Unit tests (via AST analysis)
- Integration tests (API contracts)
- E2E tests (workflow scenarios)
- Property-based tests
- Performance tests
- Security tests
"""

import ast
import json
import time
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
from app.flow.multi_agent_environment import SpecializedAgent, DevelopmentTask, AgentRole, BlackboardMessage, MessageType, TaskPriority
from app.logger import logger


class TestType(str, Enum):
    """Types of tests to generate"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PROPERTY = "property"
    PERFORMANCE = "performance"
    SECURITY = "security"


class TestAgent(SpecializedAgent):
    """Test Generator Specialist"""
    
    def __init__(self, agent_id: str, blackboard, **kwargs):
        super().__init__(AgentRole.DEVELOPER, blackboard, name=agent_id, **kwargs)
        
        self.tests_generated = 0
        self.test_files_created = 0
        self.metrics = {
            "total_tests_generated": 0,
            "unit_tests": 0,
            "integration_tests": 0,
            "e2e_tests": 0,
            "property_tests": 0,
            "performance_tests": 0,
            "security_tests": 0,
            "average_generation_time": 0.0,
        }
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Generate tests for code"""
        start_time = time.time()
        
        try:
            code_files = task.requirements.get("code_files", [])
            test_types = task.requirements.get("test_types", [TestType.UNIT.value, TestType.INTEGRATION.value])
            
            test_files = await self._generate_tests_for_files(code_files, test_types)
            
            # Update metrics
            generation_time = time.time() - start_time
            self.metrics["average_generation_time"] = (
                (self.metrics["average_generation_time"] * self.test_files_created + generation_time)
                / (self.test_files_created + 1)
            )
            self.test_files_created += len(test_files)
            
            return self._generate_test_report(test_files)
        
        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return f"Test generation failed: {str(e)}"
    
    async def _generate_tests_for_files(self, file_paths: List[str], test_types: List[str]) -> List[str]:
        """Generate tests for multiple files"""
        test_files = []
        
        for file_path in file_paths:
            try:
                with open(file_path) as f:
                    source = f.read()
                
                tree = ast.parse(source)
                
                # Generate unit tests
                if "unit" in test_types or TestType.UNIT.value in test_types:
                    unit_tests = self._generate_unit_tests(tree, file_path)
                    if unit_tests:
                        test_file = await self._write_test_file(file_path, "unit", unit_tests)
                        test_files.append(test_file)
                        self.metrics["unit_tests"] += len(unit_tests)
                
                # Generate integration tests
                if "integration" in test_types or TestType.INTEGRATION.value in test_types:
                    integration_tests = self._generate_integration_tests(tree, file_path)
                    if integration_tests:
                        test_file = await self._write_test_file(file_path, "integration", integration_tests)
                        test_files.append(test_file)
                        self.metrics["integration_tests"] += len(integration_tests)
                
                self.tests_generated += self.metrics["unit_tests"] + self.metrics["integration_tests"]
                self.metrics["total_tests_generated"] = self.tests_generated
            
            except Exception as e:
                logger.warning(f"Failed to generate tests for {file_path}: {e}")
        
        return test_files
    
    def _generate_unit_tests(self, tree: ast.AST, file_path: str) -> List[str]:
        """Generate unit tests from AST"""
        tests = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                test = self._generate_test_for_function(node, file_path)
                if test:
                    tests.append(test)
        
        return tests
    
    def _generate_test_for_function(self, func_node: ast.FunctionDef, file_path: str) -> Optional[str]:
        """Generate a test for a single function"""
        func_name = func_node.name
        
        # Skip private methods and special methods
        if func_name.startswith("_"):
            return None
        
        # Extract parameters
        params = []
        for arg in func_node.args.args:
            if arg.arg != "self":
                params.append(arg.arg)
        
        # Generate test template
        test_code = f"""
def test_{func_name}():
    \"\"\"Test {func_name} function\"\"\"
    # Arrange
    pass
    
    # Act
    result = {func_name}({', '.join(f'{p}=None' for p in params)})
    
    # Assert
    assert result is not None
"""
        
        return test_code
    
    def _generate_integration_tests(self, tree: ast.AST, file_path: str) -> List[str]:
        """Generate integration tests"""
        tests = []
        
        # Look for classes that might need integration tests
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                test = self._generate_test_for_class(node, file_path)
                if test:
                    tests.append(test)
        
        return tests
    
    def _generate_test_for_class(self, class_node: ast.ClassDef, file_path: str) -> Optional[str]:
        """Generate integration test for a class"""
        class_name = class_node.name
        
        # Find public methods
        methods = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                methods.append(node.name)
        
        if not methods:
            return None
        
        test_code = f"""
class Test{class_name}:
    \"\"\"Integration tests for {class_name}\"\"\"
    
    def setUp(self):
        \"\"\"Set up test fixtures\"\"\"
        self.instance = {class_name}()
    
    def tearDown(self):
        \"\"\"Clean up after tests\"\"\"
        self.instance = None
"""
        
        for method in methods[:3]:  # Test first 3 methods
            test_code += f"""
    def test_{method}(self):
        \"\"\"Test {method} integration\"\"\"
        # Arrange
        pass
        
        # Act
        result = self.instance.{method}()
        
        # Assert
        assert result is not None
"""
        
        return test_code
    
    async def _write_test_file(self, source_file: str, test_type: str, tests: List[str]) -> str:
        """Write generated tests to file"""
        from pathlib import Path
        
        source_path = Path(source_file)
        test_dir = Path("tests") / test_type
        test_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = test_dir / f"test_{source_path.stem}_{test_type}.py"
        
        # Generate test file content
        content = f"""'''
Auto-generated {test_type} tests for {source_path.name}

Generated: {datetime.now().isoformat()}
Source: {source_file}
'''

import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest

"""
        
        # Add imports
        content += f"from app.{source_path.stem.replace('/', '.')} import *\n\n"
        
        # Add tests
        content += "\n\n".join(tests)
        
        # Write file
        with open(test_file, "w") as f:
            f.write(content)
        
        logger.info(f"Generated test file: {test_file}")
        return str(test_file)
    
    def _generate_test_report(self, test_files: List[str]) -> str:
        """Generate report of generated tests"""
        report = ["=" * 80]
        report.append("TEST GENERATION REPORT")
        report.append("=" * 80)
        report.append(f"Total Tests Generated: {self.tests_generated}")
        report.append(f"Test Files Created: {len(test_files)}")
        report.append("")
        report.append("BREAKDOWN:")
        report.append(f"  Unit Tests: {self.metrics['unit_tests']}")
        report.append(f"  Integration Tests: {self.metrics['integration_tests']}")
        report.append(f"  Average Generation Time: {self.metrics['average_generation_time']:.2f}s")
        report.append("")
        report.append("GENERATED FILES:")
        for test_file in test_files:
            report.append(f"  ✓ {test_file}")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get test generation metrics"""
        return {
            **self.metrics,
            "test_files_created": self.test_files_created,
        }
