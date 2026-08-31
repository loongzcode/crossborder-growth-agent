"""Organization-scoped data source administration and connection checks."""

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from crossborder_api.auth_dependencies import CurrentUser, require_permissions
from crossborder_api.credential_vault import CredentialDecryptionError
from crossborder_api.data_source_connections import test_data_source_connection
from crossborder_api.data_source_schemas import (
    ConnectionStatus,
    ConnectionTestResult,
    DataSourceItem,
    DataSourcePage,
    DataSourceProvider,
    DataSourceWrite,
    ProviderField,
    ProviderSpec,
)
from crossborder_api.data_source_service import (
    credential_vault,
    credentials_for_write,
    ensure_unique_name,
    get_source,
    latest_jobs,
    parse_provider,
    serialize_source,
)
from crossborder_api.dependencies import get_db_session
from crossborder_api.schemas import ApiResponse
from crossborder_domain import DataDomain
from crossborder_persistence import DataSourceModel

router = APIRouter(prefix="/api/data-sources", tags=["data-sources"])
ConnectionTester = Callable[
    [DataSourceProvider, dict[str, str | int | bool], dict[str, str]],
    Awaitable[ConnectionTestResult],
]

PROVIDER_SPECS = [
    ProviderSpec(
        value=DataSourceProvider.FILE_UPLOAD,
        label="CSV / Excel 文件",
        domains=list(DataDomain),
        fields=[],
    ),
    ProviderSpec(
        value=DataSourceProvider.TIKTOK_ADS,
        label="TikTok Ads",
        domains=[DataDomain.ADVERTISING],
        fields=[
            ProviderField(key="advertiserId", label="广告主 ID", secret=False, required=True),
            ProviderField(key="accessToken", label="访问令牌", secret=True, required=True),
        ],
    ),
    ProviderSpec(
        value=DataSourceProvider.TIKTOK_SHOP,
        label="TikTok Shop",
        domains=[
            DataDomain.ORDERS,
            DataDomain.PRODUCTS,
            DataDomain.INVENTORY,
            DataDomain.REFUNDS,
        ],
        fields=[
            ProviderField(key="appKey", label="应用 Key", secret=False, required=True),
            ProviderField(key="shopCipher", label="店铺 Cipher", secret=False, required=False),
            ProviderField(key="accessToken", label="访问令牌", secret=True, required=True),
            ProviderField(key="appSecret", label="应用密钥", secret=True, required=True),
        ],
    ),
]


@router.get("/providers", response_model=ApiResponse[list[ProviderSpec]])
async def list_provider_specs(
    _actor: Annotated[CurrentUser, Depends(require_permissions("data:source:list"))],
) -> ApiResponse[list[ProviderSpec]]:
    return ApiResponse(data=PROVIDER_SPECS)


