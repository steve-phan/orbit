"""
Tests for workflow scheduling functionality.
"""

import pytest
from datetime import datetime, timedelta
from orbit.models.schedule import WorkflowSchedule
from uuid import uuid4


def test_validate_cron_expression_valid():
    """Test validation of valid cron expressions."""
    assert WorkflowSchedule.validate_cron_expression("0 2 * * *") is True  # Daily at 2 AM
    assert WorkflowSchedule.validate_cron_expression("*/5 * * * *") is True  # Every 5 minutes
    assert WorkflowSchedule.validate_cron_expression("0 0 * * 0") is True  # Weekly on Sunday
    assert WorkflowSchedule.validate_cron_expression("0 0 1 * *") is True  # Monthly on 1st


def test_validate_cron_expression_invalid():
    """Test validation of invalid cron expressions."""
    assert WorkflowSchedule.validate_cron_expression("invalid") is False
    assert WorkflowSchedule.validate_cron_expression("* * * *") is False  # Missing field
    assert WorkflowSchedule.validate_cron_expression("60 * * * *") is False  # Invalid minute


def test_calculate_next_run():
    """Test next run calculation."""
    schedule = WorkflowSchedule(
        workflow_id=uuid4(),
        cron_expression="0 2 * * *",  # Daily at 2 AM
        timezone="UTC"
    )
    
    # Use a specific base time
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    next_run = schedule.calculate_next_run(base_time)
    
    # Next run should be at 2 AM on the same day
    assert next_run.hour == 2
    assert next_run.minute == 0
    assert next_run.day == 1


def test_calculate_next_run_after_time():
    """Test next run calculation when current time is after scheduled time."""
    schedule = WorkflowSchedule(
        workflow_id=uuid4(),
        cron_expression="0 2 * * *",  # Daily at 2 AM
        timezone="UTC"
    )
    
    # Base time is 3 AM (after 2 AM)
    base_time = datetime(2024, 1, 1, 3, 0, 0)
    next_run = schedule.calculate_next_run(base_time)
    
    # Next run should be at 2 AM the next day
    assert next_run.hour == 2
    assert next_run.minute == 0
    assert next_run.day == 2


def test_update_next_run():
    """Test update_next_run method."""
    schedule = WorkflowSchedule(
        workflow_id=uuid4(),
        cron_expression="*/5 * * * *",  # Every 5 minutes
        timezone="UTC"
    )
    
    initial_updated_at = schedule.updated_at
    schedule.update_next_run()
    
    assert schedule.next_run is not None
    assert schedule.updated_at >= initial_updated_at


def test_hourly_schedule():
    """Test hourly cron schedule."""
    schedule = WorkflowSchedule(
        workflow_id=uuid4(),
        cron_expression="0 * * * *",  # Every hour
        timezone="UTC"
    )
    
    base_time = datetime(2024, 1, 1, 10, 30, 0)
    next_run = schedule.calculate_next_run(base_time)
    
    # Next run should be at 11:00
    assert next_run.hour == 11
    assert next_run.minute == 0


def test_every_5_minutes_schedule():
    """Test every 5 minutes schedule."""
    schedule = WorkflowSchedule(
        workflow_id=uuid4(),
        cron_expression="*/5 * * * *",  # Every 5 minutes
        timezone="UTC"
    )
    
    base_time = datetime(2024, 1, 1, 10, 3, 0)
    next_run = schedule.calculate_next_run(base_time)
    
    # Next run should be at 10:05
    assert next_run.hour == 10
    assert next_run.minute == 5
