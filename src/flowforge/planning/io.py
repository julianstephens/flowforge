import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError
from rich import print
from rich.syntax import Syntax

from .errors import (
    InvalidPlanFileCode,
    InvalidPlanFileError,
    PlanValidationCode,
    PlanValidationError,
)
from .schemas import DEFAULT_SCHEMA_VERSION, ProjectPlan


def load_plan(filename: str) -> Any:
    """Load a project plan from a YAML file and return the raw data.

    Args:
        filename: The path to the plan file to load.

    Returns:
        The raw data from the plan file, typically a dictionary.

    Raises:
        InvalidPlanFileError: If the file does not exist, is not a file,
        or has an invalid extension.
    """
    planfile = Path(filename)

    if not planfile.exists():
        raise InvalidPlanFileError(filename, InvalidPlanFileCode.FILE_NOT_FOUND)

    if not planfile.is_file():
        raise InvalidPlanFileError(filename, InvalidPlanFileCode.NOT_A_FILE)

    if planfile.suffix not in [".yaml", ".yml"]:
        raise InvalidPlanFileError(filename, InvalidPlanFileCode.INVALID_EXTENSION)

    with planfile.open() as f:
        return yaml.safe_load(f)


def validate_plan(data: Any) -> ProjectPlan:
    """Validate the raw data from a project plan file against the ProjectPlan schema."""
    if not isinstance(data, dict):
        raise PlanValidationError(
            message="plan file must contain a YAML mapping at the top level"
        )

    if "schema_version" not in data:
        raise PlanValidationError(
            code=PlanValidationCode.MISSING_FIELD,
            message="plan file is missing required 'schema_version' field",
        )

    if data["schema_version"] != DEFAULT_SCHEMA_VERSION:
        raise PlanValidationError(
            code=PlanValidationCode.UNSUPPORTED_SCHEMA_VERSION,
            message=(
                f"unsupported schema version '{data['schema_version']}' "
                f"(expected '{DEFAULT_SCHEMA_VERSION}')"
            ),
        )

    try:
        valid_plan = ProjectPlan.model_validate(data)
    except ValidationError as e:
        raise PlanValidationError(PlanValidationCode.INVALID_SCHEMA, e) from e

    if not is_valid_python_package_name(valid_plan.project.package_name):
        raise PlanValidationError(
            message=(
                f"'{valid_plan.project.package_name}' is not a valid "
                "Python package name"
            )
        )

    for component_name, component in valid_plan.components.items():
        for property_name, property_value in component.model_dump().items():
            if property_value is None:
                raise PlanValidationError(
                    message=(
                        f"component '{component_name}' has a null value for "
                        f"property '{property_name}'"
                    )
                )
    return valid_plan


def save_plan(plan: ProjectPlan, filename: str) -> None:
    """Save a project plan to a YAML file."""
    planfile = Path(filename)
    if not planfile.parent.exists():
        planfile.parent.mkdir(parents=True, exist_ok=True)

    with planfile.open("w") as f:
        yaml.safe_dump(plan.model_dump(), f)


def print_plan(plan: ProjectPlan) -> None:
    """Print a project plan to the console in YAML format."""
    yaml_data = yaml.safe_dump(plan.model_dump())
    syntax = Syntax(yaml_data, "yaml", theme="monokai", line_numbers=True)
    print(syntax)


def is_valid_python_package_name(name: str) -> bool:
    """Check if a string is a valid Python package name."""
    # check valid characters
    if not re.match(r"\w+$", name):
        return False
    # check starting character
    if not name[0].isalpha() and name[0] != "_":
        return False
    # check no hyphens or dots
    if "-" in name or "." in name:
        return False
    # check reserved keywords
    if name in {
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
        return False
    # check all lowercase
    return name.islower()
