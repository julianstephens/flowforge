import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def test_plan_path():
    return "tests/data/plan.yaml"


@pytest.fixture
def invalid_extension_plan_path():
    return "tests/data/invalid_extension.txt"


@pytest.fixture
def test_plans():
    return {
        "valid": [
            "tests/data/plan.yaml",
            "tests/data/distributed_batch_map_plan.yaml",
            "tests/data/locked_distributed_batch_map_plan.yaml",
        ],
        "invalid": [
            "tests/data/invalid_plan_semantic.yaml",
            "tests/data/invalid_distributed_batch_map_plan.yaml",
            "tests/data/invalid_locks_table_plan.yaml",
            "tests/data/invalid_dlq_plan.yaml",
            "tests/data/invalid_component_type_plan.yaml",
        ],
    }
