# Flowforge Project Specification

## 1. Purpose

Flowforge is a local developer tool for generating AWS-native distributed workflow projects.

The tool helps a developer describe a workflow, review a recommended architecture plan, edit that plan, and generate a local project containing Terraform infrastructure, Python runtime helpers, Pydantic models, and Lambda scaffolds.

Flowforge is not a hosted workflow platform. It is not a replacement for Temporal, Inngest, Trigger.dev, Airflow, Dagster, or AWS Step Functions. It is a project generator that produces plain, inspectable AWS infrastructure and application scaffolding.

The generated project should be understandable and maintainable without Flowforge after generation.

## 2. Core Thesis

Most AWS workflow projects require the same infrastructure pieces repeatedly:

- Step Functions for orchestration
- Distributed Map for large bounded batch fan-out
- Lambda for task execution
- DynamoDB for job/task state and optional locks
- S3 for inputs, outputs, and artifacts
- CloudWatch for logs, metrics, dashboards, and alarms
- SQS for asynchronous queues when the workload is open-ended or event-driven

Flowforge packages these recurring patterns into a deterministic generator.

The tool should recommend a setup from a controlled component catalog, but the user must be able to inspect and edit the plan before files are written.

## 3. Non-Goals

Flowforge should not attempt to do the following in the initial version:

- Require an LLM or remote agent API token
- Generate arbitrary Terraform using unconstrained natural language
- Hide AWS resources behind a proprietary runtime
- Act as a deployment platform
- Own Terraform state
- Replace Step Functions or SQS
- Support every AWS workflow shape
- Support Kubernetes, ECS/Fargate, multi-account deployments, or complex VPC networking in v0
- Generate business-domain logic

The first version should be narrow, deterministic, and inspectable.

## 4. Planning Model

Flowforge uses a plan-first workflow.

```text
user description
  -> local planner proposes architecture.plan.yaml
  -> user reviews/edits plan
  -> validator checks plan
  -> generator writes project files
```

The plan file is the contract between recommendation and generation.

The generator must be deterministic. Given the same plan and the same template version, it should produce the same project structure.

## 5. LLM Policy

LLM-based planning is out of scope for now.

The default planner should use deterministic rules and lightweight local natural-language processing:

- keyword and phrase matching
- synonym groups
- component scoring
- preset selection
- validation rules
- generated warnings and rationale

Remote LLM support may be added later as an optional planner backend. It must never be required for core use.

Future planner modes may include:

- `manual`
- `template`
- `rules`
- `local_nlp`
- `remote_llm` optional later
- `local_llm` optional later

For v0, only `manual`, `template`, and `rules` are required.

## 6. Workflow Pattern Catalog

Flowforge should begin with a small number of high-quality patterns.

### 6.1 Simple Async Queue Worker

Use when work is open-ended, event-driven, or producer/consumer shaped.

Typical resources:

- SQS standard queue
- SQS dead-letter queue
- Lambda worker
- IAM role and policies
- CloudWatch logs and alarms
- Optional DynamoDB state table

Recommended for:

- webhooks
- background jobs
- asynchronous ingestion
- traffic buffering
- continuous event processing

### 6.2 Distributed Batch Map

Use when work is finite, bounded, and dataset-driven.

Typical resources:

- Step Functions Standard workflow
- Distributed Map state
- Lambda item processor
- S3 input/artifact bucket
- DynamoDB jobs table
- DynamoDB tasks table
- CloudWatch logs, metrics, dashboard, and alarms

Recommended for:

- CSV or JSONL batch processing
- S3 object batch processing
- image/document processing
- bounded simulation runs
- fan-out/fan-in workflows

### 6.3 Locked Distributed Batch Map

Use when bounded batch work also has shared-resource constraints.

Typical resources:

- all Distributed Batch Map resources
- DynamoDB locks table
- generated Python lock manager
- lock contention metrics
- runtime helpers for conditional acquire, heartbeat, and release

Recommended for:

- tenant concurrency limits
- exclusive partition writers
- rate-limited external APIs
- scarce shared resources
- contention-sensitive batch processing

## 7. SQS vs Distributed Map Guidance

Flowforge should prefer Step Functions Distributed Map for large bounded batches.

Use Distributed Map when work is:

- finite
- batch-shaped
- dataset-driven
- known at workflow start
- fan-out/fan-in oriented
- backed by S3 input data or a manifest

Use SQS when work is:

- open-ended
- event-driven
- continuously arriving
- producer/consumer shaped
- primarily about buffering independent systems
- not naturally tied to a parent workflow fan-in step

A hybrid Step Functions plus SQS pattern may be added later, but it should not be the default recommendation for large bounded task batches.

## 8. Component Catalog

Components should be enableable or disableable per project.

Initial components:

- `api_gateway`
- `lambda_submitter`
- `lambda_worker`
- `step_functions_standard`
- `distributed_map`
- `sqs_standard_queue`
- `sqs_dlq`
- `dynamodb_jobs_table`
- `dynamodb_tasks_table`
- `dynamodb_locks_table`
- `s3_artifact_bucket`
- `cloudwatch_logs`
- `cloudwatch_dashboard`
- `cloudwatch_alarms`
- `python_runtime`
- `pydantic_models`
- `boto3_clients`
- `lock_manager`
- `idempotency_helpers`

