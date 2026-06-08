from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from jinja2 import TemplateNotFound

from flowforge.catalog.registry import ComponentNotFoundError
from flowforge.generation.models import GeneratedFile, RenderResult, TemplateSpec
from flowforge.generation.renderer import (
    InvalidTemplateSpecError,
    RenderContextError,
    Renderer,
)
from flowforge.planning.schemas import (
    AwsConfig,
    ComponentConfig,
    ProjectConfig,
    ProjectPlan,
    RuntimeConfig,
)


def _make_plan(components: dict[str, dict] | None = None) -> ProjectPlan:
    if components is None:
        components = {
            "orchestrator": {"type": "step_functions_standard", "enabled": True},
        }
    return ProjectPlan(
        project=ProjectConfig(
            name="test",
            package_name="test",
            runtime="python",
            iac="terraform",
        ),
        aws=AwsConfig(region="us-east-1"),
        components={k: ComponentConfig(**v) for k, v in components.items()},
        runtime=RuntimeConfig(
            pydantic_models=False,
            boto3_clients=False,
            lock_manager=False,
            idempotency_helpers=False,
            structured_logging=False,
        ),
    )


class TestRenderContextError:
    def test_stores_spec_and_cause(self):
        spec = TemplateSpec(
            template_path=Path("templates/foo.j2"),
            output_path=Path("out/foo.tf"),
        )
        cause = ComponentNotFoundError("missing_type")
        err = RenderContextError(spec, cause)

        assert err.spec is spec
        assert err.cause is cause

    def test_message_includes_template_path(self):
        spec = TemplateSpec(
            template_path=Path("templates/bar.j2"),
            output_path=Path("out/bar.tf"),
        )
        err = RenderContextError(spec)
        assert "bar.j2" in str(err)

    def test_cause_defaults_to_none(self):
        spec = TemplateSpec(
            template_path=Path("templates/baz.j2"),
            output_path=Path("out/baz.tf"),
        )
        err = RenderContextError(spec)
        assert err.cause is None


class TestBuildRenderContext:
    def test_contains_expected_keys(self):
        plan = _make_plan()
        ctx = Renderer.build_render_context(plan)

        assert "plan" in ctx
        assert "project" in ctx
        assert "aws" in ctx
        assert "runtime" in ctx
        assert "components" in ctx
        assert "enabled_components" in ctx
        assert "enabled_component_types" in ctx
        assert "alarmable_components" in ctx
        assert "project_name" in ctx
        assert "package_name" in ctx

    def test_plan_references_match(self):
        plan = _make_plan()
        ctx = Renderer.build_render_context(plan)

        assert ctx["plan"] is plan
        assert ctx["project"] is plan.project
        assert ctx["aws"] is plan.aws
        assert ctx["runtime"] is plan.runtime
        assert ctx["components"] is plan.components
        assert ctx["project_name"] == plan.project.name
        assert ctx["package_name"] == plan.project.package_name

    def test_component_types_is_set_of_type_strings(self):
        plan = _make_plan(
            {
                "orchestrator": {"type": "step_functions_standard", "enabled": True},
                "batch_map": {
                    "type": "distributed_map",
                    "enabled": True,
                    "item_source": "s3",
                    "input_type": "jsonl",
                    "max_concurrency": 500,
                    "tolerated_failure_percentage": 5,
                    "result_writer": "s3",
                },
            }
        )
        ctx = Renderer.build_render_context(plan)
        assert isinstance(ctx["enabled_component_types"], set)
        assert "step_functions_standard" in ctx["enabled_component_types"]
        assert "distributed_map" in ctx["enabled_component_types"]

    def test_disabled_components_excluded(self):
        plan = _make_plan(
            {
                "orchestrator": {"type": "step_functions_standard", "enabled": True},
                "logs": {"type": "cloudwatch_logs", "enabled": False},
            }
        )
        ctx = Renderer.build_render_context(plan)
        component_types = ctx["enabled_component_types"]
        assert "cloudwatch_logs" not in component_types

    def test_raises_on_unknown_component_type(self):
        plan = _make_plan({"bad": {"type": "nonexistent_xyz", "enabled": True}})
        with pytest.raises(ComponentNotFoundError):
            Renderer.build_render_context(plan)


