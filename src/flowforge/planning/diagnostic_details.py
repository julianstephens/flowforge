from typing import Any

from .schemas import ComponentConfig


def component_details(
    *,
    component_name: str,
    component: ComponentConfig,
    **extra: Any,
) -> dict[str, Any]:
    """Build standard diagnostic details for a plan component."""
    return {
        "component_name": component_name,
        "component_type": component.type,
        "component_enabled": component.enabled,
        "component": component.model_dump(),
        **extra,
    }


def missing_dependency_details(
    *,
    component_name: str,
    component: ComponentConfig,
    missing_dependency: str,
) -> dict[str, Any]:
    return component_details(
        component_name=component_name,
        component=component,
        missing_dependency=missing_dependency,
    )


def component_conflict_details(
    *,
    component_name: str,
    component: ComponentConfig,
    conflicting_component_type: str,
) -> dict[str, Any]:
    return component_details(
        component_name=component_name,
        component=component,
        conflicting_component_type=conflicting_component_type,
    )


def unknown_component_details(
    *,
    component_name: str,
    component: ComponentConfig,
) -> dict[str, Any]:
    return component_details(
        component_name=component_name,
        component=component,
        unknown_component_type=component.type,
    )


def lambda_worker_trigger_details(
    *,
    component_name: str,
    component: ComponentConfig,
    valid_trigger_component_types: set[str],
    enabled_component_types: set[str],
) -> dict[str, Any]:
    return component_details(
        component_name=component_name,
        component=component,
        valid_trigger_component_types=sorted(valid_trigger_component_types),
        enabled_component_types=sorted(enabled_component_types),
    )


def distributed_map_artifact_bucket_details(
    *,
    component_name: str,
    component: ComponentConfig,
) -> dict[str, Any]:
    return component_details(
        component_name=component_name,
        component=component,
        recommended_component_type="s3_artifact_bucket",
    )


def cloudwatch_alarm_details(
    *,
    component_name: str,
    component: ComponentConfig,
    alarmable_component_names: set[str],
    alarmable_component_types: set[str],
) -> dict[str, Any]:
    return component_details(
        component_name=component_name,
        component=component,
        alarmable_component_names=sorted(alarmable_component_names),
        alarmable_component_types=sorted(alarmable_component_types),
    )


def locks_table_runtime_details(
    *,
    component_name: str,
    component: ComponentConfig,
    runtime_lock_manager_enabled: bool,
    enabled_component_types: set[str],
) -> dict[str, Any]:
    return component_details(
        component_name=component_name,
        component=component,
        runtime_lock_manager_enabled=runtime_lock_manager_enabled,
        required_component_type="lock_manager",
        enabled_component_types=sorted(enabled_component_types),
    )
