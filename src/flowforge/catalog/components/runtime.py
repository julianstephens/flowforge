from flowforge.catalog.models import ComponentDefinition, ComponentKind

PYTHON_RUNTIME = ComponentDefinition(
    type="python_runtime",
    kind=ComponentKind.RUNTIME,
    display_name="Python Runtime",
    description=(
        "Generates the local Python package structure used by Lambda handlers, "
        "client wrappers, models, workflow helpers, and tests."
    ),
)

PYDANTIC_MODELS = ComponentDefinition(
    type="pydantic_models",
    kind=ComponentKind.RUNTIME,
    display_name="Pydantic Models",
    description=(
        "Generates typed Pydantic models for workflow input, jobs, tasks, messages, "
        "results, locks, and other selected project data structures."
    ),
    dependencies=["python_runtime"],
)

BOTO3_CLIENTS = ComponentDefinition(
    type="boto3_clients",
    kind=ComponentKind.RUNTIME,
    display_name="Boto3 Clients",
    description=(
        "Generates thin boto3 client factories and wrappers for the AWS services "
        "enabled in the plan."
    ),
    dependencies=["python_runtime"],
)

LOCK_MANAGER = ComponentDefinition(
    type="lock_manager",
    kind=ComponentKind.RUNTIME,
    display_name="Lock Manager",
    description=(
        "Generates runtime helpers for acquiring, heartbeating, and releasing "
        "DynamoDB lease locks with conditional writes and owner-token checks. "
        "Use this when tasks need exclusive or concurrency-limited access to "
        "shared resources."
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
        "Generates helpers for making retries safe by deriving idempotency keys, "
        "detecting repeated work, and avoiding duplicate output writes."
    ),
    dependencies=["python_runtime"],
)

COMPONENTS = [
    PYTHON_RUNTIME,
    PYDANTIC_MODELS,
    BOTO3_CLIENTS,
    LOCK_MANAGER,
    IDEMPOTENCY_HELPERS,
]
