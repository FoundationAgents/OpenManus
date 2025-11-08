"""
Tests for Hybrid QA System

Comprehensive test suite for AI-powered QA with specialist team,
automatic fixing, and post-check validation.
"""

import pytest
import asyncio
from typing import List, Tuple, Dict, Any

from app.qa import (
    HybridQASystem,
    AIQAAgent,
    CodeExpert,
    PlannerExpert,
    FixerExpert,
    CleanupAgent,
    PostCheckValidator,
    HybridQAStatus
)


class TestCodeExpert:
    """Test Code Expert specialist"""
    
    @pytest.fixture
    def code_expert(self):
        return CodeExpert()
    
    @pytest.mark.asyncio
    async def test_analyze_valid_code(self, code_expert):
        """Test analyzing valid code"""
        code = """
def hello(name: str) -> str:
    \"\"\"Greet someone.\"\"\"
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(hello("World"))
"""
        result = await code_expert.analyze_code(code, "test.py")
        
        assert result.specialist_type.value == "code_expert"
        assert result.decision_type == "analyze"
        assert result.findings["syntax_valid"] is True
        assert result.confidence > 0.9
    
    @pytest.mark.asyncio
    async def test_detect_security_issues(self, code_expert):
        """Test security issue detection"""
        code = """
import os
password = "secret123"
os.system(f"command {password}")
"""
        result = await code_expert.analyze_code(code, "test.py")
        
        assert len(result.findings.get("security_issues", [])) > 0
        assert result.priority == "critical"
    
    @pytest.mark.asyncio
    async def test_detect_complexity(self, code_expert):
        """Test complexity detection"""
        code = """
def complex_func(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        return "very high"
    return "low"
"""
        result = await code_expert.analyze_code(code, "test.py")
        
        assert result.findings["complexity_score"] > 5
        assert "High cyclomatic complexity" in result.recommendations[0]


class TestPlannerExpert:
    """Test Planner Expert specialist"""
    
    @pytest.fixture
    def planner_expert(self):
        return PlannerExpert()
    
    @pytest.mark.asyncio
    async def test_validate_good_planning(self, planner_expert):
        """Test validation of good planning"""
        plan = {
            "tasks": [
                {
                    "id": "task-1",
                    "description": "Implement feature",
                    "estimated_hours": 4,
                    "dependencies": [],
                    "complexity": "medium"
                },
                {
                    "id": "task-2",
                    "description": "Write tests",
                    "estimated_hours": 3,
                    "dependencies": ["task-1"],
                    "complexity": "low"
                }
            ]
        }
        
        result = await planner_expert.validate_planning(plan)
        
        assert result.specialist_type.value == "planner_expert"
        assert result.findings["circular_deps"] is False
        assert result.findings["total_tasks"] == 2
    
    @pytest.mark.asyncio
    async def test_detect_circular_dependencies(self, planner_expert):
        """Test circular dependency detection"""
        plan = {
            "tasks": [
                {"id": "task-1", "dependencies": ["task-2"]},
                {"id": "task-2", "dependencies": ["task-3"]},
                {"id": "task-3", "dependencies": ["task-1"]}
            ]
        }
        
        result = await planner_expert.validate_planning(plan)
        
        assert result.findings["circular_deps"] is True
        assert result.priority == "high"
    
    @pytest.mark.asyncio
    async def test_detect_excessive_effort(self, planner_expert):
        """Test excessive effort detection"""
        plan = {
            "tasks": [
                {
                    "id": "task-1",
                    "estimated_hours": 80,
                    "complexity": "high"
                }
            ]
        }
        
        result = await planner_expert.validate_planning(plan)
        
        assert "excessive effort" in result.recommendations[0].lower()


