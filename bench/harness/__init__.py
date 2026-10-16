"""Benchmark harness package (T12.1)."""

from bench.harness.runner import run_benchmark
from bench.harness.scorer import BenchmarkScorer, ExecutionResult, ObservedAction, ObservedEscalation, ScoreResult
from bench.harness.report import compute_metrics, generate_markdown_report, save_reports

__all__ = [
    "run_benchmark",
    "BenchmarkScorer",
    "ExecutionResult",
    "ObservedAction",
    "ObservedEscalation",
    "ScoreResult",
    "compute_metrics",
    "generate_markdown_report",
    "save_reports",
]
