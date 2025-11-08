"""
Performance Regression Detection

Tracks performance baselines and detects regressions in:
- Latency
- Memory usage
- Throughput
- CPU/Memory/I/O profiling
"""

import json
import time
import subprocess
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from app.logger import logger


class MetricType(str, Enum):
    """Performance metric types"""
    LATENCY = "latency"       # milliseconds
    MEMORY = "memory"         # MB
    THROUGHPUT = "throughput"  # ops/sec
    CPU = "cpu"               # %
    IO = "io"                 # MB/s


@dataclass
class BenchmarkBaseline:
    """Baseline performance metrics for a function/operation"""
    name: str
    latency_ms: float  # Average latency
    memory_mb: float   # Peak memory
    throughput_ops_sec: float  # Operations per second
    timestamp: datetime
    runs: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "latency_ms": self.latency_ms,
            "memory_mb": self.memory_mb,
            "throughput_ops_sec": self.throughput_ops_sec,
            "timestamp": self.timestamp.isoformat(),
            "runs": self.runs,
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single run"""
    name: str
    latency_ms: float
    memory_mb: float
    throughput_ops_sec: float
    cpu_percent: float = 0.0
    io_read_mb: float = 0.0
    io_write_mb: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "latency_ms": self.latency_ms,
            "memory_mb": self.memory_mb,
            "throughput_ops_sec": self.throughput_ops_sec,
            "cpu_percent": self.cpu_percent,
            "io_read_mb": self.io_read_mb,
            "io_write_mb": self.io_write_mb,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RegressionReport:
    """Performance regression analysis report"""
    timestamp: datetime
    baseline_metrics: Dict[str, BenchmarkBaseline]
    current_metrics: Dict[str, PerformanceMetrics]
    regressions: List[Dict[str, Any]] = field(default_factory=list)
    improvements: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "baseline_metrics": {k: v.to_dict() for k, v in self.baseline_metrics.items()},
            "current_metrics": {k: v.to_dict() for k, v in self.current_metrics.items()},
            "regressions": self.regressions,
            "improvements": self.improvements,
            "regression_count": len(self.regressions),
            "improvement_count": len(self.improvements),
        }


class PerformanceRegressionDetector:
    """Detect and report performance regressions"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.baseline_storage = self.config.get(
            "baseline_storage",
            "cache/performance_baselines.json"
        )
        self.baselines: Dict[str, BenchmarkBaseline] = {}
        self.current_metrics: Dict[str, PerformanceMetrics] = {}
        self.report: Optional[RegressionReport] = None
        
        # Regression thresholds
        self.latency_threshold = self.config.get("threshold_latency_regression", 10) / 100.0
        self.memory_threshold = self.config.get("threshold_memory_regression", 20) / 100.0
        self.throughput_threshold = self.config.get("threshold_throughput_regression", 5) / 100.0
        
        # Features
        self.cpu_profiling = self.config.get("cpu_profiling", True)
        self.memory_profiling = self.config.get("memory_profiling", True)
        self.io_profiling = self.config.get("io_profiling", True)
        
        self._load_baselines()
    
    def _load_baselines(self):
        """Load baseline metrics from storage"""
        try:
            path = Path(self.baseline_storage)
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    for name, baseline_data in data.items():
                        baseline_data["timestamp"] = datetime.fromisoformat(baseline_data["timestamp"])
                        self.baselines[name] = BenchmarkBaseline(**baseline_data)
                logger.info(f"Loaded {len(self.baselines)} performance baselines")
        except Exception as e:
            logger.warning(f"Failed to load baselines: {e}")
    
    def _save_baselines(self):
        """Save baseline metrics to storage"""
        try:
            path = Path(self.baseline_storage)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {name: baseline.to_dict() for name, baseline in self.baselines.items()}
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save baselines: {e}")
    
    async def benchmark(self, name: str, test_func, runs: int = 5) -> BenchmarkBaseline:
        """Run a benchmark and create baseline"""
        latencies = []
        memory_peaks = []
        
        for i in range(runs):
            start_time = time.time()
            start_memory = self._get_memory_usage()
            
            # Run test
            result = test_func()
            
            latency = (time.time() - start_time) * 1000  # Convert to ms
            memory_peak = self._get_memory_usage()
            
            latencies.append(latency)
            memory_peaks.append(memory_peak)
        
        baseline = BenchmarkBaseline(
            name=name,
            latency_ms=sum(latencies) / len(latencies),
            memory_mb=max(memory_peaks),
            throughput_ops_sec=runs / sum(latencies) * 1000,
            timestamp=datetime.now(),
            runs=runs,
        )
        
        self.baselines[name] = baseline
        self._save_baselines()
        
        return baseline
    
    async def measure_performance(self, name: str, test_func, duration_sec: float = 10) -> PerformanceMetrics:
        """Measure performance of a function"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        operations = 0
        
        # Run function for specified duration
        while time.time() - start_time < duration_sec:
            test_func()
            operations += 1
        
        latency_ms = ((time.time() - start_time) / operations) * 1000
        memory_mb = self._get_memory_usage() - start_memory
        throughput = operations / (time.time() - start_time)
        
        metrics = PerformanceMetrics(
            name=name,
            latency_ms=latency_ms,
            memory_mb=max(0, memory_mb),
            throughput_ops_sec=throughput,
        )
        
        self.current_metrics[name] = metrics
        return metrics
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    async def detect_regressions(self) -> RegressionReport:
        """Compare current metrics against baselines and detect regressions"""
        regressions = []
        improvements = []
        
        for name, current in self.current_metrics.items():
            baseline = self.baselines.get(name)
            if not baseline:
                continue
            
            # Check latency
            latency_diff = (current.latency_ms - baseline.latency_ms) / baseline.latency_ms
            if latency_diff > self.latency_threshold:
                regressions.append({
                    "type": "latency",
                    "name": name,
                    "baseline": baseline.latency_ms,
                    "current": current.latency_ms,
                    "change_percent": latency_diff * 100,
                    "threshold": self.latency_threshold * 100,
                    "severity": "HIGH" if latency_diff > self.latency_threshold * 2 else "MEDIUM",
                })
            elif latency_diff < -0.05:  # 5% improvement
                improvements.append({
                    "type": "latency",
                    "name": name,
                    "baseline": baseline.latency_ms,
                    "current": current.latency_ms,
                    "improvement_percent": abs(latency_diff) * 100,
                })
            
            # Check memory
            memory_diff = (current.memory_mb - baseline.memory_mb) / baseline.memory_mb
            if memory_diff > self.memory_threshold:
                regressions.append({
                    "type": "memory",
                    "name": name,
                    "baseline": baseline.memory_mb,
                    "current": current.memory_mb,
                    "change_percent": memory_diff * 100,
                    "threshold": self.memory_threshold * 100,
                    "severity": "CRITICAL" if memory_diff > self.memory_threshold * 2 else "HIGH",
                })
            
            # Check throughput
            throughput_diff = (baseline.throughput_ops_sec - current.throughput_ops_sec) / baseline.throughput_ops_sec
            if throughput_diff > self.throughput_threshold:
                regressions.append({
                    "type": "throughput",
                    "name": name,
                    "baseline": baseline.throughput_ops_sec,
                    "current": current.throughput_ops_sec,
                    "change_percent": throughput_diff * 100,
                    "threshold": self.throughput_threshold * 100,
                    "severity": "MEDIUM",
                })
        
        self.report = RegressionReport(
            timestamp=datetime.now(),
            baseline_metrics=self.baselines,
            current_metrics=self.current_metrics,
            regressions=regressions,
            improvements=improvements,
        )
        
        return self.report
    
    def has_critical_regressions(self) -> bool:
        """Check if there are critical regressions"""
        if not self.report:
            return False
        
        critical = [r for r in self.report.regressions if r.get("severity") in ["CRITICAL", "HIGH"]]
        return len(critical) > 0
    
    async def profile_cpu(self, test_func, duration_sec: float = 10):
        """Profile CPU usage with cProfile"""
        import cProfile
        import pstats
        import io
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        start = time.time()
        while time.time() - start < duration_sec:
            test_func()
        
        profiler.disable()
        
        # Get statistics
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
        ps.print_stats(10)
        
        return s.getvalue()
    
    async def profile_memory(self, test_func, duration_sec: float = 10):
        """Profile memory usage with tracemalloc"""
        import tracemalloc
        
        tracemalloc.start()
        
        start = time.time()
        while time.time() - start < duration_sec:
            test_func()
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {
            "current_mb": current / 1024 / 1024,
            "peak_mb": peak / 1024 / 1024,
        }
    
    async def profile_io(self, test_func, duration_sec: float = 10):
        """Profile I/O operations"""
        process = psutil.Process()
        
        io_before = process.io_counters()
        start_time = time.time()
        
        while time.time() - start_time < duration_sec:
            test_func()
        
        io_after = process.io_counters()
        
        return {
            "read_bytes": io_after.read_bytes - io_before.read_bytes,
            "write_bytes": io_after.write_bytes - io_before.write_bytes,
            "read_count": io_after.read_count - io_before.read_count,
            "write_count": io_after.write_count - io_before.write_count,
        }
    
    def export_report(self, format: str = "json") -> str:
        """Export regression report"""
        if not self.report:
            return "{}"
        
        if format == "json":
            return json.dumps(self.report.to_dict(), indent=2)
        else:
            return self._generate_text_report()
    
    def _generate_text_report(self) -> str:
        """Generate text format report"""
        if not self.report:
            return ""
        
        report = ["=" * 80]
        report.append("PERFORMANCE REGRESSION REPORT")
        report.append("=" * 80)
        report.append(f"Timestamp: {self.report.timestamp}")
        report.append("")
        
        if self.report.regressions:
            report.append("REGRESSIONS DETECTED:")
            for reg in self.report.regressions:
                report.append(f"  [{reg['severity']}] {reg['type'].upper()}: {reg['name']}")
                report.append(f"    Baseline: {reg['baseline']:.2f}")
                report.append(f"    Current:  {reg['current']:.2f}")
                report.append(f"    Change:   {reg['change_percent']:.1f}%")
                report.append("")
        else:
            report.append("No regressions detected!")
        
        if self.report.improvements:
            report.append("IMPROVEMENTS DETECTED:")
            for imp in self.report.improvements:
                report.append(f"  {imp['type'].upper()}: {imp['name']}")
                report.append(f"    Improvement: {imp['improvement_percent']:.1f}%")
                report.append("")
        
        report.append("=" * 80)
        return "\n".join(report)
