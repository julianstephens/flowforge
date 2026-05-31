from functools import cache
from typing import TYPE_CHECKING

from flowforge.catalog.components import ALL_COMPONENTS

from .models import ComponentDefinition

if TYPE_CHECKING:
    from flowforge.planning.schemas import ProjectPlan


class ComponentNotFoundError(Exception):
    """Raised when a component definition is not found in the registry."""

    def __init__(self, component_type: str):
        super().__init__(f"Component definition not found for type: {component_type}")


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
    def get_component(component_type: str) -> ComponentDefinition:
        """Get a component definition by its type.

        Args:
            component_type: The type of the component to retrieve.

        Returns:
            The ComponentDefinition instance if found, otherwise None.

        Raises:
            ComponentNotFoundError: If the component type is not found in the registry.
        """
        if not component_type:
            raise ComponentNotFoundError(component_type)

        all_components = list(ComponentRegistry.list_components())
        for component in all_components:
            if component.type == component_type:
                return component

        raise ComponentNotFoundError(component_type)

    @staticmethod
    def get_component_dependencies(component_type: str) -> list[str]:
        """Get the dependencies of a component by its type.

        Args:
            component_type: The type of the component.

        Returns:
            A list of component types that the specified component depends on.

        Raises:
            ComponentNotFoundError: If the component type is not found in the registry.
        """
        component = ComponentRegistry.get_component(component_type)
        return component.dependencies

    @staticmethod
    def get_component_conflicts(component_type: str) -> list[str]:
        """Get the conflicting components for a given component type.

        Args:
            component_type: The type of the component.

        Returns:
            A list of component types that conflict with the specified component.

        Raises:
            ComponentNotFoundError: If the component type is not found in the registry.
        """
        component = ComponentRegistry.get_component(component_type)
        return component.conflicts

    @staticmethod
    def get_component_kind(component_type: str) -> str:
        """Get the kind of a component by its type.

        Args:
            component_type: The type of the component.

        Returns:
            The kind of the component.

        Raises:
            ComponentNotFoundError: If the component type is not found in the registry.
        """
        component = ComponentRegistry.get_component(component_type)
        return component.kind

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
        try:
            ComponentRegistry.get_component(component_type)
        except ComponentNotFoundError:
            return False
        else:
            return True

    @staticmethod
    def get_enabled_components(
        plan: "ProjectPlan",
    ) -> dict[str, ComponentDefinition]:
        """Get the enabled components from a project plan.

        Args:
            plan: The ProjectPlan instance containing the component configurations.

        Returns:
            A dictionary mapping component names to their ComponentDefinition instances
            if enabled.

        Raises:
            ComponentNotFoundError: If any enabled component type is not found in
            the registry.
        """
        return {
            name: ComponentRegistry.get_component(config.type)
            for name, config in plan.components.items()
            if config.enabled
        }
