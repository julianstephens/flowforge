def component_path(component_name: str) -> str:
    return f"components.{component_name}"


def component_field_path(component_name: str, field_name: str) -> str:
    return f"components.{component_name}.{field_name}"


def runtime_path(field_name: str) -> str:
    return f"runtime.{field_name}"


def project_path(field_name: str) -> str:
    return f"project.{field_name}"


def aws_path(field_name: str) -> str:
    return f"aws.{field_name}"
