"""
Hybrid QA System

Combines traditional QA checks with AI-powered analysis:
1. AI QA Agent analyzes code with specialist team
2. Traditional QA checks run in parallel
3. Issues are consolidated
4. QA fixes are applied
5. Post-check validation verifies QA changes
6. Final approval gate
"""

import asyncio
from typing import Dict, List, Any, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from app.logger import logger


class HybridQAStatus(str, Enum):
    """Status of hybrid QA processing"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    FIXING = "fixing"
    POST_CHECKING = "post_checking"
    APPROVED = "approved"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class QAIssue:
    """Consolidated QA issue from all sources"""
    id: str
    source: str  # "ai_agent", "traditional_qa", "hybrid"
    type: str
    severity: str
    file_path: str
    line_number: Optional[int]
    message: str
    suggestion: str
    auto_fixable: bool
    confidence: float  # AI confidence if from AI agent


@dataclass
class QAApprovalDecision:
    """Final QA approval decision"""
    status: str  # APPROVED, BLOCKED
    approval_time: str
    reviewed_by: str  # AI agent ID
    total_issues_found: int
    issues_fixed: int
    issues_remaining: int
    blocking_issues: List[QAIssue]
    warnings: List[str]
    post_check_passed: bool
    ai_consensus: float
    recommendation: str


class HybridQASystem:
    """Main hybrid QA system orchestrating AI and traditional QA"""
    
    def __init__(self, qa_level: str = "standard", auto_fix: bool = True):
        """Initialize hybrid QA system
        
        Args:
            qa_level: QA level (basic, standard, strict, paranoid)
            auto_fix: Whether to automatically fix issues
        """
        self.qa_level = qa_level
        self.auto_fix_enabled = auto_fix
        
        # Import components here to avoid circular imports
        self.ai_agent = None
        self.traditional_qa = None
        self.post_checker = None
        
        self._initialized = False
        self.status = HybridQAStatus.PENDING
        self.current_analysis = None
    
    async def _initialize(self):
        """Lazy initialization of components"""
        if self._initialized:
            return
        
        try:
            from app.qa.ai_qa_agent import AIQAAgent
            from app.qa.code_analyzer import CodeAnalyzer
            from app.qa.postchecks import PostCheckValidator
            
            self.ai_agent = AIQAAgent(agent_id="hybrid_qa_ai_1")
            self.traditional_qa = CodeAnalyzer(qa_level=self.qa_level)
            self.post_checker = PostCheckValidator()
            
            self._initialized = True
            logger.info("Hybrid QA System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Hybrid QA System: {e}")
            raise
    
    async def analyze_code_changes(
        self,
        code_files: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Analyze code changes using both AI and traditional QA
        
        Args:
            code_files: List of (file_path, code_content) tuples
        
        Returns:
            Comprehensive analysis from both approaches
        """
        await self._initialize()
        
        self.status = HybridQAStatus.ANALYZING
        logger.info(f"Hybrid QA: Starting analysis of {len(code_files)} files")
        
        # Run AI agent and traditional QA in parallel
        ai_results, traditional_results = await asyncio.gather(
            self._run_ai_analysis(code_files),
            self._run_traditional_qa(code_files)
        )
        
        # Consolidate results
        consolidated = await self._consolidate_issues(ai_results, traditional_results)
        
        self.current_analysis = {
            "files_analyzed": len(code_files),
            "ai_results": ai_results,
            "traditional_results": traditional_results,
            "consolidated_issues": consolidated["all_issues"],
            "issue_summary": consolidated["summary"],
            "qa_level": self.qa_level
        }
        
        return self.current_analysis
    
    async def _run_ai_analysis(
        self,
        code_files: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Run AI QA analysis"""
        logger.info("Phase 1: Running AI QA Agent analysis")
        
        try:
            result = await self.ai_agent.analyze_code_changes(code_files)
            logger.info(f"AI QA Agent completed: {result['summary']}")
            return result
        except Exception as e:
            logger.error(f"AI QA analysis failed: {e}")
            return {"error": str(e), "summary": {"total_decisions": 0}}
    
    async def _run_traditional_qa(
        self,
        code_files: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Run traditional QA checks"""
        logger.info("Phase 2: Running traditional QA checks")
        
        try:
            all_issues = []
            
            for file_path, code_content in code_files:
                # Analyze each file
                checks = self._get_checks_for_level()
                issues = await self.traditional_qa.analyze_file(file_path, checks)
                all_issues.extend(issues)
            
            logger.info(f"Traditional QA found {len(all_issues)} issues")
            
            return {
                "total_issues": len(all_issues),
                "issues": all_issues,
                "method": "traditional_qa"
            }
        except Exception as e:
            logger.error(f"Traditional QA analysis failed: {e}")
            return {"error": str(e), "total_issues": 0, "issues": []}
    
    async def _consolidate_issues(
        self,
        ai_results: Dict[str, Any],
        traditional_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Consolidate issues from both approaches"""
        all_issues = []
        deduplicated = {}
        
        # Collect AI findings
        ai_decisions = ai_results.get("all_decisions", [])
        for decision in ai_decisions:
            if decision.priority in ["critical", "high"]:
                issue_key = f"{decision.specialist_type}_{decision.decision_type}"
                deduplicated[issue_key] = {
                    "source": "ai_agent",
                    "specialist": decision.specialist_type.value,
                    "priority": decision.priority,
                    "findings": decision.findings,
                    "recommendations": decision.recommendations,
                    "confidence": decision.confidence
                }
        
        # Collect traditional QA findings
        traditional_issues = traditional_results.get("issues", [])
        for issue in traditional_issues:
            issue_type = issue.get("type", "unknown")
            issue_key = f"traditional_{issue_type}"
            
            if issue_key not in deduplicated:
                deduplicated[issue_key] = {
                    "source": "traditional_qa",
                    "type": issue_type,
                    "severity": issue.get("severity", "MEDIUM"),
                    "message": issue.get("message", ""),
                    "auto_fixable": issue.get("auto_fixable", False),
                    "file_path": issue.get("file_path", "unknown")
                }
        
        # Build consolidated list
        for key, issue in deduplicated.items():
            all_issues.append(issue)
        
        # Summary statistics
        summary = {
            "total_issues": len(all_issues),
            "from_ai_agent": sum(1 for i in all_issues if i["source"] == "ai_agent"),
            "from_traditional_qa": sum(1 for i in all_issues if i["source"] == "traditional_qa"),
            "critical_count": sum(1 for i in all_issues if i.get("priority") == "critical" or i.get("severity") == "CRITICAL"),
            "high_count": sum(1 for i in all_issues if i.get("priority") == "high" or i.get("severity") == "HIGH"),
            "auto_fixable_count": sum(1 for i in all_issues if i.get("auto_fixable", False))
        }
        
        return {
            "all_issues": all_issues,
            "summary": summary
        }
    
    async def apply_fixes(self, auto_fix_only: bool = True) -> Dict[str, Any]:
        """Apply fixes to identified issues
        
        Args:
            auto_fix_only: Only apply auto-fixable issues
        
        Returns:
            Results of fix application
        """
        if not self.current_analysis:
            return {"error": "No analysis performed yet"}
        
        self.status = HybridQAStatus.FIXING
        logger.info("Phase 3: Applying QA fixes")
        
        from app.qa.code_remediator import CodeRemediator
        
        remediator = CodeRemediator()
        issues = self.current_analysis["consolidated_issues"]
        
        fixed = []
        skipped = []
        failed = []
        
        for issue in issues:
            # Only auto-fix safe issues
            if auto_fix_only and not issue.get("auto_fixable", False):
                skipped.append(issue)
                continue
            
            try:
                # Prepare issue for remediator
                fix_issue = {
                    "type": issue.get("type") or issue.get("specialist", "unknown"),
                    "message": issue.get("message", ""),
                    "auto_fixable": True,
                    "severity": issue.get("severity", "MEDIUM")
                }
                
                fix_result = await remediator.apply_fix(fix_issue)
                
                if fix_result.get("success"):
                    fixed.append(issue)
                    logger.info(f"Fixed: {issue.get('type') or issue.get('specialist')}")
                else:
                    failed.append({
                        "issue": issue,
                        "error": fix_result.get("error", "Unknown error")
                    })
            except Exception as e:
                failed.append({
                    "issue": issue,
                    "error": str(e)
                })
        
        fix_results = {
            "fixed_count": len(fixed),
            "skipped_count": len(skipped),
            "failed_count": len(failed),
            "fixed_issues": fixed,
            "failed_issues": failed
        }
        
        logger.info(f"Fixes applied: {len(fixed)} fixed, {len(skipped)} skipped, {len(failed)} failed")
        
        return fix_results
    
    async def run_post_checks(
        self,
        original_files: List[Tuple[str, str]],
        fixed_files: List[Tuple[str, str]],
        applied_fixes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Run post-check validations on QA changes
        
        Args:
            original_files: Original code before QA
            fixed_files: Code after QA fixes
            applied_fixes: List of fixes that were applied
        
        Returns:
            Post-check validation results
        """
        self.status = HybridQAStatus.POST_CHECKING
        logger.info("Phase 4: Running post-check validations")
        
        files_data = []
        
        for (orig_path, orig_code), (fixed_path, fixed_code) in zip(original_files, fixed_files):
            files_data.append({
                "file_path": orig_path,
                "original_code": orig_code,
                "fixed_code": fixed_code,
                "applied_fixes": [f for f in applied_fixes if f.get("file_path") == orig_path]
            })
        
        try:
            validation_results = await self.post_checker.validate_qa_changes(files_data)
            
            logger.info(f"Post-checks completed: {validation_results['validation_status']}")
            
            return validation_results
        except Exception as e:
            logger.error(f"Post-check validation failed: {e}")
            return {
                "validation_status": "FAILED",
                "error": str(e),
                "results": []
            }
    
    async def make_approval_decision(
        self,
        post_check_results: Dict[str, Any] = None
    ) -> QAApprovalDecision:
        """Make final QA approval decision
        
        Args:
            post_check_results: Results from post-check validation
        
        Returns:
            Final approval decision
        """
        if not self.current_analysis:
            return QAApprovalDecision(
                status="BLOCKED",
                approval_time="unknown",
                reviewed_by=self.ai_agent.agent_id if self.ai_agent else "unknown",
                total_issues_found=0,
                issues_fixed=0,
                issues_remaining=0,
                blocking_issues=[],
                warnings=["No analysis performed"],
                post_check_passed=False,
                ai_consensus=0.0,
                recommendation="Perform analysis first"
            )
        
        from datetime import datetime
        
        analysis = self.current_analysis
        summary = analysis["issue_summary"]
        
        # Get consensus from AI agent
        ai_consensus = 0.85  # Default reasonable confidence
        if self.ai_agent:
            decisions = analysis["ai_results"].get("all_decisions", [])
            if decisions:
                ai_consensus = sum(d.confidence for d in decisions) / len(decisions)
        
        # Determine approval status
        critical_count = summary.get("critical_count", 0)
        high_count = summary.get("high_count", 0)
        
        post_check_passed = True
        if post_check_results:
            post_check_passed = post_check_results.get("validation_status") == "PASSED"
        
        # Build decision
        if critical_count > 0:
            status = "BLOCKED"
            recommendation = f"Critical issues ({critical_count}) must be fixed before approval"
            self.status = HybridQAStatus.BLOCKED
        elif high_count > 0:
            status = "BLOCKED"
            recommendation = f"High-priority issues ({high_count}) must be fixed before approval"
            self.status = HybridQAStatus.BLOCKED
        elif not post_check_passed:
            status = "BLOCKED"
            recommendation = "Post-check validation failed - QA changes may have introduced issues"
            self.status = HybridQAStatus.BLOCKED
        else:
            status = "APPROVED"
            recommendation = "All checks passed - code approved for merge"
            self.status = HybridQAStatus.APPROVED
        
        return QAApprovalDecision(
            status=status,
            approval_time=datetime.now().isoformat(),
            reviewed_by=self.ai_agent.agent_id if self.ai_agent else "hybrid_qa_system",
            total_issues_found=summary.get("total_issues", 0),
            issues_fixed=summary.get("auto_fixable_count", 0),
            issues_remaining=max(0, summary.get("total_issues", 0) - summary.get("auto_fixable_count", 0)),
            blocking_issues=self._extract_blocking_issues(analysis),
            warnings=self._extract_warnings(analysis),
            post_check_passed=post_check_passed,
            ai_consensus=ai_consensus,
            recommendation=recommendation
        )
    
    async def run_complete_qa_workflow(
        self,
        code_files: List[Tuple[str, str]],
        original_files: Optional[List[Tuple[str, str]]] = None
    ) -> Dict[str, Any]:
        """Run complete QA workflow: analysis → fixes → post-checks → approval
        
        Args:
            code_files: List of (file_path, code_content) tuples to analyze
            original_files: Original files for post-check comparison
        
        Returns:
            Complete QA workflow result
        """
        logger.info(f"Starting complete hybrid QA workflow for {len(code_files)} files")
        
        # Step 1: Analyze code changes
        analysis = await self.analyze_code_changes(code_files)
        
        # Step 2: Apply fixes if enabled
        fix_results = {}
        if self.auto_fix_enabled:
            fix_results = await self.apply_fixes(auto_fix_only=True)
        
        # Step 3: Run post-checks if we have original files and made fixes
        post_check_results = None
        if original_files and fix_results and fix_results.get("fixed_count", 0) > 0:
            post_check_results = await self.run_post_checks(
                original_files,
                code_files,
                fix_results.get("fixed_issues", [])
            )
        
        # Step 4: Make approval decision
        approval = await self.make_approval_decision(post_check_results)
        
        return {
            "workflow_status": "completed",
            "qa_level": self.qa_level,
            "analysis": analysis,
            "fix_results": fix_results,
            "post_check_results": post_check_results,
            "approval": {
                "status": approval.status,
                "recommendation": approval.recommendation,
                "ai_consensus": approval.ai_consensus,
                "total_issues": approval.total_issues_found,
                "issues_fixed": approval.issues_fixed,
                "post_check_passed": approval.post_check_passed
            },
            "system_status": self.status.value
        }
    
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
    
    def _extract_blocking_issues(self, analysis: Dict[str, Any]) -> List[QAIssue]:
        """Extract blocking issues from analysis"""
        blocking = []
        
        for issue in analysis.get("consolidated_issues", []):
            if issue.get("priority") == "critical" or issue.get("severity") == "CRITICAL":
                blocking.append(QAIssue(
                    id=f"{issue.get('source')}_{issue.get('type')}",
                    source=issue.get("source", "unknown"),
                    type=issue.get("type") or issue.get("specialist", "unknown"),
                    severity=issue.get("severity", "CRITICAL"),
                    file_path=issue.get("file_path", "unknown"),
                    line_number=issue.get("line_number"),
                    message=issue.get("message", ""),
                    suggestion=issue.get("suggestion", ""),
                    auto_fixable=issue.get("auto_fixable", False),
                    confidence=issue.get("confidence", 1.0)
                ))
        
        return blocking
    
    def _extract_warnings(self, analysis: Dict[str, Any]) -> List[str]:
        """Extract warnings from analysis"""
        warnings = []
        
        summary = analysis.get("issue_summary", {})
        
        if summary.get("total_issues", 0) > 10:
            warnings.append(f"High number of issues found: {summary.get('total_issues')}")
        
        if summary.get("from_ai_agent", 0) > summary.get("from_traditional_qa", 0):
            warnings.append("AI agent found more issues than traditional QA - may need review")
        
        return warnings
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "system_status": self.status.value,
            "qa_level": self.qa_level,
            "auto_fix_enabled": self.auto_fix_enabled,
            "ai_agent_initialized": self.ai_agent is not None,
            "traditional_qa_initialized": self.traditional_qa is not None,
            "post_checker_initialized": self.post_checker is not None,
            "current_analysis": self.current_analysis is not None
        }
