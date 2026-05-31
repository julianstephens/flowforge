from flowforge.catalog.models import ComponentDefinition
from flowforge.catalog.registry import ComponentRegistry


def test_list_components():
    components = list(ComponentRegistry.list_components())
    assert len(components) > 0, "Expected at least one component in the registry"
    assert all(
        isinstance(component, ComponentDefinition) for component in components
    ), "All items should be instances of ComponentDefinition"


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
