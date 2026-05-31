import pytest

from flowforge.planning.errors import PlanValidationCode
from src.flowforge.planning.io import (
    InvalidPlanFileCode,
    InvalidPlanFileError,
    PlanValidationError,
    is_valid_python_package_name,
    load_plan,
    validate_plan,
)


def test_load_plan():
    plan = load_plan("tests/data/plan.yaml")

    assert plan == {
        "schema_version": 1,
        "project": {
            "name": "csv_importer",
            "package_name": "csv_importer",
            "runtime": "python",
            "iac": "terraform",
        },
        "aws": {"region": "us-east-1", "account_id": None},
        "components": {
            "orchestrator": {"type": "step_functions_standard", "enabled": True},
            "batch_map": {
                "type": "distributed_map",
                "enabled": True,
                "item_source": "s3",
                "input_type": "jsonl",
                "max_concurrency": 500,
                "tolerated_failure_percentage": 5,
                "result_writer": "s3",
            },
            "item_processor": {
                "type": "lambda_worker",
                "enabled": True,
                "runtime": "python3.12",
                "timeout_seconds": 300,
                "memory_mb": 1024,
            },
            "jobs_table": {"type": "dynamodb_jobs_table", "enabled": True},
            "tasks_table": {"type": "dynamodb_tasks_table", "enabled": True},
            "locks_table": {
                "type": "dynamodb_locks_table",
                "enabled": True,
                "ttl_attribute": "expires_at",
            },
            "artifacts": {"type": "s3_artifact_bucket", "enabled": True},
        },
        "runtime": {
            "pydantic_models": True,
            "boto3_clients": True,
            "lock_manager": True,
            "idempotency_helpers": True,
            "structured_logging": True,
        },
    }


def test_load_plan_invalid_yaml():
    with pytest.raises(InvalidPlanFileError) as exc_info:
        load_plan("tests/data/missing.yaml")
    e = exc_info.value
    assert e.code == InvalidPlanFileCode.FILE_NOT_FOUND

    with pytest.raises(InvalidPlanFileError) as exc_info:
        load_plan("tests/data")
    e = exc_info.value
    assert e.code == InvalidPlanFileCode.NOT_A_FILE

    with pytest.raises(InvalidPlanFileError) as exc_info:
        load_plan("tests/data/invalid_extension.txt")
    e = exc_info.value
    assert e.code == InvalidPlanFileCode.INVALID_EXTENSION


def test_validate_plan():
    data = load_plan("tests/data/plan.yaml")

    plan = validate_plan(data)
    assert plan.project.name == "csv_importer"
    assert plan.project.package_name == "csv_importer"
    assert plan.project.runtime == "python"
    assert plan.project.iac == "terraform"

    assert len(plan.components) == 7
    assert "orchestrator" in plan.components
    assert plan.components["orchestrator"].type == "step_functions_standard"
    assert plan.components["orchestrator"].enabled is True

    assert "batch_map" in plan.components
    assert plan.components["batch_map"].type == "distributed_map"
    assert plan.components["batch_map"].enabled is True
    model_data = plan.components["batch_map"].model_dump()
    assert model_data is not None
    assert model_data["item_source"] == "s3"
    assert model_data["input_type"] == "jsonl"
    assert model_data["max_concurrency"] == 500
    assert model_data["tolerated_failure_percentage"] == 5
    assert model_data["result_writer"] == "s3"


def test_validate_invalid_plan():
    with pytest.raises(PlanValidationError) as exc_info:
        validate_plan("not a dict")
    e = exc_info.value
    assert e.code.value == PlanValidationCode.INVALID_SCHEMA.value
    assert "plan file must contain a YAML mapping at the top level" in str(e)

    with pytest.raises(PlanValidationError) as exc_info:
        validate_plan({"schema_version": 999})
    e = exc_info.value
    assert e.code.value == PlanValidationCode.UNSUPPORTED_SCHEMA_VERSION.value
    assert "unsupported schema version '999' (expected '1')" in str(e)

    with pytest.raises(PlanValidationError) as exc_info:
        validate_plan(
            {"schema_version": 1, "project": {"package_name": "invalid-package-name"}}
        )
    e = exc_info.value
    assert e.code.value == PlanValidationCode.INVALID_SCHEMA.value
    assert e.validation_error is not None


def test_is_valid_python_package_name():
    assert is_valid_python_package_name("valid_package_name")
    assert is_valid_python_package_name("valid_pass_package_name_123")
    assert not is_valid_python_package_name("valid-package-name")
    assert not is_valid_python_package_name("invalid package name")
    assert not is_valid_python_package_name("invalid.package.name")
    assert not is_valid_python_package_name("invalid-package-name!")
    assert not is_valid_python_package_name("finally")
    assert not is_valid_python_package_name("123invalid_package_name")
