"""
Comprehensive QA System Tests

Tests all QA components:
- Code analyzer
- Code remediator
- Planning validator
- Production readiness checker
- Knowledge base
- Metrics collector
- QA agent
- Workflow integration
"""

import pytest
import os
import tempfile
from pathlib import Path

from app.qa import (
    CodeAnalyzer,
    CodeRemediator,
    PlanningValidator,
    ProductionReadinessChecker,
    QAKnowledgeGraph,
    QAMetricsCollector
)


class TestCodeAnalyzer:
    """Test code analyzer"""
    
    @pytest.mark.asyncio
    async def test_syntax_validation(self):
        """Test syntax error detection"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def broken(:\n    pass")
            f.flush()
            
            analyzer = CodeAnalyzer()
            issues = await analyzer.analyze_file(f.name, ["syntax_validation"])
            
            assert len(issues) > 0
            assert any("syntax" in i.get("type", "").lower() for i in issues)
            
            os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_stub_detection(self):
        """Test stub/placeholder detection"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def incomplete():
    # TODO: implement this
    pass

def not_done():
    raise NotImplementedError
""")
            f.flush()
            
            analyzer = CodeAnalyzer()
            issues = await analyzer.analyze_file(f.name, ["code_smell_detection"])
            
            # Should detect pass and NotImplementedError
            assert len(issues) > 0
            stub_issues = [i for i in issues if "stub" in i.get("type", "").lower()]
            assert len(stub_issues) >= 2
            
            os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_hack_detection(self):
        """Test hack/workaround detection"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
# HACK: Quick fix for the deadline
def temp_solution():
    while True:
        break  # XXX: This is terrible
    
    try:
        risky_operation()
    except:
        pass  # Silent fail
""")
            f.flush()
            
            analyzer = CodeAnalyzer()
            issues = await analyzer.analyze_file(f.name, ["code_smell_detection"])
            
            # Should detect HACK comment, while True: break, and silent except
            hack_issues = [i for i in issues if "hack" in i.get("type", "").lower()]
            assert len(hack_issues) > 0
            
            os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_security_scan(self):
        """Test security vulnerability detection"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import sqlite3

def dangerous(user_id):
    query = f"SELECT * FROM users WHERE id={user_id}"
    cursor.execute(query)
    
    password = "hardcoded_secret"
    api_key = "12345abcde"
""")
            f.flush()
            
            analyzer = CodeAnalyzer()
            issues = await analyzer.analyze_file(f.name, ["security_scan"])
            
            # Should detect SQL injection and hardcoded secrets
            assert len(issues) > 0
            security_issues = [i for i in issues if i.get("severity") == "CRITICAL"]
            assert len(security_issues) > 0
            
            os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_magic_number_detection(self):
        """Test magic number detection"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def process():
    if len(items) > 42:  # Magic number!
        time.sleep(3600)  # Another one
        return items[:100]  # And another
""")
            f.flush()
            
            analyzer = CodeAnalyzer()
            issues = await analyzer.analyze_file(f.name, ["code_smell_detection"])
            
            magic_issues = [i for i in issues if "magic" in i.get("type", "").lower()]
            assert len(magic_issues) > 0
            
            os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_long_function_detection(self):
        """Test long function detection"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            # Create a very long function
            lines = ["def very_long_function():\n"]
            lines.extend([f"    line_{i} = {i}\n" for i in range(60)])
            f.write("".join(lines))
            f.flush()
            
            analyzer = CodeAnalyzer()
            issues = await analyzer.analyze_file(f.name, ["code_smell_detection"])
            
            long_func_issues = [i for i in issues if "long_function" in i.get("type", "")]
            assert len(long_func_issues) > 0
            
            os.unlink(f.name)


