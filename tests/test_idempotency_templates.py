"""
Tests for idempotency and templates.
"""

from uuid import uuid4

import pytest

from orbit.services.idempotency_service import IdempotencyService
from orbit.services.template_service import TemplateService


def test_idempotency_key_generation():
    """Test idempotency key generation."""

    # Mock session (not used for key generation)
    service = IdempotencyService(None)  # type: ignore

    workflow_id = uuid4()
    task_name = "test_task"

    # Same inputs should generate same key
    key1 = service.generate_key(workflow_id, task_name)
    key2 = service.generate_key(workflow_id, task_name)
    assert key1 == key2

    # Different inputs should generate different keys
    key3 = service.generate_key(uuid4(), task_name)
    assert key1 != key3


def test_idempotency_key_with_payload():
    """Test idempotency key generation with payload."""

    service = IdempotencyService(None)  # type: ignore

    workflow_id = uuid4()
    task_name = "test_task"
    payload1 = {"key": "value", "number": 123}
    payload2 = {"number": 123, "key": "value"}  # Same content, different order

    # Same payload (different order) should generate same key
    key1 = service.generate_key(workflow_id, task_name, payload1)
    key2 = service.generate_key(workflow_id, task_name, payload2)
    assert key1 == key2

    # Different payload should generate different key
    payload3 = {"key": "different"}
    key3 = service.generate_key(workflow_id, task_name, payload3)
    assert key1 != key3


def test_template_parameter_validation():
    """Test template parameter validation."""

    service = TemplateService(None)  # type: ignore

    # Valid integer
    service._validate_parameter(
        "count",
        10,
        {"type": "integer", "validation": {"min": 1, "max": 100}}
    )

    # Invalid: below minimum
    with pytest.raises(ValueError, match="must be >= 1"):
        service._validate_parameter(
            "count",
            0,
            {"type": "integer", "validation": {"min": 1}}
        )

    # Invalid: above maximum
    with pytest.raises(ValueError, match="must be <= 100"):
        service._validate_parameter(
            "count",
            200,
            {"type": "integer", "validation": {"max": 100}}
        )


def test_template_parameter_enum_validation():
    """Test enum validation."""

    service = TemplateService(None)  # type: ignore

    # Valid enum value
    service._validate_parameter(
        "environment",
        "production",
        {"type": "string", "validation": {"enum": ["development", "staging", "production"]}}
    )

    # Invalid enum value
    with pytest.raises(ValueError, match="must be one of"):
        service._validate_parameter(
            "environment",
            "invalid",
            {"type": "string", "validation": {"enum": ["development", "staging", "production"]}}
        )


def test_template_parameter_type_validation():
    """Test type validation."""

    service = TemplateService(None)  # type: ignore

    # Valid types
    service._validate_parameter("name", "test", {"type": "string"})
    service._validate_parameter("count", 10, {"type": "integer"})
    service._validate_parameter("ratio", 0.5, {"type": "float"})
    service._validate_parameter("enabled", True, {"type": "boolean"})
    service._validate_parameter("items", [1, 2, 3], {"type": "array"})
    service._validate_parameter("config", {"key": "value"}, {"type": "object"})

    # Invalid type
    with pytest.raises(ValueError, match="must be of type integer"):
        service._validate_parameter("count", "not a number", {"type": "integer"})


def test_template_parameter_merge():
    """Test parameter merging with defaults."""

    service = TemplateService(None)  # type: ignore

    param_defs = {
        "required_param": {
            "type": "string",
            "required": True
        },
        "optional_param": {
            "type": "integer",
            "default": 100
        }
    }

    # With all parameters
    merged = service._merge_parameters(
        param_defs,
        {"required_param": "value", "optional_param": 200}
    )
    assert merged["required_param"] == "value"
    assert merged["optional_param"] == 200

    # With only required parameter (should use default)
    merged = service._merge_parameters(
        param_defs,
        {"required_param": "value"}
    )
    assert merged["required_param"] == "value"
    assert merged["optional_param"] == 100

    # Missing required parameter
    with pytest.raises(ValueError, match="Required parameter missing"):
        service._merge_parameters(param_defs, {})


def test_template_interpolation():
    """Test template interpolation."""

    service = TemplateService(None)  # type: ignore

    template_data = {
        "name": "{{workflow_name}}",
        "config": {
            "url": "{{api_url}}",
            "timeout": "{{timeout}}"
        }
    }

    parameters = {
        "workflow_name": "Test Workflow",
        "api_url": "https://api.example.com",
        "timeout": 30
    }

    result = service._interpolate_template(template_data, parameters)

    assert result["name"] == "Test Workflow"
    assert result["config"]["url"] == "https://api.example.com"
    # Numeric values are converted to strings during interpolation
    assert result["config"]["timeout"] == "30"
