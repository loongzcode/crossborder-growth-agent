"""Application-level encryption for external platform credentials."""

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class CredentialDecryptionError(RuntimeError):
    """Raised when stored credentials cannot be decrypted with the active key."""


class CredentialVault:
    def __init__(self, signing_secret: str) -> None:
        digest = hashlib.sha256(f"data-source:v1:{signing_secret}".encode()).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, credentials: dict[str, str]) -> str:
        payload = json.dumps(credentials, ensure_ascii=False, sort_keys=True).encode()
        return self._fernet.encrypt(payload).decode()

    def decrypt(self, ciphertext: str | None) -> dict[str, str]:
        if not ciphertext:
            return {}
        try:
            payload: Any = json.loads(self._fernet.decrypt(ciphertext.encode()).decode())
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CredentialDecryptionError("数据源凭证无法解密，请重新授权") from exc
        if not isinstance(payload, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in payload.items()
        ):
            raise CredentialDecryptionError("数据源凭证格式无效，请重新授权")
        return payload
