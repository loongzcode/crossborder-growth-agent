"""Application dependency boundaries."""

from collections.abc import AsyncIterator

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crossborder_persistence import session_scope


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state, "session_factory", None
    )
    if session_factory is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "数据库会话尚未就绪")
    async with session_scope(session_factory) as session:
        yield session
