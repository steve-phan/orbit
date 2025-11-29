import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.models.workflow import Task, Workflow
from orbit.services.dag_executor import DAGExecutor
from orbit.services.websocket_manager import ConnectionManager


class TaskRunner:
    """
    Executes tasks based on their dependencies and action types.
    Manages workflow execution state and broadcasts updates.
    """

    def __init__(self, session: AsyncSession, ws_manager: ConnectionManager):
        self.session = session
        self.ws_manager = ws_manager

    async def execute_workflow(self, workflow_id: UUID) -> None:
        """
        Execute a workflow by running its tasks in topological order.

        Args:
            workflow_id: UUID of the workflow to execute
        """
        # Load workflow with tasks
        statement = (
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(selectinload(Workflow.tasks))
        )
        result = await self.session.exec(statement)
        workflow = result.one()

        # Update workflow status
        workflow.status = "running"
        workflow.updated_at = datetime.utcnow()
        self.session.add(workflow)
        await self.session.commit()
        await self.ws_manager.broadcast(
            {"workflow_id": str(workflow_id), "status": "running"}
        )

        try:
            # Get execution order
            execution_levels = DAGExecutor.topological_sort(workflow.tasks)

            # Execute tasks level by level
            for level in execution_levels:
                # Get tasks for this level
                level_tasks = [task for task in workflow.tasks if task.name in level]

                # Execute all tasks in this level concurrently
                await asyncio.gather(
                    *[self._execute_task(task) for task in level_tasks]
                )

            # Mark workflow as completed
            workflow.status = "completed"
            workflow.updated_at = datetime.utcnow()
            self.session.add(workflow)
            await self.session.commit()
            await self.ws_manager.broadcast(
                {"workflow_id": str(workflow_id), "status": "completed"}
            )

        except Exception as e:
            # Mark workflow as failed
            workflow.status = "failed"
            workflow.updated_at = datetime.utcnow()
            self.session.add(workflow)
            await self.session.commit()
            await self.ws_manager.broadcast(
                {"workflow_id": str(workflow_id), "status": "failed", "error": str(e)}
            )
            raise

    async def _execute_task(self, task: Task) -> None:
        """
        Execute a single task based on its action type.

        Args:
            task: Task object to execute
        """
        # Update task status to running
        task.status = "running"
        task.updated_at = datetime.utcnow()
        self.session.add(task)
        await self.session.commit()
        await self.ws_manager.broadcast(
            {"task_id": str(task.id), "task_name": task.name, "status": "running"}
        )

        try:
            # Execute based on action type
            result = await self._execute_action(task.action_type, task.action_payload)

            # Update task with result
            task.status = "completed"
            task.result = result
            task.updated_at = datetime.utcnow()
            self.session.add(task)
            await self.session.commit()
            await self.ws_manager.broadcast(
                {
                    "task_id": str(task.id),
                    "task_name": task.name,
                    "status": "completed",
                    "result": result,
                }
            )

        except Exception as e:
            # Mark task as failed
            task.status = "failed"
            task.result = {"error": str(e)}
            task.updated_at = datetime.utcnow()
            self.session.add(task)
            await self.session.commit()
            await self.ws_manager.broadcast(
                {
                    "task_id": str(task.id),
                    "task_name": task.name,
                    "status": "failed",
                    "error": str(e),
                }
            )
            raise

    async def _execute_action(
        self, action_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute a task action based on its type.

        Args:
            action_type: Type of action to execute
            payload: Action configuration

        Returns:
            Result dictionary
        """
        if action_type == "http_request":
            return await self._execute_http_request(payload)
        elif action_type == "shell_command":
            return await self._execute_shell_command(payload)
        elif action_type == "python_script":
            return await self._execute_python_script(payload)
        elif action_type == "sleep":
            return await self._execute_sleep(payload)
        else:
            # For demo purposes, simulate execution
            await asyncio.sleep(1)
            return {"status": "success", "action_type": action_type, "payload": payload}

    async def _execute_http_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute HTTP request action."""
        # Simulate HTTP request
        await asyncio.sleep(0.5)
        return {"status": "success", "url": payload.get("url"), "simulated": True}

    async def _execute_shell_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute shell command action."""
        # Simulate shell command
        await asyncio.sleep(0.3)
        return {
            "status": "success",
            "command": payload.get("command"),
            "simulated": True,
        }

    async def _execute_python_script(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute Python script action."""
        # Simulate Python script execution
        await asyncio.sleep(0.7)
        return {"status": "success", "script": payload.get("script"), "simulated": True}

    async def _execute_sleep(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute sleep action for testing."""
        duration = payload.get("duration", 1)
        await asyncio.sleep(duration)
        return {"status": "success", "slept": duration}