Each component should define:

- name
- description
- dependencies
- conflicts
- Terraform templates
- Python runtime templates, if any
- Lambda handler templates, if any
- validation rules
- warnings
- outputs

## 9. Generated Project Shape

A generated project should look like this:

```text
my-workflow-project/
  README.md
  pyproject.toml
  .env.example
  Makefile

  infra/
    main.tf
    variables.tf
    outputs.tf
    providers.tf
    versions.tf
    modules/
      api_gateway/
      lambda_function/
      sqs_queue/
      dynamodb_table/
      s3_bucket/
      step_function/
      cloudwatch/

  src/
    my_workflow/
      __init__.py
      config.py
      models.py
      clients/
        dynamodb.py
        s3.py
        sqs.py
        stepfunctions.py
      workflow/
        jobs.py
        tasks.py
        locks.py
        idempotency.py
      handlers/
        submit_job.py
        worker.py
        aggregate.py
      observability/
        logging.py
        metrics.py

  lambdas/
    submit_job/
      handler.py
    worker/
      handler.py
    aggregate/
      handler.py

  workflows/
    state_machine.asl.json

  plans/
    architecture.plan.yaml

  tests/
    unit/
    integration/
```

Generated output should use ordinary Terraform and ordinary Python. A developer should be able to run and modify the project without Flowforge-specific runtime magic.

## 10. Plan Schema

The plan should be YAML and versioned.

Example:

```yaml
schema_version: 1

project:
  name: csv_importer
  package_name: csv_importer
  runtime: python
  iac: terraform

aws:
  region: us-east-1
  account_id: null

components:
  orchestrator:
    type: step_functions_standard
    enabled: true

  batch_map:
    type: distributed_map
    enabled: true
    item_source: s3
    input_type: jsonl
    max_concurrency: 500
    tolerated_failure_percentage: 5
    result_writer: s3

  item_processor:
    type: lambda_worker
    enabled: true
    runtime: python3.12
    timeout_seconds: 300
    memory_mb: 1024

  jobs_table:
    type: dynamodb_jobs_table
    enabled: true

  tasks_table:
    type: dynamodb_tasks_table
    enabled: true

  locks_table:
    type: dynamodb_locks_table
    enabled: true
    ttl_attribute: expires_at

  artifacts:
    type: s3_artifact_bucket
    enabled: true

runtime:
  pydantic_models: true
  boto3_clients: true
  lock_manager: true
  idempotency_helpers: true
  structured_logging: true
```

## 11. Planner Behavior

The rules planner should infer architecture from signals.

Batch signals:

- batch
- CSV
- JSONL
- rows
- records
- files
- images
- documents
- S3 objects
- dataset
- manifest

Queue signals:

- webhook
- event
- background job
- async
- buffer
- producer
- consumer
- queue

Lock signals:

- tenant limit
- concurrency limit
- exclusive
- only one at a time
- shared resource
- rate limit
- quota
- partition writer
- contention

Orchestration signals:

- workflow
- stages
- validate
- transform
- aggregate
- publish
- fan out
- fan-in
- approval

The planner should emit:

- recommended plan
- rationale
- warnings
- editable component list

Example rationale:

```text
Recommended: locked distributed batch workflow.

Why:
- You described bounded batch input: CSV files and rows.
- You described multiple stages: validate and transform.
- You described tenant concurrency limits.
- Distributed Map is a better fit than SQS for bounded batch fan-out.
- DynamoDB locks are needed to enforce tenant concurrency.
```

## 12. Validation Rules

The validator should reject incoherent plans before generation.

Initial validation rules:

- `distributed_map` requires `step_functions_standard`.
- `distributed_map` requires an item processor.
- `distributed_map` should usually require `s3_artifact_bucket`.
- `sqs_dlq` requires `sqs_standard_queue`.
- `lambda_worker` requires at least one trigger.
- `dynamodb_locks_table` requires `lock_manager` if generated runtime is enabled.
- Tenant concurrency recommendations require locks.
- CloudWatch alarms require the monitored resources.
- API submission requires `api_gateway` and `lambda_submitter`.
- Generated lock helpers require DynamoDB locks table configuration.

Errors should block generation. Warnings should be visible but not blocking.

## 13. Python Runtime Requirements

The generated Python runtime should be thin and explicit.

Required modules:

- configuration loading
- Pydantic models
- boto3 client factories
- DynamoDB job store
- DynamoDB task store
- optional DynamoDB lock manager
- S3 artifact helpers
- Step Functions execution helpers
- SQS helpers when queues are enabled
- structured logging
- metric helpers
- idempotency helpers

The runtime should not conceal AWS behavior. It should provide safer defaults and typed helpers.

## 14. Locking Semantics

The generated lock manager must use DynamoDB conditional writes.

Required operations:

- acquire lock
- heartbeat lock
- release lock

