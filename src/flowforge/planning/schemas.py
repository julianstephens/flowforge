import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

DEFAULT_SCHEMA_VERSION = 1


class ProjectConfig(BaseModel):
    name: str
    package_name: str
    runtime: Literal["python"]
    iac: Literal["terraform"]

    @field_validator("package_name", mode="after")
    @classmethod
    def is_valid_python_package_name(cls, value: str) -> str:
        """Check if a string is a valid Python package name."""
        # check valid characters
        if not re.match(r"\w+$", value):
            raise ValueError
        # check starting character
        if not value[0].isalpha() and value[0] != "_":
            raise ValueError
        # check no hyphens or dots
        if "-" in value or "." in value:
            raise ValueError
        # check reserved keywords
        if value in {
            "False",
            "None",
            "True",
            "and",
            "as",
            "assert",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "try",
            "while",
            "with",
            "yield",
        }:
            raise ValueError
        # check all lowercase
        if not value.islower():
            raise ValueError
        return value


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
    schema_version: int = DEFAULT_SCHEMA_VERSION
    project: ProjectConfig
    aws: AwsConfig
    components: dict[str, ComponentConfig]
    runtime: RuntimeConfig
