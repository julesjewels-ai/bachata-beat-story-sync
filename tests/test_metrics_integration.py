"""
Integration tests for PipelineMetrics tracking.
"""

import json
import os
import shutil
import uuid
from datetime import UTC, datetime

import pytest
from src.core.models import PipelineMetrics
from src.core.repository import FileSystemRepository
from src.services.metrics import PipelineMetricsService

METRICS_DIR = ".test_metrics"


@pytest.fixture
def metrics_repo():
    """Provides a fresh FileSystemRepository for PipelineMetrics."""
    if os.path.exists(METRICS_DIR):
        shutil.rmtree(METRICS_DIR)

    repo = FileSystemRepository[PipelineMetrics](METRICS_DIR, PipelineMetrics)
    yield repo

    if os.path.exists(METRICS_DIR):
        shutil.rmtree(METRICS_DIR)


@pytest.fixture
def metrics_service(metrics_repo):
    """Provides the PipelineMetricsService initialized with the test repo."""
    return PipelineMetricsService(metrics_repo)


def test_record_and_get_metrics(metrics_service):
    """Test full flow: from service layer interface to file system storage."""

    run_id = str(uuid.uuid4())
    test_metrics = PipelineMetrics(
        id=run_id,
        audio_path="dummy_audio.wav",
        video_clips_count=10,
        montage_clips_count=5,
        broll_clips_count=2,
        duration_seconds=60.5,
        execution_time_seconds=12.3,
        timestamp=datetime.now(UTC).isoformat()
    )

    # Act: Record the metrics via service
    metrics_service.record_metrics(test_metrics)

    # Assert: Verify file exists on disk
    file_path = os.path.join(METRICS_DIR, f"{run_id}.json")
    assert os.path.exists(file_path), "Metrics file was not created on disk."

    # Assert: Content is valid JSON and matches
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["id"] == run_id
    assert data["audio_path"] == "dummy_audio.wav"
    assert data["execution_time_seconds"] == 12.3

    # Act: Retrieve metrics via service
    retrieved_metrics = metrics_service.get_metrics(run_id)

    # Assert: The retrieved object matches the saved model
    assert retrieved_metrics is not None
    assert retrieved_metrics.id == run_id
    assert retrieved_metrics.video_clips_count == 10


def test_get_nonexistent_metrics(metrics_service):
    """Test retrieving a run ID that doesn't exist returns None."""
    result = metrics_service.get_metrics("non-existent-id")
    assert result is None
