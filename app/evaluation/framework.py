"""
FreEco.ai Platform - Evaluation Framework
Enhanced OpenManus with comprehensive evaluation and benchmarking

This module provides evaluation capabilities:
- Quality metrics (accuracy, precision, recall, F1)
- Benchmark suite for standard test cases
- A/B testing for comparing approaches
- Performance tracking over time
- Comprehensive evaluation reports
- Continuous evaluation

Part of Enhancement #5: Performance, UX & Evaluation
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Evaluation metric types"""

    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    SUCCESS_RATE = "success_rate"
    LATENCY = "latency"
    THROUGHPUT = "throughput"


@dataclass
class EvaluationMetrics:
    """Evaluation metrics container"""

    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    throughput_per_sec: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "throughput_per_sec": self.throughput_per_sec,
        }

    def __str__(self) -> str:
        return (
            f"Accuracy: {self.accuracy:.2%}, "
            f"Precision: {self.precision:.2%}, "
            f"Recall: {self.recall:.2%}, "
            f"F1: {self.f1_score:.2%}, "
            f"Success Rate: {self.success_rate:.2%}, "
            f"Latency: {self.avg_latency_ms:.1f}ms"
        )


@dataclass
class BenchmarkCase:
    """Benchmark test case"""

    name: str
    description: str
    input_data: Any
    expected_output: Any
    category: str = "general"
    difficulty: str = "medium"  # easy, medium, hard

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "difficulty": self.difficulty,
        }


@dataclass
class BenchmarkResult:
    """Result of a benchmark test"""

    case: BenchmarkCase
    actual_output: Any
    success: bool
    latency_ms: float
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "case": self.case.to_dict(),
            "success": self.success,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ABTestResult:
    """A/B test comparison result"""

    variant_a_name: str
    variant_b_name: str
    variant_a_metrics: EvaluationMetrics
    variant_b_metrics: EvaluationMetrics
    winner: str  # "A", "B", or "tie"
    confidence: float  # 0.0 to 1.0
    sample_size: int

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "variant_a": {
                "name": self.variant_a_name,
                "metrics": self.variant_a_metrics.to_dict(),
            },
            "variant_b": {
                "name": self.variant_b_name,
                "metrics": self.variant_b_metrics.to_dict(),
            },
            "winner": self.winner,
            "confidence": self.confidence,
            "sample_size": self.sample_size,
        }

    def __str__(self) -> str:
        return (
            f"A/B Test: {self.variant_a_name} vs {self.variant_b_name}\n"
            f"Winner: {self.winner} (confidence: {self.confidence:.2%})\n"
            f"Sample size: {self.sample_size}\n"
            f"Variant A: {self.variant_a_metrics}\n"
            f"Variant B: {self.variant_b_metrics}"
        )


@dataclass
class PerformanceHistory:
    """Performance tracking over time"""

    model_name: str
    metrics_history: List[Tuple[datetime, EvaluationMetrics]] = field(
        default_factory=list
    )

    def add_metrics(self, metrics: EvaluationMetrics):
        """Add metrics to history"""
        self.metrics_history.append((datetime.now(), metrics))

    def get_trend(self, metric_name: str) -> str:
        """Get trend for a specific metric"""
        if len(self.metrics_history) < 2:
            return "insufficient_data"

        values = [getattr(m, metric_name) for _, m in self.metrics_history]

        # Simple trend: compare first half to second half
        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / mid if mid > 0 else 0
        second_half_avg = (
            sum(values[mid:]) / (len(values) - mid) if len(values) > mid else 0
        )

        if second_half_avg > first_half_avg * 1.05:
            return "improving"
        elif second_half_avg < first_half_avg * 0.95:
            return "declining"
        else:
            return "stable"


@dataclass
class EvaluationReport:
    """Comprehensive evaluation report"""

    timestamp: datetime
    model_name: str
    metrics: EvaluationMetrics
    benchmark_results: List[BenchmarkResult]
    total_cases: int
    passed_cases: int
    failed_cases: int
    avg_latency_ms: float

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "model_name": self.model_name,
            "metrics": self.metrics.to_dict(),
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "pass_rate": self.passed_cases / self.total_cases
            if self.total_cases > 0
            else 0.0,
            "avg_latency_ms": self.avg_latency_ms,
        }

    def __str__(self) -> str:
        pass_rate = (
            self.passed_cases / self.total_cases if self.total_cases > 0 else 0.0
        )
        return (
            f"Evaluation Report - {self.model_name}\n"
            f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Pass Rate: {pass_rate:.2%} ({self.passed_cases}/{self.total_cases})\n"
            f"Avg Latency: {self.avg_latency_ms:.1f}ms\n"
            f"{self.metrics}"
        )


