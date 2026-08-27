"""System-management persistence-to-API transformations."""

from collections import defaultdict
from uuid import UUID

from crossborder_api.system_schemas import (
    MenuMeta,
    MenuPermission,
    MenuRoute,
    RoleListItem,
    UserListItem,
)
from crossborder_persistence import SystemMenuModel, SystemRoleModel, SystemUserModel


def serialize_user(user: SystemUserModel) -> UserListItem:
    return UserListItem(
        id=str(user.id),
        avatar=user.avatar_url,
        status="1" if user.enabled else "4",
        userName=user.username,
        userGender=user.gender,
        nickName=user.nickname,
        userPhone=user.phone,
        userEmail=user.email,
        userRoles=sorted(role.code for role in user.roles),
        createTime=user.created_at,
        updateTime=user.updated_at,
    )


def serialize_role(role: SystemRoleModel) -> RoleListItem:
    return RoleListItem(
        roleId=str(role.id),
        roleName=role.name,
        roleCode=role.code,
        description=role.description,
        enabled=role.enabled,
        createTime=role.created_at,
        isSystem=role.is_system,
    )


def build_menu_tree(menus: list[SystemMenuModel]) -> list[MenuRoute]:
    by_parent: dict[UUID | None, list[SystemMenuModel]] = defaultdict(list)
    for menu in menus:
        by_parent[menu.parent_id].append(menu)
    for siblings in by_parent.values():
        siblings.sort(key=lambda item: (item.sort, item.name))

    def convert(menu: SystemMenuModel) -> MenuRoute:
        permissions = sorted(menu.permissions, key=lambda item: (item.sort, item.code))
        return MenuRoute(
            id=str(menu.id),
            parentId=str(menu.parent_id) if menu.parent_id else None,
            name=menu.name,
            path=menu.path,
            component=menu.component,
            meta=MenuMeta(
                title=menu.title,
                icon=menu.icon or None,
                sort=menu.sort,
                isEnable=menu.enabled,
                isHide=menu.hidden,
                isHideTab=menu.hide_tab,
                keepAlive=menu.keep_alive,
                fixedTab=menu.fixed_tab,
                isFullPage=menu.full_page,
                link=menu.link or None,
                isIframe=menu.iframe,
                activePath=menu.active_path or None,
                authList=[
                    MenuPermission(
                        id=str(permission.id),
                        title=permission.title,
                        authMark=permission.code.rsplit(":", maxsplit=1)[-1],
                        permissionCode=permission.code,
                    )
                    for permission in permissions
                ],
            ),
            children=[convert(child) for child in by_parent.get(menu.id, [])],
        )

    return [convert(root) for root in by_parent.get(None, [])]
