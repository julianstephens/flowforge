from flowforge.catalog.models import ComponentDefinition, ComponentKind

CLOUDWATCH_LOGS = ComponentDefinition(
    type="cloudwatch_logs",
    kind=ComponentKind.OBSERVABILITY,
    display_name="CloudWatch Logs",
    description=(
        "Adds CloudWatch log groups and logging configuration for generated "
        "Lambda functions, workflows, and runtime helpers."
    ),
)

CLOUDWATCH_ALARMS = ComponentDefinition(
    type="cloudwatch_alarms",
    kind=ComponentKind.OBSERVABILITY,
    display_name="CloudWatch Alarms",
    description=(
        "Adds a CloudWatch dashboard summarizing the generated workflow's operational "
        "state, such as executions, failures, queue depth, task progress, and lock "
        "contention where available."
    ),
    dependencies=["cloudwatch_logs"],
)

CLOUDWATCH_DASHBOARD = ComponentDefinition(
    type="cloudwatch_dashboard",
    kind=ComponentKind.OBSERVABILITY,
    display_name="CloudWatch Dashboard",
    description=(
        "Adds basic CloudWatch alarms for selected resources, such as Lambda errors, "
        "throttles, SQS message age, DLQ depth, Step Functions failures, "
        "and DynamoDB throttling."
    ),
    dependencies=["cloudwatch_logs"],
)

COMPONENTS = [
    CLOUDWATCH_LOGS,
    CLOUDWATCH_ALARMS,
    CLOUDWATCH_DASHBOARD,
]