@router.get("", response_model=ApiResponse[DataSourcePage])
async def list_data_sources(
    actor: Annotated[CurrentUser, Depends(require_permissions("data:source:list"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    name: Annotated[str | None, Query(max_length=200)] = None,
    provider: DataSourceProvider | None = None,
    domain: DataDomain | None = None,
    connection_status: Annotated[ConnectionStatus | None, Query(alias="connectionStatus")] = None,
    enabled: bool | None = None,
    sort_by: Annotated[
        str, Query(alias="sortBy", pattern="^(createdAt|name|lastTestedAt)$")
    ] = "createdAt",
    sort_order: Annotated[str, Query(alias="sortOrder", pattern="^(asc|desc)$")] = "desc",
) -> ApiResponse[DataSourcePage]:
    filters = [DataSourceModel.organization_id == actor.user.organization_id]
    if name:
        filters.append(DataSourceModel.name.ilike(f"%{name.strip()}%"))
    if provider:
        filters.append(DataSourceModel.provider == provider.value)
    if domain:
        filters.append(DataSourceModel.domain == domain)
    if connection_status:
        filters.append(DataSourceModel.connection_status == connection_status.value)
    if enabled is not None:
        filters.append(DataSourceModel.enabled.is_(enabled))
    total = int(
        await session.scalar(select(func.count()).select_from(DataSourceModel).where(*filters)) or 0
    )
    sort_column = {
        "createdAt": DataSourceModel.created_at,
        "name": DataSourceModel.name,
        "lastTestedAt": DataSourceModel.last_tested_at,
    }[sort_by]
    order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
    sources = list(
        (
            await session.scalars(
                select(DataSourceModel)
                .where(*filters)
                .order_by(order, DataSourceModel.id)
                .offset((current - 1) * size)
                .limit(size)
            )
        ).all()
    )
    jobs = await latest_jobs(session, [source.id for source in sources])
    return ApiResponse(
        data=DataSourcePage(
            records=[serialize_source(source, jobs.get(source.id)) for source in sources],
            current=current,
            size=size,
            total=total,
        )
    )


@router.get("/{data_source_id}", response_model=ApiResponse[DataSourceItem])
async def get_data_source(
    data_source_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("data:source:list"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[DataSourceItem]:
    source = await get_source(session, actor.user.organization_id, data_source_id)
    jobs = await latest_jobs(session, [source.id])
    return ApiResponse(data=serialize_source(source, jobs.get(source.id)))


@router.post("", response_model=ApiResponse[DataSourceItem])
async def create_data_source(
    payload: DataSourceWrite,
    request: Request,
    actor: Annotated[CurrentUser, Depends(require_permissions("data:source:add"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[DataSourceItem]:
    await ensure_unique_name(session, actor.user.organization_id, payload.name)
    credentials = credentials_for_write(payload.provider, payload.credentials)
    source = DataSourceModel(
        organization_id=actor.user.organization_id,
        name=payload.name,
        provider=payload.provider.value,
        domain=payload.domain,
        configuration=payload.configuration,
        credentials_encrypted=credential_vault(request).encrypt(credentials)
        if credentials
        else None,
        enabled=payload.enabled,
        connection_status=ConnectionStatus.UNTESTED.value,
    )
    session.add(source)
    await session.flush()
    await session.refresh(source)
    return ApiResponse(data=serialize_source(source), msg="数据源创建成功")


@router.put("/{data_source_id}", response_model=ApiResponse[DataSourceItem])
async def update_data_source(
    data_source_id: UUID,
    payload: DataSourceWrite,
    request: Request,
    actor: Annotated[CurrentUser, Depends(require_permissions("data:source:edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[DataSourceItem]:
    source = await get_source(session, actor.user.organization_id, data_source_id)
    await ensure_unique_name(
        session, actor.user.organization_id, payload.name, excluding_id=data_source_id
    )
    vault = credential_vault(request)
    try:
        existing = vault.decrypt(source.credentials_encrypted)
    except CredentialDecryptionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    provider_changed = source.provider != payload.provider.value
    credentials = credentials_for_write(
        payload.provider,
        payload.credentials,
        existing={} if provider_changed else existing,
    )
    connection_changed = (
        provider_changed or source.configuration != payload.configuration or credentials != existing
    )
    source.name = payload.name
    source.provider = payload.provider.value
    source.domain = payload.domain
    source.configuration = payload.configuration
    source.credentials_encrypted = vault.encrypt(credentials) if credentials else None
    source.enabled = payload.enabled
    if connection_changed:
        source.connection_status = ConnectionStatus.UNTESTED.value
        source.last_tested_at = None
        source.last_error_code = None
        source.last_error_message = None
    await session.flush()
    await session.refresh(source)
    return ApiResponse(data=serialize_source(source), msg="数据源更新成功")


@router.delete("/{data_source_id}", response_model=ApiResponse[dict[str, bool]])
async def disable_data_source(
    data_source_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("data:source:delete"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[dict[str, bool]]:
    source = await get_source(session, actor.user.organization_id, data_source_id)
    source.enabled = False
    await session.flush()
    return ApiResponse(data={"disabled": True}, msg="数据源已停用")


@router.post(
    "/{data_source_id}/test-connection",
    response_model=ApiResponse[ConnectionTestResult],
)
async def test_connection(
    data_source_id: UUID,
    request: Request,
    actor: Annotated[CurrentUser, Depends(require_permissions("data:source:test"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[ConnectionTestResult]:
    source = await get_source(session, actor.user.organization_id, data_source_id)
    if not source.enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "数据源已停用，不能测试连接")
    try:
        credentials = credential_vault(request).decrypt(source.credentials_encrypted)
    except CredentialDecryptionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    tester: ConnectionTester = getattr(
        request.app.state, "data_source_connection_tester", test_data_source_connection
    )
    result = await tester(parse_provider(source.provider), source.configuration, credentials)
    source.connection_status = result.status.value
    source.last_tested_at = result.checked_at
    if result.status is ConnectionStatus.CONNECTED:
        source.last_error_code = None
        source.last_error_message = None
    else:
        source.last_error_code = "connection_failed"
        source.last_error_message = result.message
    await session.flush()
    return ApiResponse(data=result, msg=result.message)
