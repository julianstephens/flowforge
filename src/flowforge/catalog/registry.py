from functools import cache

from flowforge.catalog.components import ALL_COMPONENTS
from flowforge.planning.schemas import ProjectPlan

from .models import ComponentDefinition


class DuplicateComponentError(Exception):
    """Raised when a duplicate component definition is found in the registry."""

    def __init__(self, component_type: str):
        super().__init__(
            f"Duplicate component definition found for type: {component_type}"
        )


class ComponentRegistry:
    """A registry for managing and retrieving component definitions."""

    @staticmethod
    @cache
    def list_components() -> list[ComponentDefinition]:
        """List all available component definitions by dynamically importing them from
        the components directory.

        Returns:
            A list of ComponentDefinition instances.
        """
        res = []
        seen_types = set()
        for component in ALL_COMPONENTS:
            if component.type in seen_types:
                raise DuplicateComponentError(component.type)
            seen_types.add(component.type)
            res.append(component)
        return res

    @staticmethod
    def get_component(component_type: str) -> ComponentDefinition | None:
        """Get a component definition by its type.

        Args:
            component_type: The type of the component to retrieve.

        Returns:
            The ComponentDefinition instance if found, otherwise None.
        """
        if not component_type:
            return None

        all_components = list(ComponentRegistry.list_components())
        for component in all_components:
            if component.type == component_type:
                return component
        return None

    @staticmethod
    def get_component_dependencies(component_type: str) -> list[str]:
        """Get the dependencies of a component by its type.

        Args:
            component_type: The type of the component.

        Returns:
            A list of component types that the specified component depends on.
        """
        if not component_type:
            return []

        component = ComponentRegistry.get_component(component_type)
        if component:
            return component.dependencies
        return []

    @staticmethod
    def get_component_conflicts(component_type: str) -> list[str]:
        """Get the conflicting components for a given component type.

        Args:
            component_type: The type of the component.

        Returns:
            A list of component types that conflict with the specified component.
        """
        if not component_type:
            return []

        component = ComponentRegistry.get_component(component_type)
        if component:
            return component.conflicts
        return []

    @staticmethod
    def is_valid_component_type(component_type: str) -> bool:
        """Check if a component type is valid.

        Args:
            component_type: The type of the component.

        Returns:
            True if the component type is valid, False otherwise.
        """
        if not component_type:
            return False
        return ComponentRegistry.get_component(component_type) is not None

    @staticmethod
    def get_enabled_components(
        plan: ProjectPlan,
    ) -> dict[str, ComponentDefinition | None]:
        """Get the enabled components from a project plan.

        Args:
            plan: The ProjectPlan instance containing the component configurations.

        Returns:
            A dictionary mapping component names to their ComponentDefinition instances
            if enabled, or None if the component type is invalid.
        """
        return {
            name: ComponentRegistry.get_component(config.type)
            for name, config in plan.components.items()
            if config.enabled
        }
