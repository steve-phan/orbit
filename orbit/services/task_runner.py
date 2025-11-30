import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.logging import get_logger
from orbit.models.retry_policy import RetryPolicy
from orbit.models.workflow import Task, Workflow
from orbit.services import metrics
from orbit.services.dag_executor import DAGExecutor
from orbit.services.websocket_manager import ConnectionManager

logger = get_logger("services.task_runner")


class TaskRunner:
    """
    Executes tasks based on their dependencies and action types.
    Manages workflow execution state and broadcasts updates.
    Implements retry logic with exponential backoff and timeout handling.
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
        start_time = datetime.utcnow()

        # Load workflow with tasks
        statement = (
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(selectinload(Workflow.tasks))
        )
        result = await self.session.exec(statement)
        workflow = result.one()

        # Track active workflows
        metrics.active_workflows.inc()

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
                # Check if workflow was paused
                await self.session.refresh(workflow)
                if workflow.status == "paused":
                    logger.info(f"Workflow {workflow_id} was paused, stopping execution")
                    await self.ws_manager.broadcast(
                        {
                            "workflow_id": str(workflow_id),
                            "status": "paused",
                            "message": "Workflow paused during execution",
                        }
                    )
                    return

                # Get tasks for this level
                level_tasks = [task for task in workflow.tasks if task.name in level]

                # Execute all tasks in this level concurrently
                await asyncio.gather(
                    *[self._execute_task_with_retry(task) for task in level_tasks]
                )

            # Mark workflow as completed
            workflow.status = "completed"
            workflow.updated_at = datetime.utcnow()
            self.session.add(workflow)
            await self.session.commit()
            await self.ws_manager.broadcast(
                {"workflow_id": str(workflow_id), "status": "completed"}
            )

            # Track metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            metrics.workflow_executions_total.labels(
                workflow_name=workflow.name, status="completed"
            ).inc()
            metrics.workflow_duration_seconds.labels(
                workflow_name=workflow.name
            ).observe(duration)
            metrics.active_workflows.dec()

        except Exception as e:
            # Mark workflow as failed
            workflow.status = "failed"
            workflow.updated_at = datetime.utcnow()
            self.session.add(workflow)
            await self.session.commit()
            await self.ws_manager.broadcast(
                {"workflow_id": str(workflow_id), "status": "failed", "error": str(e)}
            )

            # Track metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            metrics.workflow_executions_total.labels(
                workflow_name=workflow.name, status="failed"
            ).inc()
            metrics.workflow_duration_seconds.labels(
                workflow_name=workflow.name
            ).observe(duration)
            metrics.active_workflows.dec()
            raise

    async def _execute_task_with_retry(self, task: Task) -> None:
        """
        Execute a task with retry logic and timeout handling.

        Args:
            task: Task object to execute
        """
        # Parse retry policy
        retry_policy = RetryPolicy(**task.retry_policy) if task.retry_policy else RetryPolicy()

        last_error = None

        for attempt in range(retry_policy.max_retries + 1):
            try:
                # Update retry count
                task.retry_count = attempt
                self.session.add(task)
                await self.session.commit()

                # Execute task with timeout
                await self._execute_task(task)
                return  # Success!

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"Task {task.name} timed out on attempt {attempt + 1}/{retry_policy.max_retries + 1}"
                )

                if not retry_policy.should_retry(attempt):
                    # No more retries
                    task.status = "failed"
                    task.result = {"error": "Task timed out", "attempts": attempt + 1}
                    task.updated_at = datetime.utcnow()
                    self.session.add(task)
                    await self.session.commit()
                    await self.ws_manager.broadcast(
                        {
                            "task_id": str(task.id),
                            "task_name": task.name,
                            "status": "failed",
                            "error": "timeout",
                        }
                    )
                    raise

                # Track retry
                metrics.task_retries_total.labels(task_name=task.name).inc()

                # Calculate delay and retry
                delay = retry_policy.calculate_delay(attempt)
                logger.info(f"Retrying task {task.name} after {delay:.2f}s")
                await asyncio.sleep(delay)

            except Exception as e:
                last_error = e
                logger.error(
                    f"Task {task.name} failed on attempt {attempt + 1}/{retry_policy.max_retries + 1}: {e}"
                )

                if not retry_policy.should_retry(attempt):
                    # No more retries
                    task.status = "failed"
                    task.result = {"error": str(e), "attempts": attempt + 1}
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

                # Calculate delay and retry
                delay = retry_policy.calculate_delay(attempt)
                logger.info(f"Retrying task {task.name} after {delay:.2f}s")
                await asyncio.sleep(delay)

        # If we get here, all retries failed
        if last_error:
            raise last_error

    async def _execute_task(self, task: Task) -> None:
        """
        Execute a single task based on its action type.

        Args:
            task: Task object to execute
        """
        task_start_time = datetime.utcnow()
        # Update task status to running
        task.status = "running"
        task.updated_at = datetime.utcnow()
        self.session.add(task)
        await self.session.commit()
        await self.ws_manager.broadcast(
            {"task_id": str(task.id), "task_name": task.name, "status": "running"}
        )

        try:
            # Execute with timeout if specified
            if task.timeout_seconds:
                result = await asyncio.wait_for(
                    self._execute_action(task.action_type, task.action_payload),
                    timeout=task.timeout_seconds,
                )
            else:
                result = await self._execute_action(
                    task.action_type, task.action_payload
                )

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

            # Track metrics
            task_duration = (datetime.utcnow() - task_start_time).total_seconds()
            metrics.task_executions_total.labels(
                task_name=task.name, status="completed"
            ).inc()
            metrics.task_duration_seconds.labels(task_name=task.name).observe(task_duration)

        except asyncio.TimeoutError:
            # Timeout - will be handled by retry logic
            logger.error(f"Task {task.name} timed out after {task.timeout_seconds}s")
            raise

        except Exception as e:
            # Other errors - will be handled by retry logic
            logger.error(f"Task {task.name} failed: {e}")
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
            return {
                "status": "success",
                "action_type": action_type,
                "payload": payload,
            }

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
