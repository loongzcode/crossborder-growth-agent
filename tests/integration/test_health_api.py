from httpx import ASGITransport, AsyncClient

from crossborder_api.config import Settings
from crossborder_api.main import create_app


async def test_liveness_uses_frontend_response_envelope() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/live", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"
    payload = response.json()
    assert payload["code"] == 200
    assert payload["msg"] == "ok"
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["environment"] == "test"


async def test_unknown_route_returns_safe_problem_details() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/not-found")

    assert response.status_code == 404
    payload = response.json()
    assert payload["code"] == 404
    assert payload["data"]["status"] == 404
    assert "traceback" not in response.text.lower()
