"""Idempotent initial organization, RBAC, and dynamic-menu seed."""

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crossborder_persistence.models import OrganizationModel
from crossborder_persistence.system_models import (
    SystemMenuModel,
    SystemPermissionModel,
    SystemRoleModel,
    SystemUserModel,
)


@dataclass(frozen=True)
class MenuSeed:
    name: str
    path: str
    component: str
    title: str
    icon: str = ""
    sort: int = 0
    permissions: tuple[tuple[str, str], ...] = ()
    children: tuple["MenuSeed", ...] = field(default_factory=tuple)


MENU_SEEDS = (
    MenuSeed(
        "Dashboard",
        "/dashboard",
        "/index/index",
        "menus.dashboard.title",
        "ri:dashboard-line",
        10,
        children=(
            MenuSeed(
                "Console", "console", "/dashboard/console", "menus.dashboard.console", sort=10
            ),
        ),
    ),
    MenuSeed(
        "DataCenter",
        "/data",
        "/index/index",
        "menus.data.title",
        "ri:database-2-line",
        20,
        children=(
            MenuSeed(
                "DataSources",
                "sources",
                "/data/sources",
                "menus.data.sources",
                sort=10,
                permissions=(
                    ("data:source:list", "查看数据源"),
                    ("data:source:add", "新增数据源"),
                    ("data:source:edit", "编辑数据源"),
                    ("data:source:delete", "停用数据源"),
                    ("data:source:test", "测试连接"),
                ),
            ),
            MenuSeed(
                "DataImports",
                "imports",
                "/data/imports",
                "menus.data.imports",
                sort=20,
                permissions=(
                    ("data:ingestion:preview", "预检上传文件"),
                    ("data:ingestion:template", "管理列映射模板"),
                    ("data:ingestion:import", "确认正式导入"),
                    ("data:ingestion:lineage", "查看导入血缘"),
                ),
            ),
            MenuSeed("DataQuality", "quality", "/workspace/index", "menus.data.quality", sort=30),
        ),
    ),
    MenuSeed(
        "Advertising",
        "/advertising",
        "/index/index",
        "menus.advertising.title",
        "ri:megaphone-line",
        30,
        children=(
            MenuSeed(
                "AdDiagnosis",
                "diagnosis",
                "/workspace/index",
                "menus.advertising.diagnosis",
                sort=10,
            ),
            MenuSeed(
                "BudgetSimulation",
                "budget-simulation",
                "/workspace/index",
                "menus.advertising.budgetSimulation",
                sort=20,
            ),
        ),
    ),
    MenuSeed(
        "Products",
        "/products",
        "/index/index",
        "menus.products.title",
        "ri:shopping-bag-3-line",
        40,
        children=(
            MenuSeed(
                "ProductCandidates",
                "candidates",
                "/workspace/index",
                "menus.products.candidates",
                sort=10,
            ),
            MenuSeed(
                "ProductBacktests",
                "backtests",
                "/workspace/index",
                "menus.products.backtests",
                sort=20,
            ),
        ),
    ),
    MenuSeed(
        "ProfitSupply",
        "/profit-supply",
        "/index/index",
        "menus.profitSupply.title",
        "ri:funds-line",
        50,
        children=(
            MenuSeed(
                "ContributionProfit",
                "profit",
                "/workspace/index",
                "menus.profitSupply.profit",
                sort=10,
            ),
            MenuSeed(
                "InventoryRisk",
                "inventory",
                "/workspace/index",
                "menus.profitSupply.inventory",
                sort=20,
            ),
        ),
    ),
    MenuSeed(
        "Insights",
        "/insights",
        "/index/index",
        "menus.insights.title",
        "ri:user-search-line",
        60,
        children=(
            MenuSeed(
                "CustomerInsights",
                "customers",
                "/workspace/index",
                "menus.insights.customers",
                sort=10,
            ),
            MenuSeed(
                "CreativeInsights",
                "creatives",
                "/workspace/index",
                "menus.insights.creatives",
                sort=20,
            ),
        ),
    ),
    MenuSeed(
        "Risk",
        "/risk",
        "/index/index",
        "menus.risk.title",
        "ri:shield-check-line",
        70,
        children=(
            MenuSeed(
                "ComplianceReview",
                "compliance",
                "/workspace/index",
                "menus.risk.compliance",
                sort=10,
            ),
        ),
    ),
    MenuSeed(
        "Agents",
        "/agents",
        "/index/index",
        "menus.agents.title",
        "ri:robot-2-line",
        80,
        children=(
            MenuSeed("AgentRuns", "runs", "/workspace/index", "menus.agents.runs", sort=10),
            MenuSeed(
                "ApprovalCenter",
                "approvals",
                "/workspace/index",
                "menus.agents.approvals",
                sort=20,
            ),
            MenuSeed(
                "EvaluationCenter",
                "evaluations",
                "/workspace/index",
                "menus.agents.evaluations",
                sort=30,
            ),
        ),
    ),
    MenuSeed(
        "System",
        "/system",
        "/index/index",
        "menus.system.title",
        "ri:settings-3-line",
        90,
        children=(
            MenuSeed(
                "User",
                "user",
                "/system/user",
                "menus.system.user",
                sort=10,
                permissions=(
                    ("system:user:add", "新增用户"),
                    ("system:user:edit", "编辑用户"),
                    ("system:user:delete", "停用用户"),
                ),
            ),
            MenuSeed(
                "Role",
                "role",
                "/system/role",
                "menus.system.role",
                sort=20,
                permissions=(
                    ("system:role:add", "新增角色"),
                    ("system:role:edit", "编辑角色"),
                    ("system:role:delete", "删除角色"),
                    ("system:role:grant", "分配权限"),
                ),
            ),
            MenuSeed(
                "Menus",
                "menu",
                "/system/menu",
                "menus.system.menu",
                sort=30,
                permissions=(
                    ("system:menu:add", "新增菜单"),
                    ("system:menu:edit", "编辑菜单"),
                    ("system:menu:delete", "删除菜单"),
                ),
            ),
        ),
    ),
)


