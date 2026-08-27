"""Password hashing and signed access-token primitives."""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from crossborder_api.config import Settings

password_hasher = PasswordHash.recommended()


class InvalidAccessToken(ValueError):
    pass


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_token(
    *,
    user_id: UUID,
    organization_id: UUID,
    token_type: Literal["access", "refresh"],
    settings: Settings,
) -> str:
    now = datetime.now(UTC)
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_days)
    )
    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "type": token_type,
        "iat": now,
        "exp": now + lifetime,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.signing_secret, algorithm="HS256")


def decode_token(
    token: str,
    *,
    expected_type: Literal["access", "refresh"],
    settings: Settings,
) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.signing_secret, algorithms=["HS256"])
        if payload.get("type") != expected_type:
            raise InvalidAccessToken("令牌类型不正确")
        UUID(str(payload["sub"]))
        UUID(str(payload["org"]))
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessToken("登录状态无效或已过期") from exc
    return payload