class EvaluationFramework:
    """
    Comprehensive evaluation and benchmarking framework

    Features:
    - Quality metrics calculation
    - Benchmark test suites
    - A/B testing
    - Performance tracking
    - Evaluation reports
    - Continuous evaluation

    Example:
        framework = EvaluationFramework()

        # Add benchmark cases
        framework.add_benchmark_case(
            name="simple_query",
            description="Test simple query handling",
            input_data="What is 2+2?",
            expected_output="4",
        )

        # Run benchmarks
        results = framework.run_benchmark(my_model)

        # Calculate metrics
        metrics = framework.calculate_metrics(predictions, actuals)

        # A/B test
        comparison = framework.ab_test(model_a, model_b, test_cases)
    """

    def __init__(self):
        """Initialize evaluation framework"""
        self.benchmark_suite: List[BenchmarkCase] = []
        self.performance_history: Dict[str, PerformanceHistory] = {}
        self.evaluation_history: List[EvaluationReport] = []

        # Initialize with default benchmark cases
        self._init_default_benchmarks()

    def _init_default_benchmarks(self):
        """Initialize default benchmark cases"""
        # Simple reasoning
        self.add_benchmark_case(
            name="simple_math",
            description="Simple arithmetic",
            input_data="What is 15 + 27?",
            expected_output="42",
            category="reasoning",
            difficulty="easy",
        )

        # Planning
        self.add_benchmark_case(
            name="task_planning",
            description="Break down a complex task",
            input_data="Plan how to organize a vegan dinner party for 10 people",
            expected_output="multi_step_plan",
            category="planning",
            difficulty="medium",
        )

        # Ethical decision
        self.add_benchmark_case(
            name="ethical_decision",
            description="Make an ethical decision",
            input_data="Should I buy leather shoes or vegan alternatives?",
            expected_output="vegan_alternatives",
            category="ethics",
            difficulty="easy",
        )

    def add_benchmark_case(
        self,
        name: str,
        description: str,
        input_data: Any,
        expected_output: Any,
        category: str = "general",
        difficulty: str = "medium",
    ):
        """
        Add a benchmark test case

        Args:
            name: Test case name
            description: Test case description
            input_data: Input for the test
            expected_output: Expected output
            category: Test category
            difficulty: Test difficulty
        """
        case = BenchmarkCase(
            name=name,
            description=description,
            input_data=input_data,
            expected_output=expected_output,
            category=category,
            difficulty=difficulty,
        )

        self.benchmark_suite.append(case)
        logger.info(f"Added benchmark case: {name}")

    def run_benchmark(
        self,
        model_func: Callable[[Any], Any],
        category: Optional[str] = None,
    ) -> List[BenchmarkResult]:
        """
        Run benchmark suite on a model

        Args:
            model_func: Function that takes input and returns output
            category: Optional category filter

        Returns:
            List of BenchmarkResult objects
        """
        results = []

        # Filter cases by category if specified
        cases = self.benchmark_suite
        if category:
            cases = [c for c in cases if c.category == category]

        for case in cases:
            start_time = time.time()
            success = False
            actual_output = None
            error = None

            try:
                actual_output = model_func(case.input_data)
                success = self._check_output(actual_output, case.expected_output)

            except Exception as e:
                error = str(e)
                logger.error(f"Benchmark case '{case.name}' failed: {e}")

            latency_ms = (time.time() - start_time) * 1000

            result = BenchmarkResult(
                case=case,
                actual_output=actual_output,
                success=success,
                latency_ms=latency_ms,
                error=error,
            )

            results.append(result)

        return results

    def _check_output(self, actual: Any, expected: Any) -> bool:
        """Check if actual output matches expected"""
        # Handle special expected values
        if expected == "multi_step_plan":
            # Check if output contains multiple steps
            return isinstance(actual, (list, str)) and len(str(actual)) > 50

        elif expected == "vegan_alternatives":
            # Check if output mentions vegan
            return "vegan" in str(actual).lower()

        # Direct comparison
        return str(actual).strip() == str(expected).strip()

    def calculate_metrics(
        self,
        predictions: List[Any],
        actuals: List[Any],
        latencies_ms: Optional[List[float]] = None,
    ) -> EvaluationMetrics:
        """
        Calculate evaluation metrics

        Args:
            predictions: List of predicted values
            actuals: List of actual values
            latencies_ms: Optional list of latencies

        Returns:
            EvaluationMetrics object
        """
        if len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must have same length")

        n = len(predictions)

        # Calculate success rate
        successes = sum(
            1 for p, a in zip(predictions, actuals) if self._check_output(p, a)
        )
        success_rate = successes / n if n > 0 else 0.0

        # For binary classification metrics, convert to binary
        binary_preds = [
            1 if self._check_output(p, a) else 0 for p, a in zip(predictions, actuals)
        ]
        binary_actuals = [1] * n  # Assume all actuals are correct

        # Calculate precision, recall, F1
        true_positives = sum(binary_preds)
        false_positives = (
            0  # In our case, all predictions are either correct or incorrect
        )
        false_negatives = n - true_positives

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )

        if precision + recall > 0:
            f1_score = 2 * (precision * recall) / (precision + recall)
        else:
            f1_score = 0.0

        # Calculate latency metrics
        avg_latency_ms = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0
        throughput = 1000 / avg_latency_ms if avg_latency_ms > 0 else 0.0

        return EvaluationMetrics(
            accuracy=success_rate,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            success_rate=success_rate,
            avg_latency_ms=avg_latency_ms,
            throughput_per_sec=throughput,
        )

    def ab_test(
        self,
        variant_a: Callable[[Any], Any],
        variant_b: Callable[[Any], Any],
        test_cases: Optional[List[BenchmarkCase]] = None,
        variant_a_name: str = "Variant A",
        variant_b_name: str = "Variant B",
    ) -> ABTestResult:
        """
        Run A/B test comparing two variants

        Args:
            variant_a: First variant function
            variant_b: Second variant function
            test_cases: Test cases (uses benchmark suite if None)
            variant_a_name: Name for variant A
            variant_b_name: Name for variant B

        Returns:
            ABTestResult with comparison
        """
        if test_cases is None:
            test_cases = self.benchmark_suite

        # Run both variants
        results_a = self.run_benchmark(variant_a)
        results_b = self.run_benchmark(variant_b)

        # Extract predictions and latencies
        preds_a = [r.actual_output for r in results_a]
        preds_b = [r.actual_output for r in results_b]
        actuals = [c.expected_output for c in test_cases]
        latencies_a = [r.latency_ms for r in results_a]
        latencies_b = [r.latency_ms for r in results_b]

        # Calculate metrics
        metrics_a = self.calculate_metrics(preds_a, actuals, latencies_a)
        metrics_b = self.calculate_metrics(preds_b, actuals, latencies_b)

        # Determine winner based on F1 score
        if metrics_a.f1_score > metrics_b.f1_score * 1.05:
            winner = "A"
            confidence = (metrics_a.f1_score - metrics_b.f1_score) / metrics_a.f1_score
        elif metrics_b.f1_score > metrics_a.f1_score * 1.05:
            winner = "B"
            confidence = (metrics_b.f1_score - metrics_a.f1_score) / metrics_b.f1_score
        else:
            winner = "tie"
            confidence = 1.0 - abs(metrics_a.f1_score - metrics_b.f1_score)

        return ABTestResult(
            variant_a_name=variant_a_name,
            variant_b_name=variant_b_name,
            variant_a_metrics=metrics_a,
            variant_b_metrics=metrics_b,
            winner=winner,
            confidence=min(1.0, confidence),
            sample_size=len(test_cases),
        )

    def track_performance(
        self,
        model_name: str,
        metrics: EvaluationMetrics,
    ):
        """
        Track performance over time

        Args:
            model_name: Name of the model
            metrics: Evaluation metrics
        """
        if model_name not in self.performance_history:
            self.performance_history[model_name] = PerformanceHistory(
                model_name=model_name
            )

        self.performance_history[model_name].add_metrics(metrics)
        logger.info(f"Tracked performance for {model_name}")

    def generate_report(
        self,
        model_name: str,
        benchmark_results: List[BenchmarkResult],
    ) -> EvaluationReport:
        """
        Generate comprehensive evaluation report

        Args:
            model_name: Name of the model
            benchmark_results: Results from benchmark run

        Returns:
            EvaluationReport object
        """
        total_cases = len(benchmark_results)
        passed_cases = sum(1 for r in benchmark_results if r.success)
        failed_cases = total_cases - passed_cases
        avg_latency = (
            sum(r.latency_ms for r in benchmark_results) / total_cases
            if total_cases > 0
            else 0.0
        )

        # Calculate metrics
        predictions = [r.actual_output for r in benchmark_results]
        actuals = [r.case.expected_output for r in benchmark_results]
        latencies = [r.latency_ms for r in benchmark_results]

        metrics = self.calculate_metrics(predictions, actuals, latencies)

        report = EvaluationReport(
            timestamp=datetime.now(),
            model_name=model_name,
            metrics=metrics,
            benchmark_results=benchmark_results,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            avg_latency_ms=avg_latency,
        )

        self.evaluation_history.append(report)

        return report

    def evaluate_continuously(
        self,
        model_func: Callable[[Any], Any],
        model_name: str,
    ) -> EvaluationReport:
        """
        Run continuous evaluation

        Args:
            model_func: Model function to evaluate
            model_name: Name of the model

        Returns:
            EvaluationReport
        """
        # Run benchmark
        results = self.run_benchmark(model_func)

        # Generate report
        report = self.generate_report(model_name, results)

        # Track performance
        self.track_performance(model_name, report.metrics)

        logger.info(f"Continuous evaluation complete for {model_name}")
        logger.info(str(report))

        return report


# Global evaluation framework instance
default_framework = EvaluationFramework()
