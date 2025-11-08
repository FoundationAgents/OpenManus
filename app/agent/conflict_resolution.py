"""Conflict resolution and team disagreement mediation system."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ConflictType(str, Enum):
    """Type of conflict."""
    TECHNICAL_DISAGREEMENT = "technical_disagreement"
    RESOURCE_CONTENTION = "resource_contention"
    WORKLOAD_DISPUTE = "workload_dispute"
    COMMUNICATION_BREAKDOWN = "communication_breakdown"
    PERSONALITY_CLASH = "personality_clash"
    PROCESS_DISAGREEMENT = "process_disagreement"
    PRIORITY_MISMATCH = "priority_mismatch"
    OTHER = "other"


class ConflictSeverity(str, Enum):
    """Severity of the conflict."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConflictStatus(str, Enum):
    """Status of conflict resolution."""
    OPEN = "open"
    IN_RESOLUTION = "in_resolution"
    PROPOSED = "proposed"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class ConflictPerspective(BaseModel):
    """One person's perspective on a conflict."""
    person: str = Field(..., description="Person providing perspective")
    perspective: str = Field(..., description="Their view of the situation")
    underlying_concerns: List[str] = Field(default_factory=list, description="Root concerns")
    proposed_solutions: List[str] = Field(default_factory=list, description="Their proposed solutions")
    willingness_to_compromise: int = Field(default=5, ge=1, le=10, description="Willingness to compromise (1-10)")


class ConflictAnalysis(BaseModel):
    """Analysis of a conflict."""
    surface_issue: str = Field(..., description="The surface issue being debated")
    root_cause: str = Field(..., description="The actual underlying cause")
    common_ground: List[str] = Field(default_factory=list, description="Areas of agreement")
    key_differences: List[str] = Field(default_factory=list, description="Key differences in perspective")
    misconceptions: List[str] = Field(default_factory=list, description="Identified misconceptions")


class ConflictResolution(BaseModel):
    """Proposed resolution for a conflict."""
    id: str = Field(..., description="Resolution ID")
    conflict_id: str = Field(..., description="Associated conflict ID")
    proposed_solution: str = Field(..., description="Proposed solution")
    rationale: str = Field(..., description="Why this is a good solution")
    benefits: List[str] = Field(default_factory=list, description="Benefits of this solution")
    trade_offs: List[str] = Field(default_factory=list, description="Trade-offs or compromises")
    implementation_steps: List[str] = Field(default_factory=list, description="Steps to implement")
    success_criteria: List[str] = Field(default_factory=list, description="How to measure success")
    timeline: Optional[str] = Field(None, description="Timeline for implementation")


