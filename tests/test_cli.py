from flowforge.cli import app


def test_list_components(cli_runner):
    result = cli_runner.invoke(app, ["list-components"])
    assert result.exit_code == 0
    assert "cloudwatch_logs" in result.stdout
    assert "CloudWatch Logs" in result.stdout
