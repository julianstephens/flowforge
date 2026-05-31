from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Diagnostic(BaseModel):
    severity: DiagnosticSeverity
    code: str
    message: str
    path: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
