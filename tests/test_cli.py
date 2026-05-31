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
