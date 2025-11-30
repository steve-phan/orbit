"""
Dynamic task generation service.
Implements map-reduce patterns for parallel processing.
"""

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.logging import get_logger
from orbit.models.dynamic_tasks import DynamicTaskGroup

logger = get_logger("services.dynamic_tasks")


class DynamicTaskService:
    """
    Service for dynamic task generation.
    Enables map-reduce patterns for parallel array processing.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_map_tasks(
        self,
        workflow_id: UUID,
        parent_task_name: str,
        items: list[Any],
        task_template: dict[str, Any],
    ) -> DynamicTaskGroup:
        """
        Create a map task group that processes each item in parallel.

        Args:
            workflow_id: Workflow UUID
            parent_task_name: Name of the map task
            items: List of items to process
            task_template: Template for each generated task

        Returns:
            Created DynamicTaskGroup
        """
        task_group = DynamicTaskGroup(
            workflow_id=workflow_id,
            parent_task_name=parent_task_name,
            task_type="map",
            items=items,
            task_template=task_template,
            total_tasks=len(items),
        )

        self.session.add(task_group)
        await self.session.commit()
        await self.session.refresh(task_group)

        logger.info(
            f"Created map task group: {parent_task_name} with {len(items)} items"
        )

        return task_group

    async def execute_map_tasks(
        self,
        task_group_id: UUID,
        executor_func: callable,
    ) -> list[Any]:
        """
        Execute all tasks in a map group in parallel.

        Args:
            task_group_id: DynamicTaskGroup UUID
            executor_func: Async function to execute for each item

        Returns:
            List of results
        """
        # Get task group
        statement = select(DynamicTaskGroup).where(DynamicTaskGroup.id == task_group_id)
        result = await self.session.exec(statement)
        task_group = result.first()

        if not task_group:
            raise ValueError(f"Task group {task_group_id} not found")

        # Update status
        task_group.status = "running"
        self.session.add(task_group)
        await self.session.commit()

        # Execute all items in parallel
        tasks = []
        for idx, item in enumerate(task_group.items):
            # Interpolate template with item
            task_config = self._interpolate_template(
                task_group.task_template, {"item": item, "index": idx}
            )
            tasks.append(executor_func(task_config))

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Update task group
        task_group.completed_tasks = len([r for r in results if not isinstance(r, Exception)])
        task_group.failed_tasks = len([r for r in results if isinstance(r, Exception)])
        task_group.results = [
            str(r) if isinstance(r, Exception) else r for r in results
        ]
        task_group.status = "completed" if task_group.failed_tasks == 0 else "failed"
        task_group.completed_at = datetime.utcnow()

        self.session.add(task_group)
        await self.session.commit()

        logger.info(
            f"Map task group completed: {task_group.completed_tasks}/{task_group.total_tasks} successful"
        )

        return task_group.results

    async def create_reduce_task(
        self,
        workflow_id: UUID,
        parent_task_name: str,
        map_results: list[Any],
        reduce_template: dict[str, Any],
    ) -> DynamicTaskGroup:
        """
        Create a reduce task that aggregates map results.

        Args:
            workflow_id: Workflow UUID
            parent_task_name: Name of the reduce task
            map_results: Results from map tasks
            reduce_template: Template for reduce task

        Returns:
            Created DynamicTaskGroup
        """
        task_group = DynamicTaskGroup(
            workflow_id=workflow_id,
            parent_task_name=parent_task_name,
            task_type="reduce",
            items=map_results,
            task_template=reduce_template,
            total_tasks=1,
        )

        self.session.add(task_group)
        await self.session.commit()
        await self.session.refresh(task_group)

        logger.info(f"Created reduce task: {parent_task_name}")

        return task_group

    async def execute_reduce_task(
        self,
        task_group_id: UUID,
        reducer_func: callable,
    ) -> Any:
        """
        Execute reduce task to aggregate results.

        Args:
            task_group_id: DynamicTaskGroup UUID
            reducer_func: Async function to reduce results

        Returns:
            Reduced result
        """
        # Get task group
        statement = select(DynamicTaskGroup).where(DynamicTaskGroup.id == task_group_id)
        result = await self.session.exec(statement)
        task_group = result.first()

        if not task_group:
            raise ValueError(f"Task group {task_group_id} not found")

        # Update status
        task_group.status = "running"
        self.session.add(task_group)
        await self.session.commit()

        # Execute reduce
        try:
            result = await reducer_func(task_group.items, task_group.task_template)

            task_group.results = [result]
            task_group.completed_tasks = 1
            task_group.status = "completed"

        except Exception as e:
            logger.error(f"Reduce task failed: {e}")
            task_group.failed_tasks = 1
            task_group.status = "failed"
            task_group.results = [str(e)]

        task_group.completed_at = datetime.utcnow()
        self.session.add(task_group)
        await self.session.commit()

        logger.info(f"Reduce task completed: {task_group.parent_task_name}")

        return task_group.results[0] if task_group.results else None

    def _interpolate_template(
        self, template: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Interpolate template with context variables.
        Supports nested properties like {{item.user.id}}.

        Args:
            template: Template dictionary
            context: Context variables

        Returns:
            Interpolated template
        """
        import json
        import re

        template_str = json.dumps(template)

        # Find all placeholders
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, template_str)

        for match in matches:
            # Get value from nested path
            value = context
            for key in match.split('.'):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break

            if value is not None:
                placeholder = f"{{{{{match}}}}}"
                template_str = template_str.replace(f'"{placeholder}"', json.dumps(value))
                template_str = template_str.replace(placeholder, str(value))

        return json.loads(template_str)

    async def get_task_group_status(self, task_group_id: UUID) -> dict[str, Any]:
        """
        Get status of a dynamic task group.

        Args:
            task_group_id: DynamicTaskGroup UUID

        Returns:
            Status dictionary
        """
        statement = select(DynamicTaskGroup).where(DynamicTaskGroup.id == task_group_id)
        result = await self.session.exec(statement)
        task_group = result.first()

        if not task_group:
            raise ValueError(f"Task group {task_group_id} not found")

        return {
            "id": str(task_group.id),
            "workflow_id": str(task_group.workflow_id),
            "task_type": task_group.task_type,
            "status": task_group.status,
            "total_tasks": task_group.total_tasks,
            "completed_tasks": task_group.completed_tasks,
            "failed_tasks": task_group.failed_tasks,
            "progress_percentage": task_group.progress_percentage(),
            "created_at": task_group.created_at.isoformat(),
            "completed_at": (
                task_group.completed_at.isoformat() if task_group.completed_at else None
            ),
        }
