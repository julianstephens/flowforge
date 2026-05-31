from flowforge.catalog.models import ComponentDefinition, ComponentKind

API_GATEWAY = ComponentDefinition(
    type="api_gateway",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="API Gateway",
    description="An API Gateway component for managing API Gateway resources",
    dependencies=["lambda_submitter"],
)

LAMBDA_SUBMITTER = ComponentDefinition(
    type="lambda_submitter",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="Lambda Submitter",
    description=(
        "A Lambda Submitter component that can be used to submit tasks to a "
        "serverless environment"
    ),
    dependencies=["step_functions_standard", "dynamodb_jobs_table"],
)

LAMBDA_WORKER = ComponentDefinition(
    type="lambda_worker",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="Lambda Worker",
    description=(
        "A Lambda Worker component that can be used to run tasks in a "
        "serverless environment"
    ),
    dependencies=["cloudwatch_logs"],
)

SQS_STANDARD_QUEUE = ComponentDefinition(
    type="sqs_standard_queue",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="SQS Standard Queue",
    description=(
        "An SQS Standard Queue component that can be used to manage SQS "
        "Standard Queue resources"
    ),
)

SQS_DLQ = ComponentDefinition(
    type="sqs_dlq",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="SQS Dead Letter Queue",
    description=(
        "An SQS Dead Letter Queue component that can be used to manage SQS "
        "Dead Letter Queue resources"
    ),
    dependencies=["sqs_standard_queue"],
)

DYNAMODB_JOBS_TABLE = ComponentDefinition(
    type="dynamodb_jobs_table",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="DynamoDB Jobs Table",
    description=(
        "A DynamoDB Jobs Table component that can be used to manage DynamoDB "
        "tables for job tracking"
    ),
)

DYNAMODB_TASKS_TABLE = ComponentDefinition(
    type="dynamodb_tasks_table",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="DynamoDB Tasks Table",
    description=(
        "A DynamoDB Tasks Table component that can be used to manage DynamoDB "
        "tables for task tracking"
    ),
)

DYNAMODB_LOCKS_TABLE = ComponentDefinition(
    type="dynamodb_locks_table",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="DynamoDB Locks Table",
    description=(
        "A DynamoDB Locks Table component that can be used to manage DynamoDB "
        "tables for lock management"
    ),
)

S3_ARTIFACT_BUCKET = ComponentDefinition(
    type="s3_artifact_bucket",
    kind=ComponentKind.INFRASTRUCTURE,
    display_name="S3 Artifact Bucket",
    description=(
        "An S3 Artifact Bucket component that can be used to manage S3 "
        "buckets for artifact storage"
    ),
)
