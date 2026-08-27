from collections.abc import AsyncIterator

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
async def system_client() -> AsyncIterator[AsyncClient]:
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


async def _login(client: AsyncClient, username: str = "Super", password: str = "12345678") -> str:
    response = await client.post(
        "/api/auth/login",
        json={"userName": username, "password": password},
    )
    assert response.status_code == 200
    return str(response.json()["data"]["token"])


def _authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_bootstrap_admin_can_login_and_receive_database_menus(
    system_client: AsyncClient,
) -> None:
    token = await _login(system_client)
    headers = _authorization(token)

    user_info = await system_client.get("/api/user/info", headers=headers)
    menus = await system_client.get("/api/v3/system/menus/simple", headers=headers)

    assert user_info.status_code == 200
    assert user_info.json()["data"]["roles"] == ["R_SUPER"]
    assert menus.status_code == 200
    assert {item["name"] for item in menus.json()["data"]} >= {"Dashboard", "System"}


@pytest.mark.asyncio
async def test_system_admin_can_create_role_and_user(system_client: AsyncClient) -> None:
    token = await _login(system_client)
    headers = _authorization(token)
    role_response = await system_client.post(
        "/api/role",
        headers=headers,
        json={
            "roleName": "广告运营",
            "roleCode": "R_AD_OPERATOR",
            "description": "只读广告运营角色",
            "enabled": True,
        },
    )
    assert role_response.status_code == 200

    user_response = await system_client.post(
        "/api/user",
        headers=headers,
        json={
            "userName": "Operator",
            "nickName": "广告运营",
            "userEmail": "operator@example.com",
            "userPhone": "13800000000",
            "userGender": "保密",
            "avatar": "",
            "password": "operator123",
            "userRoles": ["R_AD_OPERATOR"],
            "enabled": True,
        },
    )
    assert user_response.status_code == 200

    user_list = await system_client.get(
        "/api/user/list",
        headers=headers,
        params={"current": 1, "size": 20, "userName": "Operator"},
    )
    assert user_list.status_code == 200
    assert user_list.json()["data"]["records"][0]["userRoles"] == ["R_AD_OPERATOR"]


@pytest.mark.asyncio
async def test_role_menu_assignment_limits_dynamic_routes_and_write_access(
    system_client: AsyncClient,
) -> None:
    super_token = await _login(system_client)
    super_headers = _authorization(super_token)
    role = await system_client.post(
        "/api/role",
        headers=super_headers,
        json={
            "roleName": "经营查看者",
            "roleCode": "R_VIEWER",
            "description": "只能查看经营总览",
            "enabled": True,
        },
    )
    role_id = role.json()["data"]["roleId"]
    menu_tree = (await system_client.get("/api/menu/list", headers=super_headers)).json()["data"]
    dashboard = next(item for item in menu_tree if item["name"] == "Dashboard")
    dashboard_ids = [dashboard["id"], *[child["id"] for child in dashboard["children"]]]
    access_response = await system_client.put(
        f"/api/role/{role_id}/permissions",
        headers=super_headers,
        json={"menuIds": dashboard_ids, "permissionIds": []},
    )
    assert access_response.status_code == 200

    await system_client.post(
        "/api/user",
        headers=super_headers,
        json={
            "userName": "Viewer",
            "nickName": "查看者",
            "userEmail": "viewer@example.com",
            "userPhone": "",
            "userGender": "保密",
            "avatar": "",
            "password": "viewer123",
            "userRoles": ["R_VIEWER"],
            "enabled": True,
        },
    )
    viewer_token = await _login(system_client, "Viewer", "viewer123")
    viewer_headers = _authorization(viewer_token)
    viewer_menus = await system_client.get("/api/v3/system/menus/simple", headers=viewer_headers)
    forbidden = await system_client.post(
        "/api/role",
        headers=viewer_headers,
        json={
            "roleName": "越权角色",
            "roleCode": "R_FORBIDDEN",
            "description": "不应创建",
            "enabled": True,
        },
    )

    assert [item["name"] for item in viewer_menus.json()["data"]] == ["Dashboard"]
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_invalid_token_is_rejected(system_client: AsyncClient) -> None:
    response = await system_client.get(
        "/api/user/info",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