class TestRenderFiles:
    def _make_spec(
        self, tmp_path: Path, name: str = "foo.j2", out: str = "out/foo.tf"
    ) -> TemplateSpec:
        template = tmp_path / "templates" / name
        template.parent.mkdir(parents=True, exist_ok=True)
        template.write_text("")
        return TemplateSpec(
            template_path=template,
            output_path=Path(out),
        )

    def _mock_env(self, rendered_content: str = "rendered"):
        mock_template = MagicMock()
        mock_template.render.return_value = rendered_content
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template
        return mock_env

    @pytest.fixture(autouse=True)
    def patch_package_loader(self):
        with patch("flowforge.generation.renderer.PackageLoader"):
            yield

    def test_returns_generated_files(self, tmp_path):
        plan = _make_plan()
        spec = self._make_spec(tmp_path)
        mock_env = self._mock_env("output content")

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            result = Renderer.render_files(plan=plan, template_specs=[spec])

        assert isinstance(result, RenderResult)
        assert len(result.generated_files) == 1
        assert isinstance(result.generated_files[0], GeneratedFile)
        assert result.generated_files[0].path == spec.output_path
        assert result.generated_files[0].content == "output content"
        assert result.generated_files[0].overwrite == spec.overwrite

    def test_renders_multiple_specs(self, tmp_path):
        plan = _make_plan()
        specs = [
            self._make_spec(tmp_path, "a.j2", "out/a.tf"),
            self._make_spec(tmp_path, "b.j2", "out/b.tf"),
        ]
        mock_env = self._mock_env()

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            result = Renderer.render_files(plan=plan, template_specs=specs)

        assert len(result.generated_files) == 2

    def test_empty_specs_returns_empty_result(self):
        plan = _make_plan()
        mock_env = self._mock_env()

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            result = Renderer.render_files(plan=plan, template_specs=[])

        assert result.generated_files == []
        assert result.errors == {}

    def test_overwrite_flag_propagated(self, tmp_path):
        plan = _make_plan()
        spec = self._make_spec(tmp_path, "foo.j2", "out/foo.tf")
        spec = TemplateSpec(
            template_path=spec.template_path,
            output_path=Path("out/foo.tf"),
            overwrite=True,
        )
        mock_env = self._mock_env()

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            result = Renderer.render_files(plan=plan, template_specs=[spec])

        assert result.generated_files[0].overwrite is True

    def test_invalid_spec_error_collected_not_raised(self, tmp_path):
        plan = _make_plan()
        spec = TemplateSpec(
            template_path=tmp_path / "templates" / "bad.txt",
            output_path=Path("out/foo.tf"),
        )
        mock_env = self._mock_env()

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            result = Renderer.render_files(plan=plan, template_specs=[spec])

        assert len(result.generated_files) == 0
        assert str(spec.template_path) in result.errors
        assert isinstance(
            result.errors[str(spec.template_path)], InvalidTemplateSpecError
        )

    def test_template_not_found_error_collected(self, tmp_path):
        plan = _make_plan()
        spec = self._make_spec(tmp_path)
        mock_env = self._mock_env()
        mock_env.get_template.side_effect = TemplateNotFound("foo.j2")

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            result = Renderer.render_files(plan=plan, template_specs=[spec])

        assert len(result.generated_files) == 0
        assert str(spec.template_path) in result.errors
        assert isinstance(
            result.errors[str(spec.template_path)], InvalidTemplateSpecError
        )

    def test_render_context_error_collected(self, tmp_path):
        plan = _make_plan({"bad": {"type": "nonexistent_xyz", "enabled": True}})
        spec = self._make_spec(tmp_path)
        mock_env = self._mock_env()

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            result = Renderer.render_files(plan=plan, template_specs=[spec])

        assert len(result.generated_files) == 0
        assert str(spec.template_path) in result.errors
        assert isinstance(result.errors[str(spec.template_path)], RenderContextError)

    def test_processing_continues_after_error(self, tmp_path):
        plan = _make_plan()
        bad_spec = TemplateSpec(
            template_path=tmp_path / "templates" / "bad.txt",
            output_path=Path("out/bad.tf"),
        )
        good_spec = self._make_spec(tmp_path, "good.j2", "out/good.tf")
        mock_env = self._mock_env("rendered")

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            result = Renderer.render_files(
                plan=plan, template_specs=[bad_spec, good_spec]
            )

        assert len(result.generated_files) == 1
        assert result.generated_files[0].path == good_spec.output_path
        assert str(bad_spec.template_path) in result.errors

    def test_render_error_during_rendering_collected(self, tmp_path):
        plan = _make_plan()
        spec = self._make_spec(tmp_path)
        mock_template = MagicMock()
        mock_template.render.side_effect = RuntimeError("render boom")
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            result = Renderer.render_files(plan=plan, template_specs=[spec])

        assert len(result.generated_files) == 0
        assert str(spec.template_path) in result.errors

    def test_get_template_called_with_template_name(self, tmp_path):
        plan = _make_plan()
        spec = self._make_spec(tmp_path, "mytemplate.j2", "out/foo.tf")
        mock_env = self._mock_env()

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            Renderer.render_files(plan=plan, template_specs=[spec])

        mock_env.get_template.assert_called_with(str(spec.template_path))

    def test_template_render_called_with_context_keys(self, tmp_path):
        plan = _make_plan()
        spec = self._make_spec(tmp_path)
        mock_template = MagicMock()
        mock_template.render.return_value = ""
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            Renderer.render_files(plan=plan, template_specs=[spec])

        call_kwargs = mock_template.render.call_args.kwargs
        assert "plan" in call_kwargs
        assert "project" in call_kwargs
        assert "aws" in call_kwargs
        assert "runtime" in call_kwargs
        assert "components" in call_kwargs
        assert "enabled_components" in call_kwargs
        assert "enabled_component_types" in call_kwargs
        assert "alarmable_components" in call_kwargs
        assert "project_name" in call_kwargs
        assert "package_name" in call_kwargs

    def test_deterministic_rendering_same_plan(self, tmp_path):
        plan = _make_plan()
        spec = self._make_spec(tmp_path)
        call_count = 0

        def deterministic_render(**kwargs):
            nonlocal call_count
            call_count += 1
            return f"rendered-{kwargs['project'].name}"

        mock_template = MagicMock()
        mock_template.render.side_effect = deterministic_render
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            result1 = Renderer.render_files(plan=plan, template_specs=[spec])

        spec2 = self._make_spec(tmp_path, "foo2.j2")
        mock_template2 = MagicMock()
        mock_template2.render.side_effect = deterministic_render
        mock_env2 = MagicMock()
        mock_env2.get_template.return_value = mock_template2

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env2):
            result2 = Renderer.render_files(plan=plan, template_specs=[spec2])

        assert result1.generated_files[0].content == result2.generated_files[0].content

    def test_all_invalid_specs_produces_empty_generated_files(self, tmp_path):
        plan = _make_plan()
        specs = [
            TemplateSpec(
                template_path=tmp_path / "templates" / "a.txt",
                output_path=Path("out/a.tf"),
            ),
            TemplateSpec(
                template_path=tmp_path / "templates" / "b.txt",
                output_path=Path("out/b.tf"),
            ),
        ]
        mock_env = self._mock_env()

        with patch("flowforge.generation.renderer.Environment", return_value=mock_env):
            result = Renderer.render_files(plan=plan, template_specs=specs)

        assert result.generated_files == []
        assert len(result.errors) == 2


