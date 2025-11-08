"""Team recognition and motivation system."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RecognitionType(str, Enum):
    """Type of recognition."""
    GREAT_WORK = "great_work"
    GOING_ABOVE_AND_BEYOND = "above_and_beyond"
    MENTORING = "mentoring"
    TEAMWORK = "teamwork"
    INNOVATION = "innovation"
    RESILIENCE = "resilience"
    COMMUNICATION = "communication"
    QUALITY = "quality"
    SPEED = "speed"
    PROBLEM_SOLVING = "problem_solving"


class Recognition(BaseModel):
    """Recognition of team member accomplishment."""
    id: str = Field(..., description="Recognition ID")
    recipient: str = Field(..., description="Who is being recognized")
    recognizer: str = Field(..., description="Who gave the recognition")
    recognition_type: RecognitionType = Field(..., description="Type of recognition")
    title: str = Field(..., description="Recognition title")
    description: str = Field(..., description="Detailed description")
    impact: Optional[str] = Field(None, description="Impact on team/project")
    public: bool = Field(default=True, description="Public or private recognition")
    created_date: datetime = Field(default_factory=datetime.now, description="When recognized")
    reward: Optional[str] = Field(None, description="Any reward/bonus")
    tags: List[str] = Field(default_factory=list, description="Tags")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class MilestoneAchievement(BaseModel):
    """Milestone achievement for a team member."""
    id: str = Field(..., description="Achievement ID")
    member: str = Field(..., description="Team member")
    milestone: str = Field(..., description="Milestone description")
    date: datetime = Field(default_factory=datetime.now, description="Achievement date")
    significance: int = Field(default=3, ge=1, le=5, description="Significance level (1-5)")
    next_milestone: Optional[str] = Field(None, description="Suggested next milestone")


class GrowthRecord(BaseModel):
    """Record of team member growth and development."""
    member: str = Field(..., description="Team member")
    start_date: datetime = Field(..., description="Record start date")
    skills_developed: List[str] = Field(default_factory=list, description="Skills developed")
    promotions: List[str] = Field(default_factory=list, description="Promotions/role changes")
    achievements: List[str] = Field(default_factory=list, description="Major achievements")
    recognitions_received: int = Field(default=0, description="Recognition count")
    projects_led: int = Field(default=0, description="Projects led")
    mentees: List[str] = Field(default_factory=list, description="People mentored")
    growth_trajectory: str = Field(default="steady", description="Growth trajectory assessment")
    notes: Optional[str] = Field(None, description="Additional notes")


class RecognitionManager:
    """Manages team recognition and motivation."""

    def __init__(self):
        """Initialize the recognition manager."""
        self.recognitions: Dict[str, Recognition] = {}
        self.milestones: Dict[str, List[MilestoneAchievement]] = {}
        self.growth_records: Dict[str, GrowthRecord] = {}
        self.member_stats: Dict[str, Dict] = {}  # Recognition stats per member

    def give_recognition(self, recognition: Recognition) -> str:
        """Give recognition to a team member.
        
        Args:
            recognition: The recognition to give
            
        Returns:
            Recognition ID
        """
        if recognition.id in self.recognitions:
            raise ValueError(f"Recognition {recognition.id} already exists")

        self.recognitions[recognition.id] = recognition

        # Update member stats
        if recognition.recipient not in self.member_stats:
            self.member_stats[recognition.recipient] = {
                "total_recognitions": 0,
                "by_type": {},
                "last_recognition": None,
                "recognizers": []
            }

        stats = self.member_stats[recognition.recipient]
        stats["total_recognitions"] += 1
        rec_type = recognition.recognition_type.value
        stats["by_type"][rec_type] = stats["by_type"].get(rec_type, 0) + 1
        stats["last_recognition"] = recognition.created_date
        if recognition.recognizer not in stats["recognizers"]:
            stats["recognizers"].append(recognition.recognizer)

        return recognition.id

    def record_milestone(self, achievement: MilestoneAchievement) -> str:
        """Record a milestone achievement.
        
        Args:
            achievement: The milestone to record
            
        Returns:
            Achievement ID
        """
        if achievement.member not in self.milestones:
            self.milestones[achievement.member] = []

        self.milestones[achievement.member].append(achievement)
        return achievement.id

    def get_recognitions_for_member(self, member: str, days: int = 90) -> List[Recognition]:
        """Get recent recognitions for a member.
        
        Args:
            member: Team member
            days: Days to look back
            
        Returns:
            List of recognitions
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        return [
            r for r in self.recognitions.values()
            if r.recipient == member and r.created_date.timestamp() > cutoff
        ]

    def get_public_recognitions(self, limit: int = 10) -> List[Recognition]:
        """Get recent public recognitions for team morale.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of public recognitions
        """
        public = [r for r in self.recognitions.values() if r.public]
        return sorted(public, key=lambda r: -r.created_date.timestamp())[:limit]

    def get_member_stats(self, member: str) -> Dict:
        """Get recognition stats for a member.
        
        Args:
            member: Team member
            
        Returns:
            Stats dictionary
        """
        return self.member_stats.get(member, {
            "total_recognitions": 0,
            "by_type": {},
            "last_recognition": None,
            "recognizers": []
        })

    def get_top_recognized_members(self, period_days: int = 90, limit: int = 5) -> List[tuple]:
        """Get top recognized members.
        
        Args:
            period_days: Days to look back
            limit: Number of members to return
            
        Returns:
            List of (member, recognition_count) tuples
        """
        cutoff = datetime.now().timestamp() - (period_days * 24 * 3600)
        recognition_counts = {}

        for recognition in self.recognitions.values():
            if recognition.created_date.timestamp() > cutoff:
                member = recognition.recipient
                recognition_counts[member] = recognition_counts.get(member, 0) + 1

        return sorted(recognition_counts.items(), key=lambda x: -x[1])[:limit]

    def get_recognition_by_type(self, rec_type: RecognitionType, limit: int = 10) -> List[Recognition]:
        """Get recognitions of a specific type.
        
        Args:
            rec_type: Type of recognition
            limit: Maximum number to return
            
        Returns:
            List of recognitions
        """
        matching = [r for r in self.recognitions.values() if r.recognition_type == rec_type]
        return sorted(matching, key=lambda r: -r.created_date.timestamp())[:limit]

    def suggest_recognition(self, member: str, recent_accomplishments: List[str]) -> Optional[str]:
        """Suggest a recognition for a member based on accomplishments.
        
        Args:
            member: Team member
            recent_accomplishments: List of recent accomplishments
            
        Returns:
            Suggestion text
        """
        if not recent_accomplishments:
            return None

        # Analyze accomplishments to suggest recognition type
        accomplishment_text = " ".join(recent_accomplishments).lower()

        if any(word in accomplishment_text for word in ["mentored", "helped", "trained", "guided"]):
            return f"Consider recognizing {member} for mentoring others"

        if any(word in accomplishment_text for word in ["innovation", "novel", "creative", "first"]):
            return f"Consider recognizing {member} for innovation"

        if any(word in accomplishment_text for word in ["teamwork", "collaboration", "together", "supported"]):
            return f"Consider recognizing {member} for great teamwork"

        if any(word in accomplishment_text for word in ["fixed", "resolved", "solved", "debug"]):
            return f"Consider recognizing {member} for problem-solving"

        if any(word in accomplishment_text for word in ["fast", "quick", "delivered", "ahead"]):
            return f"Consider recognizing {member} for speed and execution"

        return f"Consider recognizing {member} for: {recent_accomplishments[0]}"

    def generate_team_recognition_report(self, period_days: int = 90) -> str:
        """Generate a team recognition report.
        
        Args:
            period_days: Days to cover
            
        Returns:
            Formatted report
        """
        cutoff = datetime.now().timestamp() - (period_days * 24 * 3600)

        recent_recognitions = [
            r for r in self.recognitions.values()
            if r.created_date.timestamp() > cutoff
        ]

        report = [
            "# Team Recognition Report",
            f"Period: Last {period_days} days",
            f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        if not recent_recognitions:
            report.append("No recognitions in this period. Let's celebrate team accomplishments!")
            return "\n".join(report)

        # Stats
        report.append("## Statistics")
        report.append(f"Total Recognitions: {len(recent_recognitions)}")

        # By type
        by_type = {}
        for recognition in recent_recognitions:
            rec_type = recognition.recognition_type.value
            by_type[rec_type] = by_type.get(rec_type, 0) + 1

        report.append("\n### By Type")
        for rec_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
            report.append(f"- {rec_type}: {count}")

        # Top recognized
        top_recognized = self.get_top_recognized_members(period_days)
        if top_recognized:
            report.append("\n### Most Recognized Members")
            for member, count in top_recognized[:5]:
                report.append(f"- {member}: {count} recognitions")

        # Recent highlights
        report.append("\n## Recent Highlights")
        for recognition in recent_recognitions[-5:]:
            report.append(f"\n**{recognition.title}**")
            report.append(f"- {recognition.recipient}")
            report.append(f"- {recognition.description}")
            if recognition.impact:
                report.append(f"- Impact: {recognition.impact}")

        # Suggestions
        members_with_no_recent = set(self.member_stats.keys()) - set(r.recipient for r in recent_recognitions)
        if members_with_no_recent:
            report.append("\n## 💡 Consider Recognizing")
            report.append(f"These team members haven't been recently recognized:")
            for member in list(members_with_no_recent)[:5]:
                report.append(f"- {member}")

        return "\n".join(report)

    def get_growth_trajectory(self, member: str) -> str:
        """Assess a member's growth trajectory.
        
        Args:
            member: Team member
            
        Returns:
            Growth trajectory assessment
        """
        if member not in self.growth_records:
            return "New member or no growth record"

        record = self.growth_records[member]

        # Calculate metrics
        recognitions = len(self.get_recognitions_for_member(member, days=365))
        months = max(1, (datetime.now() - record.start_date).days // 30)
        recognition_rate = recognitions / months if months > 0 else 0

        skills_gained = len(record.skills_developed)
        projects_led = record.projects_led
        mentees_count = len(record.mentees)

        # Assess
        indicators = []
        if recognition_rate > 2:
            indicators.append("⭐ Highly recognized")
        if skills_gained > 3:
            indicators.append("📚 Rapid skill development")
        if projects_led > 0:
            indicators.append("🎯 Leadership opportunities")
        if mentees_count > 0:
            indicators.append("👥 Mentoring others")

        if not indicators:
            trajectory = "Steady contributor"
        elif len(indicators) >= 3:
            trajectory = "High performer - star track"
        elif len(indicators) == 2:
            trajectory = "Strong performer"
        else:
            trajectory = "Solid contributor"

        return f"{trajectory}: {', '.join(indicators)}"

    def should_recognize_milestone(self, member: str) -> Optional[str]:
        """Check if member should be recognized for a milestone.
        
        Args:
            member: Team member
            
        Returns:
            Suggestion or None
        """
        stats = self.get_member_stats(member)

        # Milestone: 10 recognitions
        if stats.get("total_recognitions", 0) == 10:
            return f"Celebrate {member}'s 10th recognition!"

        # Milestone: 50 recognitions
        if stats.get("total_recognitions", 0) == 50:
            return f"🌟 Celebrate {member}'s 50th recognition - a recognition superstar!"

        if member in self.milestones:
            recent_milestones = [
                m for m in self.milestones[member]
                if (datetime.now() - m.date).days < 7
            ]
            if recent_milestones:
                return f"Celebrate {member}'s recent milestone: {recent_milestones[0].milestone}"

        return None
