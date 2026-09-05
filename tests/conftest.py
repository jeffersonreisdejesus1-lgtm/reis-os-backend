import os
from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.main import app
from app.shared.config.settings import get_settings
from app.shared.database.base import Base
from app.shared.database.models import (  # noqa: F401
    AuditEventModel,
    CommandRefreshPolicyModel,
    MembershipModel,
    OrganizationModel,
    ProjectModel,
    TaskModel,
    UserModel,
    WorkspaceModel,
)
from app.shared.database.session import get_db_session

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

engine_options: dict[str, object] = {}
if TEST_DATABASE_URL.startswith("sqlite"):
    engine_options = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }

engine = create_async_engine(TEST_DATABASE_URL, **engine_options)
TestSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_db_session() -> AsyncIterator[AsyncSession]:
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
def configure_test_capability_surface(request: pytest.FixtureRequest) -> Iterator[None]:
    """Keep historical platform tests explicit without weakening product defaults."""
    settings = get_settings()
    original_signup = settings.public_signup_enabled
    original_org_self_service = settings.organization_self_service_enabled
    private_contract_test = request.path.name == "test_command_p3_private_product.py"
    if not private_contract_test:
        settings.public_signup_enabled = True
        settings.organization_self_service_enabled = True
    try:
        yield
    finally:
        settings.public_signup_enabled = original_signup
        settings.organization_self_service_enabled = original_org_self_service


@pytest.fixture(autouse=True)
async def reset_database() -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_db_session] = override_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
