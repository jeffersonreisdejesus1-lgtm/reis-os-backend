import pytest
from httpx import AsyncClient



pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_ready(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}