class TestCodeRemediator:
    """Test code remediator"""
    
    @pytest.mark.asyncio
    async def test_trailing_whitespace_fix(self):
        """Test trailing whitespace removal"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test():   \n    pass  \n")
            f.flush()
            
            remediator = CodeRemediator()
            issue = {
                "type": "trailing_whitespace",
                "file_path": f.name,
                "line_number": 1,
                "auto_fixable": True
            }
            
            result = await remediator.apply_fix(issue)
            assert result["success"]
            
            # Check file was fixed
            with open(f.name, 'r') as rf:
                content = rf.read()
                assert not content.endswith('   ')
            
            os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_bare_except_fix(self):
        """Test bare except clause fix"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("try:\n    risky()\nexcept:\n    pass\n")
            f.flush()
            
            remediator = CodeRemediator()
            issue = {
                "type": "bare_except",
                "file_path": f.name,
                "line_number": 3,
                "auto_fixable": True
            }
            
            result = await remediator.apply_fix(issue)
            assert result["success"]
            
            # Check file was fixed
            with open(f.name, 'r') as rf:
                content = rf.read()
                assert "except Exception:" in content
            
            os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_non_fixable_issue(self):
        """Test handling of non-auto-fixable issue"""
        remediator = CodeRemediator()
        issue = {
            "type": "complex_logic_error",
            "file_path": "/tmp/test.py",
            "line_number": 1,
            "auto_fixable": False
        }
        
        result = await remediator.apply_fix(issue)
        assert not result["success"]
        assert "not auto-fixable" in result["reason"].lower()


class TestPlanningValidator:
    """Test planning validator"""
    
    @pytest.mark.asyncio
    async def test_empty_plan(self):
        """Test validation of empty plan"""
        validator = PlanningValidator()
        result = await validator.validate({"tasks": []})
        
        assert result["status"] == "fail"
        assert len(result["issues"]) > 0
    
    @pytest.mark.asyncio
    async def test_task_too_large(self):
        """Test detection of overly large tasks"""
        validator = PlanningValidator()
        plan = {
            "tasks": [
                {
                    "id": "task-1",
                    "description": "Implement entire system",
                    "estimated_hours": 40,  # Too large!
                    "dependencies": [],
                    "acceptance_criteria": ["Done"]
                }
            ]
        }
        
        result = await validator.validate(plan)
        
        issues = result["issues"]
        large_task_issues = [i for i in issues if i["type"] == "task_too_large"]
        assert len(large_task_issues) > 0
    
    @pytest.mark.asyncio
    async def test_circular_dependency(self):
        """Test circular dependency detection"""
        validator = PlanningValidator()
        plan = {
            "tasks": [
                {
                    "id": "task-1",
                    "description": "Task 1",
                    "estimated_hours": 2,
                    "dependencies": ["task-2"],
                    "acceptance_criteria": ["Done"]
                },
                {
                    "id": "task-2",
                    "description": "Task 2",
                    "estimated_hours": 2,
                    "dependencies": ["task-1"],  # Circular!
                    "acceptance_criteria": ["Done"]
                }
            ]
        }
        
        result = await validator.validate(plan)
        
        issues = result["issues"]
        circular_issues = [i for i in issues if i["type"] == "circular_dependency"]
        assert len(circular_issues) > 0
    
    @pytest.mark.asyncio
    async def test_valid_plan(self):
        """Test validation of valid plan"""
        validator = PlanningValidator()
        plan = {
            "tasks": [
                {
                    "id": "task-1",
                    "description": "Implement feature X with proper error handling and tests",
                    "estimated_hours": 3,
                    "dependencies": [],
                    "acceptance_criteria": [
                        "Feature X works correctly",
                        "All tests pass",
                        "Code coverage > 80%"
                    ],
                    "test_strategy": "Unit tests + integration tests",
                    "assignee": "dev-agent-1"
                }
            ]
        }
        
        result = await validator.validate(plan)
        
        # May have warnings but should not fail
        assert result["status"] != "fail"


