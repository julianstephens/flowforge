from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DiagnosticCode(StrEnum):
    UNKNOWN_COMPONENT_TYPE = "unknown_component_type"
    MISSING_COMPONENT_DEPENDENCY = "missing_component_dependency"
    COMPONENT_CONFLICT = "component_conflict"

    LAMBDA_WORKER_REQUIRES_TRIGGER = "lambda_worker_requires_trigger"

    DISTRIBUTED_MAP_WITHOUT_ARTIFACT_BUCKET = "distributed_map_without_artifact_bucket"

    CLOUDWATCH_ALARMS_REQUIRE_MONITORED_RESOURCE = (
        "cloudwatch_alarms_require_monitored_resource"
    )

    LOCKS_TABLE_REQUIRES_LOCK_MANAGER_WHEN_RUNTIME_ENABLED = (
        "locks_table_requires_lock_manager_when_runtime_enabled"
    )

    SQS_DLQ_REQUIRES_QUEUE = "sqs_dlq_requires_queue"


class Diagnostic(BaseModel):
    severity: DiagnosticSeverity
    code: DiagnosticCode
    message: str
    path: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
