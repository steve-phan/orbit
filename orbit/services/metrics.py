"""
Prometheus metrics for Orbit.
Provides observability and monitoring capabilities.
"""

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# Workflow metrics
workflow_executions_total = Counter(
    "orbit_workflow_executions_total",
    "Total number of workflow executions",
    ["workflow_name", "status"],
)

workflow_duration_seconds = Histogram(
    "orbit_workflow_duration_seconds",
    "Workflow execution duration in seconds",
    ["workflow_name"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
)

active_workflows = Gauge(
    "orbit_active_workflows",
    "Number of currently running workflows",
)

# Task metrics
task_executions_total = Counter(
    "orbit_task_executions_total",
    "Total number of task executions",
    ["task_name", "status"],
)

task_duration_seconds = Histogram(
    "orbit_task_duration_seconds",
    "Task execution duration in seconds",
    ["task_name"],
    buckets=(0.1, 0.5, 1, 5, 10, 30, 60, 120, 300),
)

task_retries_total = Counter(
    "orbit_task_retries_total",
    "Total number of task retries",
    ["task_name"],
)

# Schedule metrics
scheduled_executions_total = Counter(
    "orbit_scheduled_executions_total",
    "Total number of scheduled workflow executions",
    ["workflow_name"],
)

# System metrics
database_queries_total = Counter(
    "orbit_database_queries_total",
    "Total number of database queries",
    ["operation"],
)


def get_metrics() -> Response:
    """
    Get Prometheus metrics in text format.

    Returns:
        Response with Prometheus metrics
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
