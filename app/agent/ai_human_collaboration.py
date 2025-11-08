"""AI-Human collaboration optimization system."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TaskPhase(str, Enum):
    """Phases of task execution."""
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REVIEW = "review"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"


class CollaborationRole(str, Enum):
    """Role in collaboration."""
    LEAD = "lead"
    SUPPORT = "support"
    REVIEWER = "reviewer"
    TESTER = "tester"


class CollaborationPattern(str, Enum):
    """Patterns of AI-Human collaboration."""
    HUMAN_LEAD_AI_SUPPORT = "human_lead_ai_support"
    AI_LEAD_HUMAN_REVIEW = "ai_lead_human_review"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    ITERATIVE = "iterative"


class CollaborationSession(BaseModel):
    """Represents an AI-Human collaboration session."""
    id: str = Field(..., description="Session ID")
    task_id: str = Field(..., description="Associated task ID")
    human_member: str = Field(..., description="Human participant")
    ai_agent: str = Field(..., description="AI agent participant")
    pattern: CollaborationPattern = Field(..., description="Collaboration pattern")
    phase: TaskPhase = Field(default=TaskPhase.DESIGN, description="Current phase")
    start_date: datetime = Field(default_factory=datetime.now, description="Session start")
    end_date: Optional[datetime] = Field(None, description="Session end")
    human_role: CollaborationRole = Field(..., description="Human's role in this phase")
    ai_role: CollaborationRole = Field(..., description="AI agent's role in this phase")
    outcomes: List[str] = Field(default_factory=list, description="Session outcomes")
    effectiveness_score: float = Field(default=0.0, ge=0, le=10, description="Effectiveness rating (0-10)")
    lessons_learned: List[str] = Field(default_factory=list, description="Lessons from this session")
    completed: bool = Field(default=False, description="Whether session is completed")


class CollaborationGuideline(BaseModel):
    """Guideline for AI-Human collaboration in a specific phase."""
    phase: TaskPhase = Field(..., description="Task phase")
    human_strengths: List[str] = Field(..., description="What humans do best in this phase")
    ai_strengths: List[str] = Field(..., description="What AI agents do best in this phase")
    recommended_pattern: CollaborationPattern = Field(..., description="Recommended collaboration pattern")
    human_responsibilities: List[str] = Field(..., description="What human should do")
    ai_responsibilities: List[str] = Field(..., description="What AI agent should do")
    coordination_points: List[str] = Field(..., description="Key coordination points")
    failure_modes: List[str] = Field(..., description="Common failure modes to avoid")


class AIHumanCollaborationOptimizer:
    """Optimizes AI-Human collaboration patterns."""

    def __init__(self):
        """Initialize the collaboration optimizer."""
        self.sessions: Dict[str, CollaborationSession] = {}
        self.guidelines = self._initialize_guidelines()

    def _initialize_guidelines(self) -> Dict[TaskPhase, CollaborationGuideline]:
        """Initialize best practices for each phase."""
        return {
            TaskPhase.DESIGN: CollaborationGuideline(
                phase=TaskPhase.DESIGN,
                human_strengths=[
                    "Creative direction and vision",
                    "Understanding user needs",
                    "Tradeoff decisions",
                    "Domain expertise and constraints",
                    "Stakeholder communication"
                ],
                ai_strengths=[
                    "Generating multiple options quickly",
                    "Identifying patterns from similar solutions",
                    "Documenting design decisions",
                    "Rapid prototyping ideas",
                    "Technical feasibility assessment"
                ],
                recommended_pattern=CollaborationPattern.HUMAN_LEAD_AI_SUPPORT,
                human_responsibilities=[
                    "Define requirements and constraints",
                    "Make key architectural decisions",
                    "Evaluate and select final design",
                    "Document design rationale",
                    "Communicate with stakeholders"
                ],
                ai_responsibilities=[
                    "Generate multiple design options",
                    "Research similar solutions",
                    "Create design documentation",
                    "Identify risks and tradeoffs",
                    "Suggest optimizations"
                ],
                coordination_points=[
                    "Initial requirements review",
                    "After design options generated",
                    "Before final selection",
                    "Design documentation complete"
                ],
                failure_modes=[
                    "AI generates options without understanding requirements",
                    "Human ignores AI suggestions without explanation",
                    "No clear decision criteria defined",
                    "Design doc created but not validated"
                ]
            ),

            TaskPhase.IMPLEMENTATION: CollaborationGuideline(
                phase=TaskPhase.IMPLEMENTATION,
                human_strengths=[
                    "Complex problem solving",
                    "Understanding context and nuance",
                    "Making judgment calls",
                    "Handling edge cases and exceptions",
                    "Code quality and maintainability"
                ],
                ai_strengths=[
                    "Rapid code generation and scaffolding",
                    "Generating tests",
                    "Refactoring and optimization",
                    "Following patterns consistently",
                    "Documentation generation"
                ],
                recommended_pattern=CollaborationPattern.AI_LEAD_HUMAN_REVIEW,
                human_responsibilities=[
                    "Review AI-generated code",
                    "Catch bugs and logical errors",
                    "Ensure architectural consistency",
                    "Handle complex algorithms",
                    "Make implementation decisions"
                ],
                ai_responsibilities=[
                    "Generate initial code from spec",
                    "Generate unit tests",
                    "Refactor for readability",
                    "Add comments and docstrings",
                    "Flag complex areas for review"
                ],
                coordination_points=[
                    "After initial code generation",
                    "After test generation",
                    "After refactoring",
                    "Before code review approval"
                ],
                failure_modes=[
                    "AI generates untestable code",
                    "Human doesn't understand AI-generated code",
                    "Tests don't cover actual code paths",
                    "Refactoring breaks functionality"
                ]
            ),

            TaskPhase.TESTING: CollaborationGuideline(
                phase=TaskPhase.TESTING,
                human_strengths=[
                    "Exploratory testing and edge cases",
                    "User scenario understanding",
                    "Performance investigation",
                    "Usability assessment",
                    "Integration testing"
                ],
                ai_strengths=[
                    "Generating comprehensive test cases",
                    "Regression testing",
                    "Automated test execution",
                    "Identifying untested code paths",
                    "Performance profiling"
                ],
                recommended_pattern=CollaborationPattern.PARALLEL,
                human_responsibilities=[
                    "Do exploratory testing",
                    "Test user scenarios",
                    "Verify performance",
                    "Test integration points",
                    "Prioritize and verify bugs"
                ],
                ai_responsibilities=[
                    "Generate automated test cases",
                    "Run regression tests",
                    "Measure code coverage",
                    "Profile performance",
                    "Generate test reports"
                ],
                coordination_points=[
                    "Test plan review",
                    "After automated tests generated",
                    "Bug triage meetings",
                    "Final test summary"
                ],
                failure_modes=[
                    "AI tests don't cover user scenarios",
                    "Human tests are unstructured",
                    "Bugs found in production",
                    "Low test coverage undetected"
                ]
            ),

            TaskPhase.REVIEW: CollaborationGuideline(
                phase=TaskPhase.REVIEW,
                human_strengths=[
                    "Architecture and design review",
                    "Security assessment",
                    "Code clarity and maintainability",
                    "API design",
                    "Performance considerations"
                ],
                ai_strengths=[
                    "Static analysis",
                    "Pattern detection",
                    "Test coverage analysis",
                    "Documentation verification",
                    "Consistency checking"
                ],
                recommended_pattern=CollaborationPattern.SEQUENTIAL,
                human_responsibilities=[
                    "Do manual code review",
                    "Check architecture decisions",
                    "Review security implications",
                    "Ensure maintainability",
                    "Approve for merge"
                ],
                ai_responsibilities=[
                    "Automated linting and analysis",
                    "Find duplicated code",
                    "Check for common mistakes",
                    "Verify test coverage",
                    "Generate review summary"
                ],
                coordination_points=[
                    "After automated checks",
                    "During manual review",
                    "Before approval"
                ],
                failure_modes=[
                    "Automated checks miss issues",
                    "Manual review is superficial",
                    "No clear review criteria",
                    "Review bottleneck"
                ]
            ),

            TaskPhase.DEPLOYMENT: CollaborationGuideline(
                phase=TaskPhase.DEPLOYMENT,
                human_strengths=[
                    "Risk assessment and mitigation",
                    "Go/no-go decisions",
                    "Stakeholder communication",
                    "Rollback decisions",
                    "On-call support"
                ],
                ai_strengths=[
                    "Infrastructure provisioning",
                    "Deployment automation",
                    "Configuration generation",
                    "Rollback execution",
                    "Deployment verification"
                ],
                recommended_pattern=CollaborationPattern.HUMAN_LEAD_AI_SUPPORT,
                human_responsibilities=[
                    "Make go/no-go decision",
                    "Monitor deployment",
                    "Communicate status",
                    "Decide on rollback",
                    "Post-deployment review"
                ],
                ai_responsibilities=[
                    "Automate deployment process",
                    "Run deployment tests",
                    "Monitor system health",
                    "Execute rollback if needed",
                    "Generate deployment report"
                ],
                coordination_points=[
                    "Pre-deployment checklist",
                    "Deployment start",
                    "During monitoring",
                    "Post-deployment review"
                ],
                failure_modes=[
                    "Automated deployment fails without fallback",
                    "No human monitoring during deploy",
                    "Rollback not prepared",
                    "Unclear deployment success criteria"
                ]
            ),

            TaskPhase.MONITORING: CollaborationGuideline(
                phase=TaskPhase.MONITORING,
                human_strengths=[
                    "Interpreting anomalies",
                    "Root cause analysis",
                    "User impact assessment",
                    "Incident response",
                    "Learning and improvement"
                ],
                ai_strengths=[
                    "Metrics collection and analysis",
                    "Anomaly detection",
                    "Trend analysis",
                    "Alert generation",
                    "Performance optimization suggestions"
                ],
                recommended_pattern=CollaborationPattern.PARALLEL,
                human_responsibilities=[
                    "Monitor dashboards",
                    "Respond to incidents",
                    "Investigate root causes",
                    "Make optimization decisions",
                    "Update runbooks"
                ],
                ai_responsibilities=[
                    "Collect and aggregate metrics",
                    "Detect anomalies",
                    "Generate alerts",
                    "Suggest optimizations",
                    "Maintain performance baselines"
                ],
                coordination_points=[
                    "Daily metric review",
                    "Alert triage",
                    "Incident response",
                    "Weekly performance review"
                ],
                failure_modes=[
                    "Too many false positive alerts",
                    "Humans ignore AI alerts",
                    "No clear incident response",
                    "Monitoring data not acted upon"
                ]
            )
        }

    def get_guideline_for_phase(self, phase: TaskPhase) -> Optional[CollaborationGuideline]:
        """Get collaboration guideline for a phase.
        
        Args:
            phase: Task phase
            
        Returns:
            Collaboration guideline or None
        """
        return self.guidelines.get(phase)

    def create_collaboration_session(
        self,
        task_id: str,
        human_member: str,
        ai_agent: str,
        phase: TaskPhase,
        pattern: CollaborationPattern = None
    ) -> CollaborationSession:
        """Create a new collaboration session.
        
        Args:
            task_id: Task ID
            human_member: Human team member
            ai_agent: AI agent name
            phase: Current phase
            pattern: Collaboration pattern (auto-selected if not provided)
            
        Returns:
            Created collaboration session
        """
        if pattern is None:
            guideline = self.get_guideline_for_phase(phase)
            pattern = guideline.recommended_pattern if guideline else CollaborationPattern.SEQUENTIAL

        # Determine roles based on phase and pattern
        if pattern == CollaborationPattern.HUMAN_LEAD_AI_SUPPORT:
            human_role = CollaborationRole.LEAD
            ai_role = CollaborationRole.SUPPORT
        elif pattern == CollaborationPattern.AI_LEAD_HUMAN_REVIEW:
            human_role = CollaborationRole.REVIEWER
            ai_role = CollaborationRole.LEAD
        elif pattern == CollaborationPattern.PARALLEL:
            human_role = CollaborationRole.LEAD
            ai_role = CollaborationRole.SUPPORT
        else:
            human_role = CollaborationRole.LEAD
            ai_role = CollaborationRole.SUPPORT

        session_id = f"collab-{task_id}-{phase.value}"

        session = CollaborationSession(
            id=session_id,
            task_id=task_id,
            human_member=human_member,
            ai_agent=ai_agent,
            pattern=pattern,
            phase=phase,
            human_role=human_role,
            ai_role=ai_role
        )

        self.sessions[session_id] = session
        return session

    def advance_phase(self, session_id: str, next_phase: TaskPhase) -> CollaborationSession:
        """Advance collaboration to next phase.
        
        Args:
            session_id: Session ID
            next_phase: Next phase
            
        Returns:
            Updated session
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        old_session = self.sessions[session_id]

        # Create new session for next phase
        new_session = self.create_collaboration_session(
            task_id=old_session.task_id,
            human_member=old_session.human_member,
            ai_agent=old_session.ai_agent,
            phase=next_phase
        )

        # Copy relevant information
        new_session.outcomes = old_session.outcomes

        # Mark old session as completed
        old_session.completed = True

        return new_session

    def record_session_outcome(self, session_id: str, outcome: str) -> None:
        """Record an outcome from a collaboration session.
        
        Args:
            session_id: Session ID
            outcome: Outcome description
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        self.sessions[session_id].outcomes.append(outcome)

    def rate_collaboration_effectiveness(self, session_id: str, score: float, lessons: List[str]) -> None:
        """Rate collaboration effectiveness.
        
        Args:
            session_id: Session ID
            score: Effectiveness score (0-10)
            lessons: Lessons learned
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.sessions[session_id]
        session.effectiveness_score = score
        session.lessons_learned = lessons
        session.completed = True
        session.end_date = datetime.now()

    def get_collaboration_recommendations(self, task_complexity: int, human_skills: List[str], ai_capabilities: List[str]) -> Dict:
        """Get collaboration recommendations based on task and team characteristics.
        
        Args:
            task_complexity: Complexity level (1-5)
            human_skills: List of human team member skills
            ai_capabilities: List of AI agent capabilities
            
        Returns:
            Recommendations dictionary with patterns and phases
        """
        recommendations = {
            "recommended_pattern": CollaborationPattern.SEQUENTIAL,
            "phase_assignments": {},
            "critical_coordination_points": [],
            "risk_mitigation": [],
            "success_factors": []
        }

        # Recommend pattern based on complexity
        if task_complexity >= 4:
            # Complex tasks benefit from human leadership
            recommendations["recommended_pattern"] = CollaborationPattern.HUMAN_LEAD_AI_SUPPORT
            recommendations["success_factors"].append("Clear human direction at every phase")
        elif task_complexity >= 3:
            # Medium complexity can use AI-led with review
            recommendations["recommended_pattern"] = CollaborationPattern.AI_LEAD_HUMAN_REVIEW
            recommendations["success_factors"].append("Thorough human review of AI work")
        else:
            # Simple tasks can be parallel
            recommendations["recommended_pattern"] = CollaborationPattern.PARALLEL
            recommendations["success_factors"].append("Good async coordination")

        # Assign roles to each phase
        for phase, guideline in self.guidelines.items():
            if recommendations["recommended_pattern"] == CollaborationPattern.HUMAN_LEAD_AI_SUPPORT:
                recommendations["phase_assignments"][phase.value] = {
                    "human_role": CollaborationRole.LEAD.value,
                    "ai_role": CollaborationRole.SUPPORT.value
                }
            elif recommendations["recommended_pattern"] == CollaborationPattern.AI_LEAD_HUMAN_REVIEW:
                recommendations["phase_assignments"][phase.value] = {
                    "human_role": CollaborationRole.REVIEWER.value,
                    "ai_role": CollaborationRole.LEAD.value
                }
            else:
                recommendations["phase_assignments"][phase.value] = {
                    "human_role": CollaborationRole.LEAD.value,
                    "ai_role": CollaborationRole.SUPPORT.value
                }

        # Add critical coordination points
        recommendations["critical_coordination_points"] = [
            "Task start - align on requirements",
            "Phase transitions - verify readiness",
            "Before decision points - confirm criteria",
            "Before deployment - go/no-go"
        ]

        # Add risk mitigations
        if "code_generation" in ai_capabilities:
            recommendations["risk_mitigation"].append("Require human review of all AI-generated code")
        if task_complexity >= 4:
            recommendations["risk_mitigation"].append("Have human document all key decisions")

        return recommendations

    def get_effectiveness_analysis(self) -> Dict:
        """Analyze effectiveness of AI-Human collaborations.
        
        Returns:
            Analysis dictionary with metrics and insights
        """
        if not self.sessions:
            return {"total_sessions": 0, "analysis": "No sessions to analyze"}

        completed = [s for s in self.sessions.values() if s.completed]
        if not completed:
            return {"total_sessions": len(self.sessions), "analysis": "No completed sessions to analyze"}

        total_sessions = len(completed)
        avg_effectiveness = sum(s.effectiveness_score for s in completed) / total_sessions

        # Analyze by pattern
        by_pattern = {}
        for session in completed:
            pattern = session.pattern.value
            if pattern not in by_pattern:
                by_pattern[pattern] = {"count": 0, "avg_score": 0}
            by_pattern[pattern]["count"] += 1
            by_pattern[pattern]["avg_score"] = (
                (by_pattern[pattern]["avg_score"] * (by_pattern[pattern]["count"] - 1) + session.effectiveness_score) /
                by_pattern[pattern]["count"]
            )

        # Find best pattern
        best_pattern = max(by_pattern.items(), key=lambda x: x[1]["avg_score"])

        return {
            "total_sessions": total_sessions,
            "average_effectiveness": round(avg_effectiveness, 2),
            "by_pattern": by_pattern,
            "best_pattern": best_pattern[0],
            "recommendation": f"Use {best_pattern[0]} pattern for better results"
        }
