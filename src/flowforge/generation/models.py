from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class GeneratedFile(BaseModel):
    """Represents a file generated from a Jinja template, including its path, content,
    and whether it should overwrite existing files."""

    path: Path
    content: str
    overwrite: bool = False


class TemplateSpec(BaseModel):
    """An instruction to render one Jinja template into one project-relative output
    file."""

    template_path: Path
    output_path: Path
    overwrite: bool = False


class RenderResult(BaseModel):
    """The result of rendering a template, including the generated file and any errors
    that occurred during rendering."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    generated_files: list[GeneratedFile] = Field(default_factory=list)
    errors: dict[str, Exception] = Field(default_factory=dict)


class WriterResult(BaseModel):
    """The result of writing generated files to disk, including lists of successfully
    written files and any errors that occurred."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # The list of files that were successfully written to disk.
    written_files: list[GeneratedFile] = Field(default_factory=list)
    # The list of files that were skipped because they already exist and overwrite
    # is False.
    skipped_files: list[GeneratedFile] = Field(default_factory=list)
    # A mapping of file paths to exceptions for any files that failed to write due to
    # errors other than existing files.
    errors: dict[str, Exception] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    """The overall result of the project generation process, including the list of
    generated files and any errors that occurred during rendering or writing."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    generated_files: list[GeneratedFile] = Field(default_factory=list)
    render_errors: dict[str, Exception] = Field(default_factory=dict)
    write_result: WriterResult = Field(default_factory=WriterResult)
