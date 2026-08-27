"""Organization-scoped role and access-assignment endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crossborder_api.auth_dependencies import (
    CurrentUser,
    CurrentUserDependency,
    require_permissions,
)
from crossborder_api.dependencies import get_db_session
from crossborder_api.schemas import ApiResponse
from crossborder_api.system_schemas import RoleAccess, RoleListItem, RolePage, RoleWrite
from crossborder_api.system_serializers import serialize_role
from crossborder_persistence import (
    SystemMenuModel,
    SystemPermissionModel,
    SystemRoleModel,
    user_role_assignments,
)

router = APIRouter(prefix="/api/role", tags=["system-roles"])


async def _get_role(session: AsyncSession, organization_id: UUID, role_id: UUID) -> SystemRoleModel:
    role = await session.scalar(
        select(SystemRoleModel)
        .options(
            selectinload(SystemRoleModel.menus),
            selectinload(SystemRoleModel.permissions),
        )
        .where(
            SystemRoleModel.id == role_id,
            SystemRoleModel.organization_id == organization_id,
        )
    )
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "角色不存在")
    return role


@router.get("/list", response_model=ApiResponse[RolePage])
async def list_roles(
    current_user: CurrentUserDependency,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    role_name: Annotated[str | None, Query(alias="roleName")] = None,
    role_code: Annotated[str | None, Query(alias="roleCode")] = None,
    description: str | None = None,
    enabled: bool | None = None,
    start_time: Annotated[datetime | None, Query(alias="startTime")] = None,
    end_time: Annotated[datetime | None, Query(alias="endTime")] = None,
) -> ApiResponse[RolePage]:
    filters = [SystemRoleModel.organization_id == current_user.user.organization_id]
    if role_name:
        filters.append(SystemRoleModel.name.ilike(f"%{role_name}%"))
    if role_code:
        filters.append(SystemRoleModel.code.ilike(f"%{role_code}%"))
    if description:
        filters.append(SystemRoleModel.description.ilike(f"%{description}%"))
    if enabled is not None:
        filters.append(SystemRoleModel.enabled.is_(enabled))
    if start_time:
        filters.append(SystemRoleModel.created_at >= start_time)
    if end_time:
        filters.append(SystemRoleModel.created_at <= end_time)

    total = int(
        await session.scalar(select(func.count()).select_from(SystemRoleModel).where(*filters)) or 0
    )
    roles = list(
        (
            await session.scalars(
                select(SystemRoleModel)
                .where(*filters)
                .order_by(SystemRoleModel.created_at.desc())
                .offset((current - 1) * size)
                .limit(size)
            )
        ).all()
    )
    return ApiResponse(
        data=RolePage(
            records=[serialize_role(role) for role in roles],
            current=current,
            size=size,
            total=total,
        )
    )


@router.post("", response_model=ApiResponse[RoleListItem])
async def create_role(
    payload: RoleWrite,
    actor: Annotated[CurrentUser, Depends(require_permissions("system:role:add"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[RoleListItem]:
    duplicate = await session.scalar(
        select(SystemRoleModel.id).where(
            SystemRoleModel.organization_id == actor.user.organization_id,
            func.lower(SystemRoleModel.code) == payload.code.lower(),
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "角色编码已存在")
    role = SystemRoleModel(
        organization_id=actor.user.organization_id,
        name=payload.name,
        code=payload.code,
        description=payload.description,
        enabled=payload.enabled,
    )
    session.add(role)
    await session.flush()
    return ApiResponse(data=serialize_role(role), msg="角色创建成功")


@router.put("/{role_id}", response_model=ApiResponse[RoleListItem])
async def update_role(
    role_id: UUID,
    payload: RoleWrite,
    actor: Annotated[CurrentUser, Depends(require_permissions("system:role:edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[RoleListItem]:
    role = await _get_role(session, actor.user.organization_id, role_id)
    if role.is_system and role.code != payload.code:
        raise HTTPException(status.HTTP_409_CONFLICT, "系统角色编码不能修改")
    duplicate = await session.scalar(
        select(SystemRoleModel.id).where(
            SystemRoleModel.organization_id == actor.user.organization_id,
            SystemRoleModel.id != role_id,
            func.lower(SystemRoleModel.code) == payload.code.lower(),
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "角色编码已存在")
    role.name = payload.name
    role.code = payload.code
    role.description = payload.description
    role.enabled = payload.enabled
    await session.flush()
    return ApiResponse(data=serialize_role(role), msg="角色更新成功")


@router.delete("/{role_id}", response_model=ApiResponse[dict[str, bool]])
async def delete_role(
    role_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("system:role:delete"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[dict[str, bool]]:
    role = await _get_role(session, actor.user.organization_id, role_id)
    if role.is_system:
        raise HTTPException(status.HTTP_409_CONFLICT, "系统角色不能删除")
    await session.execute(
        delete(user_role_assignments).where(user_role_assignments.c.role_id == role.id)
    )
    await session.delete(role)
    await session.flush()
    return ApiResponse(data={"deleted": True}, msg="角色删除成功")


@router.get("/{role_id}/permissions", response_model=ApiResponse[RoleAccess])
async def get_role_access(
    role_id: UUID,
    current_user: CurrentUserDependency,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[RoleAccess]:
    role = await _get_role(session, current_user.user.organization_id, role_id)
    return ApiResponse(
        data=RoleAccess(
            menuIds=[str(menu.id) for menu in role.menus],
            permissionIds=[str(permission.id) for permission in role.permissions],
        )
    )


@router.put("/{role_id}/permissions", response_model=ApiResponse[RoleAccess])
async def update_role_access(
    role_id: UUID,
    payload: RoleAccess,
    actor: Annotated[CurrentUser, Depends(require_permissions("system:role:grant"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[RoleAccess]:
    role = await _get_role(session, actor.user.organization_id, role_id)
    menu_ids = {UUID(value) for value in payload.menu_ids}
    permission_ids = {UUID(value) for value in payload.permission_ids}
    menus = list(
        (
            await session.scalars(select(SystemMenuModel).where(SystemMenuModel.id.in_(menu_ids)))
        ).all()
    )
    permissions = list(
        (
            await session.scalars(
                select(SystemPermissionModel).where(SystemPermissionModel.id.in_(permission_ids))
            )
        ).all()
    )
    if len(menus) != len(menu_ids) or len(permissions) != len(permission_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "包含不存在的菜单或权限")
    role.menus = menus
    role.permissions = permissions
    await session.flush()
    return ApiResponse(data=payload, msg="角色权限保存成功")
