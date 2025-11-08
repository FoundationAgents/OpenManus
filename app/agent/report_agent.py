"""Report and summary generation agent."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.logger import logger
from app.prompt.communication import SYSTEM_PROMPT
from app.schema import Message
from app.tool import Terminate, ToolCollection


class ReportAgent(ToolCallAgent):
    """Agent for generating reports, summaries, and digests."""

    name: str = "ReportAgent"
    description: str = (
        "An intelligent report generation agent that creates status reports, "
        "weekly summaries, performance metrics, and planning documents"
    )

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = "Generate reports and summaries as needed."

    max_steps: int = 20
    max_observe: int = 15000

    # Report data
    activities: List[Dict] = Field(
        default_factory=list, description="Activity log for reports"
    )
    metrics: Dict = Field(default_factory=dict, description="Performance metrics")
    accomplishments: List[str] = Field(
        default_factory=list, description="List of accomplishments"
    )
    blockers: List[str] = Field(
        default_factory=list, description="Current blockers/issues"
    )

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(Terminate())
    )

    class Config:
        arbitrary_types_allowed = True

    async def step(self) -> str:
        """Execute a single step in report generation."""
        try:
            # Check what reports are needed
            current_day = datetime.now().weekday()
            current_hour = datetime.now().hour

            # Generate weekly report on Monday morning
            if current_day == 0 and 8 <= current_hour < 9:
                return await self._generate_weekly_report()

            # Generate daily digest in evening
            if 17 <= current_hour < 18:
                return await self._generate_daily_digest()

            return "No reports due at this time"

        except Exception as e:
            logger.error(f"Error in report agent step: {e}")
            return f"Error: {str(e)}"

    async def _generate_weekly_report(self) -> str:
        """Generate weekly status report."""
        # Get activities from past week
        week_ago = datetime.now() - timedelta(days=7)
        week_activities = [
            a for a in self.activities
            if datetime.fromisoformat(a["timestamp"]) > week_ago
        ]

        # Build report
        report = self._build_weekly_report(week_activities)

        # Save and return
        logger.info(f"✓ Generated weekly report")
        self.update_memory("assistant", report)
        return report

    async def _generate_daily_digest(self) -> str:
        """Generate daily summary digest."""
        # Get today's activities
        today = datetime.now().date()
        today_activities = [
            a for a in self.activities
            if datetime.fromisoformat(a["timestamp"]).date() == today
        ]

        # Build digest
        digest = self._build_daily_digest(today_activities)

        logger.info(f"✓ Generated daily digest")
        self.update_memory("assistant", digest)
        return digest

    def _build_weekly_report(self, activities: List[Dict]) -> str:
        """Build comprehensive weekly report."""
        report = f"""
=== Weekly Status Report ===
Week of: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')}

## Accomplishments

