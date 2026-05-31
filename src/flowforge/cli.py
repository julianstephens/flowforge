import typer
from rich import print
from rich.table import Table
from typer import Typer

from flowforge.catalog.registry import ComponentRegistry

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


@app.command(name="validate", help="Validate the FlowForge architecture plan")
def validate():
    print(":warning: The 'validate' command is not implemented yet.")
    raise NotImplementedError


@app.command(
    name="list-components",
    help="List available components in the FlowForge catalog",
)
def list_components():
    components = list(ComponentRegistry.list_components())
    if not components or len(components) == 0:
        print(":error: No components found in the registry.")
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