class TestCleanupAgent:
    """Test Cleanup Agent specialist"""
    
    @pytest.fixture
    def cleanup_agent(self):
        return CleanupAgent()
    
    @pytest.mark.asyncio
    async def test_detect_formatting_issues(self, cleanup_agent):
        """Test formatting issue detection"""
        code = "x = 1  \ny = 2\t"  # trailing spaces and tab
        
        result = await cleanup_agent.analyze_for_cleanup(code, "test.py")
        
        assert len(result.findings["formatting_issues"]) > 0
    
    @pytest.mark.asyncio
    async def test_detect_dead_code(self, cleanup_agent):
        """Test dead code detection"""
        code = """
if False:
    print("This never runs")
"""
        
        result = await cleanup_agent.analyze_for_cleanup(code, "test.py")
        
        assert len(result.findings["dead_code"]) > 0


class TestAIQAAgent:
    """Test AI QA Agent coordinator"""
    
    @pytest.fixture
    async def ai_agent(self):
        agent = AIQAAgent(agent_id="test_ai_1")
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization"""
        agent = AIQAAgent(agent_id="test_ai_1")
        
        status = agent.get_agent_status()
        
        assert status["agent_id"] == "test_ai_1"
        assert status["specialists_count"] == 4
        assert status["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_analyze_code_changes(self):
        """Test code analysis workflow"""
        agent = AIQAAgent(agent_id="test_ai_1")
        
        code_files = [
            ("file1.py", """
def hello():
    pass
"""),
            ("file2.py", """
import os
password = "secret"
""")
        ]
        
        result = await agent.analyze_code_changes(code_files)
        
        assert result["files_analyzed"] == 2
        assert result["specialists_involved"] == 4
        assert len(result["all_decisions"]) > 0
        assert "summary" in result
    
    @pytest.mark.asyncio
    async def test_make_qa_decision(self):
        """Test QA decision making"""
        agent = AIQAAgent(agent_id="test_ai_1")
        
        code_files = [
            ("file.py", "def hello(): pass")
        ]
        
        result = await agent.make_qa_decision(code_files)
        
        assert "approval_status" in result
        assert "specialist_consensus" in result
        assert "recommendations" in result


class TestPostCheckValidator:
    """Test post-check validation system"""
    
    @pytest.fixture
    def post_checker(self):
        return PostCheckValidator()
    
    @pytest.mark.asyncio
    async def test_syntax_check_pass(self, post_checker):
        """Test syntax validation pass"""
        from app.qa.postchecks import CodeIntegrityChecker
        
        checker = CodeIntegrityChecker()
        
        result = await checker.check_syntax(
            "test.py",
            "def hello(): return 42"
        )
        
        assert result.passed is True
        assert result.check_type.value == "code_integrity"
    
    @pytest.mark.asyncio
    async def test_syntax_check_fail(self, post_checker):
        """Test syntax validation failure"""
        from app.qa.postchecks import CodeIntegrityChecker
        
        checker = CodeIntegrityChecker()
        
        result = await checker.check_syntax(
            "test.py",
            "def hello(): return"  # invalid syntax
        )
        
        assert result.passed is False
        assert len(result.issues_found) > 0
    
    @pytest.mark.asyncio
    async def test_behavior_preservation(self, post_checker):
        """Test behavior preservation check"""
        from app.qa.postchecks import BehaviorPreservationChecker
        
        checker = BehaviorPreservationChecker()
        
        original = """
def greet(name):
    return f"Hello, {name}"
"""
        
        fixed = """
def greet(name):
    \"\"\"Greet someone.\"\"\"
    return f"Hello, {name}"