class TestProductionReadinessChecker:
    """Test production readiness checker"""
    
    @pytest.mark.asyncio
    async def test_readiness_check(self):
        """Test basic readiness check"""
        checker = ProductionReadinessChecker()
        result = await checker.check_readiness([])
        
        # Should have multiple checks
        assert "checks" in result
        assert len(result["checks"]) > 10
    
    @pytest.mark.asyncio
    async def test_hardcoded_secrets_detection(self):
        """Test detection of hardcoded secrets"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('password="secret123"\napi_key="abc123"\n')
            f.flush()
            
            checker = ProductionReadinessChecker()
            result = await checker.check_readiness([f.name])
            
            # Should detect secrets
            secrets_check = [c for c in result["checks"] if "secret" in c["name"].lower()]
            assert len(secrets_check) > 0
            assert not secrets_check[0]["passed"]
            
            os.unlink(f.name)


class TestQAKnowledgeGraph:
    """Test QA knowledge base"""
    
    def test_initialization(self):
        """Test knowledge base initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = QAKnowledgeGraph(storage_path=os.path.join(tmpdir, "kb.json"))
            
            # Should have default patterns
            assert len(kb.knowledge_base) > 0
    
    def test_add_issue(self):
        """Test adding issue to knowledge base"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = QAKnowledgeGraph(storage_path=os.path.join(tmpdir, "kb.json"))
            
            initial_count = len(kb.knowledge_base)
            
            issue = {
                "type": "new_pattern",
                "severity": "HIGH",
                "message": "New issue detected",
                "context": "example code"
            }
            
            kb.add_issue(issue)
            
            # Should add or update entry
            assert "kb_new_pattern" in kb.knowledge_base
    
    def test_query(self):
        """Test querying knowledge base"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = QAKnowledgeGraph(storage_path=os.path.join(tmpdir, "kb.json"))
            
            results = kb.query("sql")
            
            # Should find SQL-related patterns
            assert len(results) > 0
            assert any("sql" in r.pattern.lower() for r in results)
    
    def test_get_context_for_llm(self):
        """Test LLM context generation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = QAKnowledgeGraph(storage_path=os.path.join(tmpdir, "kb.json"))
            
            # Add an issue first
            issue = {
                "type": "test_pattern",
                "severity": "MEDIUM",
                "message": "Test issue",
                "context": "test context"
            }
            kb.add_issue(issue)
            
            context = kb.get_context_for_llm("test_pattern")
            
            assert len(context) > 0
            assert "test_pattern" in context.lower()


class TestQAMetricsCollector:
    """Test QA metrics collector"""
    
    def test_record_review(self):
        """Test recording a review"""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = QAMetricsCollector(storage_path=os.path.join(tmpdir, "metrics.json"))
            
            issues = [
                {"severity": "HIGH", "type": "test1"},
                {"severity": "MEDIUM", "type": "test2"}
            ]
            
            collector.record_review(issues, auto_fixed=1, lines_of_code=100, review_time=5.0)
            
            assert collector.current_period_stats["total_reviews"] == 1
            assert collector.current_period_stats["total_issues"] == 2
    
    def test_calculate_quality_score(self):
        """Test quality score calculation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = QAMetricsCollector(storage_path=os.path.join(tmpdir, "metrics.json"))
            
            # No issues = perfect score
            score = collector.calculate_code_quality_score([], 100)
            assert score == 100.0
            
            # Some issues = lower score
            issues = [
                {"severity": "CRITICAL"},
                {"severity": "HIGH"}
            ]
            score = collector.calculate_code_quality_score(issues, 100)
            assert score < 100.0
    
    def test_daily_report(self):
        """Test daily report generation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = QAMetricsCollector(storage_path=os.path.join(tmpdir, "metrics.json"))
            
            # Record some data
            issues = [{"severity": "MEDIUM"}]
            collector.record_review(issues, auto_fixed=1, lines_of_code=100, review_time=5.0)
            
            report = collector.get_daily_report()
            
            assert "total_reviews" in report
            assert report["total_reviews"] == 1


class TestQAAgent:
    """Test QA Agent"""
    
    @pytest.mark.skip(reason="QAAgent import requires resolving LLM import conflict")
    def test_agent_initialization(self):
        """Test QA agent initialization"""
        # TODO: Fix after resolving app.llm module vs package conflict
        pass
    
    @pytest.mark.skip(reason="QAAgent import requires resolving LLM import conflict")
    def test_qa_levels(self):
        """Test different QA levels"""
        # TODO: Fix after resolving app.llm module vs package conflict
        pass


class TestWorkflowIntegration:
    """Test workflow integration"""
    
    @pytest.mark.asyncio
    async def test_qa_gate_review(self):
        """Test QA gate code review"""
        from app.workflows.qa_integration import QAGate
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test():\n    pass\n")
            f.flush()
            
            gate = QAGate(qa_level="basic", auto_fix=False)
            result = await gate.review_code([f.name], "dev-agent-1", "task-123")
            
            assert "approval_status" in result
            assert "total_issues" in result
            
            os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_planning_validation_integration(self):
        """Test planning validation through QA gate"""
        from app.workflows.qa_integration import QAGate
        
        gate = QAGate()
        
        plan = {
            "tasks": [
                {
                    "id": "task-1",
                    "description": "Test task with good planning",
                    "estimated_hours": 2,
                    "dependencies": [],
                    "acceptance_criteria": ["Criterion 1", "Criterion 2"],
                    "test_strategy": "Unit tests",
                    "assignee": "dev-1"
                }
            ]
        }
        
        result = await gate.validate_planning(plan)
        
        assert "status" in result
        assert result["status"] in ["pass", "warning", "fail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
