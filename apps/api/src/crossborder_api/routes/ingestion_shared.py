"""Shared request helpers for ingestion routes."""

from fastapi import HTTPException, UploadFile, status

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


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
