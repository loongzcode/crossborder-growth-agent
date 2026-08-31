"""Validation, versioning, and organization scoping for mapping templates."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from crossborder_api.data_source_service import get_source
from crossborder_api.ingestion_schemas import (
    MappingOverride,
    MappingTemplateItem,
    MappingTemplateWrite,
)
from crossborder_connectors.mapping import (
    ADVERTISING_FIELD_ALIASES,
    DATASET_FIELD_ALIASES,
    DATASET_REQUIRED_FIELDS,
    REQUIRED_ADVERTISING_FIELDS,
    mapping_signature,
)
from crossborder_domain import ColumnMapping, DataDomain, MappingStatus
from crossborder_persistence import DataSourceModel, MappingTemplateModel


def field_rules(domain: DataDomain) -> tuple[set[str], frozenset[str]]:
    if domain is DataDomain.ADVERTISING:
        return set(ADVERTISING_FIELD_ALIASES), REQUIRED_ADVERTISING_FIELDS
    return set(DATASET_FIELD_ALIASES[domain]), DATASET_REQUIRED_FIELDS[domain]


def validate_mapping_overrides(
    mappings: list[MappingOverride], domain: DataDomain
) -> list[ColumnMapping]:
    sources = [mapping.source_column for mapping in mappings]
    if len(sources) != len(set(sources)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "源列不能重复")
    targets = [mapping.canonical_field for mapping in mappings if mapping.canonical_field]
    if len(targets) != len(set(targets)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "标准字段不能重复映射")
    allowed, required = field_rules(domain)
    invalid = sorted(set(targets) - allowed)
    if invalid:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"包含不支持的标准字段：{', '.join(invalid)}",
        )
    missing = sorted(required - set(targets))
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"缺少必填字段映射：{', '.join(missing)}",
        )
    return [
        ColumnMapping(
            source_column=mapping.source_column,
            canonical_field=mapping.canonical_field,
            status=MappingStatus.CONFIRMED if mapping.canonical_field else MappingStatus.UNMAPPED,
            confidence=1 if mapping.canonical_field else 0,
        )
        for mapping in mappings
    ]


async def source_for_ingestion(
    session: AsyncSession,
    organization_id: UUID,
    data_source_id: UUID,
    domain: DataDomain,
) -> DataSourceModel:
    source = await get_source(session, organization_id, data_source_id)
    if not source.enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "数据源已停用，不能导入数据")
    if source.domain != domain:
        raise HTTPException(status.HTTP_409_CONFLICT, "数据源领域与导入文件不一致")
    return source


def serialize_template(template: MappingTemplateModel) -> MappingTemplateItem:
    return MappingTemplateItem(
        id=str(template.id),
        data_source_id=str(template.data_source_id),
        domain=template.domain,
        name=template.name,
        version=template.version,
        schema_version=template.schema_version,
        mappings=[MappingOverride.model_validate(item) for item in template.mappings],
        mapping_signature=template.mapping_signature,
        active=template.active,
        created_by=str(template.created_by) if template.created_by else None,
        created_at=template.created_at,
    )


async def create_mapping_template(
    session: AsyncSession,
    *,
    organization_id: UUID,
    data_source_id: UUID,
    created_by: UUID,
    payload: MappingTemplateWrite,
) -> MappingTemplateModel:
    await source_for_ingestion(session, organization_id, data_source_id, payload.domain)
    await session.execute(
        select(DataSourceModel.id)
        .where(
            DataSourceModel.id == data_source_id,
            DataSourceModel.organization_id == organization_id,
        )
        .with_for_update()
    )
    columns = validate_mapping_overrides(payload.mappings, payload.domain)
    signature = mapping_signature(columns)
    if signature != payload.expected_mapping_signature.lower():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "列映射已变化，请重新预检后再保存模板",
        )
    latest_version = int(
        await session.scalar(
            select(func.max(MappingTemplateModel.version)).where(
                MappingTemplateModel.organization_id == organization_id,
                MappingTemplateModel.data_source_id == data_source_id,
                func.lower(MappingTemplateModel.name) == payload.name.lower(),
            )
        )
        or 0
    )
    await session.execute(
        update(MappingTemplateModel)
        .where(
            MappingTemplateModel.organization_id == organization_id,
            MappingTemplateModel.data_source_id == data_source_id,
            func.lower(MappingTemplateModel.name) == payload.name.lower(),
            MappingTemplateModel.active.is_(True),
        )
        .values(active=False)
    )
    template = MappingTemplateModel(
        organization_id=organization_id,
        data_source_id=data_source_id,
        domain=payload.domain,
        name=payload.name,
        version=latest_version + 1,
        schema_version=payload.schema_version,
        mappings=[mapping.model_dump() for mapping in payload.mappings],
        mapping_signature=signature,
        active=True,
        created_by=created_by,
    )
    session.add(template)
    await session.flush()
    await session.refresh(template)
    return template


async def list_mapping_templates(
    session: AsyncSession,
    *,
    organization_id: UUID,
    data_source_id: UUID,
    active_only: bool,
) -> list[MappingTemplateModel]:
    await get_source(session, organization_id, data_source_id)
    filters = [
        MappingTemplateModel.organization_id == organization_id,
        MappingTemplateModel.data_source_id == data_source_id,
    ]
    if active_only:
        filters.append(MappingTemplateModel.active.is_(True))
    return list(
        (
            await session.scalars(
                select(MappingTemplateModel)
                .where(*filters)
                .order_by(
                    MappingTemplateModel.active.desc(),
                    MappingTemplateModel.name,
                    MappingTemplateModel.version.desc(),
                )
            )
        ).all()
    )


async def get_mapping_template(
    session: AsyncSession,
    *,
    organization_id: UUID,
    data_source_id: UUID,
    template_id: UUID,
    domain: DataDomain,
) -> MappingTemplateModel:
    template = await session.scalar(
        select(MappingTemplateModel).where(
            MappingTemplateModel.id == template_id,
            MappingTemplateModel.organization_id == organization_id,
            MappingTemplateModel.data_source_id == data_source_id,
            MappingTemplateModel.domain == domain,
        )
    )
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "列映射模板不存在")
    return template
