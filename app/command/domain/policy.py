from enum import StrEnum


class CommandOperationClass(StrEnum):
    READ = "read"
    INTERNAL_OBSERVABILITY_WRITE = "internal_observability_write"
    EXTERNAL_SOURCE_MUTATION = "external_source_mutation"
    INSTITUTIONAL_MUTATION = "institutional_mutation"


_ALLOWED_IN_OBSERVE = frozenset(
    {
        CommandOperationClass.READ,
        CommandOperationClass.INTERNAL_OBSERVABILITY_WRITE,
    }
)


def is_allowed_in_observe(operation: CommandOperationClass) -> bool:
    """Default-deny policy for COMMAND v0.1 — OBSERVAR."""
    return operation in _ALLOWED_IN_OBSERVE


def require_observe_permission(operation: CommandOperationClass) -> None:
    """Fail closed when an operation is outside the G4 observation boundary."""
    if not is_allowed_in_observe(operation):
        raise PermissionError(f"Operation {operation.value!r} is not allowed in OBSERVAR")
