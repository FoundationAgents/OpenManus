"""
QA Integration with Workflow

Integrates QA gate into development workflow:
Dev Agent → QA Agent → Production
"""

from typing import Dict, List, Optional, Any, Tuple
from app.logger import logger
from app.qa import (
    CodeAnalyzer,
    CodeRemediator,
    PlanningValidator,
    ProductionReadinessChecker,
    QAKnowledgeGraph,
    QAMetricsCollector,
    HybridQASystem
)


class QAGate:
    """QA gate for code review"""
    
    def __init__(self, qa_level: str = "standard", auto_fix: bool = True):
        self.qa_level = qa_level
        self.auto_fix_enabled = auto_fix
        self.auto_fix_safe_only = True
        
        # Initialize QA components
        self.analyzer = CodeAnalyzer(qa_level=qa_level)
        self.remediator = CodeRemediator()
        self.prod_checker = ProductionReadinessChecker()
        self.knowledge_base = QAKnowledgeGraph()
        self.metrics = QAMetricsCollector()
    
    async def review_code(
        self,
        code_files: List[str],
        author_agent: str,
        task_id: str
    ) -> Dict[str, Any]:
        """Review code changes"""
        logger.info(f"QA Gate: Reviewing code from {author_agent} for task {task_id}")
        
        # Analyze code
        checks = self._get_checks_for_level()
        all_issues = []
        
        for file_path in code_files:
            issues = await self.analyzer.analyze_file(file_path, checks)
            all_issues.extend(issues)
        
        # Learn from issues
        for issue in all_issues:
            self.knowledge_base.add_issue(issue)
        
        # Auto-fix if enabled
        auto_fixed = []
        manual_required = []
        
        if self.auto_fix_enabled:
            for issue in all_issues:
                if issue.get("auto_fixable", False):
                    if self.auto_fix_safe_only and not self._is_safe_fix(issue):
                        manual_required.append(issue)
                        continue
                    
                    fix_result = await self.remediator.apply_fix(issue)
                    if fix_result.get("success"):
                        auto_fixed.append(issue)
                    else:
                        manual_required.append(issue)
                else:
                    manual_required.append(issue)
        else:
            manual_required = all_issues
        
        # Determine approval status
        approval = self._determine_approval(manual_required)
        
        # Record metrics
        loc = self._count_lines_of_code(code_files)
        self.metrics.record_review(all_issues, len(auto_fixed), loc, 0)  # TODO: track review time
        
        result = {
            "task_id": task_id,
            "author_agent": author_agent,
            "approval_status": approval["status"],
            "total_issues": len(all_issues),
            "auto_fixed": len(auto_fixed),
            "manual_required": len(manual_required),
            "blockers": approval["blockers"],
            "issues": {
                "all": all_issues,
                "fixed": auto_fixed,
                "pending": manual_required
            }
        }
        
        logger.info(f"QA Gate: {approval['status']} - {len(all_issues)} issues found, {len(auto_fixed)} auto-fixed")
        
        return result
    
    async def validate_planning(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate task planning"""
        validator = PlanningValidator()
        result = await validator.validate(plan_data)
        
        return result
    
    async def check_production_readiness(self, code_files: List[str]) -> Dict[str, Any]:
        """Check production readiness"""
        result = await self.prod_checker.check_readiness(code_files)
        
        return result
    
    def _get_checks_for_level(self) -> List[str]:
        """Get checks for QA level"""
        checks_by_level = {
            "basic": [
                "syntax_validation",
                "import_check",
                "basic_linting"
            ],
            "standard": [
                "syntax_validation",
                "import_check",
                "basic_linting",
                "code_smell_detection",
                "naming_convention_check",
                "error_handling_validation"
            ],
            "strict": [
                "syntax_validation",
                "import_check",
                "basic_linting",
                "code_smell_detection",
                "naming_convention_check",
                "error_handling_validation",
                "performance_analysis",
                "security_scan",
                "architectural_pattern_check"
            ],
            "paranoid": [
                "syntax_validation",
                "import_check",
                "basic_linting",
                "code_smell_detection",
                "naming_convention_check",
                "error_handling_validation",
                "performance_analysis",
                "security_scan",
                "architectural_pattern_check",
                "style_nitpick_check",
                "documentation_completeness",
                "test_coverage_check"
            ]
        }
        
        return checks_by_level.get(self.qa_level, checks_by_level["standard"])
    
    def _is_safe_fix(self, issue: Dict[str, Any]) -> bool:
        """Check if fix is safe to apply automatically"""
        # Only formatting and import fixes are considered safe
        safe_types = [
            "import_order",
            "trailing_whitespace",
            "bare_except",
            "missing_docstring"
        ]
        
        return issue.get("type") in safe_types
    
    def _determine_approval(self, manual_required: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Determine approval status"""
        critical = [i for i in manual_required if i.get("severity") == "CRITICAL"]
        high = [i for i in manual_required if i.get("severity") == "HIGH"]
        
        if critical:
            return {
                "status": "BLOCKED",
                "reason": "Critical issues must be fixed",
                "blockers": critical
            }
        elif high:
            return {
                "status": "BLOCKED",
                "reason": "High priority issues must be fixed",
                "blockers": high
            }
        elif manual_required:
            return {
                "status": "APPROVED_WITH_RECOMMENDATIONS",
                "reason": "Some issues found but not blocking",
                "blockers": []
            }
        else:
            return {
                "status": "APPROVED",
                "reason": "All checks passed",
                "blockers": []
            }
    
    def _count_lines_of_code(self, code_files: List[str]) -> int:
        """Count lines of code"""
        total = 0
        
        for file_path in code_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Count non-empty, non-comment lines
                    total += sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))
            except Exception as e:
                logger.debug(f"Could not count lines in {file_path}: {e}")
        
        return total