"""
        if self.accomplishments:
            for i, accomplishment in enumerate(self.accomplishments[:5], 1):
                report += f"{i}. {accomplishment}\n"
        else:
            report += "- No accomplishments recorded\n"

        report += "\n## Metrics\n\n"
        if self.metrics:
            for key, value in self.metrics.items():
                report += f"- {key}: {value}\n"
        else:
            report += "- No metrics available\n"

        report += "\n## Blockers/Issues\n\n"
        if self.blockers:
            for blocker in self.blockers[:3]:
                report += f"- {blocker}\n"
        else:
            report += "- No current blockers\n"

        # Add activity summary
        if activities:
            report += "\n## Activity Summary\n\n"
            report += f"- Total activities: {len(activities)}\n"

            # Group by type
            activity_types = {}
            for activity in activities:
                activity_type = activity.get("type", "other")
                activity_types[activity_type] = activity_types.get(activity_type, 0) + 1

            for activity_type, count in activity_types.items():
                report += f"- {activity_type}: {count}\n"

        # Time breakdown
        if self.metrics.get("time_breakdown"):
            report += "\n## Time Breakdown\n\n"
            for category, percentage in self.metrics["time_breakdown"].items():
                report += f"- {category}: {percentage}%\n"

        report += "\n## Next Week Planning\n\n"
        report += "- Focus on key deliverables\n"
        report += "- Address any blockers\n"
        report += "- Schedule necessary meetings\n"

        return report

    def _build_daily_digest(self, activities: List[Dict]) -> str:
        """Build daily digest summary."""
        digest = f"=== Daily Summary - {datetime.now().strftime('%Y-%m-%d')} ===\n\n"

        if not activities:
            digest += "No activities recorded today.\n"
            return digest

        # Categorize activities
        categories = {}
        for activity in activities:
            category = activity.get("category", "other")
            if category not in categories:
                categories[category] = []
            categories[category].append(activity)

        for category, items in categories.items():
            digest += f"\n**{category.title()}** ({len(items)} items):\n"
            for item in items[:5]:  # Show top 5 per category
                digest += f"- {item.get('description', 'No description')}\n"

        # Summary stats
        digest += f"\n**Summary:**\n"
        digest += f"- Total activities: {len(activities)}\n"
        digest += f"- Categories: {len(categories)}\n"

        return digest

    def add_accomplishment(self, accomplishment: str) -> None:
        """Add an accomplishment to track."""
        if accomplishment not in self.accomplishments:
            self.accomplishments.append(accomplishment)
            logger.info(f"✓ Added accomplishment: {accomplishment}")

    def add_blocker(self, blocker: str) -> None:
        """Add a blocker/issue."""
        if blocker not in self.blockers:
            self.blockers.append(blocker)
            logger.info(f"✓ Added blocker: {blocker}")

    def remove_blocker(self, blocker: str) -> bool:
        """Remove a resolved blocker."""
        if blocker in self.blockers:
            self.blockers.remove(blocker)
            logger.info(f"✓ Removed blocker: {blocker}")
            return True
        return False

    def update_metric(self, metric_name: str, value) -> None:
        """Update a metric."""
        self.metrics[metric_name] = value
        logger.info(f"✓ Updated metric {metric_name}: {value}")

    def log_activity(
        self,
        category: str,
        description: str,
        duration_minutes: Optional[int] = None,
    ) -> None:
        """Log an activity."""
        activity = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "description": description,
            "duration_minutes": duration_minutes,
        }
        self.activities.append(activity)
        logger.info(f"✓ Logged activity: {category} - {description}")

    def get_report_summary(self) -> str:
        """Get summary of reports and data."""
        today = datetime.now().date()
        today_activities = [
            a for a in self.activities
            if datetime.fromisoformat(a["timestamp"]).date() == today
        ]

        summary = f"""Report Agent Status:
- Accomplishments tracked: {len(self.accomplishments)}
- Current blockers: {len(self.blockers)}
- Metrics tracked: {len(self.metrics)}
- Today's activities: {len(today_activities)}
- Total activities logged: {len(self.activities)}"""

        return summary

    async def generate_custom_report(self, report_type: str, **kwargs) -> str:
        """Generate a custom report.

        Args:
            report_type: Type of report (status, metrics, timeline, etc.)
            **kwargs: Additional parameters

        Returns:
            Generated report
        """
        if report_type == "status":
            return self._build_status_report(**kwargs)
        elif report_type == "metrics":
            return self._build_metrics_report(**kwargs)
        elif report_type == "timeline":
            return self._build_timeline_report(**kwargs)
        else:
            return f"Unknown report type: {report_type}"

    def _build_status_report(self, **kwargs) -> str:
        """Build status report."""
        report = "=== Status Report ===\n\n"

        for key, value in kwargs.items():
            report += f"**{key.replace('_', ' ').title()}:**\n"
            if isinstance(value, list):
                for item in value:
                    report += f"- {item}\n"
            else:
                report += f"{value}\n"
            report += "\n"

        return report

    def _build_metrics_report(self, **kwargs) -> str:
        """Build metrics report."""
        report = "=== Metrics Report ===\n\n"

        combined_metrics = {**self.metrics, **kwargs}
        for key, value in combined_metrics.items():
            report += f"- {key}: {value}\n"

        return report

    def _build_timeline_report(self, **kwargs) -> str:
        """Build timeline report."""
        report = "=== Timeline Report ===\n\n"

        # Sort activities by date
        sorted_activities = sorted(
            self.activities,
            key=lambda a: a["timestamp"],
        )

        for activity in sorted_activities[-10:]:  # Show last 10
            timestamp = datetime.fromisoformat(activity["timestamp"]).strftime(
                "%Y-%m-%d %H:%M"
            )
            category = activity.get("category", "other")
            description = activity.get("description", "No description")
            report += f"[{timestamp}] {category}: {description}\n"

        return report
