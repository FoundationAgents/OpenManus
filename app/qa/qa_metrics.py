"""
QA Metrics & Reporting

Tracks and reports QA system performance and code quality trends.
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from app.logger import logger


@dataclass
class QAMetric:
    """QA metric entry"""
    timestamp: str
    code_quality_score: float
    issues_per_kloc: float
    auto_fix_rate: float
    false_positive_rate: float
    review_time_avg: float
    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QAMetricsCollector:
    """Collects and analyzes QA metrics"""
    
    def __init__(self, storage_path: str = "cache/qa_metrics.json"):
        self.storage_path = storage_path
        self.metrics_history: List[QAMetric] = []
        self.current_period_stats = {
            "total_reviews": 0,
            "total_issues": 0,
            "total_fixes": 0,
            "total_loc": 0,
            "false_positives": 0,
            "review_times": []
        }
        self.load()
    
    def load(self):
        """Load metrics from storage"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for metric_data in data.get("metrics", []):
                    metric = QAMetric(**metric_data)
                    self.metrics_history.append(metric)
                
                logger.info(f"Loaded {len(self.metrics_history)} metric entries")
            
            except Exception as e:
                logger.error(f"Failed to load metrics: {e}")
    
    def save(self):
        """Save metrics to storage"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            data = {
                "metrics": [m.to_dict() for m in self.metrics_history],
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(self.metrics_history)} metrics")
        
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def record_review(
        self,
        issues_found: List[Dict[str, Any]],
        auto_fixed: int,
        lines_of_code: int,
        review_time: float
    ):
        """Record a code review"""
        self.current_period_stats["total_reviews"] += 1
        self.current_period_stats["total_issues"] += len(issues_found)
        self.current_period_stats["total_fixes"] += auto_fixed
        self.current_period_stats["total_loc"] += lines_of_code
        self.current_period_stats["review_times"].append(review_time)
        
        # Calculate and save metric snapshot
        self._save_snapshot(issues_found)
    
    def record_false_positive(self):
        """Record a false positive"""
        self.current_period_stats["false_positives"] += 1
    
    def calculate_code_quality_score(self, issues: List[Dict[str, Any]], loc: int) -> float:
        """Calculate code quality score (0-100)"""
        if loc == 0:
            return 100.0
        
        # Weight by severity
        severity_weights = {
            "CRITICAL": 10,
            "HIGH": 5,
            "MEDIUM": 2,
            "LOW": 1
        }
        
        weighted_issues = sum(
            severity_weights.get(issue.get("severity", "MEDIUM"), 2)
            for issue in issues
        )
        
        # Calculate score (max 100, min 0)
        issues_per_kloc = (weighted_issues / loc) * 1000
        score = max(0, 100 - issues_per_kloc * 5)
        
        return round(score, 2)
    
    def get_daily_report(self) -> Dict[str, Any]:
        """Generate daily QA report"""
        stats = self.current_period_stats
        
        if stats["total_reviews"] == 0:
            return {
                "period": "daily",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "message": "No reviews performed today"
            }
        
        issues_per_kloc = (stats["total_issues"] / max(stats["total_loc"], 1)) * 1000
        auto_fix_rate = (stats["total_fixes"] / max(stats["total_issues"], 1)) * 100
        avg_review_time = sum(stats["review_times"]) / len(stats["review_times"]) if stats["review_times"] else 0
        
        return {
            "period": "daily",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_reviews": stats["total_reviews"],
            "total_issues": stats["total_issues"],
            "issues_per_1000_loc": round(issues_per_kloc, 2),
            "auto_fix_rate": round(auto_fix_rate, 2),
            "average_review_time": round(avg_review_time, 2),
            "false_positives": stats["false_positives"]
        }
    
    def get_weekly_report(self) -> Dict[str, Any]:
        """Generate weekly QA report"""
        week_ago = datetime.now() - timedelta(days=7)
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m.timestamp) >= week_ago
        ]
        
        if not recent_metrics:
            return {
                "period": "weekly",
                "message": "No data for the past week"
            }
        
        # Calculate trends
        avg_quality = sum(m.code_quality_score for m in recent_metrics) / len(recent_metrics)
        avg_issues_per_kloc = sum(m.issues_per_kloc for m in recent_metrics) / len(recent_metrics)
        avg_auto_fix = sum(m.auto_fix_rate for m in recent_metrics) / len(recent_metrics)
        
        # Calculate trend direction
        if len(recent_metrics) >= 2:
            quality_trend = "improving" if recent_metrics[-1].code_quality_score > recent_metrics[0].code_quality_score else "declining"
        else:
            quality_trend = "stable"
        
        return {
            "period": "weekly",
            "date_range": f"{week_ago.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}",
            "average_quality_score": round(avg_quality, 2),
            "average_issues_per_1000_loc": round(avg_issues_per_kloc, 2),
            "average_auto_fix_rate": round(avg_auto_fix, 2),
            "quality_trend": quality_trend,
            "total_reviews": len(recent_metrics)
        }
    
    def get_agent_comparison(self, agent_metrics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Compare quality across agents"""
        comparison = []
        
        for agent_id, metrics in agent_metrics.items():
            comparison.append({
                "agent": agent_id,
                "code_quality": metrics.get("quality_score", 0),
                "issues_found": metrics.get("issues_count", 0),
                "auto_fix_rate": metrics.get("auto_fix_rate", 0)
            })
        
        # Sort by quality
        comparison.sort(key=lambda x: x["code_quality"], reverse=True)
        
        return {
            "comparison": comparison,
            "best_agent": comparison[0]["agent"] if comparison else None,
            "needs_improvement": [a["agent"] for a in comparison if a["code_quality"] < 70]
        }
    
    def get_historical_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get historical trend data"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m.timestamp) >= cutoff
        ]
        
        if not recent:
            return {"message": "No historical data"}
        
        # Organize by date
        by_date = defaultdict(list)
        for metric in recent:
            date = datetime.fromisoformat(metric.timestamp).strftime("%Y-%m-%d")
            by_date[date].append(metric)
        
        trend_data = []
        for date in sorted(by_date.keys()):
            day_metrics = by_date[date]
            avg_quality = sum(m.code_quality_score for m in day_metrics) / len(day_metrics)
            avg_issues = sum(m.issues_per_kloc for m in day_metrics) / len(day_metrics)
            
            trend_data.append({
                "date": date,
                "quality_score": round(avg_quality, 2),
                "issues_per_kloc": round(avg_issues, 2),
                "reviews": len(day_metrics)
            })
        
        return {
            "period_days": days,
            "data_points": len(trend_data),
            "trends": trend_data
        }
    
    def _save_snapshot(self, issues: List[Dict[str, Any]]):
        """Save current metrics snapshot"""
        stats = self.current_period_stats
        
        if stats["total_reviews"] == 0:
            return
        
        # Calculate metrics
        quality_score = self.calculate_code_quality_score(issues, stats["total_loc"])
        issues_per_kloc = (stats["total_issues"] / max(stats["total_loc"], 1)) * 1000
        auto_fix_rate = (stats["total_fixes"] / max(stats["total_issues"], 1)) * 100
        false_positive_rate = (stats["false_positives"] / max(stats["total_issues"], 1)) * 100
        avg_review_time = sum(stats["review_times"]) / len(stats["review_times"]) if stats["review_times"] else 0
        
        # Count by severity
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in issues:
            severity = issue.get("severity", "MEDIUM")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        metric = QAMetric(
            timestamp=datetime.now().isoformat(),
            code_quality_score=quality_score,
            issues_per_kloc=round(issues_per_kloc, 2),
            auto_fix_rate=round(auto_fix_rate, 2),
            false_positive_rate=round(false_positive_rate, 2),
            review_time_avg=round(avg_review_time, 2),
            issues_by_severity=severity_counts
        )
        
        self.metrics_history.append(metric)
        
        # Keep only last 90 days
        cutoff = datetime.now() - timedelta(days=90)
        self.metrics_history = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m.timestamp) >= cutoff
        ]
        
        self.save()