"""
        
        result = await checker.check_function_signatures(
            original, fixed, "test.py"
        )
        
        assert result.passed is True
    
    @pytest.mark.asyncio
    async def test_signature_changed_detection(self, post_checker):
        """Test detection of changed signatures"""
        from app.qa.postchecks import BehaviorPreservationChecker
        
        checker = BehaviorPreservationChecker()
        
        original = "def hello(name): return f'Hello, {name}'"
        fixed = "def hello(name, greeting='Hi'): return f'{greeting}, {name}'"
        
        result = await checker.check_function_signatures(
            original, fixed, "test.py"
        )
        
        assert result.passed is False
        assert len(result.issues_found) > 0
    
    @pytest.mark.asyncio
    async def test_regression_detection(self, post_checker):
        """Test regression detection"""
        from app.qa.postchecks import RegressionDetector
        
        detector = RegressionDetector()
        
        original = "def hello():\n    return 42"
        fixed = "def hello():\n    return 42"
        
        result = await detector.check_logic_preservation(
            original, fixed, "test.py"
        )
        
        assert result.passed is True


class TestHybridQASystem:
    """Test complete Hybrid QA System"""
    
    @pytest.fixture
    def hybrid_qa(self):
        return HybridQASystem(qa_level="standard", auto_fix=True)
    
    @pytest.mark.asyncio
    async def test_initialization(self, hybrid_qa):
        """Test system initialization"""
        status = hybrid_qa.get_status()
        
        assert status["qa_level"] == "standard"
        assert status["auto_fix_enabled"] is True
        assert status["system_status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_code_analysis(self, hybrid_qa):
        """Test code analysis phase"""
        code_files = [
            ("file.py", "def hello(): return 42"),
            ("module.py", "import os\nprint('test')")
        ]
        
        result = await hybrid_qa.analyze_code_changes(code_files)
        
        assert result["files_analyzed"] == 2
        assert "issue_summary" in result
        assert hybrid_qa.status == HybridQAStatus.ANALYZING
    
    @pytest.mark.asyncio
    async def test_approval_decision(self, hybrid_qa):
        """Test approval decision making"""
        code_files = [("file.py", "def hello(): return 42")]
        
        # Analyze first
        await hybrid_qa.analyze_code_changes(code_files)
        
        # Make decision
        approval = await hybrid_qa.make_approval_decision()
        
        assert approval.status in ["APPROVED", "BLOCKED"]
        assert approval.ai_consensus > 0


class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_qa_workflow(self):
        """Test complete QA workflow from start to finish"""
        hybrid_qa = HybridQASystem(qa_level="standard", auto_fix=True)
        
        code_files = [
            ("feature.py", """
def process_data(data):
    # TODO: validate input
    return data
"""),
            ("utils.py", """
def helper():
    pass
""")
        ]
        
        result = await hybrid_qa.run_complete_qa_workflow(code_files)
        
        assert result["workflow_status"] == "completed"
        assert "approval" in result
        assert "analysis" in result
        assert result["qa_level"] == "standard"
    
    @pytest.mark.asyncio
    async def test_hybrid_qa_gate_integration(self):
        """Test integration with workflow"""
        from app.workflows.qa_integration import HybridQAGate
        
        gate = HybridQAGate(qa_level="standard", auto_fix=True)
        
        code_files = [("test.py", "def test(): return True")]
        
        result = await gate.review_code_hybrid(
            code_files=[(f, c) for f, c in code_files],
            author_agent="test_agent",
            task_id="test_task"
        )
        
        assert result["review_method"] == "hybrid_qa"
        assert "approval_status" in result
        assert "ai_consensus" in result


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_invalid_python_code(self):
        """Test handling of invalid Python"""
        agent = AIQAAgent(agent_id="test")
        
        code_files = [("invalid.py", "def hello(: return")]  # syntax error
        
        result = await agent.analyze_code_changes(code_files)
        
        assert result["files_analyzed"] == 1
        # Should still process, just report issues
        assert result["total_decisions"] >= 0
    
    @pytest.mark.asyncio
    async def test_empty_files(self):
        """Test handling of empty files"""
        hybrid_qa = HybridQASystem()
        
        code_files = [("empty.py", "")]
        
        result = await hybrid_qa.analyze_code_changes(code_files)
        
        assert result["files_analyzed"] == 1
    
    @pytest.mark.asyncio
    async def test_large_file(self):
        """Test handling of large files"""
        hybrid_qa = HybridQASystem()
        
        # Create a large file
        code = "\n".join([f"def func_{i}(): pass" for i in range(100)])
        code_files = [("large.py", code)]
        
        result = await hybrid_qa.analyze_code_changes(code_files)
        
        assert result["files_analyzed"] == 1
        assert hybrid_qa.status == HybridQAStatus.ANALYZING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
