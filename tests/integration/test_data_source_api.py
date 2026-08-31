from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from crossborder_api.config import Settings
from crossborder_api.dependencies import get_db_session
from crossborder_api.main import create_app
from crossborder_api.security import hash_password
from crossborder_persistence import Base, seed_default_system
from crossborder_persistence.database import session_scope


@pytest_asyncio.fixture
async def data_source_client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_scope(session_factory) as session:
        await seed_default_system(session, admin_password_hash=hash_password("12345678"))

    app = create_app(
        Settings(
            app_env="test", app_secret_key="test-secret-key-32-characters-long", _env_file=None
        )
    )

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_scope(session_factory) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    await engine.dispose()


async def _headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/auth/login", json={"userName": "Super", "password": "12345678"}
    )
    return {"Authorization": f"Bearer {response.json()['data']['token']}"}


@pytest.mark.asyncio
async def test_file_data_source_crud_and_connection_status(data_source_client: AsyncClient) -> None:
    headers = await _headers(data_source_client)
    created = await data_source_client.post(
        "/api/data-sources",
        headers=headers,
        json={
            "name": "运营日报上传",
            "provider": "file_upload",
            "domain": "orders",
            "configuration": {},
            "enabled": True,
        },
    )
    assert created.status_code == 200
    source_id = created.json()["data"]["id"]
    assert created.json()["data"]["connectionStatus"] == "untested"

    tested = await data_source_client.post(
        f"/api/data-sources/{source_id}/test-connection", headers=headers
    )
    assert tested.status_code == 200
    assert tested.json()["data"]["status"] == "connected"

    listed = await data_source_client.get(
        "/api/data-sources",
        headers=headers,
        params={"name": "运营日报", "connectionStatus": "connected"},
    )
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["records"][0]["connectionStatus"] == "connected"

    updated = await data_source_client.put(
        f"/api/data-sources/{source_id}",
        headers=headers,
        json={
            "name": "订单日报上传",
            "provider": "file_upload",
            "domain": "orders",
            "configuration": {},
            "enabled": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "订单日报上传"

    disabled = await data_source_client.delete(f"/api/data-sources/{source_id}", headers=headers)
    assert disabled.status_code == 200
    detail = await data_source_client.get(f"/api/data-sources/{source_id}", headers=headers)
    assert detail.json()["data"]["enabled"] is False


@pytest.mark.asyncio
async def test_tiktok_credentials_are_never_returned(data_source_client: AsyncClient) -> None:
    headers = await _headers(data_source_client)
    response = await data_source_client.post(
        "/api/data-sources",
        headers=headers,
        json={
            "name": "TikTok 广告账户",
            "provider": "tiktok_ads",
            "domain": "advertising",
            "configuration": {"advertiserId": "7123456789012345678"},
            "credentials": {"accessToken": "sensitive-access-token"},
            "enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["hasCredentials"] is True
    assert "sensitive-access-token" not in response.text
    detail = await data_source_client.get(
        f"/api/data-sources/{payload['data']['id']}", headers=headers
    )
    assert "credentials" not in detail.json()["data"]
    assert "sensitive-access-token" not in detail.text


@pytest.mark.asyncio
async def test_data_source_validation_and_organization_scope(
    data_source_client: AsyncClient,
) -> None:
    headers = await _headers(data_source_client)
    invalid = await data_source_client.post(
        "/api/data-sources",
        headers=headers,
        json={
            "name": "错误领域",
            "provider": "tiktok_ads",
            "domain": "orders",
            "configuration": {"advertiserId": "1"},
            "credentials": {"accessToken": "token"},
            "enabled": True,
        },
    )
    missing = await data_source_client.get(f"/api/data-sources/{uuid4()}", headers=headers)

    assert invalid.status_code == 422
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_provider_catalog_requires_authentication(data_source_client: AsyncClient) -> None:
    unauthenticated = await data_source_client.get("/api/data-sources/providers")
    assert unauthenticated.status_code == 401

    response = await data_source_client.get(
        "/api/data-sources/providers", headers=await _headers(data_source_client)
    )
    assert response.status_code == 200
    assert {item["value"] for item in response.json()["data"]} == {
        "file_upload",
        "tiktok_ads",
        "tiktok_shop",
    }
