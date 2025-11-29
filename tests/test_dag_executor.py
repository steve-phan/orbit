import pytest
from uuid import uuid4
from orbit.services.dag_executor import DAGExecutor
from orbit.models.workflow import Task

def test_topological_sort_linear():
    """Test topological sort with linear dependencies."""
    tasks = [
        Task(id=uuid4(), workflow_id=uuid4(), name="A", action_type="test", dependencies=[]),
        Task(id=uuid4(), workflow_id=uuid4(), name="B", action_type="test", dependencies=["A"]),
        Task(id=uuid4(), workflow_id=uuid4(), name="C", action_type="test", dependencies=["B"]),
    ]
    
    result = DAGExecutor.topological_sort(tasks)
    
    assert len(result) == 3
    assert result[0] == ["A"]
    assert result[1] == ["B"]
    assert result[2] == ["C"]

def test_topological_sort_parallel():
    """Test topological sort with parallel tasks."""
    tasks = [
        Task(id=uuid4(), workflow_id=uuid4(), name="A", action_type="test", dependencies=[]),
        Task(id=uuid4(), workflow_id=uuid4(), name="B", action_type="test", dependencies=[]),
        Task(id=uuid4(), workflow_id=uuid4(), name="C", action_type="test", dependencies=["A", "B"]),
    ]
    
    result = DAGExecutor.topological_sort(tasks)
    
    assert len(result) == 2
    assert set(result[0]) == {"A", "B"}
    assert result[1] == ["C"]

def test_topological_sort_complex():
    """Test topological sort with complex dependencies."""
    tasks = [
        Task(id=uuid4(), workflow_id=uuid4(), name="fetch", action_type="test", dependencies=[]),
        Task(id=uuid4(), workflow_id=uuid4(), name="process1", action_type="test", dependencies=["fetch"]),
        Task(id=uuid4(), workflow_id=uuid4(), name="process2", action_type="test", dependencies=["fetch"]),
        Task(id=uuid4(), workflow_id=uuid4(), name="merge", action_type="test", dependencies=["process1", "process2"]),
        Task(id=uuid4(), workflow_id=uuid4(), name="report", action_type="test", dependencies=["merge"]),
    ]
    
    result = DAGExecutor.topological_sort(tasks)
    
    assert len(result) == 4
    assert result[0] == ["fetch"]
    assert set(result[1]) == {"process1", "process2"}
    assert result[2] == ["merge"]
    assert result[3] == ["report"]

def test_circular_dependency_detection():
    """Test that circular dependencies are detected."""
    tasks = [
        Task(id=uuid4(), workflow_id=uuid4(), name="A", action_type="test", dependencies=["B"]),
        Task(id=uuid4(), workflow_id=uuid4(), name="B", action_type="test", dependencies=["A"]),
    ]
    
    with pytest.raises(ValueError, match="Circular dependency"):
        DAGExecutor.topological_sort(tasks)

def test_missing_dependency():
    """Test that missing dependencies are detected."""
    tasks = [
        Task(id=uuid4(), workflow_id=uuid4(), name="A", action_type="test", dependencies=["NonExistent"]),
    ]
    
    with pytest.raises(ValueError, match="non-existent"):
        DAGExecutor.topological_sort(tasks)
