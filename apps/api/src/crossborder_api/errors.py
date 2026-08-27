"""Centralized exception handling."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from crossborder_api.schemas import ApiResponse, ProblemDetail


def _error_response(request: Request, status: int, title: str, detail: str) -> JSONResponse:
    problem = ProblemDetail(
        type="about:blank",
        title=title,
        status=status,
        detail=detail,
        request_id=getattr(request.state, "request_id", None),
    )
    envelope = ApiResponse[ProblemDetail](code=status, msg=title, data=problem)
    return JSONResponse(status_code=status, content=envelope.model_dump(mode="json"))


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
    return _error_response(request, exc.status_code, "请求错误", detail)


async def unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
    return _error_response(request, 500, "服务内部错误", "服务暂时无法完成请求")


async def validation_exception_handler(
    request: Request, _exc: RequestValidationError
) -> JSONResponse:
    return _error_response(request, 422, "参数校验失败", "请求字段或数据格式不符合要求")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
