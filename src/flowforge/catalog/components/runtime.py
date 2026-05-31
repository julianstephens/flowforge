from flowforge.catalog.models import ComponentDefinition, ComponentKind

PYTHON_RUNTIME = ComponentDefinition(
    type="python_runtime",
    kind=ComponentKind.RUNTIME,
    display_name="Python Runtime",
    description=(
        "A Python Runtime component that can be used to manage Python "
        "runtime environments for executing tasks"
    ),
)

PYDANTIC_MODELS = ComponentDefinition(
    type="pydantic_models",
    kind=ComponentKind.RUNTIME,
    display_name="Pydantic Models",
    description=(
        "A Pydantic Models component that can be used to manage Pydantic "
        "models for data validation and serialization"
    ),
    dependencies=["python_runtime"],
)

BOTO3_CLIENTS = ComponentDefinition(
    type="boto3_clients",
    kind=ComponentKind.RUNTIME,
    display_name="Boto3 Clients",
    description=(
        "A Boto3 Clients component that can be used to manage Boto3 clients "
        "for interacting with AWS services"
    ),
    dependencies=["python_runtime"],
)

LOCK_MANAGER = ComponentDefinition(
    type="lock_manager",
    kind=ComponentKind.RUNTIME,
    display_name="Lock Manager",
    description=(
        "A Lock Manager component that can be used to manage distributed "
        "locks for coordinating access to shared resources"
    ),
    dependencies=[
        "python_runtime",
        "boto3_clients",
        "pydantic_models",
        "dynamodb_locks_table",
    ],
)

IDEMPOTENCY_HELPERS = ComponentDefinition(
    type="idempotency_helpers",
    kind=ComponentKind.RUNTIME,
    display_name="Idempotency Helpers",
    description=(
        "An Idempotency Helpers component that can be used to manage "
        "idempotency helpers for ensuring idempotent task execution"
    ),
    dependencies=["python_runtime"],
)
