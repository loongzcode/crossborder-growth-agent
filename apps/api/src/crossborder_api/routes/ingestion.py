"""Data-ingestion route composition."""

from fastapi import APIRouter

from crossborder_api.routes.ingestion_catalogs import router as catalogs_router
from crossborder_api.routes.ingestion_imports import router as imports_router
from crossborder_api.routes.ingestion_lineage import router as lineage_router
from crossborder_api.routes.ingestion_previews import router as previews_router

router = APIRouter(prefix="/ingestion", tags=["data-ingestion"])
router.include_router(catalogs_router)
router.include_router(previews_router)
router.include_router(imports_router)
router.include_router(lineage_router)
