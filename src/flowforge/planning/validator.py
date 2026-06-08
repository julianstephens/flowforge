from collections import defaultdict

from flowforge.catalog.components.infrastructure import (
    API_GATEWAY,
    DYNAMODB_LOCKS_TABLE,
    LAMBDA_WORKER,
    S3_ARTIFACT_BUCKET,
    SQS_DLQ,
    SQS_STANDARD_QUEUE,
)
from flowforge.catalog.components.runtime import LOCK_MANAGER, PYTHON_RUNTIME
from flowforge.catalog.components.workflow import DISTRIBUTED_MAP
from flowforge.catalog.models import ComponentKind
from flowforge.catalog.registry import ComponentNotFoundError, ComponentRegistry
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
    _components_by_kind: dict[ComponentKind, list[tuple[str, ComponentConfig]]]

    def __init__(self, plan: ProjectPlan, plan_path: str | None = None):
        self.plan = plan
        self.plan_path = plan_path
        self._diagnostics = []
        self._components_by_kind = defaultdict(list)

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
        enabled_configs_by_name: dict[str, ComponentConfig] = {
            name: config
            for name, config in self.plan.components.items()
            if config.enabled
        }
        known_enabled_components_by_name: dict[str, ComponentConfig] = {}
        unknown_enabled_components: dict[str, ComponentConfig] = {}

        # build enabled component lookup and check for unknown types
        for name, component_config in enabled_configs_by_name.items():
            try:
                ComponentRegistry.get_component(component_config.type)
            except ComponentNotFoundError:
                unknown_enabled_components[name] = component_config
            else:
                known_enabled_components_by_name[name] = component_config

        enabled_types = {d.type for d in known_enabled_components_by_name.values()}

        # populate components by kind for known types to use in dependency and
        # compatibility checks
        for name, component_config in known_enabled_components_by_name.items():
            self._components_by_kind[
                ComponentKind(
                    ComponentRegistry.get_component_kind(component_config.type)
                )
            ].append((name, component_config))

        # emit diagnostics for unknown component types
        for name, component_config in unknown_enabled_components.items():
            self._diagnostics.append(
                Diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    code=DiagnosticCode.UNKNOWN_COMPONENT_TYPE,
                    message=f"Unknown component type '{component_config.type}'",
                    path=component_field_path(name, "type"),
                    details=unknown_component_details(
                        component_name=name, component=component_config
                    ),
                )
            )

        for name, component_config in known_enabled_components_by_name.items():
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

        for name, component in self._components_by_kind[ComponentKind.OBSERVABILITY]:
            if component.type == "cloudwatch_alarms":
                self._validate_cloudwatch_alarm_component(
                    name, component, known_enabled_components_by_name
                )

        return self._diagnostics

    def _validate_component_type(self, name: str, component: ComponentConfig) -> bool:
        """Checks if the component type is valid and recognized. If not, adds an error
        diagnostic.

        Args:
            name: The name of the component in the plan.
            component: The ComponentConfig object representing the component's
            configuration.

        Returns:
            True if the component type is valid and recognized, False otherwise.
        """
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
        return True

    def _validate_component_dependencies(
        self, name: str, component: ComponentConfig, enabled_component_types: set[str]
    ):
        """Checks if all dependencies for the component are satisfied by the enabled
        components in the plan. If any dependencies are missing, adds an error
        diagnostic.

        Args:
            name: The name of the component in the plan.
            component: The ComponentConfig object representing the component's
            configuration.
            enabled_component_types: A set of enabled component types in the plan.
        """
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
        """Checks if the component is compatible with other enabled components in the
        plan. If any conflicts are found, adds an error diagnostic.

        Args:
            name: The name of the component in the plan.
            component: The ComponentConfig object representing the component's
            configuration.
            enabled_component_types: A set of enabled component types in the plan.
        """
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
        self,
        name: str,
        component: ComponentConfig,
        known_enabled_components_by_name: dict[str, ComponentConfig],
    ):
        """Checks if there are any enabled components that support CloudWatch alarms
        when the CloudWatch Alarms component is enabled. If not, adds an error
        diagnostic.

        Args:
            name: The name of the CloudWatch Alarms component in the plan.
            component: The ComponentConfig object representing the CloudWatch Alarms
            component's configuration.
            known_enabled_components_by_name: A dictionary of enabled component names to
            their ComponentConfig objects for
            components with recognized types, used to determine which enabled components
            support alarms.
        """
        alarmable_components = {}
        for name, component in known_enabled_components_by_name.items():
            definition = ComponentRegistry.get_component(component.type)
            if definition.supports_alarms:
                alarmable_components[name] = definition

        if not alarmable_components:
            self._diagnostics.append(
                Diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    code=DiagnosticCode.CLOUDWATCH_ALARMS_REQUIRE_MONITORED_RESOURCE,
                    message=(
                        "CloudWatch alarms are enabled, but no enabled component "
                        "supports default alarms."
                    ),
                    path=component_path(name),
                    details=cloudwatch_alarm_details(
                        component_name=name,
                        component=component,
                        alarmable_component_names=set(alarmable_components.keys()),
                        alarmable_component_types={
                            d.type for d in alarmable_components.values()
                        },
                    ),
                )
            )

    def _validate_distributed_map_component(
        self, name: str, component: ComponentConfig, enabled_component_types: set[str]
    ):
        """Checks if a Distributed Map component is enabled without an S3 Artifact
        Bucket component. If so, adds a warning diagnostic about potential performance
        issues and recommends adding an S3 Artifact Bucket.

        Args:
            name: The name of the Distributed Map component in the plan.
            component: The ComponentConfig object representing the Distributed Map
            component's configuration.
            enabled_component_types: A set of enabled component types in the plan
        """
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
        """Checks if an SQS Dead Letter Queue component is enabled without a standard
        SQS Queue. If so, adds an error diagnostic about potential misconfiguration and
        recommends adding an SQS Standard Queue.

        Args:
            name: The name of the SQS Dead Letter Queue component in the plan.
            component: The ComponentConfig object representing the SQS Dead Letter Queue
            component's configuration.
            enabled_component_types: A set of enabled component types in the plan
        """
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
        """Checks if a Lambda Worker component is enabled without a valid trigger
        component (Distributed Map, SQS Standard Queue, or API Gateway). If so,
        adds an error diagnostic about potential non-functionality and recommends adding
        a compatible trigger component.

        Args:
            name: The name of the Lambda Worker component in the plan.
            component: The ComponentConfig object representing the Lambda Worker
            component's configuration.
            enabled_component_types: A set of enabled component types in the plan
        """
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
        """Checks if a DynamoDB Locks Table component is enabled while the Python
        Runtime component is also enabled, but the Lock Manager component is not
        enabled. If so, adds an error diagnostic about potential issues with distributed
        locking and recommends adding the Lock Manager component.

        Args:
            name: The name of the DynamoDB Locks Table component in the plan.
            component: The ComponentConfig object representing the DynamoDB Locks Table
            component's configuration.
            enabled_component_types: A set of enabled component types in the plan
        """
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