class TestValidateTemplateSpec:
    def test_nonexistent_template_path_still_valid_if_extension_correct(self, tmp_path):
        spec = TemplateSpec(
            template_path=tmp_path / "missing.j2",
            output_path=Path("out/foo.tf"),
        )
        Renderer.validate_template_spec(spec)  # existence no longer checked

    def test_wrong_extension_raises(self, tmp_path):
        bad = tmp_path / "template.txt"
        bad.write_text("")
        spec = TemplateSpec(template_path=bad, output_path=Path("out/foo.tf"))
        with pytest.raises(InvalidTemplateSpecError) as exc_info:
            Renderer.validate_template_spec(spec)
        assert exc_info.value.spec is spec
        assert ".j2" in str(exc_info.value)

    def test_output_path_without_extension_raises(self, tmp_path):
        template = tmp_path / "template.j2"
        template.write_text("")
        spec = TemplateSpec(
            template_path=template, output_path=Path("out/no_extension")
        )
        with pytest.raises(InvalidTemplateSpecError) as exc_info:
            Renderer.validate_template_spec(spec)
        assert exc_info.value.spec is spec
        assert "extension" in str(exc_info.value)

    def test_valid_spec_does_not_raise(self):
        spec = TemplateSpec(
            template_path=Path("template.j2"), output_path=Path("out/foo.tf")
        )
        Renderer.validate_template_spec(spec)  # should not raise

    def test_spec_stored_on_error(self):
        spec = TemplateSpec(
            template_path=Path("wrong_extension.txt"),
            output_path=Path("out/foo.tf"),
        )
        with pytest.raises(InvalidTemplateSpecError) as exc_info:
            Renderer.validate_template_spec(spec)
        assert exc_info.value.spec is spec


