from collections import defaultdict

from flowforge.catalog.components.infrastructure import (
    API_GATEWAY,
    DYNAMODB_LOCKS_TABLE,
    LAMBDA_WORKER,
    S3_ARTIFACT_BUCKET,
    SQS_DLQ,
    SQS_STANDARD_QUEUE,
)
from flowforge.catalog.components.observability import CLOUDWATCH_ALARMS
from flowforge.catalog.components.runtime import LOCK_MANAGER, PYTHON_RUNTIME
from flowforge.catalog.components.workflow import DISTRIBUTED_MAP
from flowforge.catalog.models import ComponentDefinition, ComponentKind
from flowforge.catalog.registry import ComponentRegistry
from flowforge.planning.diagnostic_details import (
    cloudwatch_alarm_details,
    component_conflict_details,
    component_details,
    distributed_map_artifact_bucket_details,
    lambda_worker_trigger_details,
    locks_table_runtime_details,
    missing_dependency_details,
    unknown_component_details,
)
from flowforge.planning.diagnostics import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
)
from flowforge.planning.paths import component_field_path, component_path
from flowforge.planning.schemas import ComponentConfig, ProjectPlan


class Validator:
    """Validates a project plan for correctness, consistency, and best practices, and
    produces diagnostics for any issues found."""

    plan: ProjectPlan
    _diagnostics: list[Diagnostic]
    _components_by_kind: dict[ComponentKind, list[ComponentConfig]]

    def __init__(self, plan: ProjectPlan, plan_path: str | None = None):
        self.plan = plan
        self.plan_path = plan_path

    def validate(self) -> list[Diagnostic]:
        """Performs validation checks on the project plan and returns a list of
        diagnostics.

        Validation checks include:
        - Verifying that all component types are valid and recognized.
        - Ensuring that all component dependencies are satisfied.
        - Checking for incompatible component combinations.
        - Providing warnings for potential issues such as using a Distributed Map
          without an S3 Artifact Bucket or an SQS Dead Letter Queue without a standard
          SQS Queue.

        Returns:
            A list of Diagnostic objects representing any errors or warnings found
            during validation.
        """
        self._diagnostics = []
        self._components_by_kind = defaultdict(list)
        enabled_configs_by_name: dict[str, ComponentConfig] = {}
        enabled_types: set[str] = set()
        known_enabled_defs_by_name: dict[str, ComponentDefinition] = {}
        unknown_enabled_components: dict[str, ComponentConfig] = {}
        for name, component_config in self.plan.components.items():
            if component_config.enabled:
                enabled_configs_by_name[name] = component_config
                enabled_types.add(component_config.type)
                try:
                    comp_def = ComponentRegistry.get_component(component_config.type)
                    known_enabled_defs_by_name[name] = comp_def
                except Exception:
                    unknown_enabled_components[name] = component_config

        for name, component_config in enabled_configs_by_name.items():
            if not self._validate_component_type(name, component_config):
                continue
            self._validate_component_dependencies(name, component_config, enabled_types)
            self._validate_component_compatibility(
                name, component_config, enabled_types
            )

            match component_config.type:
                case DYNAMODB_LOCKS_TABLE.type:
                    self._validate_dynamodb_locks_table_component(
                        name, component_config, enabled_types
                    )
                case DISTRIBUTED_MAP.type:
                    self._validate_distributed_map_component(
                        name, component_config, enabled_types
                    )
                case SQS_DLQ.type:
                    self._validate_sqs_dlq_component(
                        name, component_config, enabled_types
                    )
                case LAMBDA_WORKER.type:
                    self._validate_lambda_worker_component(
                        name, component_config, enabled_types
                    )
                case CLOUDWATCH_ALARMS.type:
                    self._validate_cloudwatch_alarm_component(name, component_config)
        return self._diagnostics

    def _validate_component_type(self, name: str, component: ComponentConfig) -> bool:
        if not ComponentRegistry.is_valid_component_type(component.type):
            self._diagnostics.append(
                Diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    code=DiagnosticCode.UNKNOWN_COMPONENT_TYPE,
                    message=f"Unknown component type '{component.type}'",
                    path=component_field_path(name, "type"),
                    details=unknown_component_details(
                        component_name=name, component=component
                    ),
                )
            )
            return False
        self._components_by_kind[
            ComponentKind(ComponentRegistry.get_component_kind(component.type))
        ].append(component)
        return True

    def _validate_component_dependencies(
        self, name: str, component: ComponentConfig, enabled_component_types: set[str]
    ):
        for dependency in ComponentRegistry.get_component_dependencies(component.type):
            if dependency not in enabled_component_types:
                self._diagnostics.append(
                    Diagnostic(
                        severity=DiagnosticSeverity.ERROR,
                        code=DiagnosticCode.MISSING_COMPONENT_DEPENDENCY,
                        message=(
                            f"Component '{name}' requires component type "
                            f"'{dependency}' to be enabled."
                        ),
                        path=component_path(name),
                        details=missing_dependency_details(
                            component_name=name,
                            component=component,
                            missing_dependency=dependency,
                        ),
                    )
                )

    def _validate_component_compatibility(
        self, name: str, component: ComponentConfig, enabled_component_types: set[str]
    ):
        for conflict in ComponentRegistry.get_component_conflicts(component.type):
            if conflict in enabled_component_types:
                self._diagnostics.append(
                    Diagnostic(
                        severity=DiagnosticSeverity.ERROR,
                        code=DiagnosticCode.COMPONENT_CONFLICT,
                        message=(
                            f"Component '{name}' is incompatible with "
                            f"component type '{conflict}'"
                        ),
                        path=component_path(name),
                        details=component_conflict_details(
                            component_name=name,
                            component=component,
                            conflicting_component_type=conflict,
                        ),
                    )
                )

    def _validate_cloudwatch_alarm_component(
        self, name: str, component: ComponentConfig
    ):
        if len(self._components_by_kind[ComponentKind.INFRASTRUCTURE]) < 1:
            self._diagnostics.append(
                Diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    code=DiagnosticCode.CLOUDWATCH_ALARMS_REQUIRE_MONITORED_RESOURCE,
                    message=(
                        "A CloudWatch Alarm component requires at least one "
                        "infrastructure component to be present in the plan. "
                        "Consider adding an infrastructure component such as a "
                        "DynamoDB Jobs Table or SQS Standard Queue to store job "
                        "data and ensure proper monitoring and alerting."
                    ),
                    path=component_path(name),
                    details=cloudwatch_alarm_details(
                        component_name=name,
                        component=component,
                        monitored_component_types={
                            c.type
                            for c in self._components_by_kind[
                                ComponentKind.INFRASTRUCTURE
                            ]
                        },
                    ),
                )
            )

    def _validate_distributed_map_component(
        self, name: str, component: ComponentConfig, enabled_component_types: set[str]
    ):
        if (
            component.type == DISTRIBUTED_MAP.type
            and S3_ARTIFACT_BUCKET.type not in enabled_component_types
        ):
            self._diagnostics.append(
                Diagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    code=DiagnosticCode.DISTRIBUTED_MAP_WITHOUT_ARTIFACT_BUCKET,
                    message=(
                        "Using a Distributed Map component without an S3 "
                        "Artifact Bucket may lead to performance issues or "
                        "failures due to large payloads. Consider adding "
                        "an S3 Artifact Bucket to store intermediate data."
                    ),
                    path=component_path(name),
                    details=distributed_map_artifact_bucket_details(
                        component_name=name,
                        component=component,
                    ),
                )
            )

    def _validate_sqs_dlq_component(
        self, name: str, component: ComponentConfig, enabled_component_types: set[str]
    ):
        if (
            component.type == SQS_DLQ.type
            and SQS_STANDARD_QUEUE.type not in enabled_component_types
        ):
            self._diagnostics.append(
                Diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    code=DiagnosticCode.SQS_DLQ_REQUIRES_QUEUE,
                    message=(
                        "Using an SQS Dead Letter Queue without a standard "
                        "SQS Queue may lead to misconfiguration. Consider "
                        "adding an SQS Standard Queue to handle message "
                        "processing and retries."
                    ),
                    path=component_path(name),
                    details=component_details(
                        component_name=name,
                        component=component,
                    ),
                )
            )

    def _validate_lambda_worker_component(
        self, name: str, component: ComponentConfig, enabled_component_types: set[str]
    ):
        valid_trigger_components = {
            DISTRIBUTED_MAP.type,
            SQS_STANDARD_QUEUE.type,
            API_GATEWAY.type,
        }
        if not any(c in valid_trigger_components for c in enabled_component_types):
            self._diagnostics.append(
                Diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    code=DiagnosticCode.LAMBDA_WORKER_REQUIRES_TRIGGER,
                    message=(
                        "Using a Lambda Worker component without a valid trigger "
                        "component (Distributed Map, SQS Standard Queue, or API "
                        "Gateway) may lead to a non-functional workflow. Consider "
                        "adding a compatible trigger component to ensure proper "
                        "execution of the Lambda Worker."
                    ),
                    path=component_path(name),
                    details=lambda_worker_trigger_details(
                        component_name=name,
                        component=component,
                        valid_trigger_component_types=valid_trigger_components,
                        enabled_component_types=enabled_component_types,
                    ),
                )
            )

    def _validate_dynamodb_locks_table_component(
        self, name: str, component: ComponentConfig, enabled_component_types: set[str]
    ):
        if (
            PYTHON_RUNTIME.type in enabled_component_types
            and LOCK_MANAGER.type not in enabled_component_types
        ):
            self._diagnostics.append(
                Diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    code=DiagnosticCode.LOCKS_TABLE_REQUIRES_LOCK_MANAGER_WHEN_RUNTIME_ENABLED,
                    message=(
                        "Using the DynamoDB Locks Table component with the Python "
                        "Runtime component requires adding the Lock Manager component "
                        "to ensure proper handling of distributed locks. Consider "
                        "adding the Lock Manager component to manage lock acquisition, "
                        "heartbeating, and release operations correctly."
                    ),
                    path=component_path(name),
                    details=locks_table_runtime_details(
                        component_name=name,
                        component=component,
                        runtime_lock_manager_enabled=LOCK_MANAGER.type
                        in enabled_component_types,
                        enabled_component_types=enabled_component_types,
                    ),
                )
            )

    def has_errors(self) -> bool:
        return any(d.severity == DiagnosticSeverity.ERROR for d in self._diagnostics)

    def has_warnings(self) -> bool:
        return any(d.severity == DiagnosticSeverity.WARNING for d in self._diagnostics)
