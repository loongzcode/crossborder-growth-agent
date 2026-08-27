"""File validation and normalized-record preview routes."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from crossborder_api.routes.ingestion_shared import read_upload
from crossborder_api.schemas import ApiResponse
from crossborder_connectors import preview_advertising_file, preview_dataset_file
from crossborder_connectors.tabular import UnsupportedTabularFile
from crossborder_domain import AdvertisingIngestionPreview, DataDomain, DatasetIngestionPreview

router = APIRouter()


@router.post(
    "/advertising/preview",
    response_model=ApiResponse[AdvertisingIngestionPreview],
)
async def preview_advertising_report(
    file: Annotated[UploadFile, File(description="TikTok Ads CSV 或 XLSX 报表")],
) -> ApiResponse[AdvertisingIngestionPreview]:
    filename, content = await read_upload(file)
    try:
        preview = preview_advertising_file(content, filename)
    except (UnsupportedTabularFile, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return ApiResponse(data=preview)


@router.post(
    "/datasets/{domain}/preview",
    response_model=ApiResponse[DatasetIngestionPreview],
)
async def preview_dataset_report(
    domain: DataDomain,
    file: Annotated[UploadFile, File(description="业务数据 CSV 或 XLSX 报表")],
) -> ApiResponse[DatasetIngestionPreview]:
    filename, content = await read_upload(file)
    try:
        preview = preview_dataset_file(content, filename, domain)
    except (UnsupportedTabularFile, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return ApiResponse(data=preview)
