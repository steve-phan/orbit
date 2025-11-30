"""
Workflow template service.
Manages reusable workflow templates with parameterization.
"""

import re
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.models.templates import WorkflowTemplate
from orbit.models.workflow import Workflow
from orbit.schemas.workflow import WorkflowCreate, TaskCreate
from orbit.core.logging import get_logger

logger = get_logger("services.templates")


class TemplateService:
    """
    Service for managing workflow templates.
    Enables template creation, instantiation, and management.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_template(
        self,
        name: str,
        description: str,
        template_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> WorkflowTemplate:
        """
        Create a new workflow template.

        Args:
            name: Template name
            description: Template description
            template_data: Workflow definition
            parameters: Parameter definitions
            category: Template category
            tags: Template tags

        Returns:
            Created template
        """
        template = WorkflowTemplate(
            name=name,
            description=description,
            template_data=template_data,
            parameters=parameters or {},
            category=category,
            tags=tags or [],
        )
        
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        
        logger.info(f"Created template: {name}")
        return template

    async def get_template(self, template_id: UUID) -> Optional[WorkflowTemplate]:
        """Get template by ID."""
        statement = select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
        result = await self.session.exec(statement)
        return result.first()

    async def get_template_by_name(self, name: str) -> Optional[WorkflowTemplate]:
        """Get template by name."""
        statement = select(WorkflowTemplate).where(WorkflowTemplate.name == name)
        result = await self.session.exec(statement)
        return result.first()

    async def list_templates(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        active_only: bool = True,
    ) -> List[WorkflowTemplate]:
        """
        List templates with optional filtering.

        Args:
            category: Filter by category
            tag: Filter by tag
            active_only: Only return active templates

        Returns:
            List of templates
        """
        statement = select(WorkflowTemplate)
        
        if active_only:
            statement = statement.where(WorkflowTemplate.is_active == True)
        
        if category:
            statement = statement.where(WorkflowTemplate.category == category)
        
        result = await self.session.exec(statement)
        templates = list(result.all())
        
        # Filter by tag if specified
        if tag:
            templates = [t for t in templates if tag in t.tags]
        
        return templates

    async def instantiate_template(
        self,
        template_id: UUID,
        parameters: Dict[str, Any],
        workflow_name: Optional[str] = None,
    ) -> WorkflowCreate:
        """
        Instantiate a template with parameters.

        Args:
            template_id: Template UUID
            parameters: Parameter values
            workflow_name: Override workflow name

        Returns:
            WorkflowCreate schema ready for execution
        """
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        if not template.is_active:
            raise ValueError(f"Template {template.name} is not active")
        
        # Validate and merge parameters
        merged_params = self._merge_parameters(template.parameters, parameters)
        
        # Interpolate template with parameters
        workflow_data = self._interpolate_template(template.template_data, merged_params)
        
        # Override name if provided
        if workflow_name:
            workflow_data["name"] = workflow_name
        else:
            workflow_data["name"] = f"{template.name}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Update usage tracking
        template.usage_count += 1
        template.last_used_at = datetime.utcnow()
        self.session.add(template)
        await self.session.commit()
        
        logger.info(f"Instantiated template: {template.name}")
        
        # Convert to WorkflowCreate
        return WorkflowCreate(**workflow_data)

    def _merge_parameters(
        self,
        param_defs: Dict[str, Any],
        param_values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge parameter definitions with provided values.

        Args:
            param_defs: Parameter definitions from template
            param_values: Parameter values provided by user

        Returns:
            Merged parameters with defaults and validation
        """
        merged = {}
        
        for param_name, param_def in param_defs.items():
            # Check if required parameter is provided
            if param_def.get("required", False) and param_name not in param_values:
                raise ValueError(f"Required parameter missing: {param_name}")
            
            # Use provided value or default
            value = param_values.get(param_name, param_def.get("default"))
            
            if value is None and param_def.get("required", False):
                raise ValueError(f"Required parameter has no value: {param_name}")
            
            # Validate value (basic validation)
            if value is not None:
                self._validate_parameter(param_name, value, param_def)
            
            merged[param_name] = value
        
        return merged

    def _validate_parameter(
        self,
        name: str,
        value: Any,
        definition: Dict[str, Any],
    ) -> None:
        """
        Validate parameter value against definition.

        Args:
            name: Parameter name
            value: Parameter value
            definition: Parameter definition

        Raises:
            ValueError: If validation fails
        """
        param_type = definition.get("type", "string")
        
        # Type validation
        type_map = {
            "string": str,
            "integer": int,
            "float": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        
        expected_type = type_map.get(param_type)
        if expected_type and not isinstance(value, expected_type):
            raise ValueError(
                f"Parameter {name} must be of type {param_type}, got {type(value).__name__}"
            )
        
        # Additional validation
        validation = definition.get("validation", {})
        
        if "min" in validation and value < validation["min"]:
            raise ValueError(f"Parameter {name} must be >= {validation['min']}")
        
        if "max" in validation and value > validation["max"]:
            raise ValueError(f"Parameter {name} must be <= {validation['max']}")
        
        if "enum" in validation and value not in validation["enum"]:
            raise ValueError(f"Parameter {name} must be one of {validation['enum']}")

    def _interpolate_template(
        self,
        template_data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Interpolate template with parameter values.

        Args:
            template_data: Template data with placeholders
            parameters: Parameter values

        Returns:
            Interpolated template data
        """
        # Convert to JSON string for easy interpolation
        import json
        template_str = json.dumps(template_data)
        
        # Replace {{param_name}} with values
        for param_name, param_value in parameters.items():
            placeholder = f"{{{{{param_name}}}}}"
            # Convert value to string for replacement
            value_str = json.dumps(param_value) if not isinstance(param_value, str) else param_value
            template_str = template_str.replace(placeholder, value_str)
        
        # Parse back to dict
        return json.loads(template_str)

    async def delete_template(self, template_id: UUID) -> bool:
        """
        Delete a template.

        Args:
            template_id: Template UUID

        Returns:
            True if deleted, False if not found
        """
        template = await self.get_template(template_id)
        if not template:
            return False
        
        await self.session.delete(template)
        await self.session.commit()
        
        logger.info(f"Deleted template: {template.name}")
        return True
