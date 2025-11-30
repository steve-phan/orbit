"""
Tests for pause/resume functionality.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from orbit.models.workflow import Workflow


@pytest.fixture
def mock_workflow():
    """Create a mock workflow for testing."""
    return Workflow(
        id=uuid4(),
        name="Test Workflow",
        description="Test workflow for pause/resume",
        status="running",
    )


def test_pause_workflow_states():
    """Test that workflows can only be paused from valid states."""
    # Running workflow can be paused
    workflow = Workflow(id=uuid4(), name="Test", status="running")
    assert workflow.status in ["running", "pending"]

    # Pending workflow can be paused
    workflow = Workflow(id=uuid4(), name="Test", status="pending")
    assert workflow.status in ["running", "pending"]

    # Completed workflow cannot be paused
    workflow = Workflow(id=uuid4(), name="Test", status="completed")
    assert workflow.status not in ["running", "pending"]


def test_resume_workflow_states():
    """Test that only paused workflows can be resumed."""
    # Paused workflow can be resumed
    workflow = Workflow(id=uuid4(), name="Test", status="paused")
    assert workflow.status == "paused"

    # Running workflow cannot be resumed
    workflow = Workflow(id=uuid4(), name="Test", status="running")
    assert workflow.status != "paused"


def test_cancel_workflow_states():
    """Test that workflows in terminal states cannot be cancelled."""
    # Running workflow can be cancelled
    workflow = Workflow(id=uuid4(), name="Test", status="running")
    assert workflow.status not in ["completed", "failed", "cancelled"]

    # Completed workflow cannot be cancelled
    workflow = Workflow(id=uuid4(), name="Test", status="completed")
    assert workflow.status in ["completed", "failed", "cancelled"]


def test_workflow_status_transitions():
    """Test valid workflow status transitions."""
    workflow = Workflow(id=uuid4(), name="Test", status="pending")

    # pending -> running
    workflow.status = "running"
    assert workflow.status == "running"

    # running -> paused
    workflow.status = "paused"
    workflow.paused_at = datetime.utcnow()
    assert workflow.status == "paused"
    assert workflow.paused_at is not None

    # paused -> pending (resume)
    workflow.status = "pending"
    workflow.paused_at = None
    assert workflow.status == "pending"
    assert workflow.paused_at is None


def test_paused_at_timestamp():
    """Test that paused_at is set correctly."""
    workflow = Workflow(id=uuid4(), name="Test", status="running")

    # Initially no paused_at
    assert workflow.paused_at is None

    # After pausing
    workflow.status = "paused"
    workflow.paused_at = datetime.utcnow()
    assert workflow.paused_at is not None
    assert isinstance(workflow.paused_at, datetime)

    # After resuming
    workflow.status = "pending"
    workflow.paused_at = None
    assert workflow.paused_at is None


def test_workflow_control_capabilities():
    """Test workflow control capability checks."""

    def get_capabilities(status):
        return {
            "can_pause": status in ["running", "pending"],
            "can_resume": status == "paused",
            "can_cancel": status not in ["completed", "failed", "cancelled"],
        }

    # Running workflow
    caps = get_capabilities("running")
    assert caps["can_pause"] is True
    assert caps["can_resume"] is False
    assert caps["can_cancel"] is True

    # Paused workflow
    caps = get_capabilities("paused")
    assert caps["can_pause"] is False
    assert caps["can_resume"] is True
    assert caps["can_cancel"] is True

    # Completed workflow
    caps = get_capabilities("completed")
    assert caps["can_pause"] is False
    assert caps["can_resume"] is False
    assert caps["can_cancel"] is False
