"""Shared persistence and credential operations for data source routes."""

from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from crossborder_api.credential_vault import CredentialVault
from crossborder_api.data_source_schemas import (
    ConnectionStatus,
    DataSourceCredentials,
    DataSourceItem,
    DataSourceProvider,
)
from crossborder_persistence import DataSourceModel, SyncJobModel


def credential_vault(request: Request) -> CredentialVault:
    return CredentialVault(request.app.state.settings.signing_secret)


def parse_provider(value: str) -> DataSourceProvider:
    try:
        return DataSourceProvider(value)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "数据源提供方配置无效") from exc


async def get_source(
    session: AsyncSession, organization_id: UUID, data_source_id: UUID
) -> DataSourceModel:
    source = await session.scalar(
        select(DataSourceModel).where(
            DataSourceModel.id == data_source_id,
            DataSourceModel.organization_id == organization_id,
        )
    )
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "数据源不存在")
    return source


async def latest_jobs(
    session: AsyncSession, data_source_ids: list[UUID]
) -> dict[UUID, SyncJobModel]:
    if not data_source_ids:
        return {}
    jobs = list(
        (
            await session.scalars(
                select(SyncJobModel)
                .where(SyncJobModel.data_source_id.in_(data_source_ids))
                .order_by(SyncJobModel.created_at.desc())
            )
        ).all()
    )
    latest: dict[UUID, SyncJobModel] = {}
    for job in jobs:
        latest.setdefault(job.data_source_id, job)
    return latest


def serialize_source(source: DataSourceModel, job: SyncJobModel | None = None) -> DataSourceItem:
    return DataSourceItem(
        id=str(source.id),
        name=source.name,
        provider=parse_provider(source.provider),
        domain=source.domain,
        configuration=source.configuration,
        hasCredentials=bool(source.credentials_encrypted),
        enabled=source.enabled,
        connectionStatus=ConnectionStatus(source.connection_status),
        lastTestedAt=source.last_tested_at,
        lastErrorCode=source.last_error_code,
        lastErrorMessage=source.last_error_message,
        lastSyncStatus=job.status if job else None,
        lastSyncAt=(job.finished_at or job.started_at or job.created_at) if job else None,
        createdAt=source.created_at,
        updatedAt=source.updated_at,
    )


def credentials_for_write(
    provider: DataSourceProvider,
    payload: DataSourceCredentials | None,
    *,
    existing: dict[str, str] | None = None,
) -> dict[str, str]:
    credentials = dict(existing or {})
    if payload:
        credentials.update(payload.provided())
    allowed = {
        DataSourceProvider.FILE_UPLOAD: set(),
        DataSourceProvider.TIKTOK_ADS: {"access_token"},
        DataSourceProvider.TIKTOK_SHOP: {"access_token", "app_secret"},
    }[provider]
    credentials = {key: value for key, value in credentials.items() if key in allowed}
    missing = sorted(allowed - credentials.keys())
    if missing:
        labels = {"access_token": "访问令牌", "app_secret": "应用密钥"}
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"缺少平台凭证：{', '.join(labels[item] for item in missing)}",
        )
    return credentials


async def ensure_unique_name(
    session: AsyncSession,
    organization_id: UUID,
    name: str,
    *,
    excluding_id: UUID | None = None,
) -> None:
    filters = [
        DataSourceModel.organization_id == organization_id,
        func.lower(DataSourceModel.name) == name.lower(),
    ]
    if excluding_id:
        filters.append(DataSourceModel.id != excluding_id)
    if await session.scalar(select(DataSourceModel.id).where(*filters)):
        raise HTTPException(status.HTTP_409_CONFLICT, "数据源名称已存在")
