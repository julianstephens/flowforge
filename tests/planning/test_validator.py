from flowforge.catalog.components.infrastructure import (
    SQS_STANDARD_QUEUE,
)
from flowforge.catalog.components.workflow import (
    DISTRIBUTED_MAP,
    STEP_FUNCTIONS_STANDARD,
)
from flowforge.catalog.registry import ComponentRegistry
from flowforge.planning.diagnostics import DiagnosticCode, DiagnosticSeverity
from flowforge.planning.io import load_and_validate_plan
from flowforge.planning.schemas import (
    AwsConfig,
    ComponentConfig,
    ProjectConfig,
    ProjectPlan,
    RuntimeConfig,
)
from flowforge.planning.validator import Validator


def _make_plan(components: dict[str, dict]) -> ProjectPlan:
    return ProjectPlan(
        project=ProjectConfig(
            name="test",
            package_name="test",
            runtime="python",
            iac="terraform",
        ),
        aws=AwsConfig(region="us-east-1"),
        components={k: ComponentConfig(**v) for k, v in components.items()},
        runtime=RuntimeConfig(
            pydantic_models=False,
            boto3_clients=False,
            lock_manager=False,
            idempotency_helpers=False,
            structured_logging=False,
        ),
    )


class TestValidator:
    def test_valid_plan(self, test_plans):
        for valid_plan_path in test_plans["valid"]:
            plan = load_and_validate_plan(valid_plan_path)
            validator = Validator(plan, valid_plan_path)
            diags = validator.validate()
            assert len(diags) == 0, f"Expected no diagnostics, but got: {diags}"

    def test_invalid_plan(self, test_plans):
        for invalid_plan_path in test_plans["invalid"]:
            plan = load_and_validate_plan(invalid_plan_path)
            validator = Validator(plan, invalid_plan_path)
            diags = validator.validate()
            assert len(diags) > 0, "Expected diagnostics for invalid plan, but got none"

    def test_unknown_component_type_produces_invalid_component(self):
        plan = _make_plan({"bad": {"type": "nonexistent_type_xyz", "enabled": True}})
        diags = Validator(plan).validate()
        assert len(diags) == 1
        assert diags[0].code == DiagnosticCode.UNKNOWN_COMPONENT_TYPE

    def test_missing_dependency_produces_missing_component_dependency(self):
        # step_functions_standard depends on cloudwatch_logs; omit cloudwatch_logs
        plan = _make_plan(
            {"orchestrator": {"type": STEP_FUNCTIONS_STANDARD.type, "enabled": True}}
        )
        diags = Validator(plan).validate()
        assert any(d.code == DiagnosticCode.MISSING_COMPONENT_DEPENDENCY for d in diags)

    def test_disabled_dependency_does_not_satisfy_enabled_component(self):
        # cloudwatch_logs is in the plan but disabled, so the dependency is unsatisfied
        plan = _make_plan(
            {
                "orchestrator": {"type": STEP_FUNCTIONS_STANDARD.type, "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": False},
            }
        )
        diags = Validator(plan).validate()
        assert any(d.code == DiagnosticCode.MISSING_COMPONENT_DEPENDENCY for d in diags)

    def test_disabled_conflict_does_not_invalidate_plan(self, monkeypatch):
        # Patch conflicts so step_functions_standard conflicts with sqs_standard_queue,
        # but sqs_standard_queue is disabled — no INCOMPATIBLE_COMPONENTS error
        # expected.
        monkeypatch.setattr(
            ComponentRegistry,
            "get_component_conflicts",
            staticmethod(
                lambda ct: (
                    [SQS_STANDARD_QUEUE.type]
                    if ct == STEP_FUNCTIONS_STANDARD.type
                    else []
                )
            ),
        )
        plan = _make_plan(
            {
                "orchestrator": {"type": STEP_FUNCTIONS_STANDARD.type, "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": True},
                "queue": {"type": SQS_STANDARD_QUEUE.type, "enabled": False},
            }
        )
        diags = Validator(plan).validate()
        assert not any(d.code == DiagnosticCode.COMPONENT_CONFLICT for d in diags)

    def test_distributed_map_without_step_functions_fails(self):
        # distributed_map depends on step_functions_standard; omit it
        plan = _make_plan(
            {
                "batch_map": {"type": DISTRIBUTED_MAP.type, "enabled": True},
                "worker": {"type": "lambda_worker", "enabled": True},
                "artifacts": {"type": "s3_artifact_bucket", "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": True},
            }
        )
        diags = Validator(plan).validate()
        missing_dep_diags = [
            d for d in diags if d.code == DiagnosticCode.MISSING_COMPONENT_DEPENDENCY
        ]
        assert any(
            STEP_FUNCTIONS_STANDARD.type in str(d.details.get("missing_dependency", ""))
            for d in missing_dep_diags
        )

    def test_distributed_map_without_s3_warns(self):
        # s3_artifact_bucket absent → WARNING from the distributed-map-specific check
        plan = _make_plan(
            {
                "orchestrator": {"type": STEP_FUNCTIONS_STANDARD.type, "enabled": True},
                "batch_map": {"type": DISTRIBUTED_MAP.type, "enabled": True},
                "worker": {"type": "lambda_worker", "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": True},
            }
        )
        diags = Validator(plan).validate()
        matching = [
            d
            for d in diags
            if d.code == DiagnosticCode.DISTRIBUTED_MAP_WITHOUT_ARTIFACT_BUCKET
        ]
        assert len(matching) == 1
        assert matching[0].severity == DiagnosticSeverity.WARNING

    def test_distributed_map_with_s3_no_warning(self):
        # s3_artifact_bucket present → no DISTRIBUTED_MAP_WITHOUT_ARTIFACT_BUCKET
        # diagnostic
        plan = _make_plan(
            {
                "orchestrator": {"type": STEP_FUNCTIONS_STANDARD.type, "enabled": True},
                "batch_map": {"type": DISTRIBUTED_MAP.type, "enabled": True},
                "worker": {"type": "lambda_worker", "enabled": True},
                "artifacts": {"type": "s3_artifact_bucket", "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": True},
            }
        )
        diags = Validator(plan).validate()
        assert not any(
            d.code == DiagnosticCode.DISTRIBUTED_MAP_WITHOUT_ARTIFACT_BUCKET
            for d in diags
        )

    def test_sqs_dlq_without_sqs_queue_fails(self):
        plan = _make_plan({"dlq": {"type": "sqs_dlq", "enabled": True}})
        diags = Validator(plan).validate()
        assert any(
            d.code == DiagnosticCode.SQS_DLQ_REQUIRES_QUEUE
            and d.severity == DiagnosticSeverity.ERROR
            for d in diags
        )

    def test_lambda_worker_without_trigger_fails(self):
        # cloudwatch_logs satisfies the lambda_worker dependency; no trigger present
        plan = _make_plan(
            {
                "worker": {"type": "lambda_worker", "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": True},
            }
        )
        diags = Validator(plan).validate()
        assert any(
            d.code == DiagnosticCode.LAMBDA_WORKER_REQUIRES_TRIGGER
            and d.severity == DiagnosticSeverity.ERROR
            for d in diags
        )

    def test_cloudwatch_alarms_without_infrastructure_fails(self):
        # cloudwatch_logs satisfies cloudwatch_alarms dependency but is not an
        # alarmable component, so the alarm check should still fail
        plan = _make_plan(
            {
                "alarms": {"type": "cloudwatch_alarms", "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": True},
            }
        )
        diags = Validator(plan).validate()
        assert any(
            d.code == DiagnosticCode.CLOUDWATCH_ALARMS_REQUIRE_MONITORED_RESOURCE
            and d.severity == DiagnosticSeverity.ERROR
            for d in diags
        )

    def test_cloudwatch_alarms_with_alarmable_component_passes(self):
        # sqs_standard_queue supports alarms, so no alarm-related error expected
        plan = _make_plan(
            {
                "alarms": {"type": "cloudwatch_alarms", "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": True},
                "queue": {"type": SQS_STANDARD_QUEUE.type, "enabled": True},
            }
        )
        diags = Validator(plan).validate()
        assert not any(
            d.code == DiagnosticCode.CLOUDWATCH_ALARMS_REQUIRE_MONITORED_RESOURCE
            for d in diags
        )

    def test_cloudwatch_alarm_validation_is_order_independent(self):
        # alarms component listed before the alarmable component; should still pass
        plan = _make_plan(
            {
                "alarms": {"type": "cloudwatch_alarms", "enabled": True},
                "queue": {"type": SQS_STANDARD_QUEUE.type, "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": True},
            }
        )
        diags = Validator(plan).validate()
        assert not any(
            d.code == DiagnosticCode.CLOUDWATCH_ALARMS_REQUIRE_MONITORED_RESOURCE
            for d in diags
        )

    def test_cloudwatch_alarms_before_infrastructure_in_yaml_does_not_fail(self):
        # cloudwatch_alarms appears before the infrastructure component in iteration
        # order (as it would when declared first in YAML); the validator must not
        # produce a false CLOUDWATCH_ALARMS_REQUIRE_MONITORED_RESOURCE error
        plan = _make_plan(
            {
                "alarms": {"type": "cloudwatch_alarms", "enabled": True},
                "queue": {"type": SQS_STANDARD_QUEUE.type, "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": True},
            }
        )
        diags = Validator(plan).validate()
        assert not any(
            d.code == DiagnosticCode.CLOUDWATCH_ALARMS_REQUIRE_MONITORED_RESOURCE
            for d in diags
        )

    def test_validate_does_not_duplicate_diagnostics_on_second_call(self):
        plan = _make_plan({"bad": {"type": "nonexistent_type_xyz", "enabled": True}})
        validator = Validator(plan)
        first = validator.validate()
        second = validator.validate()
        assert len(first) == len(second)

    def test_invalid_component_plus_rule_checked_component_does_not_crash(self):
        # unknown type alongside lambda_worker (which triggers its own rule checks)
        plan = _make_plan(
            {
                "bad": {"type": "nonexistent_type_xyz", "enabled": True},
                "worker": {"type": "lambda_worker", "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": True},
            }
        )
        diags = Validator(plan).validate()  # must not raise
        assert any(d.code == DiagnosticCode.UNKNOWN_COMPONENT_TYPE for d in diags)
        assert any(
            d.code == DiagnosticCode.LAMBDA_WORKER_REQUIRES_TRIGGER for d in diags
        )
