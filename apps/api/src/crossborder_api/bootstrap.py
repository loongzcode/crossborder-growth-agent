"""Create the first organization, dynamic menus, roles, and administrator."""

import asyncio
import os

from crossborder_api.config import get_settings
from crossborder_api.security import hash_password
from crossborder_persistence import (
    create_engine,
    create_session_factory,
    seed_default_system,
    session_scope,
)


async def bootstrap() -> None:
    settings = get_settings()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    if not password:
        if settings.app_env == "production":
            raise RuntimeError("生产环境必须设置 BOOTSTRAP_ADMIN_PASSWORD")
        password = "12345678"

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    try:
        async with session_scope(session_factory) as session:
            user = await seed_default_system(
                session,
                admin_password_hash=hash_password(password),
            )
            print(f"系统初始化完成，管理员账号：{user.username}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(bootstrap())
