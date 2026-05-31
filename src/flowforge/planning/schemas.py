from typing import Literal

from pydantic import BaseModel, ConfigDict

DEFAULT_SCHEMA_VERSION = 1


class ProjectConfig(BaseModel):
    name: str
    package_name: str
    runtime: Literal["python"]
    iac: Literal["terraform"]


class AwsConfig(BaseModel):
    region: str
    account_id: str | None = None


class RuntimeConfig(BaseModel):
    python_version: str | None = None
    pydantic_models: bool
    boto3_clients: bool
    lock_manager: bool
    idempotency_helpers: bool
    structured_logging: bool


class ComponentConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    enabled: bool


class ProjectPlan(BaseModel):
    project: ProjectConfig
    aws: AwsConfig
    components: dict[str, ComponentConfig]
    runtime: RuntimeConfig


class GeneratedFile(ProjectPlan):
    schema_version: str
