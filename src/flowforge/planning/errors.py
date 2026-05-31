from enum import StrEnum

from pydantic import ValidationError


class PlanValidationCode(StrEnum):
    """Codes for different types of plan validation errors."""

    INVALID_SCHEMA = "invalid_schema"
    MISSING_FIELD = "missing_field"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"


class PlanValidationError(Exception):
    """Error raised when a project plan fails validation against the schema."""

    def __init__(
        self,
        code: PlanValidationCode = PlanValidationCode.INVALID_SCHEMA,
        validation_error: ValidationError | None = None,
        message: str | None = None,
    ):
        self.code = code
        self.validation_error = validation_error
        super().__init__(
            f"plan validation error ({self.code.value}): {validation_error or message}"
        )


class InvalidPlanFileCode(StrEnum):
    """Codes for different types of invalid plan file errors."""

    INVALID_EXTENSION = "invalid_extension"
    FILE_NOT_FOUND = "file_not_found"
    NOT_A_FILE = "not_a_file"


class InvalidPlanFileError(ValueError):
    """Error raised when a plan file is invalid for some reason."""

    def __init__(
        self,
        filename: str,
        code: InvalidPlanFileCode = InvalidPlanFileCode.INVALID_EXTENSION,
    ):
        self.code = code
        super().__init__(f"invalid plan file ({self.code.value}): {filename}")