async def _upsert_menu_tree(
    session: AsyncSession,
    seeds: tuple[MenuSeed, ...],
    *,
    parent_id: UUID | None = None,
) -> list[SystemMenuModel]:
    created: list[SystemMenuModel] = []
    for seed in seeds:
        menu = await session.scalar(
            select(SystemMenuModel)
            .options(selectinload(SystemMenuModel.permissions))
            .where(SystemMenuModel.name == seed.name)
        )
        if menu is None:
            menu = SystemMenuModel(name=seed.name, permissions=[])
            session.add(menu)
        menu.parent_id = parent_id
        menu.path = seed.path
        menu.component = seed.component
        menu.title = seed.title
        menu.icon = seed.icon
        menu.sort = seed.sort
        menu.enabled = True
        menu.keep_alive = not bool(seed.children)
        await session.flush()
        permissions_by_code = {permission.code: permission for permission in menu.permissions}
        for sort, (code, title) in enumerate(seed.permissions, start=1):
            permission = permissions_by_code.get(code)
            if permission is None:
                permission = SystemPermissionModel(code=code, title=title, sort=sort)
                menu.permissions.append(permission)
            permission.title = title
            permission.sort = sort
        created.append(menu)
        created.extend(await _upsert_menu_tree(session, seed.children, parent_id=menu.id))
    return created


async def seed_default_system(
    session: AsyncSession,
    *,
    admin_password_hash: str,
    organization_slug: str = "demo-company",
    admin_username: str = "Super",
) -> SystemUserModel:
    organization = await session.scalar(
        select(OrganizationModel).where(OrganizationModel.slug == organization_slug)
    )
    if organization is None:
        organization = OrganizationModel(name="跨境增长演示公司", slug=organization_slug)
        session.add(organization)
        await session.flush()

    super_role = await session.scalar(
        select(SystemRoleModel)
        .options(
            selectinload(SystemRoleModel.menus),
            selectinload(SystemRoleModel.permissions),
        )
        .where(
            SystemRoleModel.organization_id == organization.id,
            SystemRoleModel.code == "R_SUPER",
        )
    )
    if super_role is None:
        super_role = SystemRoleModel(
            organization_id=organization.id,
            name="超级管理员",
            code="R_SUPER",
            description="拥有组织内全部系统管理权限",
            enabled=True,
            is_system=True,
            menus=[],
            permissions=[],
        )
        session.add(super_role)
        await session.flush()

    await _upsert_menu_tree(session, MENU_SEEDS)
    await session.flush()
    menus = list(
        (
            await session.scalars(
                select(SystemMenuModel)
                .options(selectinload(SystemMenuModel.permissions))
                .order_by(SystemMenuModel.sort)
            )
        ).all()
    )
    super_role.menus = menus
    super_role.permissions = [permission for menu in menus for permission in menu.permissions]

    user = await session.scalar(
        select(SystemUserModel)
        .options(selectinload(SystemUserModel.roles))
        .where(
            SystemUserModel.organization_id == organization.id,
            SystemUserModel.username == admin_username,
        )
    )
    if user is None:
        user = SystemUserModel(
            organization_id=organization.id,
            username=admin_username,
            nickname="系统管理员",
            email="admin@crossborder.local",
            password_hash=admin_password_hash,
            enabled=True,
            is_superuser=True,
            roles=[super_role],
        )
        session.add(user)
    elif not user.roles:
        user.roles = [super_role]
    await session.flush()
    return user
