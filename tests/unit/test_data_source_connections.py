import json

import httpx

from crossborder_api.data_source_connections import (
    test_data_source_connection as check_data_source_connection,
)
from crossborder_api.data_source_schemas import ConnectionStatus, DataSourceProvider


async def test_tiktok_ads_connection_uses_read_only_advertiser_info() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/open_api/v1.3/advertiser/info/"
        assert request.headers["Access-Token"] == "ads-token"
        assert json.loads(request.url.params["advertiser_ids"]) == ["123456"]
        return httpx.Response(
            200,
            json={"code": 0, "message": "OK", "request_id": "ads-request"},
        )

    result = await check_data_source_connection(
        DataSourceProvider.TIKTOK_ADS,
        {"advertiserId": "123456"},
        {"access_token": "ads-token"},
        transport=httpx.MockTransport(handler),
    )

    assert result.status is ConnectionStatus.CONNECTED
    assert result.upstream_request_id == "ads-request"


async def test_tiktok_shop_connection_signs_request_and_counts_authorized_shops() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/authorization/202309/shops"
        assert request.headers["x-tts-access-token"] == "shop-token"
        assert request.url.params["app_key"] == "app-key"
        assert len(request.url.params["sign"]) == 64
        return httpx.Response(
            200,
            json={
                "code": 0,
                "message": "Success",
                "request_id": "shop-request",
                "data": {"shops": [{"id": "1"}, {"id": "2"}]},
            },
        )

    result = await check_data_source_connection(
        DataSourceProvider.TIKTOK_SHOP,
        {"appKey": "app-key"},
        {"access_token": "shop-token", "app_secret": "shop-secret"},
        transport=httpx.MockTransport(handler),
    )

    assert result.status is ConnectionStatus.CONNECTED
    assert result.metadata["authorizedShopCount"] == 2


async def test_connection_failure_does_not_expose_secret() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"code": 401, "message": "token rejected"})

    result = await check_data_source_connection(
        DataSourceProvider.TIKTOK_ADS,
        {"advertiserId": "123456"},
        {"access_token": "must-never-leak"},
        transport=httpx.MockTransport(handler),
    )

    assert result.status is ConnectionStatus.FAILED
    assert "must-never-leak" not in result.message
