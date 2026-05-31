from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DiagnosticCode(StrEnum):
    INVALID_COMPONENT = "invalid_component"
    MISSING_COMPONENT_DEPENDENCY = "missing_component_dependency"
    INCOMPATIBLE_COMPONENTS = "incompatible_components"


class Diagnostic(BaseModel):
    severity: DiagnosticSeverity
    code: DiagnosticCode
    message: str
    path: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
