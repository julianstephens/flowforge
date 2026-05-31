from flowforge.catalog.components import ALL_COMPONENTS
from flowforge.cli import app


def test_list_components(cli_runner, mocker):
    result = cli_runner.invoke(app, ["list-components"])
    assert result.exit_code == 0
    for component in ALL_COMPONENTS:
        assert (
            component.type in result.stdout
        ), f"Expected '{component.type}' to be listed in output"

    mocker.patch(
        "flowforge.catalog.registry.ComponentRegistry.list_components", return_value=[]
    )
    result = cli_runner.invoke(app, ["list-components"])
    assert result.exit_code == 1


def test_validate_plan(cli_runner, test_plan_path):
    result = cli_runner.invoke(app, ["validate", str(test_plan_path)])
    assert result.exit_code == 0


def test_validate_plan_with_invalid_extension(cli_runner, invalid_extension_plan_path):
    result = cli_runner.invoke(app, ["validate", str(invalid_extension_plan_path)])
    assert result.exit_code == 1


def test_validate_plan_with_semantic_errors(cli_runner, test_plans):
    for invalid_plan_path in test_plans["invalid"]:
        result = cli_runner.invoke(app, ["validate", str(invalid_plan_path)])
        assert result.exit_code == 1, f"Expected exit code 1 for {invalid_plan_path}"
