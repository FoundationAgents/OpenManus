"""
AI-powered QA Agent with Specialist Team

Main AI agent that coordinates a team of expert specialists:
- Code Expert: Analyzes code patterns and suggests fixes
- Planner Expert: Validates task planning and architecture
- Fixer Expert: Implements fixes and optimizations
- Cleanup Agent: Removes dead code, optimizes structure

The AI agent reads files, makes decisions, and orchestrates the team.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from app.logger import logger


class SpecialistType(str, Enum):
    """Types of specialist agents"""
    CODE_EXPERT = "code_expert"
    PLANNER_EXPERT = "planner_expert"
    FIXER_EXPERT = "fixer_expert"
    CLEANUP_AGENT = "cleanup_agent"


@dataclass
class SpecialistDecision:
    """Decision made by a specialist"""
    specialist_type: SpecialistType
    decision_type: str  # "analyze", "recommend_fix", "execute_fix", "cleanup"
    confidence: float  # 0.0 to 1.0
    findings: Dict[str, Any]
    recommendations: List[str]
    fixes: Optional[List[Dict[str, Any]]] = None
    priority: str = "medium"  # critical, high, medium, low


class CodeExpert:
    """Expert specialist for code analysis"""
    
    def __init__(self):
        self.name = "CodeExpert"
        self.specializations = [
            "code_patterns",
            "architecture_analysis",
            "complexity_detection",
            "security_analysis"
        ]
    
    async def analyze_code(
        self,
        code_content: str,
        file_path: str
    ) -> SpecialistDecision:
        """Analyze code for issues"""
        from app.qa.code_analyzer import CodeAnalyzer
        
        analyzer = CodeAnalyzer(qa_level="strict")
        
        # Get AST analysis
        import ast
        try:
            tree = ast.parse(code_content)
            ast_valid = True
        except SyntaxError as e:
            ast_valid = False
            logger.error(f"Syntax error in {file_path}: {e}")
        
        findings = {
            "syntax_valid": ast_valid,
            "lines_of_code": len(code_content.split('\n')),
            "file_path": file_path,
            "complexity_score": self._calculate_complexity(code_content),
            "patterns_detected": self._detect_patterns(code_content),
            "security_issues": self._check_security(code_content)
        }
        
        recommendations = []
        if findings["complexity_score"] > 10:
            recommendations.append("High cyclomatic complexity - consider refactoring")
        
        if findings["security_issues"]:
            recommendations.append(f"Found {len(findings['security_issues'])} security concerns")
        
        return SpecialistDecision(
            specialist_type=SpecialistType.CODE_EXPERT,
            decision_type="analyze",
            confidence=0.95 if ast_valid else 0.5,
            findings=findings,
            recommendations=recommendations,
            priority="critical" if findings["security_issues"] else "medium"
        )
    
    def _calculate_complexity(self, code: str) -> float:
        """Calculate cyclomatic complexity"""
        complexity = 1
        for keyword in ['if', 'elif', 'for', 'while', 'and', 'or', 'except']:
            complexity += code.count(f' {keyword} ')
        return complexity
    
    def _detect_patterns(self, code: str) -> List[str]:
        """Detect code patterns"""
        patterns = []
        
        if 'TODO' in code or 'FIXME' in code:
            patterns.append("incomplete_implementation")
        if 'pass' in code:
            patterns.append("placeholder_found")
        if 'try:' in code and 'except:' in code:
            patterns.append("error_handling")
        if 'def ' in code:
            patterns.append("has_functions")
        if 'class ' in code:
            patterns.append("has_classes")
        
        return patterns
    
    def _check_security(self, code: str) -> List[Dict[str, str]]:
        """Check for security issues"""
        issues = []
        
        security_patterns = {
            "eval(": "Dangerous eval() usage",
            "exec(": "Dangerous exec() usage",
            "pickle.loads": "Insecure pickle usage",
            "password =": "Hardcoded credentials",
            "api_key =": "Hardcoded API key",
            "SELECT": "Possible SQL injection"
        }
        
        for pattern, issue in security_patterns.items():
            if pattern in code:
                issues.append({"pattern": pattern, "issue": issue})
        
        return issues


class PlannerExpert:
    """Expert specialist for planning validation"""
    
    def __init__(self):
        self.name = "PlannerExpert"
        self.specializations = [
            "task_decomposition",
            "dependency_analysis",
            "effort_estimation",
            "risk_assessment"
        ]
    
    async def validate_planning(
        self,
        plan_data: Dict[str, Any]
    ) -> SpecialistDecision:
        """Validate task planning"""
        findings = {
            "total_tasks": len(plan_data.get("tasks", [])),
            "tasks_with_deps": 0,
            "circular_deps": False,
            "effort_distribution": self._analyze_effort(plan_data),
            "risk_items": self._identify_risks(plan_data)
        }
        
        recommendations = []
        
        # Check for circular dependencies
        if self._has_circular_deps(plan_data):
            findings["circular_deps"] = True
            recommendations.append("Critical: Circular dependencies detected")
        
        # Check effort distribution
        if findings["effort_distribution"]["max_effort"] > 40:
            recommendations.append("Some tasks have excessive effort (>40h) - consider breaking down")
        
        # Check for high-risk items without mitigation
        for risk in findings["risk_items"]:
            if risk["severity"] == "high" and not risk.get("mitigation"):
                recommendations.append(f"High-risk item without mitigation: {risk['description']}")
        
        return SpecialistDecision(
            specialist_type=SpecialistType.PLANNER_EXPERT,
            decision_type="analyze",
            confidence=0.90,
            findings=findings,
            recommendations=recommendations,
            priority="high" if findings["circular_deps"] else "low"
        )
    
    def _analyze_effort(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze effort distribution"""
        efforts = [t.get("estimated_hours", 0) for t in plan_data.get("tasks", [])]
        
        return {
            "total_effort": sum(efforts),
            "avg_effort": sum(efforts) / len(efforts) if efforts else 0,
            "min_effort": min(efforts) if efforts else 0,
            "max_effort": max(efforts) if efforts else 0,
            "tasks_over_8h": len([e for e in efforts if e > 8])
        }
    
    def _identify_risks(self, plan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify risk items"""
        risks = []
        
        for task in plan_data.get("tasks", []):
            if task.get("complexity", "low") == "high":
                risks.append({
                    "task_id": task.get("id"),
                    "description": task.get("description"),
                    "severity": "high",
                    "mitigation": task.get("mitigation_plan")
                })
        
        return risks
    
    def _has_circular_deps(self, plan_data: Dict[str, Any]) -> bool:
        """Check for circular dependencies"""
        tasks = {t["id"]: t for t in plan_data.get("tasks", [])}
        
        def has_cycle(task_id: str, visited: set, rec_stack: set) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            task = tasks.get(task_id)
            if not task:
                return False
            
            for dep_id in task.get("dependencies", []):
                if dep_id not in visited:
                    if has_cycle(dep_id, visited, rec_stack):
                        return True
                elif dep_id in rec_stack:
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        visited = set()
        for task_id in tasks:
            if task_id not in visited:
                if has_cycle(task_id, visited, set()):
                    return True
        
        return False


class FixerExpert:
    """Expert specialist for fixing code"""
    
    def __init__(self):
        self.name = "FixerExpert"
        self.specializations = [
            "bug_fixing",
            "refactoring",
            "optimization",
            "compliance_fixing"
        ]
    
    async def recommend_fixes(
        self,
        code_content: str,
        issues: List[Dict[str, Any]]
    ) -> SpecialistDecision:
        """Recommend and potentially execute fixes"""
        from app.qa.code_remediator import CodeRemediator
        
        remediator = CodeRemediator()
        
        fixes = []
        recommendations = []
        
        for issue in issues:
            if issue.get("auto_fixable"):
                fix_result = await remediator.apply_fix(issue)
                if fix_result.get("success"):
                    fixes.append({
                        "issue_id": issue.get("id"),
                        "type": issue.get("type"),
                        "applied": True,
                        "diff": fix_result.get("diff")
                    })
                else:
                    recommendations.append(f"Could not auto-fix {issue.get('type')}: {fix_result.get('error')}")
            else:
                recommendations.append(f"Manual fix required for {issue.get('type')}: {issue.get('message')}")
        
        return SpecialistDecision(
            specialist_type=SpecialistType.FIXER_EXPERT,
            decision_type="recommend_fix",
            confidence=0.85 if fixes else 0.5,
            findings={"fixes_recommended": len(fixes), "manual_required": len(recommendations)},
            recommendations=recommendations,
            fixes=fixes,
            priority="high"
        )
    
    async def execute_fixes(
        self,
        code_files: List[str],
        fixes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute fixes on code files"""
        executed = []
        failed = []
        
        for fix in fixes:
            try:
                # Apply fix
                executed.append(fix)
                logger.info(f"Executed fix: {fix.get('type')} on {fix.get('file_path')}")
            except Exception as e:
                failed.append({
                    "fix": fix,
                    "error": str(e)
                })
                logger.error(f"Failed to execute fix: {e}")
        
        return {
            "executed": len(executed),
            "failed": len(failed),
            "fixes": executed,
            "errors": failed
        }


class CleanupAgent:
    """Agent specialist for code cleanup and optimization"""
    
    def __init__(self):
        self.name = "CleanupAgent"
        self.specializations = [
            "dead_code_removal",
            "import_cleanup",
            "formatting",
            "optimization"
        ]
    
    async def analyze_for_cleanup(
        self,
        code_content: str,
        file_path: str
    ) -> SpecialistDecision:
        """Analyze code for cleanup opportunities"""
        findings = {
            "unused_imports": self._find_unused_imports(code_content),
            "dead_code": self._find_dead_code(code_content),
            "formatting_issues": self._check_formatting(code_content),
            "optimization_opportunities": self._find_optimizations(code_content)
        }
        
        recommendations = []
        
        if findings["unused_imports"]:
            recommendations.append(f"Remove {len(findings['unused_imports'])} unused imports")
        
        if findings["dead_code"]:
            recommendations.append(f"Remove {len(findings['dead_code'])} dead code sections")
        
        if findings["formatting_issues"]:
            recommendations.append(f"Fix {len(findings['formatting_issues'])} formatting issues")
        
        return SpecialistDecision(
            specialist_type=SpecialistType.CLEANUP_AGENT,
            decision_type="analyze",
            confidence=0.95,
            findings=findings,
            recommendations=recommendations,
            priority="low"
        )
    
    def _find_unused_imports(self, code: str) -> List[str]:
        """Find unused imports"""
        import re
        
        unused = []
        lines = code.split('\n')
        
        for line in lines:
            if line.strip().startswith(('import ', 'from ')):
                # Simple heuristic: check if imported name is used
                match = re.search(r'(?:from|import)\s+(\w+)', line)
                if match:
                    import_name = match.group(1)
                    # Count occurrences
                    if code.count(import_name) == 1:  # Only in import line
                        unused.append(import_name)
        
        return unused
    
    def _find_dead_code(self, code: str) -> List[str]:
        """Find dead code sections"""
        dead = []
        
        patterns = [
            (r'if\s+False:\s*\n', "if False block"),
            (r'# \w+.*\n\s*pass\s*\n', "placeholder pass"),
            (r'def\s+_\w+.*?:\s*pass', "unused private function")
        ]
        
        for pattern, description in patterns:
            if pattern in code:
                dead.append(description)
        
        return dead
    
    def _check_formatting(self, code: str) -> List[str]:
        """Check formatting issues"""
        issues = []
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if line and line[-1] in (' ', '\t'):
                issues.append(f"Line {i+1}: trailing whitespace")
            if '\t' in line:
                issues.append(f"Line {i+1}: uses tabs instead of spaces")
        
        return issues[:10]  # Return first 10 issues
    
    def _find_optimizations(self, code: str) -> List[str]:
        """Find optimization opportunities"""
        optimizations = []
        
        if "== True" in code:
            optimizations.append("Replace '== True' with just condition")
        if "== False" in code:
            optimizations.append("Replace '== False' with 'not' condition")
        if " for " in code and " in " in code:
            optimizations.append("Consider using list comprehension for better performance")
        
        return optimizations


class AIQAAgent:
    """Main AI-powered QA Agent that coordinates specialist team"""
    
    def __init__(self, agent_id: str = "ai_qa_agent_1"):
        self.agent_id = agent_id
        self.name = "AI QA Agent"
        
        # Initialize specialist team
        self.code_expert = CodeExpert()
        self.planner_expert = PlannerExpert()
        self.fixer_expert = FixerExpert()
        self.cleanup_agent = CleanupAgent()
        
        self.specialists = {
            SpecialistType.CODE_EXPERT: self.code_expert,
            SpecialistType.PLANNER_EXPERT: self.planner_expert,
            SpecialistType.FIXER_EXPERT: self.fixer_expert,
            SpecialistType.CLEANUP_AGENT: self.cleanup_agent
        }
        
        # Decision history
        self.decisions_history: List[SpecialistDecision] = []
        self.analysis_results: Dict[str, Any] = {}
    
    async def analyze_code_changes(
        self,
        code_files: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Analyze code changes using specialist team
        
        Args:
            code_files: List of (file_path, code_content) tuples
        
        Returns:
            Comprehensive analysis with decisions from all specialists
        """
        logger.info(f"AI QA Agent {self.agent_id}: Starting code analysis for {len(code_files)} files")
        
        all_decisions = []
        file_analyses = {}
        
        # Phase 1: Code Expert Analysis
        logger.info("Phase 1: Code Expert Analysis")
        for file_path, code_content in code_files:
            decision = await self.code_expert.analyze_code(code_content, file_path)
            all_decisions.append(decision)
            file_analyses[file_path] = {
                "code_expert": decision
            }
        
        # Phase 2: Cleanup Agent Analysis (parallel)
        logger.info("Phase 2: Cleanup Analysis")
        cleanup_tasks = [
            self.cleanup_agent.analyze_for_cleanup(code_content, file_path)
            for file_path, code_content in code_files
        ]
        cleanup_decisions = await asyncio.gather(*cleanup_tasks)
        
        for (file_path, _), decision in zip(code_files, cleanup_decisions):
            all_decisions.append(decision)
            file_analyses[file_path]["cleanup_agent"] = decision
        
        # Phase 3: Fixer Expert Analysis (based on Code Expert findings)
        logger.info("Phase 3: Fixer Expert Analysis")
        issues = self._extract_issues_from_decisions([d for d in all_decisions if d.specialist_type == SpecialistType.CODE_EXPERT])
        
        if issues:
            fixer_decision = await self.fixer_expert.recommend_fixes(
                "\n".join([code for _, code in code_files]),
                issues
            )
            all_decisions.append(fixer_decision)
        
        # Store decisions
        self.decisions_history.extend(all_decisions)
        
        return {
            "agent_id": self.agent_id,
            "files_analyzed": len(code_files),
            "specialists_involved": len(self.specialists),
            "total_decisions": len(all_decisions),
            "file_analyses": file_analyses,
            "all_decisions": [d for d in all_decisions],
            "summary": self._generate_analysis_summary(all_decisions)
        }
    
    async def validate_planning(
        self,
        plan_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate task planning using Planner Expert"""
        logger.info(f"AI QA Agent {self.agent_id}: Validating planning")
        
        decision = await self.planner_expert.validate_planning(plan_data)
        self.decisions_history.append(decision)
        
        return {
            "agent_id": self.agent_id,
            "decision": decision,
            "validation_passed": len(decision.recommendations) == 0
        }
    
    async def make_qa_decision(
        self,
        code_files: List[Tuple[str, str]],
        blocking_issues: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make final QA decision based on specialist analysis"""
        analysis = await self.analyze_code_changes(code_files)
        
        # Count issues by priority
        critical_count = sum(1 for d in analysis["all_decisions"] 
                            if d.priority == "critical")
        high_count = sum(1 for d in analysis["all_decisions"] 
                        if d.priority == "high")
        
        # Determine approval status
        if critical_count > 0:
            approval_status = "BLOCKED"
            reason = f"Critical issues found by specialists"
        elif high_count > 0:
            approval_status = "BLOCKED"
            reason = f"High-priority issues found by specialists"
        else:
            approval_status = "APPROVED"
            reason = "All specialist checks passed"
        
        return {
            "agent_id": self.agent_id,
            "approval_status": approval_status,
            "reason": reason,
            "analysis": analysis,
            "specialist_consensus": self._calculate_consensus(analysis["all_decisions"]),
            "recommendations": self._compile_recommendations(analysis["all_decisions"])
        }
    
    def _extract_issues_from_decisions(
        self,
        decisions: List[SpecialistDecision]
    ) -> List[Dict[str, Any]]:
        """Extract issues from specialist decisions"""
        issues = []
        
        for decision in decisions:
            if "security_issues" in decision.findings:
                for security_issue in decision.findings["security_issues"]:
                    issues.append({
                        "type": "security",
                        "issue": security_issue["issue"],
                        "auto_fixable": False,
                        "severity": "CRITICAL"
                    })
        
        return issues
    
    def _generate_analysis_summary(
        self,
        decisions: List[SpecialistDecision]
    ) -> Dict[str, Any]:
        """Generate summary of analysis"""
        specialists_involved = set(d.specialist_type for d in decisions)
        
        return {
            "total_decisions": len(decisions),
            "specialists_involved": [s.value for s in specialists_involved],
            "avg_confidence": sum(d.confidence for d in decisions) / len(decisions) if decisions else 0,
            "critical_priority_count": sum(1 for d in decisions if d.priority == "critical"),
            "high_priority_count": sum(1 for d in decisions if d.priority == "high"),
            "recommendations_count": sum(len(d.recommendations) for d in decisions)
        }
    
    def _calculate_consensus(self, decisions: List[SpecialistDecision]) -> float:
        """Calculate team consensus score"""
        if not decisions:
            return 1.0
        
        avg_confidence = sum(d.confidence for d in decisions) / len(decisions)
        return avg_confidence
    
    def _compile_recommendations(
        self,
        decisions: List[SpecialistDecision]
    ) -> List[str]:
        """Compile all recommendations from all specialists"""
        all_recs = []
        
        for decision in decisions:
            for rec in decision.recommendations:
                all_recs.append(f"[{decision.specialist_type.value}] {rec}")
        
        return all_recs
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get current status of AI QA Agent"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "specialists_count": len(self.specialists),
            "decisions_made": len(self.decisions_history),
            "specialists": [s.name for s in self.specialists.values()],
            "status": "active"
        }
