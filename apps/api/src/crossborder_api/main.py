"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from crossborder_api.config import Settings, get_settings
from crossborder_api.errors import register_exception_handlers
from crossborder_api.middleware import request_context_middleware
from crossborder_api.routes.health import router as health_router
from crossborder_api.routes.ingestion import router as ingestion_router
from crossborder_api.routes.metrics import router as metrics_router


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    app = FastAPI(
        title=runtime_settings.app_name,
        version=runtime_settings.app_version,
        docs_url="/api/docs" if runtime_settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if runtime_settings.app_env != "production" else None,
    )
    app.state.settings = runtime_settings

    app.middleware("http")(request_context_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.parsed_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    register_exception_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(ingestion_router, prefix="/api/v1")
    app.include_router(metrics_router, prefix="/api/v1")
    return app


app = create_app()
