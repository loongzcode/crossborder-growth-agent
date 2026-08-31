import json
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
from crossborder_connectors import preview_dataset_file
from crossborder_domain import DataDomain
from crossborder_persistence import Base, seed_default_system
from crossborder_persistence.database import session_scope


@pytest_asyncio.fixture
async def ingestion_client() -> AsyncIterator[AsyncClient]:
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
            app_env="test",
            app_secret_key="test-secret-key-32-characters-long",
            _env_file=None,
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


async def _create_source(client: AsyncClient, headers: dict[str, str], domain: DataDomain) -> str:
    response = await client.post(
        "/api/data-sources",
        headers=headers,
        json={
            "name": f"{domain.value}-file-source",
            "provider": "file_upload",
            "domain": domain.value,
            "configuration": {},
            "enabled": True,
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


def _mapping_payload(preview: dict[str, object]) -> list[dict[str, str | None]]:
    mappings = preview["mappings"]
    assert isinstance(mappings, list)
    return [
        {
            "source_column": str(mapping["source_column"]),
            "canonical_field": mapping["canonical_field"],
        }
        for mapping in mappings
    ]


def test_ingestion_route_split_preserves_paths() -> None:
    app = create_app(Settings(app_env="test", _env_file=None))
    ingestion_paths = {
        path for path in app.openapi()["paths"] if path.startswith("/api/v1/ingestion/")
    }
    assert ingestion_paths == {
        "/api/v1/ingestion/advertising/fields",
        "/api/v1/ingestion/advertising/import",
        "/api/v1/ingestion/advertising/preview",
        "/api/v1/ingestion/batches/{raw_batch_id}",
        "/api/v1/ingestion/data-sources/{data_source_id}/mapping-templates",
        "/api/v1/ingestion/datasets/{domain}/fields",
        "/api/v1/ingestion/datasets/{domain}/import",
        "/api/v1/ingestion/datasets/{domain}/preview",
    }


@pytest.mark.asyncio
async def test_advertising_preview_requires_login_and_returns_metrics(
    ingestion_client: AsyncClient,
) -> None:
    content = (
        b"date,campaign_id,currency,impressions,clicks,spend,orders,revenue,note\n"
        b"2026-08-20,C-001,USD,1000,50,100,5,300,synthetic\n"
    )
    unauthenticated = await ingestion_client.post(
        "/api/v1/ingestion/advertising/preview",
        data={"data_source_id": "00000000-0000-0000-0000-000000000001"},
        files={"file": ("tiktok.csv", content, "text/csv")},
    )
    assert unauthenticated.status_code == 401

    headers = await _headers(ingestion_client)
    source_id = await _create_source(ingestion_client, headers, DataDomain.ADVERTISING)
    response = await ingestion_client.post(
        "/api/v1/ingestion/advertising/preview",
        headers=headers,
        data={"data_source_id": source_id},
        files={"file": ("tiktok.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["accepted_row_count"] == 1
    assert payload["unknown_columns"] == ["note"]
    assert payload["aggregate_metrics"]["roas"] == "3.0000"
    assert len(payload["mapping_signature"]) == 64


@pytest.mark.asyncio
async def test_manual_mapping_is_applied_during_preview(ingestion_client: AsyncClient) -> None:
    headers = await _headers(ingestion_client)
    source_id = await _create_source(ingestion_client, headers, DataDomain.PRODUCTS)
    content = (
        b"product_id,sku,custom_title,category,market,currency,unit_price,status\n"
        b"P-1,SKU-1,Travel Mug,drinkware,US,USD,19.9,active\n"
    )
    initial = await ingestion_client.post(
        "/api/v1/ingestion/datasets/products/preview",
        headers=headers,
        data={"data_source_id": source_id},
        files={"file": ("products.csv", content, "text/csv")},
    )
    initial_data = initial.json()["data"]
    mappings = _mapping_payload(initial_data)
    for mapping in mappings:
        if mapping["source_column"] == "custom_title":
            mapping["canonical_field"] = "title"
    confirmed = await ingestion_client.post(
        "/api/v1/ingestion/datasets/products/preview",
        headers=headers,
        data={"data_source_id": source_id, "mappings_json": json.dumps(mappings)},
        files={"file": ("products.csv", content, "text/csv")},
    )
    assert initial_data["accepted_row_count"] == 0
    assert confirmed.status_code == 200
    assert confirmed.json()["data"]["accepted_row_count"] == 1
    assert confirmed.json()["data"]["records"][0]["title"] == "Travel Mug"


@pytest.mark.asyncio
async def test_mapping_template_creates_versions_and_reuses_mapping(
    ingestion_client: AsyncClient,
) -> None:
    headers = await _headers(ingestion_client)
    source_id = await _create_source(ingestion_client, headers, DataDomain.ORDERS)
    content = (
        b"order_id,order_item_id,product_id,sku,ordered_at,source_timezone,market,currency,"
        b"quantity,unit_price,gross_revenue,status\n"
        b"O-1,OI-1,P-1,SKU-1,2026-08-20 10:00:00,UTC,US,USD,1,10,10,paid\n"
    )
    preview_response = await ingestion_client.post(
        "/api/v1/ingestion/datasets/orders/preview",
        headers=headers,
        data={"data_source_id": source_id},
        files={"file": ("orders.csv", content, "text/csv")},
    )
    preview = preview_response.json()["data"]
    template_payload = {
        "name": "Order Daily",
        "domain": "orders",
        "schema_version": preview["schema_version"],
        "mappings": _mapping_payload(preview),
        "expected_mapping_signature": preview["mapping_signature"],
    }
    template_url = f"/api/v1/ingestion/data-sources/{source_id}/mapping-templates"
    first = await ingestion_client.post(template_url, headers=headers, json=template_payload)
    second = await ingestion_client.post(template_url, headers=headers, json=template_payload)
    listed = await ingestion_client.get(template_url, headers=headers)
    reused = await ingestion_client.post(
        "/api/v1/ingestion/datasets/orders/preview",
        headers=headers,
        data={"data_source_id": source_id, "template_id": second.json()["data"]["id"]},
        files={"file": ("orders.csv", content, "text/csv")},
    )
    assert first.json()["data"]["version"] == 1
    assert second.json()["data"]["version"] == 2
    assert [record["active"] for record in listed.json()["data"]["records"]] == [True, False]
    assert reused.json()["data"]["mapping_template_version"] == 2
    assert reused.json()["data"]["accepted_row_count"] == 1


@pytest.mark.asyncio
async def test_import_rejects_changed_file_and_changed_mapping(
    ingestion_client: AsyncClient,
) -> None:
    headers = await _headers(ingestion_client)
    source_id = await _create_source(ingestion_client, headers, DataDomain.PRODUCTS)
    content = (
        b"product_id,sku,title,category,market,currency,unit_price,status\n"
        b"P-1,SKU-1,Travel Mug,drinkware,US,USD,19.9,active\n"
    )
    local_preview = preview_dataset_file(content, "products.csv", DataDomain.PRODUCTS)
    mappings = [
        {
            "source_column": mapping.source_column,
            "canonical_field": mapping.canonical_field,
        }
        for mapping in local_preview.mappings
    ]
    url = "/api/v1/ingestion/datasets/products/import"
    base_data = {
        "data_source_id": source_id,
        "mappings_json": json.dumps(mappings),
    }
    changed_file = await ingestion_client.post(
        url,
        headers=headers,
        data={
            **base_data,
            "expected_checksum_sha256": "0" * 64,
            "expected_mapping_signature": local_preview.mapping_signature,
        },
        files={"file": ("products.csv", content, "text/csv")},
    )
    changed_mapping = await ingestion_client.post(
        url,
        headers=headers,
        data={
            **base_data,
            "expected_checksum_sha256": local_preview.file_checksum_sha256,
            "expected_mapping_signature": "0" * 64,
        },
        files={"file": ("products.csv", content, "text/csv")},
    )
    assert changed_file.status_code == 409
    assert "校验和" in changed_file.json()["data"]["detail"]
    assert changed_mapping.status_code == 409
    assert "列映射" in changed_mapping.json()["data"]["detail"]


@pytest.mark.asyncio
async def test_ingestion_hides_unowned_data_source(ingestion_client: AsyncClient) -> None:
    headers = await _headers(ingestion_client)
    content = b"product_id,sku,title\nP-1,S-1,Test\n"
    response = await ingestion_client.post(
        "/api/v1/ingestion/datasets/products/preview",
        headers=headers,
        data={"data_source_id": "00000000-0000-0000-0000-000000000001"},
        files={"file": ("products.csv", content, "text/csv")},
    )
    assert response.status_code == 404
