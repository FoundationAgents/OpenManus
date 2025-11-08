"""Team wellbeing monitoring to prevent burnout."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class WellbeingStatus(str, Enum):
    """Status of team member wellbeing."""
    HEALTHY = "healthy"
    CAUTION = "caution"
    AT_RISK = "at_risk"
    CRITICAL = "critical"


class WellbeingAlert(BaseModel):
    """Alert about potential burnout or wellbeing issues."""
    id: str = Field(..., description="Alert ID")
    member_name: str = Field(..., description="Member affected")
    status: WellbeingStatus = Field(..., description="Wellbeing status")
    severity: int = Field(default=1, ge=1, le=5, description="Alert severity (1-5)")
    reasons: List[str] = Field(default_factory=list, description="Reasons for alert")
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions")
    created_date: datetime = Field(default_factory=datetime.now, description="When alert was created")
    resolved: bool = Field(default=False, description="Whether alert has been resolved")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class MemberWellbeing(BaseModel):
    """Tracks wellbeing metrics for a team member."""
    member_name: str = Field(..., description="Team member name")
    hours_this_week: float = Field(default=0.0, description="Hours worked this week")
    consecutive_overtime_weeks: int = Field(default=0, description="Weeks of overtime in a row")
    last_break_date: Optional[datetime] = Field(None, description="Last day off/break")
    vacation_days_used: int = Field(default=0, description="Vacation days used this year")
    vacation_days_available: int = Field(default=20, description="Total vacation days available")
    task_difficulty_current: float = Field(default=3.0, ge=1, le=5, description="Current task difficulty (1-5)")
    energy_level: float = Field(default=3.0, ge=1, le=5, description="Current energy level (1-5)")
    recent_major_projects: List[str] = Field(default_factory=list, description="Recent major projects")
    last_1_on_1: Optional[datetime] = Field(None, description="Last one-on-one with manager")
    working_late_count: int = Field(default=0, description="Days worked past normal hours this week")
    weekend_work_count: int = Field(default=0, description="Weekend days worked this month")
    meeting_load: int = Field(default=0, description="Meetings scheduled this week")
    morale_comment: Optional[str] = Field(None, description="Latest morale feedback")
    last_assessment_date: datetime = Field(default_factory=datetime.now, description="Last wellbeing assessment")


class WellbeingMonitor:
    """Monitors team member wellbeing and alerts to burnout risks."""

    def __init__(self):
        """Initialize the wellbeing monitor."""
        self.wellbeing: Dict[str, MemberWellbeing] = {}
        self.alerts: Dict[str, WellbeingAlert] = {}
        self.burnout_threshold_hours = 50.0  # Hours per week
        self.critical_threshold_hours = 60.0  # Critical burnout threshold

    def record_hours(self, member_name: str, hours: float) -> None:
        """Record hours worked by a member.
        
        Args:
            member_name: Member name
            hours: Hours worked
        """
        if member_name not in self.wellbeing:
            self.wellbeing[member_name] = MemberWellbeing(member_name=member_name)

        wb = self.wellbeing[member_name]
        wb.hours_this_week += hours

        # Check for working late
        if datetime.now().hour > 17:
            wb.working_late_count += 1

        # Check for weekend work
        if datetime.now().weekday() >= 5:  # Saturday=5, Sunday=6
            wb.weekend_work_count += 1

    def assess_wellbeing(self, member_name: str) -> WellbeingStatus:
        """Assess current wellbeing status for a member.
        
        Factors:
        - Hours worked (>50h = caution, >60h = critical)
        - Consecutive overtime weeks
        - Time since last break
        - Task difficulty vs energy level
        - Working late/weekends
        
        Args:
            member_name: Member name
            
        Returns:
            WellbeingStatus
        """
        if member_name not in self.wellbeing:
            return WellbeingStatus.HEALTHY

        wb = self.wellbeing[member_name]
        risk_score = 0

        # Hours check
        if wb.hours_this_week > self.critical_threshold_hours:
            risk_score += 30
        elif wb.hours_this_week > self.burnout_threshold_hours:
            risk_score += 20

        # Consecutive overtime
        risk_score += wb.consecutive_overtime_weeks * 15

        # Time since break
        if wb.last_break_date:
            days_since_break = (datetime.now() - wb.last_break_date).days
            if days_since_break > 60:
                risk_score += 20
            elif days_since_break > 30:
                risk_score += 10

        # Task difficulty > energy level
        if wb.task_difficulty_current > wb.energy_level:
            diff = wb.task_difficulty_current - wb.energy_level
            risk_score += diff * 10

        # Late nights and weekends
        risk_score += wb.working_late_count * 5
        risk_score += wb.weekend_work_count * 5

        # Meeting overload
        if wb.meeting_load > 10:
            risk_score += 10

        # Determine status
        if risk_score >= 70:
            return WellbeingStatus.CRITICAL
        elif risk_score >= 50:
            return WellbeingStatus.AT_RISK
        elif risk_score >= 30:
            return WellbeingStatus.CAUTION
        else:
            return WellbeingStatus.HEALTHY

    def check_for_alerts(self, member_name: str) -> List[WellbeingAlert]:
        """Check for wellbeing alerts for a member.
        
        Args:
            member_name: Member name
            
        Returns:
            List of active alerts
        """
        if member_name not in self.wellbeing:
            return []

        wb = self.wellbeing[member_name]
        status = self.assess_wellbeing(member_name)
        alerts = []

        alert_id = f"alert-{member_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        alert = WellbeingAlert(
            id=alert_id,
            member_name=member_name,
            status=status,
            severity=self._calculate_severity(wb, status)
        )

        # Check specific conditions
        if wb.hours_this_week > self.critical_threshold_hours:
            alert.reasons.append(f"Working {wb.hours_this_week:.1f}h this week (critical: >60h)")
            alert.recommendations.append("URGENT: Take immediate break or reduce workload")

        if wb.hours_this_week > self.burnout_threshold_hours:
            alert.reasons.append(f"Working {wb.hours_this_week:.1f}h this week (caution: >50h)")
            alert.recommendations.append("Suggest reducing hours or extending deadlines")

        if wb.consecutive_overtime_weeks >= 2:
            alert.reasons.append(f"{wb.consecutive_overtime_weeks} consecutive weeks of overtime")
            alert.recommendations.append("Redistribute workload to other team members")

        if wb.last_break_date and (datetime.now() - wb.last_break_date).days > 60:
            alert.reasons.append(f"No break for {(datetime.now() - wb.last_break_date).days} days")
            alert.recommendations.append("Schedule time off or at least a long weekend")

        if wb.task_difficulty_current > wb.energy_level:
            alert.reasons.append(f"High task difficulty ({wb.task_difficulty_current}) vs energy ({wb.energy_level})")
            alert.recommendations.append("Pair with support or rotate to easier tasks temporarily")

        if wb.working_late_count > 2:
            alert.reasons.append(f"Working late {wb.working_late_count} days this week")
            alert.recommendations.append("Protect work-life boundaries; stop work at normal hours")

        if wb.weekend_work_count > 1:
            alert.reasons.append(f"Working {wb.weekend_work_count} days last weekend")
            alert.recommendations.append("Ensure weekends remain off-limits unless emergency")

        if status != WellbeingStatus.HEALTHY:
            alert_key = f"{member_name}-{status.value}"
            if alert_key not in self.alerts or self.alerts[alert_key].resolved:
                self.alerts[alert_key] = alert
            return [self.alerts[alert_key]]

        return alerts

    def _calculate_severity(self, wb: MemberWellbeing, status: WellbeingStatus) -> int:
        """Calculate alert severity.
        
        Args:
            wb: Member wellbeing data
            status: Current wellbeing status
            
        Returns:
            Severity score 1-5
        """
        if status == WellbeingStatus.CRITICAL:
            return 5
        elif status == WellbeingStatus.AT_RISK:
            return 4 if wb.hours_this_week > self.critical_threshold_hours else 3
        elif status == WellbeingStatus.CAUTION:
            return 2
        else:
            return 1

    def suggest_task_rotation(self, member_name: str) -> Optional[str]:
        """Suggest task rotation if member is overloaded.
        
        Args:
            member_name: Member name
            
        Returns:
            Suggestion or None
        """
        if member_name not in self.wellbeing:
            return None

        wb = self.wellbeing[member_name]
        status = self.assess_wellbeing(member_name)

        if status in [WellbeingStatus.AT_RISK, WellbeingStatus.CRITICAL]:
            if wb.recent_major_projects:
                current_project = wb.recent_major_projects[-1]
                return f"Consider rotating {member_name} off '{current_project}' to lighter work temporarily"

        return None

    def suggest_break(self, member_name: str) -> Optional[str]:
        """Suggest a break if member needs one.
        
        Args:
            member_name: Member name
            
        Returns:
            Suggestion or None
        """
        if member_name not in self.wellbeing:
            return None

        wb = self.wellbeing[member_name]
        status = self.assess_wellbeing(member_name)

        if status == WellbeingStatus.CRITICAL:
            return f"URGENT: {member_name} should take immediate time off (1-2 weeks recommended)"

        if status == WellbeingStatus.AT_RISK:
            if wb.vacation_days_available > 0:
                return f"Recommend {member_name} take {min(3, wb.vacation_days_available)} days off"

        if wb.last_break_date and (datetime.now() - wb.last_break_date).days > 60:
            return f"Recommend {member_name} schedule long weekend (hasn't had break in {(datetime.now() - wb.last_break_date).days} days)"

        return None

    def suggest_support(self, member_name: str) -> Optional[str]:
        """Suggest support measures.
        
        Args:
            member_name: Member name
            
        Returns:
            Suggestion or None
        """
        if member_name not in self.wellbeing:
            return None

        wb = self.wellbeing[member_name]

        if wb.meeting_load > 10:
            return f"Reduce meeting load for {member_name} (currently {wb.meeting_load} meetings/week; target <8)"

        if wb.task_difficulty_current > 4 and wb.energy_level < 3:
            return f"Pair {member_name} with support on current tasks (high difficulty/low energy)"

        return None

    def record_vacation(self, member_name: str, days: int) -> None:
        """Record vacation taken by a member.
        
        Args:
            member_name: Member name
            days: Number of days taken
        """
        if member_name not in self.wellbeing:
            self.wellbeing[member_name] = MemberWellbeing(member_name=member_name)

        wb = self.wellbeing[member_name]
        wb.vacation_days_used += days
        wb.last_break_date = datetime.now()
        wb.consecutive_overtime_weeks = 0  # Reset overtime counter
        wb.working_late_count = 0
        wb.hours_this_week = 0

    def reset_weekly_metrics(self) -> None:
        """Reset weekly metrics (hours, working late, etc).
        
        Should be called weekly (e.g., Fridays)
        """
        for wb in self.wellbeing.values():
            # Track if this week was overtime to increment consecutive counter
            if wb.hours_this_week > self.burnout_threshold_hours:
                wb.consecutive_overtime_weeks += 1
            else:
                wb.consecutive_overtime_weeks = 0

            # Reset weekly counters
            wb.hours_this_week = 0
            wb.working_late_count = 0
            wb.meeting_load = 0

    def get_team_wellbeing_summary(self) -> str:
        """Generate a team wellbeing summary.
        
        Returns:
            Formatted summary
        """
        summary = ["# Team Wellbeing Summary", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]

        # Breakdown by status
        by_status = {}
        for member_name in self.wellbeing.keys():
            status = self.assess_wellbeing(member_name)
            status_name = status.value
            by_status[status_name] = by_status.get(status_name, 0) + 1

        summary.append("## Status Breakdown")
        for status in [WellbeingStatus.HEALTHY.value, WellbeingStatus.CAUTION.value,
                      WellbeingStatus.AT_RISK.value, WellbeingStatus.CRITICAL.value]:
            count = by_status.get(status, 0)
            if count > 0:
                summary.append(f"- {status.capitalize()}: {count} members")
        summary.append("")

        # At-risk members
        at_risk = [
            name for name in self.wellbeing.keys()
            if self.assess_wellbeing(name) in [WellbeingStatus.AT_RISK, WellbeingStatus.CRITICAL]
        ]

        if at_risk:
            summary.append("## ⚠️ Members At Risk")
            for member in at_risk:
                wb = self.wellbeing[member]
                status = self.assess_wellbeing(member)
                summary.append(f"- **{member}** ({status.value}): {wb.hours_this_week:.0f}h worked this week")
            summary.append("")

        # Recommendations
        recommendations = []
        for member_name in self.wellbeing.keys():
            break_suggestion = self.suggest_break(member_name)
            if break_suggestion:
                recommendations.append(f"- {break_suggestion}")

            rotation = self.suggest_task_rotation(member_name)
            if rotation:
                recommendations.append(f"- {rotation}")

            support = self.suggest_support(member_name)
            if support:
                recommendations.append(f"- {support}")

        if recommendations:
            summary.append("## Recommendations")
            summary.extend(recommendations[:10])  # Show first 10
            if len(recommendations) > 10:
                summary.append(f"- ... and {len(recommendations) - 10} more")

        return "\n".join(summary)

    def resolve_alert(self, alert_id: str) -> None:
        """Mark an alert as resolved.
        
        Args:
            alert_id: Alert ID
        """
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
