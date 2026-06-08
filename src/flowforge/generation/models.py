from pathlib import Path

from pydantic import BaseModel


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
