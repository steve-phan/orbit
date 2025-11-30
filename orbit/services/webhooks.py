"""
Webhook notification service.
Sends HTTP webhooks on workflow events.
"""

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx

from orbit.core.logging import get_logger
from orbit.models.retry_policy import RetryPolicy

logger = get_logger("services.webhooks")


class WebhookService:
    """
    Service for sending webhook notifications.
    Supports retries and multiple webhooks per event.
    """

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def send_webhook(
        self,
        url: str,
        event_type: str,
        payload: dict[str, Any],
        retry_policy: RetryPolicy | None = None,
    ) -> bool:
        """
        Send a webhook notification.

        Args:
            url: Webhook URL
            event_type: Type of event (e.g., 'workflow.completed')
            payload: Event payload
            retry_policy: Retry policy for webhook delivery

        Returns:
            True if successful, False otherwise
        """
        if retry_policy is None:
            retry_policy = RetryPolicy(max_retries=3, initial_delay=1.0)

        webhook_payload = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload,
        }

        for attempt in range(retry_policy.max_retries + 1):
            try:
                response = await self.client.post(
                    url, json=webhook_payload, headers={"Content-Type": "application/json"}
                )

                if response.status_code < 400:
                    logger.info(
                        f"Webhook sent successfully: {event_type} to {url} "
                        f"(status: {response.status_code})"
                    )
                    return True
                else:
                    logger.warning(
                        f"Webhook failed with status {response.status_code}: "
                        f"{event_type} to {url}"
                    )

            except Exception as e:
                logger.error(f"Webhook error (attempt {attempt + 1}): {e}")

            # Retry if not last attempt
            if attempt < retry_policy.max_retries:
                delay = retry_policy.calculate_delay(attempt)
                logger.info(f"Retrying webhook after {delay:.2f}s")
                await asyncio.sleep(delay)

        logger.error(f"Webhook failed after {retry_policy.max_retries + 1} attempts")
        return False

    async def send_workflow_event(
        self,
        event_type: str,
        workflow_id: UUID,
        workflow_name: str,
        status: str,
        webhooks: list[str],
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Send workflow event to configured webhooks.

        Args:
            event_type: Event type (e.g., 'workflow.completed')
            workflow_id: Workflow UUID
            workflow_name: Workflow name
            status: Workflow status
            webhooks: List of webhook URLs
            additional_data: Additional event data
        """
        payload = {
            "workflow_id": str(workflow_id),
            "workflow_name": workflow_name,
            "status": status,
            **(additional_data or {}),
        }

        # Send to all webhooks concurrently
        tasks = [
            self.send_webhook(url, event_type, payload) for url in webhooks
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Global webhook service instance
webhook_service = WebhookService()
