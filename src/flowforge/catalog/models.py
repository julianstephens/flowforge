from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ComponentKind(StrEnum):
    INFRASTRUCTURE = "infrastructure"
    WORKFLOW = "workflow"
    RUNTIME = "runtime"
    OBSERVABILITY = "observability"
    DOCUMENTATION = "documentation"


class ComponentDefinition(BaseModel):
    type: str
    kind: ComponentKind
    display_name: str
    description: str

    dependencies: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)

    default_config: dict[str, Any] = Field(default_factory=dict)

    terraform_templates: list[str] = Field(default_factory=list)
    python_templates: list[str] = Field(default_factory=list)
    lambda_templates: list[str] = Field(default_factory=list)
    workflow_templates: list[str] = Field(default_factory=list)
    docs_templates: list[str] = Field(default_factory=list)

    outputs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
