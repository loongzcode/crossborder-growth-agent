"""Read-only connection checks for supported external data providers."""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

import httpx

from crossborder_api.data_source_schemas import (
    ConnectionStatus,
    ConnectionTestResult,
    DataSourceProvider,
)

TIKTOK_ADS_INFO_URL = "https://business-api.tiktok.com/open_api/v1.3/advertiser/info/"
TIKTOK_SHOP_API_ORIGIN = "https://open-api.tiktokglobalshop.com"
TIKTOK_SHOP_AUTHORIZED_SHOPS_PATH = "/authorization/202309/shops"


def _failure(
    provider: DataSourceProvider,
    message: str,
    *,
    request_id: str | None = None,
) -> ConnectionTestResult:
    return ConnectionTestResult(
        status=ConnectionStatus.FAILED,
        provider=provider,
        message=message[:300],
        checkedAt=datetime.now(UTC),
        upstreamRequestId=request_id,
    )


def _safe_upstream_message(payload: dict[str, Any], fallback: str) -> str:
    message = payload.get("message") or payload.get("msg") or fallback
    return str(message)[:300]


def _shop_signature(path: str, params: dict[str, str], app_secret: str) -> str:
    canonical = path + "".join(f"{key}{params[key]}" for key in sorted(params))
    return hmac.new(app_secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()


async def test_data_source_connection(
    provider: DataSourceProvider,
    configuration: dict[str, str | int | bool],
    credentials: dict[str, str],
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> ConnectionTestResult:
    checked_at = datetime.now(UTC)
    if provider is DataSourceProvider.FILE_UPLOAD:
        return ConnectionTestResult(
            status=ConnectionStatus.CONNECTED,
            provider=provider,
            message="文件上传数据源可用，无需远程平台授权",
            checkedAt=checked_at,
        )

    access_token = credentials.get("access_token")
    if not access_token:
        return _failure(provider, "缺少访问令牌，请编辑数据源并重新授权")

    try:
        async with httpx.AsyncClient(
            timeout=10, follow_redirects=False, transport=transport
        ) as client:
            if provider is DataSourceProvider.TIKTOK_ADS:
                response = await client.get(
                    TIKTOK_ADS_INFO_URL,
                    params={"advertiser_ids": json.dumps([str(configuration["advertiserId"])])},
                    headers={"Access-Token": access_token},
                )
            else:
                app_secret = credentials.get("app_secret")
                if not app_secret:
                    return _failure(provider, "缺少应用密钥，请编辑数据源并重新授权")
                path = TIKTOK_SHOP_AUTHORIZED_SHOPS_PATH
                params = {
                    "app_key": str(configuration["appKey"]),
                    "timestamp": str(int(checked_at.timestamp())),
                }
                params["sign"] = _shop_signature(path, params, app_secret)
                response = await client.get(
                    f"{TIKTOK_SHOP_API_ORIGIN}{path}",
                    params=params,
                    headers={
                        "x-tts-access-token": access_token,
                        "content-type": "application/json",
                    },
                )
    except (httpx.TimeoutException, httpx.NetworkError):
        return _failure(provider, "上游平台暂时不可达，请稍后重试")

    request_id = response.headers.get("x-tts-request-id")
    try:
        payload = response.json()
    except ValueError:
        return _failure(provider, "上游平台返回了无法识别的响应", request_id=request_id)
    if not isinstance(payload, dict):
        return _failure(provider, "上游平台返回了无效响应", request_id=request_id)
    request_id = str(payload.get("request_id") or request_id or "") or None
    if response.status_code in {401, 403}:
        return _failure(provider, "平台授权无效或权限不足", request_id=request_id)
    if response.status_code == 429:
        return _failure(provider, "平台请求频率受限，请稍后重试", request_id=request_id)
    if response.status_code >= 500:
        return _failure(provider, "上游平台服务异常，请稍后重试", request_id=request_id)
    if response.status_code >= 400 or payload.get("code") not in {0, "0"}:
        return _failure(
            provider,
            _safe_upstream_message(payload, "平台拒绝了连接测试"),
            request_id=request_id,
        )

    metadata: dict[str, str | int | bool] = {}
    data = payload.get("data")
    if provider is DataSourceProvider.TIKTOK_SHOP and isinstance(data, dict):
        shops = data.get("shops") or []
        if isinstance(shops, list):
            metadata["authorizedShopCount"] = len(shops)
    return ConnectionTestResult(
        status=ConnectionStatus.CONNECTED,
        provider=provider,
        message="连接测试成功",
        checkedAt=checked_at,
        upstreamRequestId=request_id,
        metadata=metadata,
    )
