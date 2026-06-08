from typing import Any

from jinja2 import (
    Environment,
    PackageLoader,
    StrictUndefined,
    TemplateNotFound,
    select_autoescape,
)

from flowforge.catalog import ComponentNotFoundError, ComponentRegistry
from flowforge.planning import ProjectPlan

from .models import GeneratedFile, RenderResult, TemplateSpec

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


class TemplateRenderError(RendererError):
    """Raised when there is an error during template rendering."""

    def __init__(self, spec: TemplateSpec, cause: Exception):
        super().__init__(f"Failed to render template {spec.template_path}: {cause!s}")
        self.spec = spec
        self.cause = cause


class Renderer:
    """Responsible for rendering Jinja templates into output files based on a
    project plan."""

    _jinja_env: Environment

    def __init__(self):
        self._jinja_env = Environment(
            loader=PackageLoader(APP_PACKAGE),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
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
            "enabled_component_types": {d.type for d in enabled_components.values()},
            "alarmable_components": {
                name: definition
                for name, definition in enabled_components.items()
                if definition.supports_alarms
            },
            "project_name": plan.project.name,
            "package_name": plan.project.package_name,
        }

    @staticmethod
    def render_files(
        *,
        plan: ProjectPlan,
        template_specs: list[TemplateSpec],
    ) -> RenderResult:
        """Render multiple templates based on the provided template specifications and
        project plan.

        Args:
            plan: The project plan containing all necessary information for rendering.
            template_specs: A list of TemplateSpec instances specifying the templates
            to render.

        Returns:
            A RenderResult containing the list of generated files and any errors that
            occurred during rendering.
        """
        env = Environment(
            loader=PackageLoader(APP_PACKAGE),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )

        result = RenderResult()
        for spec in template_specs:
            try:
                Renderer.validate_template_spec(spec)
            except InvalidTemplateSpecError as e:
                result.errors[str(spec.template_path)] = e
                continue
            try:
                template = env.get_template(str(spec.template_path))
            except TemplateNotFound as e:
                result.errors[str(spec.template_path)] = InvalidTemplateSpecError(
                    spec, f"failed to load template: {e}"
                )
                continue
            try:
                context = Renderer.build_render_context(plan)
            except ComponentNotFoundError as e:
                result.errors[str(spec.template_path)] = RenderContextError(spec, e)
                continue
            try:
                content = template.render(**context)
            except Exception as e:
                result.errors[str(spec.template_path)] = TemplateRenderError(spec, e)
                continue
            result.generated_files.append(
                GeneratedFile(
                    path=spec.output_path,
                    content=content,
                    overwrite=spec.overwrite,
                )
            )
        return result

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
            RenderContextError: If there is an error during rendering (e.g. missing
            variables in the context).
            TemplateRenderError: If there is an error during rendering (e.g. syntax
            error in the template).
        """
        Renderer.validate_template_spec(spec)
        try:
            template = self._jinja_env.get_template(str(spec.template_path))
        except TemplateNotFound as e:
            raise InvalidTemplateSpecError(spec, f"failed to load template: {e}") from e
        try:
            content = template.render(**context)
        except Exception as e:
            raise TemplateRenderError(spec, e) from e
        return GeneratedFile(
            path=spec.output_path,
            content=content,
            overwrite=spec.overwrite,
        )