class TestRenderTemplate:
    def _make_spec(
        self, tmp_path: Path, name: str = "foo.j2", out: str = "out/foo.tf"
    ) -> TemplateSpec:
        template = tmp_path / name
        template.write_text("")
        return TemplateSpec(template_path=template, output_path=Path(out))

    def _make_renderer_with_mock_env(self, rendered_content: str = ""):
        renderer = Renderer.__new__(Renderer)
        mock_template = MagicMock()
        mock_template.render.return_value = rendered_content
        renderer._jinja_env = MagicMock()
        renderer._jinja_env.get_template.return_value = mock_template
        return renderer, renderer._jinja_env, mock_template

    def test_returns_generated_file(self, tmp_path):
        renderer, _, _ = self._make_renderer_with_mock_env("hello")
        spec = self._make_spec(tmp_path)
        context = Renderer.build_render_context(_make_plan())

        result = renderer.render_template(spec, context)

        assert isinstance(result, GeneratedFile)
        assert result.path == spec.output_path
        assert result.content == "hello"
        assert result.overwrite == spec.overwrite

    def test_overwrite_flag_propagated(self, tmp_path):
        renderer, _, _ = self._make_renderer_with_mock_env()
        template = tmp_path / "foo.j2"
        template.write_text("")
        spec = TemplateSpec(
            template_path=template, output_path=Path("out/foo.tf"), overwrite=True
        )

        result = renderer.render_template(spec, {})

        assert result.overwrite is True

    def test_get_template_called_with_name(self, tmp_path):
        renderer, mock_env, _ = self._make_renderer_with_mock_env()
        spec = self._make_spec(tmp_path, "mytemplate.j2")

        renderer.render_template(spec, {})

        mock_env.get_template.assert_called_with(str(spec.template_path))

    def test_context_passed_to_template_render(self, tmp_path):
        renderer, _, mock_template = self._make_renderer_with_mock_env()
        spec = self._make_spec(tmp_path)
        context = {"key1": "val1", "key2": "val2"}

        renderer.render_template(spec, context)

        mock_template.render.assert_called_once_with(**context)

    def test_raises_invalid_spec_on_bad_template_extension(self, tmp_path):
        renderer, _, _ = self._make_renderer_with_mock_env()
        spec = TemplateSpec(
            template_path=tmp_path / "template.txt",
            output_path=Path("out/foo.tf"),
        )
        with pytest.raises(InvalidTemplateSpecError):
            renderer.render_template(spec, {})

    def test_raises_invalid_spec_on_template_not_found(self, tmp_path):
        renderer, mock_env, _ = self._make_renderer_with_mock_env()
        spec = self._make_spec(tmp_path)
        mock_env.get_template.side_effect = TemplateNotFound("foo.j2")

        with pytest.raises(InvalidTemplateSpecError) as exc_info:
            renderer.render_template(spec, {})

        assert exc_info.value.spec is spec
        assert "failed to load template" in str(exc_info.value)

    def test_template_not_found_error_chained(self, tmp_path):
        renderer, mock_env, _ = self._make_renderer_with_mock_env()
        spec = self._make_spec(tmp_path)
        original = TemplateNotFound("foo.j2")
        mock_env.get_template.side_effect = original

        with pytest.raises(InvalidTemplateSpecError) as exc_info:
            renderer.render_template(spec, {})

        assert exc_info.value.__cause__ is original
