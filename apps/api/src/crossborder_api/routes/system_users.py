"""Organization-scoped user administration endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crossborder_api.auth_dependencies import (
    CurrentUser,
    CurrentUserDependency,
    require_permissions,
)
from crossborder_api.dependencies import get_db_session
from crossborder_api.schemas import ApiResponse
from crossborder_api.security import hash_password
from crossborder_api.system_schemas import UserListItem, UserPage, UserWrite
from crossborder_api.system_serializers import serialize_user
from crossborder_persistence import SystemRoleModel, SystemUserModel

router = APIRouter(prefix="/api/user", tags=["system-users"])


async def _roles_by_codes(
    session: AsyncSession, organization_id: UUID, codes: list[str]
) -> list[SystemRoleModel]:
    roles = list(
        (
            await session.scalars(
                select(SystemRoleModel).where(
                    SystemRoleModel.organization_id == organization_id,
                    SystemRoleModel.code.in_(codes),
                    SystemRoleModel.enabled.is_(True),
                )
            )
        ).all()
    )
    if len(roles) != len(set(codes)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "包含不存在或已停用的角色")
    return roles


async def _get_user(session: AsyncSession, organization_id: UUID, user_id: UUID) -> SystemUserModel:
    user = await session.scalar(
        select(SystemUserModel)
        .options(selectinload(SystemUserModel.roles))
        .where(
            SystemUserModel.id == user_id,
            SystemUserModel.organization_id == organization_id,
        )
    )
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    return user


@router.get("/list", response_model=ApiResponse[UserPage])
async def list_users(
    current_user: CurrentUserDependency,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    username: Annotated[str | None, Query(alias="userName")] = None,
    email: Annotated[str | None, Query(alias="userEmail")] = None,
    phone: Annotated[str | None, Query(alias="userPhone")] = None,
    gender: Annotated[str | None, Query(alias="userGender")] = None,
    status_value: Annotated[str | None, Query(alias="status")] = None,
) -> ApiResponse[UserPage]:
    filters = [SystemUserModel.organization_id == current_user.user.organization_id]
    if username:
        filters.append(SystemUserModel.username.ilike(f"%{username}%"))
    if email:
        filters.append(SystemUserModel.email.ilike(f"%{email}%"))
    if phone:
        filters.append(SystemUserModel.phone.ilike(f"%{phone}%"))
    if gender:
        filters.append(SystemUserModel.gender == gender)
    if status_value:
        filters.append(SystemUserModel.enabled.is_(status_value == "1"))

    total = int(
        await session.scalar(select(func.count()).select_from(SystemUserModel).where(*filters)) or 0
    )
    users = list(
        (
            await session.scalars(
                select(SystemUserModel)
                .options(selectinload(SystemUserModel.roles))
                .where(*filters)
                .order_by(SystemUserModel.created_at.desc())
                .offset((current - 1) * size)
                .limit(size)
            )
        ).all()
    )
    return ApiResponse(
        data=UserPage(
            records=[serialize_user(user) for user in users],
            current=current,
            size=size,
            total=total,
        )
    )


@router.post("", response_model=ApiResponse[UserListItem])
async def create_user(
    payload: UserWrite,
    actor: Annotated[CurrentUser, Depends(require_permissions("system:user:add"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[UserListItem]:
    if not payload.password:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "新增用户必须设置初始密码")
    duplicate = await session.scalar(
        select(SystemUserModel.id).where(
            SystemUserModel.organization_id == actor.user.organization_id,
            or_(
                func.lower(SystemUserModel.username) == payload.username.lower(),
                func.lower(SystemUserModel.email) == payload.email.lower(),
            ),
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名或邮箱已存在")
    roles = await _roles_by_codes(session, actor.user.organization_id, payload.role_codes)
    user = SystemUserModel(
        organization_id=actor.user.organization_id,
        username=payload.username,
        nickname=payload.nickname,
        email=payload.email,
        phone=payload.phone,
        gender=payload.gender,
        avatar_url=payload.avatar,
        password_hash=hash_password(payload.password),
        enabled=payload.enabled,
        roles=roles,
    )
    session.add(user)
    await session.flush()
    return ApiResponse(data=serialize_user(user), msg="用户创建成功")


@router.put("/{user_id}", response_model=ApiResponse[UserListItem])
async def update_user(
    user_id: UUID,
    payload: UserWrite,
    actor: Annotated[CurrentUser, Depends(require_permissions("system:user:edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[UserListItem]:
    user = await _get_user(session, actor.user.organization_id, user_id)
    duplicate = await session.scalar(
        select(SystemUserModel.id).where(
            SystemUserModel.organization_id == actor.user.organization_id,
            SystemUserModel.id != user_id,
            or_(
                func.lower(SystemUserModel.username) == payload.username.lower(),
                func.lower(SystemUserModel.email) == payload.email.lower(),
            ),
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名或邮箱已存在")
    if user.id == actor.user.id and not payload.enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "不能停用当前登录账号")
    user.username = payload.username
    user.nickname = payload.nickname
    user.email = payload.email
    user.phone = payload.phone
    user.gender = payload.gender
    user.avatar_url = payload.avatar
    user.enabled = payload.enabled
    user.roles = await _roles_by_codes(session, actor.user.organization_id, payload.role_codes)
    if payload.password:
        user.password_hash = hash_password(payload.password)
    await session.flush()
    return ApiResponse(data=serialize_user(user), msg="用户更新成功")


@router.delete("/{user_id}", response_model=ApiResponse[dict[str, bool]])
async def disable_user(
    user_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("system:user:delete"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[dict[str, bool]]:
    user = await _get_user(session, actor.user.organization_id, user_id)
    if user.id == actor.user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "不能停用当前登录账号")
    user.enabled = False
    await session.flush()
    return ApiResponse(data={"disabled": True}, msg="用户已停用")
