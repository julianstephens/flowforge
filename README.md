# Flowforge

Flowforge is a local developer tool for generating AWS-native distributed workflow projects.

It helps a developer describe a workflow, review an editable architecture plan, and generate a local project containing Terraform resources, Python runtime helpers, Pydantic models, and Lambda scaffolds.

Flowforge is not a hosted workflow platform. It does not manage Terraform state, deploy infrastructure for you, or require an LLM API token. Generated projects should remain plain, inspectable Terraform and Python.

## Core idea

```text
workflow description
  -> local rules-based planner
  -> architecture.plan.yaml
  -> user review/edit
  -> validation
  -> generated Terraform + Python + Lambda scaffolds
```

Natural language is convenience. The plan file is the contract. The validator is the judge. The generator is deterministic.

## Initial workflow patterns

Flowforge starts with three AWS workflow patterns:

- **Simple async queue worker** — SQS + DLQ + Lambda for open-ended background work.
- **Distributed batch map** — Step Functions Distributed Map + Lambda + S3 + DynamoDB for bounded batch fan-out.
- **Locked distributed batch map** — Distributed Map plus DynamoDB lease locks for tenant limits, exclusive resources, or contention-sensitive work.

For large bounded batches, Flowforge prefers Step Functions Distributed Map over SQS. SQS is reserved for open-ended producer/consumer workloads or explicit queue boundaries.

## Planned commands

```bash
flowforge new
flowforge plan
flowforge explain
flowforge generate
flowforge list-components
flowforge validate-plan
flowforge doctor
```

## Example

```bash
flowforge new ./csv-importer \
  --description "Process uploaded CSV files, validate rows, transform them, and limit each tenant to 5 concurrent workers."
```

Expected result:

```text
csv-importer/
  infra/
  src/
  lambdas/
  workflows/
  plans/architecture.plan.yaml
  tests/
  README.md
```
