from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from crossborder_api.config import Settings
from crossborder_api.dependencies import get_db_session
from crossborder_api.main import create_app

ROOT = Path(__file__).resolve().parents[2]


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


async def test_order_preview_uses_unified_dataset_endpoint() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))
    transport = ASGITransport(app=app)
    content = (
        "订单ID,订单明细ID,商品ID,商家SKU,下单时间,源时区,市场,币种,数量,商品单价,订单金额,订单状态\n"
        "O-1,OI-1,P-1,SKU-1,2026-08-20 10:00:00,UTC,US,USD,1,10,10,paid\n"
    ).encode()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingestion/datasets/orders/preview",
            files={"file": ("orders.csv", content, "text/csv")},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["domain"] == "orders"
    assert payload["accepted_row_count"] == 1
    assert payload["records"][0]["order_id"] == "O-1"


async def test_import_rejects_file_changed_after_preview() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))

    async def fake_session() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, object())

    app.dependency_overrides[get_db_session] = fake_session
    transport = ASGITransport(app=app)
    content = (ROOT / "data" / "samples" / "products_sample.csv").read_bytes()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingestion/datasets/products/import",
            headers={"X-Organization-ID": str(uuid4())},
            data={
                "data_source_id": str(uuid4()),
                "expected_checksum_sha256": "0" * 64,
            },
            files={"file": ("products.csv", content, "text/csv")},
        )

    assert response.status_code == 409
    assert "校验和" in response.json()["data"]["detail"]
