"""Database-backed dynamic menus and menu administration endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crossborder_api.auth_dependencies import (
    CurrentUser,
    CurrentUserDependency,
    require_permissions,
)
from crossborder_api.dependencies import get_db_session
from crossborder_api.schemas import ApiResponse
from crossborder_api.system_schemas import MenuRoute, MenuWrite, PermissionWrite
from crossborder_api.system_serializers import build_menu_tree
from crossborder_persistence import SystemMenuModel, SystemPermissionModel

router = APIRouter(tags=["system-menus"])


async def _all_menus(session: AsyncSession) -> list[SystemMenuModel]:
    return list(
        (
            await session.scalars(
                select(SystemMenuModel)
                .options(selectinload(SystemMenuModel.permissions))
                .order_by(SystemMenuModel.sort, SystemMenuModel.name)
            )
        ).all()
    )


async def _get_menu(session: AsyncSession, menu_id: UUID) -> SystemMenuModel:
    menu = await session.scalar(
        select(SystemMenuModel)
        .options(selectinload(SystemMenuModel.permissions))
        .where(SystemMenuModel.id == menu_id)
    )
    if menu is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "菜单不存在")
    return menu


async def _validate_parent(
    session: AsyncSession, parent_id: UUID | None, *, menu_id: UUID | None = None
) -> None:
    visited: set[UUID] = set()
    current_id = parent_id
    while current_id:
        if current_id == menu_id or current_id in visited:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "菜单层级不能形成循环")
        visited.add(current_id)
        parent = await _get_menu(session, current_id)
        current_id = parent.parent_id


def _allowed_menu_ids(current: CurrentUser, menus: list[SystemMenuModel]) -> set[UUID]:
    if current.is_superuser:
        return {menu.id for menu in menus}
    parent_by_id = {menu.id: menu.parent_id for menu in menus}
    allowed = set(current.menu_ids)
    for menu_id in tuple(allowed):
        parent_id = parent_by_id.get(menu_id)
        while parent_id:
            allowed.add(parent_id)
            parent_id = parent_by_id.get(parent_id)
    return allowed


@router.get("/api/v3/system/menus/simple", response_model=ApiResponse[list[MenuRoute]])
async def dynamic_menus(
    current: CurrentUserDependency,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[MenuRoute]]:
    menus = await _all_menus(session)
    allowed = _allowed_menu_ids(current, menus)
    visible = [menu for menu in menus if menu.id in allowed and menu.enabled]
    return ApiResponse(data=build_menu_tree(visible))


@router.get("/api/menu/list", response_model=ApiResponse[list[MenuRoute]])
async def list_menus(
    _current: CurrentUserDependency,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[MenuRoute]]:
    return ApiResponse(data=build_menu_tree(await _all_menus(session)))


def _apply_menu(menu: SystemMenuModel, payload: MenuWrite) -> None:
    menu.parent_id = payload.parent_id
    menu.name = payload.name
    menu.path = payload.path
    menu.component = payload.component
    menu.title = payload.title
    menu.icon = payload.icon
    menu.sort = payload.sort
    menu.enabled = payload.enabled
    menu.hidden = payload.hidden
    menu.hide_tab = payload.hide_tab
    menu.keep_alive = payload.keep_alive
    menu.fixed_tab = payload.fixed_tab
    menu.full_page = payload.full_page
    menu.link = payload.link
    menu.iframe = payload.iframe
    menu.active_path = payload.active_path


@router.post("/api/menu", response_model=ApiResponse[dict[str, str]])
async def create_menu(
    payload: MenuWrite,
    _actor: Annotated[CurrentUser, Depends(require_permissions("system:menu:add"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[dict[str, str]]:
    duplicate = await session.scalar(
        select(SystemMenuModel.id).where(SystemMenuModel.name == payload.name)
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "路由名称已存在")
    await _validate_parent(session, payload.parent_id)
    menu = SystemMenuModel()
    _apply_menu(menu, payload)
    session.add(menu)
    await session.flush()
    return ApiResponse(data={"id": str(menu.id)}, msg="菜单创建成功")


@router.put("/api/menu/{menu_id}", response_model=ApiResponse[dict[str, str]])
async def update_menu(
    menu_id: UUID,
    payload: MenuWrite,
    _actor: Annotated[CurrentUser, Depends(require_permissions("system:menu:edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[dict[str, str]]:
    menu = await _get_menu(session, menu_id)
    duplicate = await session.scalar(
        select(SystemMenuModel.id).where(
            SystemMenuModel.name == payload.name,
            SystemMenuModel.id != menu_id,
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "路由名称已存在")
    await _validate_parent(session, payload.parent_id, menu_id=menu.id)
    _apply_menu(menu, payload)
    await session.flush()
    return ApiResponse(data={"id": str(menu.id)}, msg="菜单更新成功")


@router.delete("/api/menu/{menu_id}", response_model=ApiResponse[dict[str, bool]])
async def delete_menu(
    menu_id: UUID,
    _actor: Annotated[CurrentUser, Depends(require_permissions("system:menu:delete"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[dict[str, bool]]:
    menu = await _get_menu(session, menu_id)
    await session.delete(menu)
    await session.flush()
    return ApiResponse(data={"deleted": True}, msg="菜单删除成功")


@router.post(
    "/api/menu/{menu_id}/permissions",
    response_model=ApiResponse[dict[str, str]],
)
async def create_menu_permission(
    menu_id: UUID,
    payload: PermissionWrite,
    _actor: Annotated[CurrentUser, Depends(require_permissions("system:menu:add"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[dict[str, str]]:
    await _get_menu(session, menu_id)
    duplicate = await session.scalar(
        select(SystemPermissionModel.id).where(
            SystemPermissionModel.menu_id == menu_id,
            SystemPermissionModel.code == payload.code,
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "该菜单下的权限标识已存在")
    permission = SystemPermissionModel(
        menu_id=menu_id,
        title=payload.title,
        code=payload.code,
        sort=payload.sort,
    )
    session.add(permission)
    await session.flush()
    return ApiResponse(data={"id": str(permission.id)}, msg="按钮权限创建成功")


@router.put(
    "/api/menu/permissions/{permission_id}",
    response_model=ApiResponse[dict[str, str]],
)
async def update_menu_permission(
    permission_id: UUID,
    payload: PermissionWrite,
    _actor: Annotated[CurrentUser, Depends(require_permissions("system:menu:edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[dict[str, str]]:
    permission = await session.get(SystemPermissionModel, permission_id)
    if permission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "按钮权限不存在")
    duplicate = await session.scalar(
        select(SystemPermissionModel.id).where(
            SystemPermissionModel.menu_id == permission.menu_id,
            SystemPermissionModel.code == payload.code,
            SystemPermissionModel.id != permission_id,
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "该菜单下的权限标识已存在")
    permission.title = payload.title
    permission.code = payload.code
    permission.sort = payload.sort
    await session.flush()
    return ApiResponse(data={"id": str(permission.id)}, msg="按钮权限更新成功")


@router.delete(
    "/api/menu/permissions/{permission_id}",
    response_model=ApiResponse[dict[str, bool]],
)
async def delete_menu_permission(
    permission_id: UUID,
    _actor: Annotated[CurrentUser, Depends(require_permissions("system:menu:delete"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[dict[str, bool]]:
    permission = await session.get(SystemPermissionModel, permission_id)
    if permission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "按钮权限不存在")
    await session.delete(permission)
    await session.flush()
    return ApiResponse(data={"deleted": True}, msg="按钮权限删除成功")
