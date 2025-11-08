"""
Planning Validator

Validates workflow and task decomposition from planning agents.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from app.logger import logger


class ValidationResult(str, Enum):
    """Validation result status"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass
class PlanningIssue:
    """Planning validation issue"""
    type: str
    severity: str
    message: str
    suggestion: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion
        }


class PlanningValidator:
    """Validates planning quality"""
    
    def __init__(self):
        self.min_task_duration = 0.25  # 15 minutes in hours
        self.max_task_duration = 4.0  # 4 hours
        self.max_dependencies = 5
    
    async def validate(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a plan"""
        issues = []
        
        tasks = plan_data.get("tasks", [])
        
        if not tasks:
            return {
                "status": ValidationResult.FAIL.value,
                "issues": [{"type": "empty_plan", "severity": "CRITICAL", "message": "No tasks in plan", "suggestion": "Add tasks"}],
                "report": "FAIL: No tasks in plan"
            }
        
        # Validate each task
        for task in tasks:
            issues.extend(self._validate_task(task))
        
        # Validate dependencies
        issues.extend(self._validate_dependencies(tasks))
        
        # Validate resource allocation
        issues.extend(self._validate_resources(tasks))
        
        # Validate acceptance criteria
        issues.extend(self._validate_acceptance_criteria(tasks))
        
        # Determine overall status
        critical_issues = [i for i in issues if i.severity == "CRITICAL"]
        high_issues = [i for i in issues if i.severity == "HIGH"]
        
        if critical_issues:
            status = ValidationResult.FAIL
        elif high_issues:
            status = ValidationResult.WARNING
        else:
            status = ValidationResult.PASS
        
        # Generate report
        report = self._generate_planning_report(status, issues, tasks)
        
        return {
            "status": status.value,
            "issues": [i.to_dict() for i in issues],
            "report": report
        }
    
    def _validate_task(self, task: Dict[str, Any]) -> List[PlanningIssue]:
        """Validate individual task"""
        issues = []
        
        task_id = task.get("id", "unknown")
        
        # Check task granularity
        estimated_hours = task.get("estimated_hours", 0)
        if estimated_hours < self.min_task_duration:
            issues.append(PlanningIssue(
                type="task_too_small",
                severity="MEDIUM",
                message=f"Task {task_id} is too small ({estimated_hours}h < {self.min_task_duration}h)",
                suggestion="Combine with related tasks"
            ))
        elif estimated_hours > self.max_task_duration:
            issues.append(PlanningIssue(
                type="task_too_large",
                severity="HIGH",
                message=f"Task {task_id} is too large ({estimated_hours}h > {self.max_task_duration}h)",
                suggestion="Break down into smaller subtasks"
            ))
        
        # Check description
        description = task.get("description", "")
        if not description or len(description) < 20:
            issues.append(PlanningIssue(
                type="insufficient_description",
                severity="HIGH",
                message=f"Task {task_id} has insufficient description",
                suggestion="Add detailed description of what needs to be done"
            ))
        
        # Check acceptance criteria
        acceptance_criteria = task.get("acceptance_criteria", [])
        if not acceptance_criteria:
            issues.append(PlanningIssue(
                type="missing_acceptance_criteria",
                severity="HIGH",
                message=f"Task {task_id} missing acceptance criteria",
                suggestion="Define SMART acceptance criteria"
            ))
        
        # Check test strategy
        test_strategy = task.get("test_strategy", "")
        if not test_strategy:
            issues.append(PlanningIssue(
                type="missing_test_strategy",
                severity="MEDIUM",
                message=f"Task {task_id} missing test strategy",
                suggestion="Define how success will be verified"
            ))
        
        # Check risk assessment
        risk_level = task.get("risk_level", "")
        if risk_level == "high" and not task.get("mitigation_plan"):
            issues.append(PlanningIssue(
                type="missing_mitigation_plan",
                severity="HIGH",
                message=f"High-risk task {task_id} missing mitigation plan",
                suggestion="Add risk mitigation strategy"
            ))
        
        return issues
    
    def _validate_dependencies(self, tasks: List[Dict[str, Any]]) -> List[PlanningIssue]:
        """Validate task dependencies"""
        issues = []
        
        # Build dependency graph
        task_ids = {task.get("id") for task in tasks}
        dependencies = {}
        
        for task in tasks:
            task_id = task.get("id")
            task_deps = set(task.get("dependencies", []))
            dependencies[task_id] = task_deps
            
            # Check for invalid dependencies
            invalid_deps = task_deps - task_ids
            if invalid_deps:
                issues.append(PlanningIssue(
                    type="invalid_dependency",
                    severity="CRITICAL",
                    message=f"Task {task_id} has invalid dependencies: {invalid_deps}",
                    suggestion="Remove or fix invalid dependencies"
                ))
            
            # Check for too many dependencies
            if len(task_deps) > self.max_dependencies:
                issues.append(PlanningIssue(
                    type="too_many_dependencies",
                    severity="MEDIUM",
                    message=f"Task {task_id} has too many dependencies ({len(task_deps)})",
                    suggestion="Consider breaking task into smaller parts"
                ))
        
        # Check for circular dependencies
        circular = self._detect_circular_dependencies(dependencies)
        if circular:
            issues.append(PlanningIssue(
                type="circular_dependency",
                severity="CRITICAL",
                message=f"Circular dependency detected: {' -> '.join(circular)}",
                suggestion="Remove circular dependency"
            ))
        
        return issues
    
    def _validate_resources(self, tasks: List[Dict[str, Any]]) -> List[PlanningIssue]:
        """Validate resource allocation"""
        issues = []
        
        # Check for single-person bottlenecks
        assignee_workload = {}
        
        for task in tasks:
            assignee = task.get("assignee", "unassigned")
            estimated_hours = task.get("estimated_hours", 0)
            assignee_workload[assignee] = assignee_workload.get(assignee, 0) + estimated_hours
        
        # Check if any single assignee has > 80% of work
        total_work = sum(assignee_workload.values())
        if total_work > 0:
            for assignee, workload in assignee_workload.items():
                if workload / total_work > 0.8:
                    issues.append(PlanningIssue(
                        type="single_person_bottleneck",
                        severity="HIGH",
                        message=f"Assignee {assignee} has {workload/total_work*100:.0f}% of total work",
                        suggestion="Distribute work more evenly"
                    ))
        
        # Check for unassigned tasks
        unassigned = [task.get("id") for task in tasks if not task.get("assignee")]
        if unassigned:
            issues.append(PlanningIssue(
                type="unassigned_tasks",
                severity="MEDIUM",
                message=f"{len(unassigned)} tasks unassigned",
                suggestion="Assign all tasks to team members"
            ))
        
        return issues
    
    def _validate_acceptance_criteria(self, tasks: List[Dict[str, Any]]) -> List[PlanningIssue]:
        """Validate acceptance criteria quality (SMART)"""
        issues = []
        
        for task in tasks:
            task_id = task.get("id")
            criteria = task.get("acceptance_criteria", [])
            
            for criterion in criteria:
                # Check if criterion is specific enough
                if len(criterion) < 10:
                    issues.append(PlanningIssue(
                        type="vague_acceptance_criteria",
                        severity="MEDIUM",
                        message=f"Task {task_id} has vague acceptance criteria: '{criterion}'",
                        suggestion="Make criteria more specific and measurable"
                    ))
                
                # Check for measurability keywords
                measurable_keywords = ["test", "verify", "measure", "coverage", "performance", "pass", "fail"]
                if not any(keyword in criterion.lower() for keyword in measurable_keywords):
                    issues.append(PlanningIssue(
                        type="non_measurable_criteria",
                        severity="LOW",
                        message=f"Task {task_id} criteria may not be measurable: '{criterion}'",
                        suggestion="Add measurable success indicators"
                    ))
        
        return issues
    
    def _detect_circular_dependencies(self, dependencies: Dict[str, set]) -> Optional[List[str]]:
        """Detect circular dependencies using DFS"""
        def dfs(node: str, visited: set, path: List[str]) -> Optional[List[str]]:
            if node in path:
                # Found cycle
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            
            if node in visited:
                return None
            
            visited.add(node)
            path.append(node)
            
            for dep in dependencies.get(node, set()):
                result = dfs(dep, visited, path.copy())
                if result:
                    return result
            
            return None
        
        visited = set()
        for node in dependencies:
            if node not in visited:
                result = dfs(node, visited, [])
                if result:
                    return result
        
        return None
    
    def _generate_planning_report(
        self,
        status: ValidationResult,
        issues: List[PlanningIssue],
        tasks: List[Dict[str, Any]]
    ) -> str:
        """Generate planning validation report"""
        report = ["=" * 80]
        report.append("PLANNING VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"Status: {status.value.upper()}")
        report.append(f"Total Tasks: {len(tasks)}")
        report.append(f"Issues Found: {len(issues)}")
        report.append("")
        
        # Group issues by severity
        critical = [i for i in issues if i.severity == "CRITICAL"]
        high = [i for i in issues if i.severity == "HIGH"]
        medium = [i for i in issues if i.severity == "MEDIUM"]
        low = [i for i in issues if i.severity == "LOW"]
        
        if critical:
            report.append("CRITICAL ISSUES:")
            for issue in critical:
                report.append(f"  ❌ {issue.message}")
                report.append(f"     💡 {issue.suggestion}")
            report.append("")
        
        if high:
            report.append("HIGH PRIORITY ISSUES:")
            for issue in high:
                report.append(f"  ⚠️  {issue.message}")
                report.append(f"     💡 {issue.suggestion}")
            report.append("")
        
        if medium:
            report.append(f"MEDIUM PRIORITY ISSUES: ({len(medium)})")
            for issue in medium[:3]:
                report.append(f"  ⚡ {issue.message}")
            if len(medium) > 3:
                report.append(f"  ... and {len(medium) - 3} more")
            report.append("")
        
        if low:
            report.append(f"LOW PRIORITY ISSUES: ({len(low)})")
        
        report.append("=" * 80)
        
        if status == ValidationResult.PASS:
            report.append("✅ Planning validation PASSED")
        elif status == ValidationResult.WARNING:
            report.append("⚠️  Planning validation PASSED WITH WARNINGS")
        else:
            report.append("❌ Planning validation FAILED - Fix critical issues before proceeding")
        
        return "\n".join(report)