Acquire should succeed only when:

- the lock does not exist
- the lock is expired
- the lock is already owned by the same owner

Release should succeed only when:

- the caller still owns the lock

Heartbeat should succeed only when:

- the caller still owns the lock

The lock manager should use explicit owner tokens. A stale worker must not be able to release a lock acquired by a newer worker.

Terraform can create the lock table, but runtime code is responsible for correct lock semantics.

## 15. Lambda Scaffold Requirements

Generated Lambda handlers should be runnable but leave domain work intentionally incomplete.

Initial handlers:

- submit job
- item processor / worker
- aggregate results

The worker scaffold should show:

- event parsing
- Pydantic validation
- task start
- optional lock acquisition
- domain work placeholder
- output write placeholder
- task completion
- failure recording
- lock release in `finally`

The business logic should be marked clearly with TODOs or `NotImplementedError`.

## 16. Terraform Requirements

Generated Terraform should be local, inspectable, and modular.

Initial Terraform should include:

- provider configuration
- version constraints
- variables
- outputs
- local modules
- IAM roles and policies
- selected AWS resources
- CloudWatch log groups
- basic alarms

Flowforge should not manage Terraform state. It should generate Terraform files and leave normal Terraform workflows intact.

## 17. CLI Requirements

Initial CLI commands:

```bash
flowforge new <directory>
flowforge plan <directory>
flowforge generate <directory>
flowforge validate <plan-file>
flowforge list-components
```

Possible usage:

```bash
flowforge new ./csv-importer \
  --description "Process uploaded CSV files, validate rows, transform them, and limit each tenant to 5 concurrent workers."
```

The command should:

1. create or propose `architecture.plan.yaml`
2. show the recommendation and warnings
3. allow the user to edit or accept the plan
4. generate files only after acceptance

## 18. Implementation Stack

Initial implementation stack:

- Python
- Typer for CLI
- Pydantic for schemas
- Jinja2 for templates
- PyYAML or ruamel.yaml for plan serialization
- pytest for tests
- ruff for linting

Generated runtime stack:

- Python 3.12
- boto3
- Pydantic
- pytest

Generated infrastructure:

- Terraform
- AWS provider

## 19. Repository Structure

The Flowforge generator repository should use this shape:

```text
flowforge/
  pyproject.toml
  README.md

  docs/
    project-specification.md

  src/
    flowforge/
      __init__.py
      cli.py

      planning/
        schemas.py
        rules.py
        validator.py
        rationale.py

      catalog/
        registry.py
        components/
          api_gateway.py
          step_functions.py
          distributed_map.py
          sqs.py
          dynamodb.py
          s3.py
          lambda_worker.py
          cloudwatch.py

      generation/
        renderer.py
        project_writer.py
        diagnostics.py

      templates/
        terraform/
        python_runtime/
        lambdas/
        docs/

  tests/
    test_plan_schema.py
    test_plan_validation.py
    test_generate_simple_worker.py
    test_generate_distributed_batch.py
    test_generate_locked_workflow.py

  examples/
    simple_async_worker.plan.yaml
    distributed_batch_map.plan.yaml
    locked_distributed_batch_map.plan.yaml
```

## 20. MVP Acceptance Criteria

The MVP is complete when:

- A user can create a project from a prompt without an LLM token.
- The rules planner can recommend one of the initial patterns.
- The generated plan is editable YAML.
- The plan validator catches incoherent combinations.
- The generator can produce a local project from a valid plan.
- Generated Terraform passes `terraform validate` after initialization.
- Generated Python imports successfully.
- Generated Lambda handlers have basic unit tests.
- The locked workflow scaffold includes conditional DynamoDB lock operations.
- The generated README explains how to deploy and where to add domain logic.

## 21. Development Phases

### Phase 1: Static Generator

- Define plan schema.
- Define component registry.
- Add static example plans.
- Render files from plans.
- Add snapshot tests.

### Phase 2: Simple Async Queue Worker

- Generate SQS queue and DLQ.
- Generate Lambda worker.
- Generate IAM policies.
- Generate Pydantic task message model.
- Generate SQS client helper.

### Phase 3: Distributed Batch Map

- Generate Step Functions Standard workflow.
- Generate Distributed Map state.
- Generate S3 artifact bucket.
- Generate item processor Lambda.
- Generate job/task models and stores.

### Phase 4: Locked Distributed Batch Map

- Generate DynamoDB locks table.
- Generate LockManager.
- Add conditional acquire/release/heartbeat.
- Integrate locks into worker scaffold.
- Add lock-related tests.

### Phase 5: Rules Planner

- Add keyword/synonym signals.
- Add preset scoring.
- Add rationale and warnings.
- Add interactive plan review.

### Phase 6: Optional GUI

- Add local FastAPI server.
- Add React interface.
- Reuse the same plan schema, validator, and generator.

GUI support should come after the CLI and plan format stabilize.

## 22. Design Principle

Natural language is convenience.

The plan schema is the contract.

The validator is the judge.

The generator is deterministic.

LLMs are optional, not foundational.
