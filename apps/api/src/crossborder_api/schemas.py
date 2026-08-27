"""Shared HTTP response schemas."""

from pydantic import BaseModel, ConfigDict


class ApiResponse[DataT](BaseModel):
    """Response envelope consumed by the Vue administration console."""

    model_config = ConfigDict(extra="forbid")

    code: int = 200
    msg: str = "ok"
    data: DataT


class ProblemDetail(BaseModel):
    """Safe error details without stack traces or secrets."""

    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    detail: str
    request_id: str | None = None
