# Components

A component is a named generation capability. It can contribute metadata, defaults, validation rules, template groups, outputs, warnings, and explanatory text to a generated project.

A component is not always a one-to-one AWS resource.

| Component            | Meaning                                                          |
| -------------------- | ---------------------------------------------------------------- |
| `sqs_standard_queue` | Maps closely to an AWS SQS queue.                                |
| `distributed_map`    | Maps to part of a Step Functions state machine definition.       |
| `lock_manager`       | Maps to generated Python runtime code.                           |
| `pydantic_models`    | Maps to generated Python model files.                            |
| `cloudwatch_alarms`  | Applies default alarm templates to enabled alarmable components. |

## Component kinds

| Kind             | Purpose                                                   |
| ---------------- | --------------------------------------------------------- |
| `infrastructure` | Usually contributes Terraform-managed AWS resources.      |
| `workflow`       | Affects Step Functions / ASL generation.                  |
| `runtime`        | Emits Python package code.                                |
| `observability`  | Emits monitoring, logging, dashboard, or alarm resources. |
| `documentation`  | Emits generated documentation.                            |

## Component definition shape

Each catalog component is described by a `ComponentDefinition`.

| Field                     | Purpose                                                                |
| ------------------------- | ---------------------------------------------------------------------- |
| `type`                    | Stable catalog identifier, for example `lambda_worker`.                |
| `kind`                    | Component category.                                                    |
| `display_name`            | Human-readable name.                                                   |
| `description`             | Brief explanation shown in CLI/docs.                                   |
| `dependencies`            | Component types that must also be enabled.                             |
| `conflicts`               | Component types that cannot be enabled at the same time.               |
| `default_config`          | Default plan configuration for this component.                         |
| `terraform_templates`     | Terraform template groups this component may contribute.               |
| `python_templates`        | Python runtime template groups this component may contribute.          |
| `lambda_templates`        | Lambda handler template groups this component may contribute.          |
| `workflow_templates`      | Workflow / ASL template groups this component may contribute.          |
| `docs_templates`          | Documentation template groups this component may contribute.           |
| `outputs`                 | Named outputs this component may expose later.                         |
| `warnings`                | Static warning codes or notes associated with the component.           |
| `supports_alarms`         | Whether default CloudWatch alarms can be generated for this component. |
| `default_alarm_templates` | Alarm template groups used when `cloudwatch_alarms` is enabled.        |

## Plan key vs component type

Plan component keys are local names chosen by the plan.

Component `type` values refer to catalog components.

```yaml
components:
  worker:
    type: lambda_worker
    enabled: true
```

| Value           | Meaning                                                 |
| --------------- | ------------------------------------------------------- |
| `worker`        | Local plan key. Used in paths like `components.worker`. |
| `lambda_worker` | Catalog component type. Used for lookup and validation. |

Validation and generation should resolve catalog definitions through `type`, not through the local plan key.

## Dependency semantics

Dependencies are component types.

If component A lists component B in `dependencies`, then enabling A requires at least one enabled component with type B.

| Example                                | Meaning                                              |
| -------------------------------------- | ---------------------------------------------------- |
| `sqs_dlq -> sqs_standard_queue`        | A DLQ requires a queue.                              |
| `lambda_worker -> cloudwatch_logs`     | A worker requires logs.                              |
| `lock_manager -> dynamodb_locks_table` | Runtime lock helpers require a lock table.           |
| `pydantic_models -> python_runtime`    | Generated models require the Python runtime package. |

Disabled components do not satisfy dependencies.

## Conflict semantics

Conflicts are component types.

If component A lists component B in `conflicts`, then A and B cannot both be enabled.

Disabled components do not create conflicts.

Most v0 components have no conflicts.

## Alarm semantics

`cloudwatch_alarms` is a global observability component.

It does not target specific plan keys in v0. When enabled, it applies default alarm templates to all enabled components whose catalog definition has:

```python
supports_alarms=True
```

and one or more entries in:

```python
default_alarm_templates
```

| Rule                            | Meaning                                                   |
| ------------------------------- | --------------------------------------------------------- |
| `cloudwatch_alarms` enabled     | Generate default alarms for enabled alarmable components. |
| No alarmable components enabled | Validation error.                                         |
| Alarmable components enabled    | Use their `default_alarm_templates`.                      |
| Explicit YAML targets           | Not supported in v0.                                      |

Future versions may support explicit alarm targets:

```yaml
components:
  alarms:
    type: cloudwatch_alarms
    enabled: true
    targets:
      - worker
      - task_queue
```

Do not implement this in v0.

## Alarmable components

Initial alarmable components should be conservative.

