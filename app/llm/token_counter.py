"""
Token usage tracking and monitoring.

Monitors:
- Tokens in each request
- Cumulative usage
- Rate limit tracking
- Daily/weekly reports
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.logger import logger


class TokenUsageRecord:
    """Records a single token usage event."""

    def __init__(self, timestamp: float, input_tokens: int, output_tokens: int, model: str):
        self.timestamp = timestamp
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = input_tokens + output_tokens
        self.model = model
        self.datetime = datetime.fromtimestamp(timestamp)

    def __repr__(self):
        return f"TokenUsage(in={self.input_tokens}, out={self.output_tokens}, total={self.total_tokens})"


class TokenCounter:
    """
    Tracks token usage across API calls.
    """

    def __init__(self, request_limit: int = 300, time_window: int = 60):
        """
        Initialize token counter.

        Args:
            request_limit: Max requests per time window
            time_window: Time window in seconds (default: 60 = 1 minute)
        """
        self.request_limit = request_limit
        self.time_window = time_window

        # Usage tracking
        self.usage_records: List[TokenUsageRecord] = []
        self.request_times: List[float] = []

        # Statistics
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0

        # Rate limiting
        self.rate_limited_until: Optional[float] = None

    def record_usage(
        self, input_tokens: int, output_tokens: int, model: str = "unknown"
    ) -> TokenUsageRecord:
        """
        Record token usage for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name

        Returns:
            TokenUsageRecord object
        """
        timestamp = time.time()
        record = TokenUsageRecord(timestamp, input_tokens, output_tokens, model)

        self.usage_records.append(record)
        self.request_times.append(timestamp)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_requests += 1

        logger.debug(f"Recorded token usage: {record}")

        # Cleanup old records (keep last hour)
        self._cleanup_old_records()

        return record

    def _cleanup_old_records(self, hours: int = 24):
        """Remove records older than the specified hours."""
        cutoff_time = time.time() - (hours * 3600)
        old_count = len(self.usage_records)

        self.usage_records = [r for r in self.usage_records if r.timestamp > cutoff_time]
        self.request_times = [t for t in self.request_times if t > cutoff_time]

        removed = old_count - len(self.usage_records)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} old records")

    def get_usage_stats(self) -> Dict:
        """Get comprehensive usage statistics."""
        if not self.usage_records:
            return {
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "average_input_tokens": 0,
                "average_output_tokens": 0,
                "average_tokens_per_request": 0,
            }

        avg_input = self.total_input_tokens / self.total_requests if self.total_requests > 0 else 0
        avg_output = self.total_output_tokens / self.total_requests if self.total_requests > 0 else 0
        avg_total = (self.total_input_tokens + self.total_output_tokens) / self.total_requests if self.total_requests > 0 else 0

        return {
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "average_input_tokens": round(avg_input, 2),
            "average_output_tokens": round(avg_output, 2),
            "average_tokens_per_request": round(avg_total, 2),
        }

    def get_window_stats(self, minutes: int = 1) -> Dict:
        """
        Get statistics for the last N minutes.

        Args:
            minutes: Number of minutes to look back

        Returns:
            Stats for the time window
        """
        cutoff_time = time.time() - (minutes * 60)
        window_records = [r for r in self.usage_records if r.timestamp > cutoff_time]

        if not window_records:
            return {
                "window_requests": 0,
                "window_tokens": 0,
                "window_input_tokens": 0,
                "window_output_tokens": 0,
            }

        input_tokens = sum(r.input_tokens for r in window_records)
        output_tokens = sum(r.output_tokens for r in window_records)

        return {
            "window_requests": len(window_records),
            "window_tokens": input_tokens + output_tokens,
            "window_input_tokens": input_tokens,
            "window_output_tokens": output_tokens,
        }

    def get_daily_stats(self) -> Dict[str, int]:
        """
        Get statistics broken down by day.

        Returns:
            Dict mapping date strings to token counts
        """
        daily_stats = defaultdict(lambda: {"requests": 0, "tokens": 0})

        for record in self.usage_records:
            date_key = record.datetime.date().isoformat()
            daily_stats[date_key]["requests"] += 1
            daily_stats[date_key]["tokens"] += record.total_tokens

        return dict(daily_stats)

    def is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        if self.rate_limited_until is None:
            return False
        if time.time() > self.rate_limited_until:
            self.rate_limited_until = None
            return False
        return True

    def get_rate_limit_reset_time(self) -> Optional[float]:
        """Get when rate limit resets (Unix timestamp)."""
        return self.rate_limited_until

    def check_rate_limit(self) -> Tuple[bool, Optional[str]]:
        """
        Check if rate limit is exceeded.

        Returns:
            (is_ok, message) - True if OK, False if rate limited
        """
        if self.is_rate_limited():
            reset_time = self.rate_limited_until - time.time()
            return False, f"Rate limited. Reset in {reset_time:.0f}s"

        # Count requests in time window
        cutoff_time = time.time() - self.time_window
        window_requests = len([t for t in self.request_times if t > cutoff_time])

        if window_requests >= self.request_limit:
            self.rate_limited_until = time.time() + self.time_window
            msg = f"Rate limit exceeded ({window_requests}/{self.request_limit} requests)"
            logger.warning(msg)
            return False, msg

        return True, None

    def get_requests_remaining(self) -> int:
        """Get remaining requests in current window."""
        cutoff_time = time.time() - self.time_window
        window_requests = len([t for t in self.request_times if t > cutoff_time])
        return max(0, self.request_limit - window_requests)

    def reset(self):
        """Reset all counters."""
        self.usage_records.clear()
        self.request_times.clear()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0
        self.rate_limited_until = None
        logger.info("Reset token counter")


class TokenBudget:
    """
    Manages a token budget with alerting.
    """

    def __init__(self, daily_budget: int, warning_threshold: float = 0.8):
        """
        Initialize token budget.

        Args:
            daily_budget: Maximum tokens allowed per day
            warning_threshold: Alert when usage exceeds this ratio
        """
        self.daily_budget = daily_budget
        self.warning_threshold = warning_threshold
        self.reset_time = self._get_next_reset_time()
        self.tokens_used_today = 0

    def _get_next_reset_time(self) -> float:
        """Get next reset time (midnight UTC)."""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(days=1)
        midnight = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.timestamp()

    def use_tokens(self, count: int) -> Dict:
        """
        Use tokens from budget.

        Args:
            count: Number of tokens to use

        Returns:
            Status dict with remaining tokens and alerts
        """
        # Check if budget should reset
        if time.time() >= self.reset_time:
            self.tokens_used_today = 0
            self.reset_time = self._get_next_reset_time()
            logger.info("Daily token budget reset")

        self.tokens_used_today += count
        remaining = self.daily_budget - self.tokens_used_today

        status = {
            "tokens_used": self.tokens_used_today,
            "remaining_tokens": max(0, remaining),
            "usage_percent": 100 * self.tokens_used_today / self.daily_budget,
            "exceeds_budget": self.tokens_used_today > self.daily_budget,
        }

        if status["usage_percent"] >= (self.warning_threshold * 100):
            status["warning"] = f"Approaching daily budget ({status['usage_percent']:.1f}%)"

        return status

    def get_status(self) -> Dict:
        """Get budget status."""
        return {
            "daily_budget": self.daily_budget,
            "tokens_used_today": self.tokens_used_today,
            "remaining_tokens": max(0, self.daily_budget - self.tokens_used_today),
            "usage_percent": 100 * self.tokens_used_today / self.daily_budget,
        }
