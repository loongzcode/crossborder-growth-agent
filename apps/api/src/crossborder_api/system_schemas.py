"""Strict API contracts for authentication and system management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SystemSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class LoginRequest(SystemSchema):
    username: str = Field(alias="userName", min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=128)
    organization_slug: str = Field(default="demo-company", alias="organizationSlug")


class LoginResponse(SystemSchema):
    token: str
    refresh_token: str = Field(alias="refreshToken")


class RefreshRequest(SystemSchema):
    refresh_token: str = Field(alias="refreshToken")


class UserInfo(SystemSchema):
    buttons: list[str]
    roles: list[str]
    user_id: str = Field(alias="userId")
    username: str = Field(alias="userName")
    email: str
    avatar: str | None = None


class UserWrite(SystemSchema):
    username: str = Field(alias="userName", min_length=2, max_length=100)
    nickname: str = Field(alias="nickName", min_length=1, max_length=100)
    email: str = Field(alias="userEmail", min_length=3, max_length=254)
    phone: str = Field(default="", alias="userPhone", max_length=32)
    gender: str = Field(default="保密", alias="userGender", max_length=16)
    avatar: str = Field(default="", max_length=500)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role_codes: list[str] = Field(default_factory=list, alias="userRoles")
    enabled: bool = True

    @field_validator("email")
    @classmethod
    def validate_email_shape(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("邮箱格式不正确")
        return normalized


class UserListItem(SystemSchema):
    id: str
    avatar: str
    status: str
    username: str = Field(alias="userName")
    gender: str = Field(alias="userGender")
    nickname: str = Field(alias="nickName")
    phone: str = Field(alias="userPhone")
    email: str = Field(alias="userEmail")
    role_codes: list[str] = Field(alias="userRoles")
    created_by: str = Field(default="system", alias="createBy")
    created_at: datetime = Field(alias="createTime")
    updated_by: str = Field(default="system", alias="updateBy")
    updated_at: datetime = Field(alias="updateTime")


class UserPage(SystemSchema):
    records: list[UserListItem]
    current: int
    size: int
    total: int


class RoleWrite(SystemSchema):
    name: str = Field(alias="roleName", min_length=2, max_length=100)
    code: str = Field(alias="roleCode", min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    enabled: bool = True


class RoleListItem(SystemSchema):
    role_id: str = Field(alias="roleId")
    role_name: str = Field(alias="roleName")
    role_code: str = Field(alias="roleCode")
    description: str
    enabled: bool
    created_at: datetime = Field(alias="createTime")
    is_system: bool = Field(alias="isSystem")


class RolePage(SystemSchema):
    records: list[RoleListItem]
    current: int
    size: int
    total: int


class RoleAccess(SystemSchema):
    menu_ids: list[str] = Field(alias="menuIds")
    permission_ids: list[str] = Field(alias="permissionIds")


class MenuWrite(SystemSchema):
    parent_id: UUID | None = Field(default=None, alias="parentId")
    name: str = Field(min_length=2, max_length=100)
    path: str = Field(min_length=1, max_length=300)
    component: str = Field(default="", max_length=300)
    title: str = Field(min_length=1, max_length=200)
    icon: str = Field(default="", max_length=100)
    sort: int = Field(default=0, ge=0, le=10000)
    enabled: bool = True
    hidden: bool = False
    hide_tab: bool = Field(default=False, alias="hideTab")
    keep_alive: bool = Field(default=False, alias="keepAlive")
    fixed_tab: bool = Field(default=False, alias="fixedTab")
    full_page: bool = Field(default=False, alias="fullPage")
    link: str = Field(default="", max_length=500)
    iframe: bool = False
    active_path: str = Field(default="", alias="activePath", max_length=300)


class PermissionWrite(SystemSchema):
    title: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100)
    sort: int = Field(default=0, ge=0, le=10000)


class MenuPermission(SystemSchema):
    id: str
    title: str
    auth_mark: str = Field(alias="authMark")
    permission_code: str = Field(alias="permissionCode")


class MenuMeta(SystemSchema):
    title: str
    icon: str | None = None
    sort: int
    is_enable: bool = Field(alias="isEnable")
    is_hide: bool = Field(alias="isHide")
    is_hide_tab: bool = Field(alias="isHideTab")
    keep_alive: bool = Field(alias="keepAlive")
    fixed_tab: bool = Field(alias="fixedTab")
    is_full_page: bool = Field(alias="isFullPage")
    link: str | None = None
    is_iframe: bool = Field(alias="isIframe")
    active_path: str | None = Field(alias="activePath")
    auth_list: list[MenuPermission] = Field(alias="authList")


class MenuRoute(SystemSchema):
    id: str
    parent_id: str | None = Field(alias="parentId")
    name: str
    path: str
    component: str
    meta: MenuMeta
    children: list["MenuRoute"] = Field(default_factory=list)
