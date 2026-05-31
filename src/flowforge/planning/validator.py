from collections import defaultdict

from flowforge.catalog.components.infrastructure import (
    API_GATEWAY,
    LAMBDA_WORKER,
    S3_ARTIFACT_BUCKET,
    SQS_DLQ,
    SQS_STANDARD_QUEUE,
)
from flowforge.catalog.components.observability import CLOUDWATCH_ALARMS
from flowforge.catalog.components.workflow import DISTRIBUTED_MAP
from flowforge.catalog.models import ComponentKind
from flowforge.catalog.registry import ComponentRegistry
from flowforge.planning.diagnostics import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
)
from flowforge.planning.schemas import ComponentConfig, ProjectPlan


class Validator:
    """Validates a project plan for correctness, consistency, and best practices, and
    produces diagnostics for any issues found."""

    plan: ProjectPlan
    _diagnostics: list[Diagnostic]

    def __init__(self, plan: ProjectPlan, plan_path: str | None = None):
        self.plan = plan
        self.plan_path = plan_path
        self._components_by_kind = defaultdict(list)
        self._diagnostics = []

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
        for name, component in self.plan.components.items():
            if not ComponentRegistry.is_valid_component_type(component.type):
                self._diagnostics.append(
                    Diagnostic(
                        severity=DiagnosticSeverity.ERROR,
                        code=DiagnosticCode.INVALID_COMPONENT,
                        message=f"Invalid component type: {component.type}",
                        path=self.plan_path,
                        details={name: component.model_dump()},
                    )
                )
                continue
            self._components_by_kind[
                ComponentRegistry.get_component_kind(component.type)
            ].append(component)
            self._validate_component_dependencies(name, component)
            self._validate_component_compatibility(name, component)
            match component.type:
                case DISTRIBUTED_MAP.type:
                    self._validate_distributed_map_component(component)
                case SQS_DLQ.type:
                    self._validate_sqs_dlq_component(component)
                case LAMBDA_WORKER.type:
                    self._validate_lambda_worker_component(component)
                case CLOUDWATCH_ALARMS.type:
                    self._validate_cloudwatch_alarm_component(component)
        return self._diagnostics

    def _validate_component_dependencies(self, name: str, component: ComponentConfig):
        for dependency in ComponentRegistry.get_component_dependencies(component.type):
            if dependency not in [c.type for c in self.plan.components.values()]:
                self._diagnostics.append(
                    Diagnostic(
                        severity=DiagnosticSeverity.ERROR,
                        code=DiagnosticCode.MISSING_COMPONENT_DEPENDENCY,
                        message=(
                            f"Component '{name}' is missing dependency: "
                            f"{dependency}"
                        ),
                        path=self.plan_path,
                        details={
                            name: component.model_dump(),
                            "missing_dependency": dependency,
                        },
                    )
                )

    def _validate_component_compatibility(self, name: str, component: ComponentConfig):
        for conflict in ComponentRegistry.get_component_conflicts(component.type):
            if conflict in [c.type for c in self.plan.components.values()]:
                self._diagnostics.append(
                    Diagnostic(
                        severity=DiagnosticSeverity.ERROR,
                        code=DiagnosticCode.INCOMPATIBLE_COMPONENTS,
                        message=(
                            f"Component '{name}' is incompatible with "
                            f"component type: {conflict}"
                        ),
                        path=self.plan_path,
                        details={
                            name: component.model_dump(),
                            "conflicting_component": conflict,
                        },
                    )
                )

    def _validate_cloudwatch_alarm_component(self, component: ComponentConfig):
        if len(self._components_by_kind[ComponentKind.INFRASTRUCTURE]) < 1:
            self._diagnostics.append(
                Diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    code=DiagnosticCode.INCOMPATIBLE_COMPONENTS,
                    message=(
                        "A CloudWatch Alarm component requires at least one "
                        "infrastructure component to be present in the plan. "
                        "Consider adding an infrastructure component such as a "
                        "DynamoDB Jobs Table or SQS Standard Queue to store job "
                        "data and ensure proper monitoring and alerting."
                    ),
                    path=self.plan_path,
                    details={"cloudwatch_alarm_component": component.model_dump()},
                )
            )

    def _validate_distributed_map_component(self, component: ComponentConfig):
        if component.type == DISTRIBUTED_MAP.type:
            enabled_components = ComponentRegistry.get_enabled_components(self.plan)
            if S3_ARTIFACT_BUCKET.type not in [
                c.type for c in enabled_components.values()
            ]:
                self._diagnostics.append(
                    Diagnostic(
                        severity=DiagnosticSeverity.WARNING,
                        code=DiagnosticCode.INCOMPATIBLE_COMPONENTS,
                        message=(
                            "Using a Distributed Map component without an S3 "
                            "Artifact Bucket may lead to performance issues or "
                            "failures due to large payloads. Consider adding "
                            "an S3 Artifact Bucket to store intermediate data."
                        ),
                        path=self.plan_path,
                        details={"distributed_map_component": component.model_dump()},
                    )
                )

    def _validate_sqs_dlq_component(self, component: ComponentConfig):
        if component.type == SQS_DLQ.type:
            enabled_components = ComponentRegistry.get_enabled_components(self.plan)
            if SQS_STANDARD_QUEUE.type not in [
                c.type for c in enabled_components.values()
            ]:
                self._diagnostics.append(
                    Diagnostic(
                        severity=DiagnosticSeverity.ERROR,
                        code=DiagnosticCode.INCOMPATIBLE_COMPONENTS,
                        message=(
                            "Using an SQS Dead Letter Queue without a standard "
                            "SQS Queue may lead to misconfiguration. Consider "
                            "adding an SQS Standard Queue to handle message "
                            "processing and retries."
                        ),
                        path=self.plan_path,
                        details={"sqs_dlq_component": component.model_dump()},
                    )
                )

    def _validate_lambda_worker_component(self, component: ComponentConfig):
        valid_trigger_components = {
            DISTRIBUTED_MAP.type,
            SQS_STANDARD_QUEUE.type,
            API_GATEWAY.type,
        }
        enabled_components = ComponentRegistry.get_enabled_components(self.plan)
        if not any(
            c.type in valid_trigger_components for c in enabled_components.values()
        ):
            self._diagnostics.append(
                Diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    code=DiagnosticCode.INCOMPATIBLE_COMPONENTS,
                    message=(
                        "Using a Lambda Worker component without a valid trigger "
                        "component (Distributed Map, SQS Standard Queue, or API "
                        "Gateway) may lead to a non-functional workflow. Consider "
                        "adding a compatible trigger component to ensure proper "
                        "execution of the Lambda Worker."
                    ),
                    path=self.plan_path,
                    details={"lambda_worker_component": component.model_dump()},
                )
            )

    def has_errors(self) -> bool:
        return any(d.severity == DiagnosticSeverity.ERROR for d in self._diagnostics)

    def has_warnings(self) -> bool:
        return any(d.severity == DiagnosticSeverity.WARNING for d in self._diagnostics)
