import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.main import app

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_is_fastapi() -> None:
    assert isinstance(app, FastAPI)
