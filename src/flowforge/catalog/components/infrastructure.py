from flowforge.catalog.models import ComponentDefinition, ComponentKind

API_GATEWAY = ComponentDefinition(
    type="api_gateway",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="API Gateway",
    description=(
        "Exposes HTTP endpoints for submitting or inspecting workflow jobs. "
        "Use this when a generated project needs an external API entrypoint."
    ),
    dependencies=["lambda_submitter"],
)

LAMBDA_SUBMITTER = ComponentDefinition(
    type="lambda_submitter",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="Lambda Submitter",
    description=(
        "Handles job-submission requests, validates input, creates initial job "
        "records, and starts the configured workflow or async processing path."
    ),
    dependencies=["step_functions_standard", "dynamodb_jobs_table"],
    supports_alarms=True,
    default_alarm_templates=[
        "cloudwatch/lambda_errors",
        "cloudwatch/lambda_throttles",
        "cloudwatch/lambda_duration",
    ],
)

LAMBDA_WORKER = ComponentDefinition(
    type="lambda_worker",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="Lambda Worker",
    description=(
        "Provides a Lambda execution unit for processing individual tasks, "
        "queue messages, or Distributed Map items. Generated scaffolds should "
        "leave domain work explicit and editable."
    ),
    dependencies=["cloudwatch_logs"],
    supports_alarms=True,
    default_alarm_templates=[
        "cloudwatch/lambda_errors",
        "cloudwatch/lambda_throttles",
        "cloudwatch/lambda_duration",
    ],
)

SQS_STANDARD_QUEUE = ComponentDefinition(
    type="sqs_standard_queue",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="SQS Standard Queue",
    description=(
        "Adds a standard SQS queue for open-ended asynchronous work, "
        "producer/consumer buffering, or decoupling workers from request-time "
        "execution. Use this for continuous event streams rather than bounded "
        "batch fan-out."
    ),
    supports_alarms=True,
    default_alarm_templates=[
        "cloudwatch/sqs_oldest_message",
        "cloudwatch/sqs_visible_messages",
    ],
)

SQS_DLQ = ComponentDefinition(
    type="sqs_dlq",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="SQS Dead Letter Queue",
    description=(
        "Adds a dead-letter queue for messages that exceed the configured retry limit. "
        "Use this to preserve failed work for inspection and redrive."
    ),
    dependencies=["sqs_standard_queue"],
    supports_alarms=True,
    default_alarm_templates=[
        "cloudwatch/sqs_dlq_visible_messages",
    ],
)

DYNAMODB_JOBS_TABLE = ComponentDefinition(
    type="dynamodb_jobs_table",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="DynamoDB Jobs Table",
    description=(
        "Stores job-level state such as status, workflow execution ARN, input/output "
        "references, task counts, timestamps, and failure summaries."
    ),
    supports_alarms=True,
    default_alarm_templates=[
        "cloudwatch/dynamodb_throttled_requests",
        "cloudwatch/dynamodb_system_errors",
    ],
)

DYNAMODB_TASKS_TABLE = ComponentDefinition(
    type="dynamodb_tasks_table",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="DynamoDB Tasks Table",
    description=(
        "Stores task-level state such as task status, attempt count, input/output "
        "references, errors, and idempotency information."
    ),
    supports_alarms=True,
    default_alarm_templates=[
        "cloudwatch/dynamodb_throttled_requests",
        "cloudwatch/dynamodb_system_errors",
    ],
)

DYNAMODB_LOCKS_TABLE = ComponentDefinition(
    type="dynamodb_locks_table",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="DynamoDB Locks Table",
    description=(
        "Stores DynamoDB-backed lease records for coordinating access to shared "
        "resources such as tenants, partitions, external APIs, or exclusive "
        "writers. Correct locking still depends on generated runtime code using "
        "conditional acquire, heartbeat, and release operations."
    ),
    supports_alarms=True,
    default_alarm_templates=[
        "cloudwatch/dynamodb_throttled_requests",
        "cloudwatch/dynamodb_system_errors",
    ],
)

S3_ARTIFACT_BUCKET = ComponentDefinition(
    type="s3_artifact_bucket",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="S3 Artifact Bucket",
    description=(
        "Stores workflow inputs, manifests, intermediate outputs, final results, "
        "and other generated artifacts that are too large or "
        "durable for workflow state."
    ),
)

COMPONENTS = [
    API_GATEWAY,
    LAMBDA_SUBMITTER,
    LAMBDA_WORKER,
    SQS_STANDARD_QUEUE,
    SQS_DLQ,
    DYNAMODB_JOBS_TABLE,
    DYNAMODB_TASKS_TABLE,
    DYNAMODB_LOCKS_TABLE,
    S3_ARTIFACT_BUCKET,
]
