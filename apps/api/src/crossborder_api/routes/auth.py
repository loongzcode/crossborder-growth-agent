"""Login, token refresh, and current-user endpoints."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crossborder_api.auth_dependencies import CurrentUserDependency
from crossborder_api.dependencies import get_db_session
from crossborder_api.schemas import ApiResponse
from crossborder_api.security import (
    InvalidAccessToken,
    create_token,
    decode_token,
    verify_password,
)
from crossborder_api.system_schemas import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    UserInfo,
)
from crossborder_persistence import OrganizationModel, SystemUserModel

router = APIRouter(tags=["authentication"])


def _issue_tokens(user: SystemUserModel, request: Request) -> LoginResponse:
    settings = request.app.state.settings
    return LoginResponse(
        token=create_token(
            user_id=user.id,
            organization_id=user.organization_id,
            token_type="access",
            settings=settings,
        ),
        refreshToken=create_token(
            user_id=user.id,
            organization_id=user.organization_id,
            token_type="refresh",
            settings=settings,
        ),
    )


@router.post("/api/auth/login", response_model=ApiResponse[LoginResponse])
async def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[LoginResponse]:
    statement = (
        select(SystemUserModel)
        .join(OrganizationModel, OrganizationModel.id == SystemUserModel.organization_id)
        .options(selectinload(SystemUserModel.roles))
        .where(
            OrganizationModel.slug == payload.organization_slug,
            func.lower(SystemUserModel.username) == payload.username.lower(),
        )
    )
    user = await session.scalar(statement)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    if not user.enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已停用")
    user.last_login_at = datetime.now(UTC)
    await session.flush()
    return ApiResponse(data=_issue_tokens(user, request))


@router.post("/api/auth/refresh", response_model=ApiResponse[LoginResponse])
async def refresh_token(
    payload: RefreshRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[LoginResponse]:
    try:
        claims = decode_token(
            payload.refresh_token,
            expected_type="refresh",
            settings=request.app.state.settings,
        )
    except InvalidAccessToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    user = await session.scalar(
        select(SystemUserModel).where(
            SystemUserModel.id == UUID(claims["sub"]),
            SystemUserModel.organization_id == UUID(claims["org"]),
            SystemUserModel.enabled.is_(True),
        )
    )
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号不存在或已停用")
    return ApiResponse(data=_issue_tokens(user, request))


@router.get("/api/user/info", response_model=ApiResponse[UserInfo])
async def current_user_info(current: CurrentUserDependency) -> ApiResponse[UserInfo]:
    return ApiResponse(
        data=UserInfo(
            buttons=sorted(current.permission_codes),
            roles=sorted(current.role_codes),
            userId=str(current.user.id),
            userName=current.user.username,
            email=current.user.email,
            avatar=current.user.avatar_url or None,
        )
    )
