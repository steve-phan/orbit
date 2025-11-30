"""
Metrics API endpoint.
Exposes Prometheus metrics for monitoring.
"""

from fastapi import APIRouter

from orbit.services.metrics import get_metrics

router = APIRouter()


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus text format.
    """
    return get_metrics()
