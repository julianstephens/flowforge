from flowforge.catalog.models import ComponentDefinition, ComponentKind

STEP_FUNCTIONS_STANDARD = ComponentDefinition(
    type="step_functions_standard",
    kind=ComponentKind.WORKFLOW,
    display_name="Step Functions Standard Workflow",
    description=(
        "A Step Functions Standard Workflow component that can be used to "
        "manage Step Functions Standard Workflow resources"
    ),
    dependencies=[
        "cloudwatch_logs",
    ],
)

DISTRIBUTED_MAP = ComponentDefinition(
    type="distributed_map",
    kind=ComponentKind.WORKFLOW,
    display_name="Distributed Map",
    description=(
        "A Distributed Map component that can be used to manage Step "
        "Functions Distributed Map resources"
    ),
    dependencies=[
        "step_functions_standard",
        "lambda_worker",
        "s3_artifact_bucket",
    ],
)

COMPONENTS = [
    STEP_FUNCTIONS_STANDARD,
    DISTRIBUTED_MAP,
]
