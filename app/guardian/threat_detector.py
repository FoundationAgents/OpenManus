"""
Threat Detection System
Uses machine learning and statistical analysis to detect threats
"""

import asyncio
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

import numpy as np
from app.logger import logger
from app.config import config
from app.database.database_service import database_service


class ThreatDetector:
    """Threat detection using statistical analysis and ML"""
    
    def __init__(self):
        self.baseline_metrics: Dict[str, List[float]] = {}
        self.anomaly_thresholds: Dict[str, float] = {}
        self._learning_period_days = 7
        self._min_samples = 30
    
    async def initialize(self):
        """Initialize threat detector with historical data"""
        logger.info("Initializing threat detector...")
        
        # Load historical metrics for baseline
        await self._load_baseline_metrics()
        
        # Calculate anomaly thresholds
        await self._calculate_thresholds()
        
        logger.info("Threat detector initialized")
    
    async def _load_baseline_metrics(self):
        """Load historical metrics for baseline calculation"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self._learning_period_days)
            
            async with await database_service.get_connection() as db:
                cursor = await db.execute("""
                    SELECT metric_name, metric_value, timestamp
                    FROM system_metrics 
                    WHERE timestamp > ?
                    ORDER BY metric_name, timestamp
                """, (cutoff_date.isoformat(),))
                
                rows = await cursor.fetchall()
                
                # Group by metric name
                metrics_by_name = {}
                for metric_name, value, timestamp in rows:
                    if metric_name not in metrics_by_name:
                        metrics_by_name[metric_name] = []
                    metrics_by_name[metric_name].append(value)
                
                # Store baseline data
                for metric_name, values in metrics_by_name.items():
                    if len(values) >= self._min_samples:
                        self.baseline_metrics[metric_name] = values
                        logger.info(f"Loaded {len(values)} samples for metric {metric_name}")
                    else:
                        logger.warning(f"Insufficient data for metric {metric_name}: {len(values)} samples")
                        
        except Exception as e:
            logger.error(f"Error loading baseline metrics: {e}")
    
    async def _calculate_thresholds(self):
        """Calculate anomaly detection thresholds"""
        for metric_name, values in self.baseline_metrics.items():
            try:
                # Calculate statistical measures
                mean = statistics.mean(values)
                stdev = statistics.stdev(values) if len(values) > 1 else 0
                
                # Use 3-sigma rule for threshold
                threshold = 3.0 * stdev if stdev > 0 else 0.1 * mean
                
                self.anomaly_thresholds[metric_name] = threshold
                logger.info(f"Calculated threshold for {metric_name}: {threshold:.4f}")
                
            except Exception as e:
                logger.error(f"Error calculating threshold for {metric_name}: {e}")
    
    async def detect_anomaly(self, metric_name: str, value: float) -> Tuple[bool, float]:
        """Detect if a metric value is anomalous"""
        try:
            if metric_name not in self.baseline_metrics:
                logger.warning(f"No baseline data for metric {metric_name}")
                return False, 0.0
            
            baseline_values = self.baseline_metrics[metric_name]
            threshold = self.anomaly_thresholds.get(metric_name, 0.0)
            
            if len(baseline_values) < self._min_samples:
                return False, 0.0
            
            # Calculate Z-score
            mean = statistics.mean(baseline_values)
            stdev = statistics.stdev(baseline_values) if len(baseline_values) > 1 else 1.0
            
            if stdev == 0:
                return False, 0.0
            
            z_score = abs(value - mean) / stdev
            
            # Normalize to confidence score (0-1)
            confidence = min(z_score / 3.0, 1.0)
            
            # Determine if anomalous
            is_anomalous = z_score > (threshold / stdev) if stdev > 0 else False
            
            return is_anomalous, confidence
            
        except Exception as e:
            logger.error(f"Error detecting anomaly for {metric_name}: {e}")
            return False, 0.0
    
    async def detect_pattern_anomaly(self, metric_name: str, recent_values: List[float]) -> Tuple[bool, float]:
        """Detect anomalies in value patterns (time series)"""
        try:
            if len(recent_values) < 10:
                return False, 0.0
            
            if metric_name not in self.baseline_metrics:
                return False, 0.0
            
            # Calculate pattern features
            recent_trend = self._calculate_trend(recent_values)
            recent_volatility = statistics.stdev(recent_values) if len(recent_values) > 1 else 0
            
            # Compare with baseline patterns
            baseline_values = self.baseline_metrics[metric_name]
            baseline_trends = []
            baseline_volatilities = []
            
            # Calculate baseline patterns from sliding windows
            window_size = len(recent_values)
            for i in range(len(baseline_values) - window_size + 1):
                window = baseline_values[i:i + window_size]
                baseline_trends.append(self._calculate_trend(window))
                if len(window) > 1:
                    baseline_volatilities.append(statistics.stdev(window))
            
            if not baseline_trends:
                return False, 0.0
            
            # Calculate pattern anomalies
            trend_z = abs(recent_trend - statistics.mean(baseline_trends)) / (
                statistics.stdev(baseline_trends) if len(baseline_trends) > 1 else 1.0
            )
            
            vol_z = abs(recent_volatility - statistics.mean(baseline_volatilities)) / (
                statistics.stdev(baseline_volatilities) if len(baseline_volatilities) > 1 else 1.0
            )
            
            # Combined anomaly score
            combined_z = (trend_z + vol_z) / 2
            confidence = min(combined_z / 3.0, 1.0)
            
            is_anomalous = combined_z > 2.0
            
            return is_anomalous, confidence
            
        except Exception as e:
            logger.error(f"Error detecting pattern anomaly for {metric_name}: {e}")
            return False, 0.0
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate linear trend (slope) of values"""
        if len(values) < 2:
            return 0.0
        
        x = list(range(len(values)))
        y = values
        
        # Simple linear regression
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        # Calculate slope
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        return slope
    
    async def detect_correlation_anomaly(self, metrics: Dict[str, float]) -> List[str]:
        """Detect anomalies in metric correlations"""
        try:
            anomalies = []
            
            # Define expected correlations
            expected_correlations = [
                ("cpu_usage", "memory_usage", 0.3),  # Positive correlation expected
                ("response_time", "error_rate", 0.5),  # Positive correlation expected
                ("throughput", "response_time", -0.4),  # Negative correlation expected
            ]
            
            # Get recent historical data for correlation analysis
            async with await database_service.get_connection() as db:
                for metric1, metric2, expected_corr in expected_correlations:
                    if metric1 not in metrics or metric2 not in metrics:
                        continue
                    
                    cursor = await db.execute("""
                        SELECT 
                            m1.metric_value as val1,
                            m2.metric_value as val2
                        FROM system_metrics m1
                        JOIN system_metrics m2 ON m1.timestamp = m2.timestamp
                        WHERE m1.metric_name = ? AND m2.metric_name = ?
                        AND m1.timestamp > datetime('now', '-1 hour')
                        ORDER BY m1.timestamp DESC
                        LIMIT 100
                    """, (metric1, metric2))
                    
                    rows = await cursor.fetchall()
                    if len(rows) < 20:
                        continue
                    
                    # Calculate correlation
                    values1 = [row[0] for row in rows]
                    values2 = [row[1] for row in rows]
                    
                    correlation = self._calculate_correlation(values1, values2)
                    
                    # Check if correlation deviates from expected
                    correlation_diff = abs(correlation - expected_corr)
                    if correlation_diff > 0.5:
                        anomalies.append(
                            f"Correlation anomaly: {metric1} vs {metric2} "
                            f"(actual: {correlation:.3f}, expected: {expected_corr:.3f})"
                        )
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting correlation anomalies: {e}")
            return []
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        sum_y2 = sum(y[i] ** 2 for i in range(n))
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    async def update_baseline(self, metric_name: str, value: float):
        """Update baseline with new data point"""
        if metric_name not in self.baseline_metrics:
            self.baseline_metrics[metric_name] = []
        
        # Add new value
        self.baseline_metrics[metric_name].append(value)
        
        # Keep only recent data (sliding window)
        max_samples = 1000
        if len(self.baseline_metrics[metric_name]) > max_samples:
            self.baseline_metrics[metric_name] = self.baseline_metrics[metric_name][-max_samples:]
        
        # Periodically recalculate thresholds
        if len(self.baseline_metrics[metric_name]) % 50 == 0:
            await self._calculate_thresholds()
    
    async def get_baseline_stats(self, metric_name: str) -> Optional[Dict[str, float]]:
        """Get baseline statistics for a metric"""
        if metric_name not in self.baseline_metrics:
            return None
        
        values = self.baseline_metrics[metric_name]
        if not values:
            return None
        
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "threshold": self.anomaly_thresholds.get(metric_name, 0.0)
        }
