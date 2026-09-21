"""
Telemetry and metrics service for tracking pipeline executions.
"""

from typing import Protocol

from src.core.models import PipelineMetrics
from src.core.repository import ModelRepository


class MetricsServiceProtocol(Protocol):
    """
    Protocol for recording pipeline metrics.
    """

    def record_metrics(self, metrics: PipelineMetrics) -> None:
        """Records telemetry data for a single pipeline run."""
        ...

    def get_metrics(self, run_id: str) -> PipelineMetrics | None:
        """Retrieves metrics for a specific run ID."""
        ...


class PipelineMetricsService:
    """
    Concrete implementation of metrics service.
    """

    def __init__(self, repository: ModelRepository[PipelineMetrics]) -> None:
        self.repository = repository

    def record_metrics(self, metrics: PipelineMetrics) -> None:
        """
        Saves the pipeline execution metrics to the repository.
        """
        self.repository.save(metrics)

    def get_metrics(self, run_id: str) -> PipelineMetrics | None:
        """
        Retrieves the metrics for a specific run ID.
        """
        return self.repository.get(run_id)
