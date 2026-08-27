"""Authenticated identity and RBAC dependencies."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crossborder_api.dependencies import get_db_session
from crossborder_api.security import InvalidAccessToken, decode_token
from crossborder_persistence import SystemRoleModel, SystemUserModel

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user: SystemUserModel
    role_codes: frozenset[str]
    permission_codes: frozenset[str]
    menu_ids: frozenset[UUID]

    @property
    def is_superuser(self) -> bool:
        return self.user.is_superuser


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "请先登录")
    try:
        payload = decode_token(
            credentials.credentials,
            expected_type="access",
            settings=request.app.state.settings,
        )
    except InvalidAccessToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    user_id = UUID(payload["sub"])
    organization_id = UUID(payload["org"])
    statement = (
        select(SystemUserModel)
        .options(
            selectinload(SystemUserModel.roles).selectinload(SystemRoleModel.menus),
            selectinload(SystemUserModel.roles).selectinload(SystemRoleModel.permissions),
        )
        .where(
            SystemUserModel.id == user_id,
            SystemUserModel.organization_id == organization_id,
            SystemUserModel.enabled.is_(True),
        )
    )
    user = await session.scalar(statement)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号不存在或已停用")

    enabled_roles = [role for role in user.roles if role.enabled]
    return CurrentUser(
        user=user,
        role_codes=frozenset(role.code for role in enabled_roles),
        permission_codes=frozenset(
            permission.code for role in enabled_roles for permission in role.permissions
        ),
        menu_ids=frozenset(menu.id for role in enabled_roles for menu in role.menus),
    )


CurrentUserDependency = Annotated[CurrentUser, Depends(get_current_user)]
PermissionDependency = Callable[..., Coroutine[Any, Any, CurrentUser]]


def require_permissions(*required: str) -> PermissionDependency:
    async def dependency(current: CurrentUserDependency) -> CurrentUser:
        if current.is_superuser or set(required) <= current.permission_codes:
            return current
        raise HTTPException(status.HTTP_403_FORBIDDEN, "没有执行此操作的权限")

    return dependency