class QAWorkflowIntegration:
    """Integrates QA into workflow manager"""
    
    def __init__(self, qa_gate: QAGate):
        self.qa_gate = qa_gate
    
    async def process_dev_task_completion(
        self,
        task_id: str,
        code_files: List[str],
        author_agent: str
    ) -> Dict[str, Any]:
        """Process dev task completion through QA gate"""
        # Step 1: Code review
        review_result = await self.qa_gate.review_code(code_files, author_agent, task_id)
        
        if review_result["approval_status"] == "BLOCKED":
            return {
                "stage": "code_review",
                "status": "blocked",
                "result": review_result,
                "next_action": "fix_issues"
            }
        
        # Step 2: Production readiness (if approved)
        if review_result["approval_status"] in ["APPROVED", "APPROVED_WITH_RECOMMENDATIONS"]:
            readiness_result = await self.qa_gate.check_production_readiness(code_files)
            
            if not readiness_result["ready"]:
                return {
                    "stage": "production_readiness",
                    "status": "blocked",
                    "result": readiness_result,
                    "next_action": "fix_readiness_issues"
                }
            
            # All checks passed
            return {
                "stage": "complete",
                "status": "approved",
                "code_review": review_result,
                "prod_readiness": readiness_result,
                "next_action": "merge_to_main"
            }
        
        return {
            "stage": "code_review",
            "status": "needs_review",
            "result": review_result,
            "next_action": "review_recommendations"
        }
    
    async def process_planning_task(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process planning validation"""
        validation_result = await self.qa_gate.validate_planning(plan_data)
        
        if validation_result["status"] == "fail":
            return {
                "status": "blocked",
                "result": validation_result,
                "next_action": "fix_planning_issues"
            }
        
        return {
            "status": "approved",
            "result": validation_result,
            "next_action": "proceed_with_plan"
        }


class HybridQAGate:
    """Hybrid QA gate combining AI and traditional QA
    
    Features:
    - AI-powered code analysis with specialist team
    - Traditional QA checks in parallel
    - Automatic fix application
    - Post-check validation to ensure QA changes are correct
    - Final approval decision
    """
    
    def __init__(self, qa_level: str = "standard", auto_fix: bool = True, enable_postcheck: bool = True):
        """Initialize Hybrid QA Gate
        
        Args:
            qa_level: QA level (basic, standard, strict, paranoid)
            auto_fix: Whether to automatically fix issues
            enable_postcheck: Whether to run post-check validation
        """
        self.qa_level = qa_level
        self.auto_fix_enabled = auto_fix
        self.enable_postcheck = enable_postcheck
        self.hybrid_qa = HybridQASystem(qa_level=qa_level, auto_fix=auto_fix)
    
    async def review_code_hybrid(
        self,
        code_files: List[Tuple[str, str]],
        original_files: Optional[List[Tuple[str, str]]] = None,
        author_agent: str = "unknown",
        task_id: str = "unknown"
    ) -> Dict[str, Any]:
        """Review code using hybrid QA system
        
        Args:
            code_files: List of (file_path, code_content) tuples
            original_files: Original files for post-check comparison
            author_agent: ID of the agent that created the code
            task_id: ID of the task
        
        Returns:
            Hybrid QA review result with approval decision
        """
        logger.info(f"Hybrid QA Gate: Reviewing {len(code_files)} files from {author_agent} (task {task_id})")
        
        # Run complete hybrid QA workflow
        workflow_result = await self.hybrid_qa.run_complete_qa_workflow(
            code_files=code_files,
            original_files=original_files
        )
        
        return {
            "task_id": task_id,
            "author_agent": author_agent,
            "review_method": "hybrid_qa",
            "approval_status": workflow_result["approval"]["status"],
            "recommendation": workflow_result["approval"]["recommendation"],
            "ai_consensus": workflow_result["approval"]["ai_consensus"],
            "total_issues": workflow_result["approval"]["total_issues"],
            "issues_fixed": workflow_result["approval"]["issues_fixed"],
            "post_check_passed": workflow_result["approval"]["post_check_passed"],
            "analysis": workflow_result["analysis"],
            "fix_results": workflow_result.get("fix_results", {}),
            "post_check_results": workflow_result.get("post_check_results"),
            "workflow_status": workflow_result["workflow_status"],
            "qa_level": workflow_result["qa_level"]
        }
    
    async def process_dev_task_with_hybrid_qa(
        self,
        task_id: str,
        code_files: List[str],
        author_agent: str,
        original_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Process dev task completion through hybrid QA gate
        
        Workflow:
        1. Code analysis (AI + traditional QA)
        2. Issue fixing
        3. Post-check validation
        4. Final approval
        5. Readiness check (if approved)
        
        Args:
            task_id: Task ID
            code_files: List of code file paths
            author_agent: Author agent ID
            original_files: Original file paths for post-check
        
        Returns:
            Complete processing result
        """
        logger.info(f"Processing task {task_id} through hybrid QA gate")
        
        # Read files
        code_content_files = []
        for file_path in code_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code_content_files.append((file_path, f.read()))
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                return {
                    "task_id": task_id,
                    "stage": "file_read",
                    "status": "failed",
                    "error": f"Could not read files: {e}"
                }
        
        # Read original files if provided
        original_content_files = None
        if original_files:
            original_content_files = []
            for file_path in original_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        original_content_files.append((file_path, f.read()))
                except Exception as e:
                    logger.warning(f"Could not read original file {file_path}: {e}")
        
        # Run hybrid QA review
        review_result = await self.review_code_hybrid(
            code_files=code_content_files,
            original_files=original_content_files,
            author_agent=author_agent,
            task_id=task_id
        )
        
        # Check approval status
        if review_result["approval_status"] == "BLOCKED":
            return {
                "task_id": task_id,
                "stage": "hybrid_qa",
                "status": "blocked",
                "result": review_result,
                "next_action": "fix_issues",
                "reason": review_result["recommendation"]
            }
        
        # If approved, run production readiness check
        if review_result["approval_status"] == "APPROVED":
            qa_gate = QAGate(qa_level=self.qa_level)
            readiness_result = await qa_gate.check_production_readiness(code_files)
            
            if not readiness_result.get("ready", True):
                return {
                    "task_id": task_id,
                    "stage": "production_readiness",
                    "status": "blocked",
                    "result": readiness_result,
                    "next_action": "fix_readiness_issues"
                }
            
            # All checks passed
            return {
                "task_id": task_id,
                "stage": "complete",
                "status": "approved",
                "hybrid_qa_review": review_result,
                "prod_readiness": readiness_result,
                "next_action": "merge_to_main"
            }
        
        # Approved with recommendations
        return {
            "task_id": task_id,
            "stage": "hybrid_qa",
            "status": "approved_with_recommendations",
            "result": review_result,
            "next_action": "review_recommendations"
        }


class HybridQAWorkflowIntegration:
    """Integrates hybrid QA into workflow manager"""
    
    def __init__(self, hybrid_qa_gate: HybridQAGate):
        self.hybrid_qa_gate = hybrid_qa_gate
    
    async def process_task_with_hybrid_qa(
        self,
        task_id: str,
        code_files: List[str],
        author_agent: str,
        original_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Process task through hybrid QA"""
        return await self.hybrid_qa_gate.process_dev_task_with_hybrid_qa(
            task_id=task_id,
            code_files=code_files,
            author_agent=author_agent,
            original_files=original_files
        )
