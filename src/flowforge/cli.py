from collections import defaultdict
from pathlib import Path
from typing import Annotated

import typer
from rich import print
from rich.table import Table
from typer import Typer

from flowforge.catalog.registry import ComponentRegistry
from flowforge.planning.diagnostics import Diagnostic, DiagnosticSeverity
from flowforge.planning.io import load_and_validate_plan
from flowforge.planning.validator import Validator

app = Typer(name="flowforge", help="FlowForge CLI")


@app.command(name="new", help="Create a new FlowForge project")
def new():
    print(":warning: The 'new' command is not implemented yet.")
    raise NotImplementedError


@app.command(
    name="plan",
    help=(
        "Create or update a Flowforge architecture plan without "
        "generating project files"
    ),
)
def plan():
    print(":warning: The 'plan' command is not implemented yet.")
    raise NotImplementedError


@app.command(
    name="generate",
    help="Generate project files based on the FlowForge architecture plan",
)
def generate():
    print(":warning: The 'generate' command is not implemented yet.")
    raise NotImplementedError


@app.command(name="validate-plan", help="Validate the FlowForge architecture plan")
def validate(
    plan_path: Annotated[
        Path,
        typer.Argument(
            help="Path to the project plan file",
            dir_okay=False,
            exists=True,
        ),
    ],
):
    try:
        plan = load_and_validate_plan(str(plan_path))
    except Exception as e:
        print(f":x: Failed to load and validate plan: {e}")
        raise typer.Exit(code=1) from e
    validator = Validator(plan, str(plan_path))
    diags = validator.validate()
    if len(diags) == 0:
        print(":white_check_mark: Plan is valid with no issues found.")
    else:
        diags_by_severity: dict[DiagnosticSeverity, list[Diagnostic]] = defaultdict(
            list
        )
        for diag in diags:
            diags_by_severity[diag.severity].append(diag)
        print(f":warning: Plan has {len(diags)} issue(s):")
        color_map = {
            "error": "red",
            "warning": "yellow",
            "info": "cyan",
        }
        for severity in DiagnosticSeverity.__members__.values():
            if severity in diags_by_severity and len(diags_by_severity[severity]) > 0:
                sev = severity.value
                print(
                    f"\n[bold {color_map[sev]}]{sev.upper()}S:"
                    f"[/bold {color_map[sev]}]"
                )
                for diag in diags_by_severity[severity]:
                    print(f"- {diag.message}")
                    if diag.path:
                        print(f"  Path: {diag.path}")
                    if diag.details:
                        print(f"  Details: {diag.details}")
        raise typer.Exit(code=1 if validator.has_errors() else 0)


@app.command(
    name="list-components",
    help="List available components in the FlowForge catalog",
)
def list_components():
    components = list(ComponentRegistry.list_components())
    if not components or len(components) == 0:
        print(":x: No components found in the registry.")
        raise typer.Exit(code=1)

    table = Table(
        show_header=True, header_style="bold magenta", show_lines=True, padding=(1, 1)
    )
    table.add_column("Type", style="dim")
    table.add_column("Display Name")
    table.add_column("Description")
    for component in components:
        table.add_row(component.type, component.display_name, component.description)
    print(table)
