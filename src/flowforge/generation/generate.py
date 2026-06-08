from pathlib import Path

from flowforge.planning.schemas import ProjectPlan

from .models import GenerationResult, TemplateSpec
from .project_writer import ProjectWriter
from .renderer import Renderer

KNOWN_TEMPLATES = {
    "README": TemplateSpec(
        template_path=Path(__file__).parent.parent
        / "templates"
        / "docs"
        / "README.md.j2",
        output_path=Path("README.md"),
        overwrite=False,
    ),
}


def create_template_specs(
    _plan: ProjectPlan, target_dir: Path, overwrite: bool
) -> list[TemplateSpec]:
    """Create a list of TemplateSpec instances based on the given ProjectPlan."""
    result: list[TemplateSpec] = []

    for template in KNOWN_TEMPLATES.values():
        template.output_path = target_dir / template.output_path
        template.overwrite = overwrite
        result.append(template)

    # TODO: add templates specs based on the plan's components and configuration

    return result


def generate_project(
    plan: ProjectPlan, target_dir: Path, *, overwrite: bool = False
) -> GenerationResult:
    """Generate a project based on the given plan and write it to the target directory.

    Args:
        plan: The ProjectPlan containing all necessary information for generation.
        target_dir: The directory where the generated files should be written.
        overwrite: Whether to overwrite existing files in the target directory.

    Returns:
        A GenerationResult containing the list of generated files and any errors that
        occurred during rendering or writing.
    """
    result = GenerationResult()
    specs = create_template_specs(plan, target_dir, overwrite)
    render_result = Renderer.render_files(plan=plan, template_specs=specs)
    result.generated_files = render_result.generated_files
    result.render_errors = render_result.errors

    if len(result.generated_files) == 0:
        return result

    writer_result = ProjectWriter.write(result.generated_files)
    result.write_result = writer_result

    return result
