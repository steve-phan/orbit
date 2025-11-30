"""
Idempotency service for task deduplication.
Prevents duplicate executions and caches results.
"""

import hashlib
import json
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.models.idempotency import IdempotencyKey
from orbit.core.logging import get_logger

logger = get_logger("services.idempotency")


class IdempotencyService:
    """
    Service for managing task idempotency.
    Prevents duplicate task executions and caches results.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def generate_key(
        self,
        workflow_id: UUID,
        task_name: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate idempotency key from workflow, task, and payload.

        Args:
            workflow_id: Workflow UUID
            task_name: Task name
            payload: Task payload (optional)

        Returns:
            Idempotency key string
        """
        # Create deterministic key from inputs
        key_parts = [str(workflow_id), task_name]
        
        if payload:
            # Sort payload for deterministic hash
            payload_str = json.dumps(payload, sort_keys=True)
            payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
            key_parts.append(payload_hash)
        
        return ":".join(key_parts)

    async def check_idempotency(
        self,
        workflow_id: UUID,
        task_name: str,
        idempotency_key: str,
    ) -> Tuple[bool, Optional[IdempotencyKey]]:
        """
        Check if task has already been executed with this key.

        Args:
            workflow_id: Workflow UUID
            task_name: Task name
            idempotency_key: Idempotency key

        Returns:
            Tuple of (is_duplicate, existing_record)
        """
        statement = select(IdempotencyKey).where(
            IdempotencyKey.workflow_id == workflow_id,
            IdempotencyKey.task_name == task_name,
            IdempotencyKey.key == idempotency_key,
        )
        
        result = await self.session.exec(statement)
        existing = result.first()
        
        if not existing:
            return False, None
        
        # Check if expired
        if existing.is_expired():
            logger.info(f"Idempotency key expired: {idempotency_key}")
            await self.session.delete(existing)
            await self.session.commit()
            return False, None
        
        # Check status
        if existing.status == "processing":
            logger.info(f"Task already processing: {idempotency_key}")
            return True, existing
        
        if existing.status == "completed":
            logger.info(f"Task already completed, returning cached result: {idempotency_key}")
            return True, existing
        
        if existing.status == "failed":
            logger.info(f"Task previously failed: {idempotency_key}")
            # Allow retry of failed tasks
            return False, existing
        
        return False, None

    async def create_idempotency_record(
        self,
        workflow_id: UUID,
        task_name: str,
        idempotency_key: str,
        payload: Optional[Dict[str, Any]] = None,
        ttl_hours: int = 24,
    ) -> IdempotencyKey:
        """
        Create idempotency record for task execution.

        Args:
            workflow_id: Workflow UUID
            task_name: Task name
            idempotency_key: Idempotency key
            payload: Task payload
            ttl_hours: Time-to-live in hours

        Returns:
            Created IdempotencyKey record
        """
        # Generate request hash
        request_hash = None
        if payload:
            payload_str = json.dumps(payload, sort_keys=True)
            request_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        
        record = IdempotencyKey(
            workflow_id=workflow_id,
            task_name=task_name,
            key=idempotency_key,
            status="processing",
            request_hash=request_hash,
        )
        
        record.set_ttl(ttl_hours)
        
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        
        logger.info(f"Created idempotency record: {idempotency_key}")
        return record

    async def mark_completed(
        self,
        idempotency_key_id: UUID,
        result: Dict[str, Any],
    ) -> None:
        """
        Mark idempotency record as completed with result.

        Args:
            idempotency_key_id: IdempotencyKey UUID
            result: Task execution result
        """
        statement = select(IdempotencyKey).where(IdempotencyKey.id == idempotency_key_id)
        result_obj = await self.session.exec(statement)
        record = result_obj.first()
        
        if record:
            record.status = "completed"
            record.result = result
            record.completed_at = datetime.utcnow()
            
            self.session.add(record)
            await self.session.commit()
            
            logger.info(f"Marked idempotency record as completed: {record.key}")

    async def mark_failed(
        self,
        idempotency_key_id: UUID,
        error_message: str,
    ) -> None:
        """
        Mark idempotency record as failed.

        Args:
            idempotency_key_id: IdempotencyKey UUID
            error_message: Error message
        """
        statement = select(IdempotencyKey).where(IdempotencyKey.id == idempotency_key_id)
        result_obj = await self.session.exec(statement)
        record = result_obj.first()
        
        if record:
            record.status = "failed"
            record.error_message = error_message
            record.completed_at = datetime.utcnow()
            
            self.session.add(record)
            await self.session.commit()
            
            logger.info(f"Marked idempotency record as failed: {record.key}")

    async def cleanup_expired(self) -> int:
        """
        Clean up expired idempotency records.

        Returns:
            Number of records deleted
        """
        statement = select(IdempotencyKey).where(
            IdempotencyKey.expires_at.isnot(None),
            IdempotencyKey.expires_at < datetime.utcnow(),
        )
        
        result = await self.session.exec(statement)
        expired = list(result.all())
        
        for record in expired:
            await self.session.delete(record)
        
        await self.session.commit()
        
        logger.info(f"Cleaned up {len(expired)} expired idempotency records")
        return len(expired)
