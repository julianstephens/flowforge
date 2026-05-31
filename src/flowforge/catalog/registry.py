from functools import cache
from pathlib import Path

from .models import ComponentDefinition


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
        component_dir = Path(__file__).parent / "components"
        res = []
        for component_file in component_dir.glob("*.py"):
            if component_file.name != "__init__.py":
                module_name = component_file.stem
                module = __import__(
                    f"flowforge.catalog.components.{module_name}",
                    fromlist=[module_name],
                )
                for attr in dir(module):
                    obj = getattr(module, attr)
                    if isinstance(obj, ComponentDefinition):
                        res.append(obj)
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
