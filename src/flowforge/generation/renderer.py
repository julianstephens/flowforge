from typing import Any

from jinja2 import Environment, PackageLoader, TemplateNotFound, select_autoescape

from flowforge.catalog.registry import ComponentNotFoundError, ComponentRegistry
from flowforge.planning.schemas import ProjectPlan

from .models import GeneratedFile, TemplateSpec

APP_PACKAGE = "flowforge"


class RendererError(Exception):
    """Base class for exceptions raised by the Renderer."""

    pass


class RenderContextError(RendererError):
    """Raised when there is an error in building the render context."""

    def __init__(self, spec: TemplateSpec, cause: Exception | None = None):
        super().__init__(
            f"Failed to build render context for template {spec.template_path}"
            f"{f': {cause!s}' if cause else ''}"
        )
        self.spec = spec
        self.cause = cause


class InvalidTemplateSpecError(RendererError):
    """Raised when a TemplateSpec is invalid."""

    def __init__(self, spec: TemplateSpec, message: str):
        super().__init__(
            f"Invalid TemplateSpec for template {spec.template_path}: {message}"
        )
        self.spec = spec


class Renderer:
    """Responsible for rendering Jinja templates into output files based on a
    project plan."""

    _jinja_env: Environment

    def __init__(self):
        self._jinja_env = Environment(
            loader=PackageLoader(APP_PACKAGE),
            autoescape=select_autoescape(),
        )

    def render_template(
        self, spec: TemplateSpec, context: dict[str, Any]
    ) -> GeneratedFile:
        """Render a single Jinja template with the given context.

        Args:
            spec: The TemplateSpec containing the template path and other metadata.
            context: A dictionary containing all relevant data for template rendering.

        Returns:
            The rendered template as a GeneratedFile.

        Raises:
            InvalidTemplateSpecError: If the template path is invalid or does not end
            with .j2, or if the template cannot be loaded.
        """
        Renderer.validate_template_spec(spec)
        try:
            template = self._jinja_env.get_template(spec.template_path.name)
        except TemplateNotFound as e:
            raise InvalidTemplateSpecError(spec, f"failed to load template: {e}") from e
        content = template.render(**context)
        return GeneratedFile(
            path=spec.output_path,
            content=content,
            overwrite=spec.overwrite,
        )

    @staticmethod
    def validate_template_spec(spec: TemplateSpec):
        """Validate a TemplateSpec to ensure it meets the necessary criteria for
        rendering.

        Args:
            spec: The TemplateSpec to validate.

        Raises:
            InvalidTemplateSpecError: If the template path is invalid or does not end
            with .j2, or if the output path does not have a file extension.
        """
        if not spec.template_path.exists():
            raise InvalidTemplateSpecError(spec, "template path does not exist")
        if spec.template_path.suffix != ".j2":
            raise InvalidTemplateSpecError(spec, "template path must end with .j2")
        if not spec.output_path.suffix:
            raise InvalidTemplateSpecError(
                spec, "output path must have a file extension"
            )

    @staticmethod
    def build_render_context(plan: ProjectPlan) -> dict[str, Any]:
        """Build a context dictionary for rendering templates based on the project plan.

        Args:
            plan: The project plan containing all necessary information for rendering.

        Returns:
            A dictionary containing all relevant data for template rendering.

        Raises:
            ComponentNotFoundError: If any component in the plan is not found in the
            registry.
        """
        enabled_components = ComponentRegistry.get_enabled_components(plan)

        return {
            "plan": plan,
            "project": plan.project,
            "aws": plan.aws,
            "runtime": plan.runtime,
            "components": plan.components,
            "enabled_components": enabled_components,
            "component_types": {c.type for c in enabled_components.values()},
        }

    @staticmethod
    def render_files(
        *,
        plan: ProjectPlan,
        template_specs: list[TemplateSpec],
    ) -> list[GeneratedFile]:
        """Render multiple templates based on the provided template specifications and
        project plan.

        Args:
            plan: The project plan containing all necessary information for rendering.
            template_specs: A list of TemplateSpec instances specifying the templates
            to render.

        Returns:
            A list of GeneratedFile instances containing the rendered templates.

        Raises:
            InvalidTemplateSpecError: If any TemplateSpec is invalid.
            RenderContextError: If there is an error in building the render context.
        """
        env = Environment(
            loader=PackageLoader(APP_PACKAGE),
            autoescape=select_autoescape(),
        )

        result: list[GeneratedFile] = []
        for spec in template_specs:
            Renderer.validate_template_spec(spec)
            template = env.get_template(spec.template_path.name)
            try:
                context = Renderer.build_render_context(plan)
            except ComponentNotFoundError as e:
                raise RenderContextError(spec, e) from e
            content = template.render(**context)
            result.append(
                GeneratedFile(
                    path=spec.output_path,
                    content=content,
                    overwrite=spec.overwrite,
                )
            )
        return result
