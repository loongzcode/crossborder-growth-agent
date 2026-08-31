"""Shared request helpers for secure ingestion routes."""

import json
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from crossborder_api.ingestion_schemas import MappingOverride
from crossborder_api.mapping_template_service import get_mapping_template
from crossborder_domain import DataDomain
from crossborder_persistence import MappingTemplateModel

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
type MappingSelection = tuple[dict[str, str | None] | None, MappingTemplateModel | None]
MAPPING_LIST_ADAPTER = TypeAdapter(list[MappingOverride])


async def read_upload(file: UploadFile) -> tuple[str, bytes]:
    filename = file.filename or "dataset.csv"
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "文件不能超过 10 MB")
    return filename, content


def verify_expected_checksum(actual: str, expected: str) -> None:
    if actual != expected.lower():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "文件校验和与预检结果不一致，请重新预检后再确认",
        )


def verify_expected_mapping_signature(actual: str, expected: str) -> None:
    if actual != expected.lower():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "列映射与预检结果不一致，请重新预检后再确认",
        )


def parse_mapping_overrides(value: str) -> list[MappingOverride]:
    try:
        raw = json.loads(value)
        mappings = MAPPING_LIST_ADAPTER.validate_python(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "列映射格式无效") from exc
    sources = [mapping.source_column for mapping in mappings]
    if len(sources) != len(set(sources)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "源列不能重复")
    return mappings


async def resolve_mapping_selection(
    session: AsyncSession,
    *,
    organization_id: UUID,
    data_source_id: UUID,
    domain: DataDomain,
    mappings_json: str | None,
    template_id: UUID | None,
    required: bool,
) -> MappingSelection:
    if mappings_json and template_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "人工列映射和映射模板不能同时提交",
        )
    if template_id:
        template = await get_mapping_template(
            session,
            organization_id=organization_id,
            data_source_id=data_source_id,
            template_id=template_id,
            domain=domain,
        )
        mappings = [MappingOverride.model_validate(item) for item in template.mappings]
        return ({mapping.source_column: mapping.canonical_field for mapping in mappings}, template)
    if mappings_json:
        mappings = parse_mapping_overrides(mappings_json)
        return ({mapping.source_column: mapping.canonical_field for mapping in mappings}, None)
    if required:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "正式导入前必须提交已确认的列映射或映射模板",
        )
    return None, None
