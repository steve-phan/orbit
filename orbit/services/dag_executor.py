from collections import deque

from orbit.models.workflow import Task


class DAGExecutor:
    """
    Directed Acyclic Graph executor for task orchestration.
    Implements topological sorting to determine execution order.
    """

    @staticmethod
    def topological_sort(tasks: list[Task]) -> list[list[str]]:
        """
        Perform topological sort on tasks to determine execution order.
        Returns a list of execution levels (tasks that can run in parallel).

        Args:
            tasks: List of Task objects with dependencies

        Returns:
            List of lists, where each inner list contains task names that can execute in parallel

        Raises:
            ValueError: If a circular dependency is detected
        """
        # Build adjacency list and in-degree map
        task_map = {task.name: task for task in tasks}
        in_degree: dict[str, int] = {task.name: 0 for task in tasks}
        adjacency: dict[str, list[str]] = {task.name: [] for task in tasks}

        # Calculate in-degrees and build adjacency list
        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_map:
                    raise ValueError(
                        f"Task '{task.name}' depends on non-existent task '{dep}'"
                    )
                adjacency[dep].append(task.name)
                in_degree[task.name] += 1

        # Find all tasks with no dependencies (in-degree = 0)
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        execution_levels: list[list[str]] = []
        processed_count = 0

        while queue:
            # All tasks in current queue can execute in parallel
            current_level = list(queue)
            execution_levels.append(current_level)
            queue.clear()

            # Process current level
            for task_name in current_level:
                processed_count += 1
                # Reduce in-degree for dependent tasks
                for dependent in adjacency[task_name]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # Check for circular dependencies
        if processed_count != len(tasks):
            raise ValueError("Circular dependency detected in workflow")

        return execution_levels

    @staticmethod
    def validate_dag(tasks: list[Task]) -> bool:
        """
        Validate that the task graph is a valid DAG.

        Args:
            tasks: List of Task objects

        Returns:
            True if valid, raises ValueError otherwise
        """
        try:
            DAGExecutor.topological_sort(tasks)
            return True
        except ValueError as e:
            raise ValueError(f"Invalid DAG: {str(e)}")