| Component                 | `supports_alarms` | Default alarm templates                                                                                                                    |
| ------------------------- | ----------------: | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `lambda_submitter`        |            `true` | `cloudwatch/lambda_errors`, `cloudwatch/lambda_throttles`, `cloudwatch/lambda_duration`                                                    |
| `lambda_worker`           |            `true` | `cloudwatch/lambda_errors`, `cloudwatch/lambda_throttles`, `cloudwatch/lambda_duration`                                                    |
| `sqs_standard_queue`      |            `true` | `cloudwatch/sqs_oldest_message`, `cloudwatch/sqs_visible_messages`                                                                         |
| `sqs_dlq`                 |            `true` | `cloudwatch/sqs_dlq_visible_messages`                                                                                                      |
| `dynamodb_jobs_table`     |            `true` | `cloudwatch/dynamodb_throttled_requests`, `cloudwatch/dynamodb_system_errors`                                                              |
| `dynamodb_tasks_table`    |            `true` | `cloudwatch/dynamodb_throttled_requests`, `cloudwatch/dynamodb_system_errors`                                                              |
| `dynamodb_locks_table`    |            `true` | `cloudwatch/dynamodb_throttled_requests`, `cloudwatch/dynamodb_system_errors`                                                              |
| `step_functions_standard` |            `true` | `cloudwatch/stepfunctions_failed_executions`, `cloudwatch/stepfunctions_timed_out_executions`, `cloudwatch/stepfunctions_throttled_events` |

Do not mark `s3_artifact_bucket` as alarmable in v0.

Do not mark `distributed_map` as alarmable in v0. It is part of workflow structure, not a standalone generated resource at this stage.

## Initial components

### Infrastructure

| Type                   | Purpose                                                                     |
| ---------------------- | --------------------------------------------------------------------------- |
| `api_gateway`          | Exposes HTTP endpoints for submitting or inspecting workflow jobs.          |
| `lambda_submitter`     | Handles job submission, creates job records, and starts workflow execution. |
| `lambda_worker`        | Processes tasks, queue messages, or Distributed Map items.                  |
| `sqs_standard_queue`   | Buffers open-ended asynchronous work.                                       |
| `sqs_dlq`              | Stores failed messages after retry exhaustion.                              |
| `dynamodb_jobs_table`  | Stores job-level state.                                                     |
| `dynamodb_tasks_table` | Stores task-level state.                                                    |
| `dynamodb_locks_table` | Stores DynamoDB-backed lease records.                                       |
| `s3_artifact_bucket`   | Stores inputs, manifests, intermediate outputs, and final artifacts.        |

### Workflow

| Type                      | Purpose                                                            |
| ------------------------- | ------------------------------------------------------------------ |
| `step_functions_standard` | Adds a durable Standard workflow for orchestration.                |
| `distributed_map`         | Adds bounded batch fan-out through Step Functions Distributed Map. |

### Runtime

| Type                  | Purpose                                       |
| --------------------- | --------------------------------------------- |
| `python_runtime`      | Generates the local Python package structure. |
| `pydantic_models`     | Generates typed Pydantic data models.         |
| `boto3_clients`       | Generates thin boto3 client wrappers.         |
| `lock_manager`        | Generates DynamoDB lease-lock helpers.        |
| `idempotency_helpers` | Generates retry-safety helpers.               |

### Observability

| Type                   | Purpose                                               |
| ---------------------- | ----------------------------------------------------- |
| `cloudwatch_logs`      | Adds CloudWatch logging support.                      |
| `cloudwatch_dashboard` | Adds a summary dashboard.                             |
| `cloudwatch_alarms`    | Adds default alarms for enabled alarmable components. |

## Validator responsibilities

The validator consumes catalog metadata and plan configuration.

| Validator check                                     | Source                     |
| --------------------------------------------------- | -------------------------- |
| Unknown component type                              | Registry lookup            |
| Missing dependency                                  | `dependencies` metadata    |
| Component conflict                                  | `conflicts` metadata       |
| CloudWatch alarms without alarmable component       | `supports_alarms` metadata |
| Distributed Map without S3 artifact bucket          | Specialized warning rule   |
| Lambda worker without trigger                       | Specialized rule           |
| Locks table with Python runtime but no lock manager | Specialized rule           |

## What components should not do

Component definitions should not contain generation logic.

| Do not put in component definitions   |
| ------------------------------------- |
| Jinja rendering code                  |
| Terraform construction logic          |
| Step Functions ASL construction logic |
| boto3 implementation code             |
| planner scoring rules                 |
| file-writing logic                    |
| runtime implementation logic          |

Components describe what exists. Other layers decide how to validate, plan, and generate from that description.

## Layer boundaries

| Layer                     | Responsibility                            |
| ------------------------- | ----------------------------------------- |
| `catalog/models.py`       | Defines component metadata structures.    |
| `catalog/components/*.py` | Declares static component definitions.    |
| `catalog/registry.py`     | Looks up and lists component definitions. |
| `planning/validator.py`   | Validates plans using catalog metadata.   |
| `planning/rules.py`       | Recommends components from local rules.   |
| `generation/*`            | Renders files from validated plans.       |
