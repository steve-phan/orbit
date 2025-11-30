"""
Tests for dynamic task generation (map-reduce).
"""

import pytest
from orbit.services.dynamic_task_service import DynamicTaskService
from uuid import uuid4


def test_template_interpolation():
    """Test template interpolation with item and index."""
    service = DynamicTaskService(None)  # type: ignore

    template = {
        "name": "task_{{index}}",
        "config": {
            "item_id": "{{item.id}}",
            "item_value": "{{item.value}}"
        }
    }

    context = {
        "index": 5,
        "item": {"id": "abc123", "value": "test"}
    }

    result = service._interpolate_template(template, context)

    assert result["name"] == "task_5"
    assert result["config"]["item_id"] == "abc123"
    assert result["config"]["item_value"] == "test"


def test_map_task_creation_structure():
    """Test map task group structure."""
    from orbit.models.dynamic_tasks import DynamicTaskGroup

    items = [1, 2, 3, 4, 5]
    task_template = {"action": "process", "value": "{{item}}"}

    task_group = DynamicTaskGroup(
        workflow_id=uuid4(),
        parent_task_name="map_numbers",
        task_type="map",
        items=items,
        task_template=task_template,
        total_tasks=len(items),
    )

    assert task_group.task_type == "map"
    assert task_group.total_tasks == 5
    assert len(task_group.items) == 5
    assert task_group.status == "pending"


def test_reduce_task_creation_structure():
    """Test reduce task group structure."""
    from orbit.models.dynamic_tasks import DynamicTaskGroup

    map_results = [10, 20, 30, 40, 50]
    reduce_template = {"action": "sum", "operation": "aggregate"}

    task_group = DynamicTaskGroup(
        workflow_id=uuid4(),
        parent_task_name="reduce_sum",
        task_type="reduce",
        items=map_results,
        task_template=reduce_template,
        total_tasks=1,
    )

    assert task_group.task_type == "reduce"
    assert task_group.total_tasks == 1
    assert len(task_group.items) == 5


def test_progress_calculation():
    """Test progress percentage calculation."""
    from orbit.models.dynamic_tasks import DynamicTaskGroup

    task_group = DynamicTaskGroup(
        workflow_id=uuid4(),
        parent_task_name="test",
        task_type="map",
        items=[1, 2, 3, 4, 5],
        task_template={},
        total_tasks=5,
    )

    # No tasks completed
    assert task_group.progress_percentage() == 0.0

    # 2 tasks completed
    task_group.completed_tasks = 2
    assert task_group.progress_percentage() == 40.0

    # All tasks completed
    task_group.completed_tasks = 5
    assert task_group.progress_percentage() == 100.0


def test_map_reduce_pattern():
    """Test map-reduce pattern conceptually."""
    # Map phase: process each item
    items = [1, 2, 3, 4, 5]
    map_results = [item * 2 for item in items]  # Double each number

    assert map_results == [2, 4, 6, 8, 10]

    # Reduce phase: aggregate results
    reduce_result = sum(map_results)

    assert reduce_result == 30


def test_nested_item_interpolation():
    """Test interpolation with nested item properties."""
    service = DynamicTaskService(None)  # type: ignore

    template = {
        "user_id": "{{item.user.id}}",
        "user_name": "{{item.user.name}}",
        "action": "process_{{item.action_type}}"
    }

    context = {
        "item": {
            "user": {"id": "user123", "name": "John"},
            "action_type": "payment"
        }
    }

    result = service._interpolate_template(template, context)

    assert result["user_id"] == "user123"
    assert result["user_name"] == "John"
    assert result["action"] == "process_payment"


def test_array_processing_simulation():
    """Test array processing simulation."""
    # Simulate processing an array of files
    files = [
        {"name": "file1.txt", "size": 100},
        {"name": "file2.txt", "size": 200},
        {"name": "file3.txt", "size": 150},
    ]

    # Map: process each file
    processed = []
    for idx, file in enumerate(files):
        result = {
            "index": idx,
            "name": file["name"],
            "processed_size": file["size"] * 2,  # Simulate processing
        }
        processed.append(result)

    assert len(processed) == 3
    assert processed[0]["processed_size"] == 200
    assert processed[1]["processed_size"] == 400

    # Reduce: aggregate
    total_size = sum(p["processed_size"] for p in processed)
    assert total_size == 900
