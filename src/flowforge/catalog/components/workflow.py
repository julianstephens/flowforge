from flowforge.catalog.models import ComponentDefinition, ComponentKind

STEP_FUNCTIONS_STANDARD = ComponentDefinition(
    type="step_functions_standard",
    kind=ComponentKind.WORKFLOW,
    display_name="Step Functions Standard Workflow",
    description=(
        "Adds a Step Functions Standard workflow for durable multi-step orchestration, "
        "retries, branching, fan-out/fan-in, and operational visibility."
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
        "Adds a Step Functions Distributed Map state for large bounded batch "
        "fan-out over S3-backed data, manifests, records, files, or item batches. "
        "Use this for finite batch workloads rather than open-ended queues."
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