class Conflict(BaseModel):
    """Represents a team conflict."""
    id: str = Field(..., description="Conflict ID")
    title: str = Field(..., description="Conflict title/summary")
    description: str = Field(..., description="Detailed description")
    type: ConflictType = Field(..., description="Type of conflict")
    severity: ConflictSeverity = Field(default=ConflictSeverity.MEDIUM, description="Severity level")
    status: ConflictStatus = Field(default=ConflictStatus.OPEN, description="Resolution status")
    parties_involved: List[str] = Field(..., description="Names of parties involved")
    perspectives: List[ConflictPerspective] = Field(default_factory=list, description="Each party's perspective")
    analysis: Optional[ConflictAnalysis] = Field(None, description="Agent's analysis")
    proposed_resolution: Optional[ConflictResolution] = Field(None, description="Proposed resolution")
    created_date: datetime = Field(default_factory=datetime.now, description="When conflict was reported")
    resolved_date: Optional[datetime] = Field(None, description="When conflict was resolved")
    impact_on_team: str = Field(default="", description="Describes impact on team productivity")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class ConflictResolver:
    """Handles team conflict resolution and mediation."""

    def __init__(self):
        """Initialize the conflict resolver."""
        self.conflicts: Dict[str, Conflict] = {}

    def report_conflict(self, conflict: Conflict) -> str:
        """Report a new conflict.
        
        Args:
            conflict: The conflict to report
            
        Returns:
            Conflict ID
        """
        if conflict.id in self.conflicts:
            raise ValueError(f"Conflict {conflict.id} already exists")

        self.conflicts[conflict.id] = conflict
        return conflict.id

    def add_perspective(self, conflict_id: str, perspective: ConflictPerspective) -> None:
        """Add a perspective to a conflict.
        
        Args:
            conflict_id: The conflict ID
            perspective: The perspective to add
        """
        if conflict_id not in self.conflicts:
            raise ValueError(f"Conflict {conflict_id} not found")

        conflict = self.conflicts[conflict_id]

        # Check if this person already provided a perspective
        for i, p in enumerate(conflict.perspectives):
            if p.person == perspective.person:
                conflict.perspectives[i] = perspective
                return

        conflict.perspectives.append(perspective)

    def analyze_conflict(self, conflict_id: str) -> ConflictAnalysis:
        """Analyze a conflict to identify root causes and common ground.
        
        Args:
            conflict_id: The conflict to analyze
            
        Returns:
            Analysis with surface/root issues and recommendations
        """
        if conflict_id not in self.conflicts:
            raise ValueError(f"Conflict {conflict_id} not found")

        conflict = self.conflicts[conflict_id]
        analysis = ConflictAnalysis(
            surface_issue=conflict.title,
            root_cause="",
            common_ground=[],
            key_differences=[],
            misconceptions=[]
        )

        if not conflict.perspectives:
            analysis.root_cause = "Insufficient information"
            return analysis

        # Extract perspectives
        concerns_by_person = {}
        for perspective in conflict.perspectives:
            concerns_by_person[perspective.person] = perspective.underlying_concerns

        # Identify common ground
        if len(concerns_by_person) > 1:
            # Find overlapping concerns
            all_concern_lists = list(concerns_by_person.values())
            common = set(all_concern_lists[0])
            for concern_list in all_concern_lists[1:]:
                common = common.intersection(set(concern_list))
            analysis.common_ground = list(common)

        # Identify key differences
        all_concerns = set()
        for concerns in concerns_by_person.values():
            all_concerns.update(concerns)
        analysis.key_differences = [c for c in all_concerns if c not in analysis.common_ground]

        # Determine root cause based on type
        if conflict.type == ConflictType.TECHNICAL_DISAGREEMENT:
            analysis.root_cause = "Different technical perspectives or incomplete information"
            analysis.misconceptions.append("May not fully understand the constraints/trade-offs")

        elif conflict.type == ConflictType.RESOURCE_CONTENTION:
            analysis.root_cause = "Limited resources causing competition"
            analysis.misconceptions.append("May underestimate resource scarcity")

        elif conflict.type == ConflictType.WORKLOAD_DISPUTE:
            analysis.root_cause = "Misalignment on task prioritization or capacity"
            analysis.misconceptions.append("May have different assumptions about available capacity")

        elif conflict.type == ConflictType.COMMUNICATION_BREAKDOWN:
            analysis.root_cause = "Miscommunication or lack of clear communication"
            analysis.misconceptions.append("May have misunderstood intentions or context")

        elif conflict.type == ConflictType.PRIORITY_MISMATCH:
            analysis.root_cause = "Different priorities or unclear alignment"
            analysis.misconceptions.append("May not understand downstream impact of priorities")

        return analysis

    def propose_resolution(self, conflict_id: str) -> Optional[ConflictResolution]:
        """Propose a resolution for a conflict.
        
        Args:
            conflict_id: The conflict to resolve
            
        Returns:
            Proposed resolution or None if cannot be proposed yet
        """
        if conflict_id not in self.conflicts:
            raise ValueError(f"Conflict {conflict_id} not found")

        conflict = self.conflicts[conflict_id]

        # Need both perspectives to propose resolution
        if len(conflict.perspectives) < 2:
            return None

        # Get or create analysis
        if not conflict.analysis:
            conflict.analysis = self.analyze_conflict(conflict_id)

        analysis = conflict.analysis

        # Generate resolution based on type
        resolution_id = f"{conflict_id}-resolution"
        solution = ""
        implementation = []
        success_criteria = []

        if conflict.type == ConflictType.TECHNICAL_DISAGREEMENT:
            solution = (
                "Schedule a technical design session with all parties. "
                "Document requirements and constraints. Evaluate both approaches against criteria."
            )
            implementation = [
                "1. Clarify requirements and constraints",
                "2. Document both proposed solutions",
                "3. Evaluate against criteria (performance, maintainability, etc.)",
                "4. Make decision based on data, not preference",
                "5. Document decision and rationale for future reference"
            ]
            success_criteria = [
                "Decision documented and understood by both parties",
                "Decision-maker satisfied with reasoning",
                "No passive resistance from either party"
            ]

        elif conflict.type == ConflictType.WORKLOAD_DISPUTE:
            solution = (
                "Review actual vs. perceived workload. Redistribute tasks or extend timelines "
                "based on data. Establish clear capacity planning process."
            )
            implementation = [
                "1. Gather objective data on workload (hours tracked, task complexity)",
                "2. Compare to original estimates",
                "3. Identify gaps and reasons",
                "4. Redistribute if needed or extend timelines",
                "5. Improve estimation process for future"
            ]
            success_criteria = [
                "Both parties agree workload is fair",
                "Clear capacity tracking in place",
                "Future conflicts reduced"
            ]

        elif conflict.type == ConflictType.COMMUNICATION_BREAKDOWN:
            solution = (
                "Establish clear communication channel, schedule regular check-ins, "
                "document decisions in writing to ensure shared understanding."
            )
            implementation = [
                "1. Identify preferred communication method",
                "2. Schedule regular (weekly) check-ins",
                "3. Document all decisions in shared space",
                "4. Use written communication for important topics",
                "5. Confirm understanding at end of discussions"
            ]
            success_criteria = [
                "Both parties feel heard",
                "Reduced miscommunication incidents",
                "Written record of key decisions"
            ]

        else:
            solution = (
                "Bring parties together to discuss underlying concerns and find common ground. "
                "Involve manager/mediator if personal conflict."
            )
            implementation = [
                "1. Meet separately to understand each perspective deeply",
                "2. Identify shared goals",
                "3. Facilitate joint discussion focused on solutions",
                "4. Document agreement",
                "5. Follow up in 1 week to ensure implementation"
            ]
            success_criteria = [
                "Both parties acknowledge legitimacy of other perspective",
                "Agreement on path forward",
                "Team cohesion restored"
            ]

        benefits = [
            "Conflict resolved quickly",
            "Team trust maintained",
            "Prevents future similar conflicts",
            "Better decision-making process"
        ]

        trade_offs = [
            "May require time investment for meeting/discussion",
            "One party may need to compromise",
            "Could reveal deeper organizational issues"
        ]

        resolution = ConflictResolution(
            id=resolution_id,
            conflict_id=conflict_id,
            proposed_solution=solution,
            rationale=f"Based on analysis: root cause is '{analysis.root_cause}'",
            benefits=benefits,
            trade_offs=trade_offs,
            implementation_steps=implementation,
            success_criteria=success_criteria,
            timeline="1-2 weeks"
        )

        conflict.proposed_resolution = resolution
        conflict.status = ConflictStatus.PROPOSED

        return resolution

    def resolve_conflict(self, conflict_id: str, resolution_notes: str) -> None:
        """Mark a conflict as resolved.
        
        Args:
            conflict_id: The conflict to mark resolved
            resolution_notes: Notes on how it was resolved
        """
        if conflict_id not in self.conflicts:
            raise ValueError(f"Conflict {conflict_id} not found")

        conflict = self.conflicts[conflict_id]
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolved_date = datetime.now()
        conflict.metadata["resolution_notes"] = resolution_notes

    def escalate_conflict(self, conflict_id: str, reason: str) -> None:
        """Escalate a conflict to management.
        
        Args:
            conflict_id: The conflict to escalate
            reason: Reason for escalation
        """
        if conflict_id not in self.conflicts:
            raise ValueError(f"Conflict {conflict_id} not found")

        conflict = self.conflicts[conflict_id]
        conflict.status = ConflictStatus.ESCALATED
        conflict.metadata["escalation_reason"] = reason
        conflict.metadata["escalated_date"] = datetime.now().isoformat()

    def get_unresolved_conflicts(self) -> List[Conflict]:
        """Get all unresolved conflicts.
        
        Returns:
            List of unresolved conflicts
        """
        return [
            c for c in self.conflicts.values()
            if c.status != ConflictStatus.RESOLVED
        ]

    def get_high_severity_conflicts(self) -> List[Conflict]:
        """Get all high-severity conflicts.
        
        Returns:
            List of high/critical severity conflicts
        """
        return [
            c for c in self.conflicts.values()
            if c.severity in [ConflictSeverity.HIGH, ConflictSeverity.CRITICAL]
        ]

    def get_conflicts_by_type(self, conflict_type: ConflictType) -> List[Conflict]:
        """Get all conflicts of a specific type.
        
        Args:
            conflict_type: Type of conflict to filter
            
        Returns:
            List of conflicts of that type
        """
        return [c for c in self.conflicts.values() if c.type == conflict_type]

    def get_conflicts_involving_person(self, person_name: str) -> List[Conflict]:
        """Get all conflicts involving a specific person.
        
        Args:
            person_name: Name of person
            
        Returns:
            List of conflicts involving that person
        """
        return [
            c for c in self.conflicts.values()
            if person_name in c.parties_involved
        ]

    def generate_conflict_report(self) -> str:
        """Generate a summary report of all conflicts.
        
        Returns:
            Formatted report string
        """
        report = ["# Conflict Report", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]

        report.append(f"Total Conflicts: {len(self.conflicts)}")
        report.append("")

        # By status
        report.append("## By Status")
        by_status = {}
        for conflict in self.conflicts.values():
            status = conflict.status.value
            by_status[status] = by_status.get(status, 0) + 1
        for status, count in sorted(by_status.items()):
            report.append(f"- {status}: {count}")
        report.append("")

        # High severity
        high_severity = self.get_high_severity_conflicts()
        if high_severity:
            report.append("## High Severity Conflicts")
            for conflict in high_severity:
                report.append(f"- **{conflict.title}** ({conflict.id}): {conflict.type.value}")
            report.append("")

        # Unresolved
        unresolved = self.get_unresolved_conflicts()
        if unresolved:
            report.append(f"## Unresolved ({len(unresolved)})")
            for conflict in unresolved[:5]:  # Show first 5
                report.append(f"- {conflict.title} ({conflict.status.value})")
            if len(unresolved) > 5:
                report.append(f"- ... and {len(unresolved) - 5} more")

        return "\n".join(report)
