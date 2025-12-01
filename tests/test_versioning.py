"""
Tests for workflow versioning.
"""

from uuid import uuid4

from orbit.models.versioning import WorkflowVersion
from orbit.services.versioning_service import VersioningService


def test_checksum_calculation():
    """Test checksum calculation for workflow data."""
    service = VersioningService(None)  # type: ignore

    data1 = {"name": "test", "tasks": [{"name": "task1"}]}
    data2 = {"tasks": [{"name": "task1"}], "name": "test"}  # Same content, different order

    checksum1 = service._calculate_checksum(data1)
    checksum2 = service._calculate_checksum(data2)

    # Same content should produce same checksum
    assert checksum1 == checksum2

    # Different content should produce different checksum
    data3 = {"name": "different", "tasks": [{"name": "task1"}]}
    checksum3 = service._calculate_checksum(data3)
    assert checksum1 != checksum3


def test_diff_calculation_created():
    """Test diff calculation for new workflow."""
    service = VersioningService(None)  # type: ignore

    new_data = {"name": "test", "description": "A test workflow"}
    diff = service._calculate_diff(None, new_data)

    assert diff["change_type"] == "created"
    assert diff["added"] == new_data


def test_diff_calculation_modified():
    """Test diff calculation for modified workflow."""
    service = VersioningService(None)  # type: ignore

    old_data = {
        "name": "test",
        "description": "Old description",
        "tasks": ["task1"],
    }

    new_data = {
        "name": "test",
        "description": "New description",
        "tasks": ["task1", "task2"],
    }

    diff = service._calculate_diff(old_data, new_data)

    assert "modified" in diff
    assert "description" in diff["modified"]
    assert diff["modified"]["description"]["old"] == "Old description"
    assert diff["modified"]["description"]["new"] == "New description"


def test_diff_calculation_removed():
    """Test diff calculation for removed fields."""
    service = VersioningService(None)  # type: ignore

    old_data = {
        "name": "test",
        "description": "A description",
        "deprecated_field": "value",
    }

    new_data = {
        "name": "test",
        "description": "A description",
    }

    diff = service._calculate_diff(old_data, new_data)

    assert "removed" in diff
    assert "deprecated_field" in diff["removed"]
    assert diff["removed"]["deprecated_field"] == "value"


def test_workflow_version_model():
    """Test WorkflowVersion model creation."""
    version = WorkflowVersion(
        workflow_id=uuid4(),
        version_number=1,
        name="Test Workflow",
        workflow_data={"tasks": []},
        is_active=True,
        checksum="abc123",
    )

    assert version.version_number == 1
    assert version.is_active is True
    assert version.is_draft is False
    assert version.checksum == "abc123"


def test_version_number_increment():
    """Test version number incrementation logic."""
    # Simulate version progression
    versions = []

    for i in range(1, 6):
        version = WorkflowVersion(
            workflow_id=uuid4(),
            version_number=i,
            name=f"Version {i}",
            workflow_data={"version": i},
            checksum=f"checksum{i}",
        )
        versions.append(version)

    assert len(versions) == 5
    assert versions[0].version_number == 1
    assert versions[-1].version_number == 5


def test_version_tagging():
    """Test version tagging functionality."""
    version = WorkflowVersion(
        workflow_id=uuid4(),
        version_number=1,
        version_tag="v1.0.0",
        name="Tagged Version",
        workflow_data={"tasks": []},
        checksum="abc",
    )

    assert version.version_tag == "v1.0.0"


def test_draft_version():
    """Test draft version functionality."""
    draft = WorkflowVersion(
        workflow_id=uuid4(),
        version_number=2,
        name="Draft Version",
        workflow_data={"tasks": []},
        is_draft=True,
        is_active=False,
        checksum="draft123",
    )

    assert draft.is_draft is True
    assert draft.is_active is False
    assert draft.activated_at is None
