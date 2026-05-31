import pytest

import flowforge.catalog.components as forge_components
from flowforge.catalog.models import ComponentDefinition, ComponentKind
from flowforge.catalog.registry import ComponentRegistry


def test_list_components(mocker):
    components = list(ComponentRegistry.list_components())
    assert len(components) > 0, "Expected at least one component in the registry"
    assert all(
        isinstance(component, ComponentDefinition) for component in components
    ), "All items should be instances of ComponentDefinition"
    for component in forge_components.ALL_COMPONENTS:
        assert (
            component in components
        ), f"Expected {component.type} to be in the registry"
    call_1 = ComponentRegistry.list_components()
    call_2 = ComponentRegistry.list_components()
    assert call_1 == call_2, "Expected cached result to be returned on subsequent calls"

    ComponentRegistry.list_components.cache_clear()
    mocker.patch(
        "flowforge.catalog.registry.ALL_COMPONENTS",
        new=[
            ComponentDefinition(
                type="test_component",
                kind=ComponentKind.INFRASTRUCTURE,
                display_name="Test Component",
                description="A test component for testing purposes",
            ),
            ComponentDefinition(
                type="test_component",
                kind=ComponentKind.INFRASTRUCTURE,
                display_name="Test Component Duplicate",
                description="A duplicate test component for testing purposes",
            ),
        ],
    )
    with pytest.raises(Exception) as exc_info:
        ComponentRegistry.list_components()
    assert (
        exc_info.typename == "DuplicateComponentError"
    ), "Expected DuplicateComponentError to be raised"


def test_get_component():
    # Test with a valid component type
    component = ComponentRegistry.get_component("cloudwatch_logs")
    assert component is not None, "Expected to find 'cloudwatch_logs' component"
    assert component.type == "cloudwatch_logs", "Component type should match"

    # Test with an invalid component type
    component = ComponentRegistry.get_component("non_existent_component")
    assert component is None, "Expected to return None for non-existent component"

    # Test with an empty string
    component = ComponentRegistry.get_component("")
    assert component is None, "Expected to return None for empty component type"


def test_get_component_dependencies():
    # Test with a valid component type that has dependencies
    dependencies = ComponentRegistry.get_component_dependencies("cloudwatch_alarms")
    assert dependencies == [
        "cloudwatch_logs"
    ], "Expected 'cloudwatch_alarms' to depend on 'cloudwatch_logs'"

    # Test with a valid component type that has no dependencies
    dependencies = ComponentRegistry.get_component_dependencies("cloudwatch_logs")
    assert dependencies == [], "Expected 'cloudwatch_logs' to have no dependencies"

    # Test with an invalid component type
    dependencies = ComponentRegistry.get_component_dependencies(
        "non_existent_component"
    )
    assert (
        dependencies == []
    ), "Expected to return an empty list for non-existent component"

    # Test with an empty string
    dependencies = ComponentRegistry.get_component_dependencies("")
    assert (
        dependencies == []
    ), "Expected to return an empty list for empty component type"


def test_is_valid_component_type():
    # Test with a valid component type
    assert ComponentRegistry.is_valid_component_type(
        "cloudwatch_logs"
    ), "Expected 'cloudwatch_logs' to be a valid component type"

    # Test with an invalid component type
    assert not ComponentRegistry.is_valid_component_type(
        "non_existent_component"
    ), "Expected 'non_existent_component' to be an invalid component type"

    # Test with an empty string
    assert not ComponentRegistry.is_valid_component_type(
        ""
    ), "Expected empty string to be an invalid component type"


def test_get_component_conflicts():
    # Test with a valid component type that has conflicts
    conflicts = ComponentRegistry.get_component_conflicts("cloudwatch_logs")
    assert conflicts == [], "Expected 'cloudwatch_logs' to have no conflicts"

    # Test with an invalid component type
    conflicts = ComponentRegistry.get_component_conflicts("non_existent_component")
    assert (
        conflicts == []
    ), "Expected to return an empty list for non-existent component"

    # Test with an empty string
    conflicts = ComponentRegistry.get_component_conflicts("")
    assert conflicts == [], "Expected to return an empty list for empty component type"
