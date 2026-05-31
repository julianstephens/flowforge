# Components

A component is a named capability that can contribute files, validation metadata, defaults, dependencies, and explanatory text to a generated project. It is not itself an AWS resource and it is not the runtime implementation.

Examples:

- `sqs_standard_queue` maps closely to an AWS SQS queue.
- `distributed_map` maps to part of a Step Functions ASL definition, not a standalone Terraform resource.
- `lock_manager` maps to generated Python runtime code, not Terraform.
- `pydantic_models` maps to generated Python files.
- `cloudwatch_alarms` maps to multiple Terraform resources depending on what else is enabled.

## Component Types

- `infrastructure`: typically contribute Terraform resources
- `workflow`: affect ASL and state machine generation
- `runtime`: emit Python package code
- `observability`: emit Terraform resources and ASL for monitoring and alerting
- `documentation`: emit markdown files for documentation
