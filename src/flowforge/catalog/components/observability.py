from flowforge.catalog.models import ComponentDefinition, ComponentKind

CLOUDWATCH_LOGS = ComponentDefinition(
    type="cloudwatch_logs",
    kind=ComponentKind.OBSERVABILITY,
    display_name="CloudWatch Logs",
    description=(
        "A CloudWatch Logs component that can be used to manage CloudWatch "
        "Logs resources"
    ),
)

CLOUDWATCH_ALARMS = ComponentDefinition(
    type="cloudwatch_alarms",
    kind=ComponentKind.OBSERVABILITY,
    display_name="CloudWatch Alarms",
    description=(
        "A CloudWatch Alarms component that can be used to manage CloudWatch "
        "Alarms resources"
    ),
    dependencies=["cloudwatch_logs"],
)

CLOUDWATCH_DASHBOARD = ComponentDefinition(
    type="cloudwatch_dashboard",
    kind=ComponentKind.OBSERVABILITY,
    display_name="CloudWatch Dashboard",
    description=(
        "A CloudWatch Dashboard component that can be used to manage "
        "CloudWatch Dashboard resources"
    ),
    dependencies=["cloudwatch_logs"],
)

COMPONENTS = [
    CLOUDWATCH_LOGS,
    CLOUDWATCH_ALARMS,
    CLOUDWATCH_DASHBOARD,
]
