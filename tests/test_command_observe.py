import pytest
from httpx import AsyncClient

from app.command.domain.policy import (
    CommandOperationClass,
    is_allowed_in_observe,
    require_observe_permission,
)


def test_observe_policy_allows_read_and_internal_observability_write() -> None:
    assert is_allowed_in_observe(CommandOperationClass.READ)
    assert is_allowed_in_observe(CommandOperationClass.INTERNAL_OBSERVABILITY_WRITE)


def test_observe_policy_denies_external_and_institutional_mutation() -> None:
    assert not is_allowed_in_observe(CommandOperationClass.EXTERNAL_SOURCE_MUTATION)
    assert not is_allowed_in_observe(CommandOperationClass.INSTITUTIONAL_MUTATION)

    with pytest.raises(PermissionError):
        require_observe_permission(CommandOperationClass.EXTERNAL_SOURCE_MUTATION)

    with pytest.raises(PermissionError):
        require_observe_permission(CommandOperationClass.INSTITUTIONAL_MUTATION)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_command_mode_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/command/mode")
    assert response.status_code == 401
