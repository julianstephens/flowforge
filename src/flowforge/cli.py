from rich import print
from typer import Typer

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
    help="List all components in the FlowForge architecture plan",
)
def list_components():
    print(":warning: The 'list-components' command is not implemented yet.")
    raise NotImplementedError
