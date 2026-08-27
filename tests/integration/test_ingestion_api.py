from httpx import ASGITransport, AsyncClient

from crossborder_api.config import Settings
from crossborder_api.main import create_app


async def test_advertising_csv_preview_returns_quality_and_metrics() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))
    transport = ASGITransport(app=app)
    content = (
        "日期,广告系列ID,币种,展示次数,点击次数,消耗,订单数,GMV,备注\n"
        "2026-08-20,C-001,USD,1000,50,100,5,300,合成数据\n"
    ).encode()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingestion/advertising/preview",
            files={"file": ("tiktok.csv", content, "text/csv")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["accepted_row_count"] == 1
    assert payload["data"]["unknown_columns"] == ["备注"]
    assert payload["data"]["aggregate_metrics"]["roas"] == "3.0000"


async def test_metric_endpoint_rejects_impossible_ad_funnel() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/metrics/advertising",
            json={"impressions": 10, "clicks": 11, "spend": 10, "orders": 1, "revenue": 20},
        )

    assert response.status_code == 422
    assert response.json()["code"] == 422
    assert response.json()["msg"] == "参数校验失败"
