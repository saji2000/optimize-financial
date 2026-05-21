from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings


PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 310_000


class AuthenticatedUser(BaseModel):
    username: str
    name: str
    role: str


CURTIS_USER = AuthenticatedUser(username="curtis", name="Curtis", role="Admin")
CURTIS_PASSWORD_SALT = "OQQl4TeQwk2jtflhufeVBQ"
CURTIS_PASSWORD_HASH = "hqMRBvSID-bSLewmpIAXg-SqwN4ZAulUDSvK_4PbG7Q"


def authenticate_user(username: str, password: str) -> AuthenticatedUser | None:
    if username.strip().casefold() != CURTIS_USER.username:
        return None
    if not _verify_password(password, CURTIS_PASSWORD_SALT, CURTIS_PASSWORD_HASH):
        return None
    return CURTIS_USER


def create_access_token(user: AuthenticatedUser) -> str:
    now = int(time.time())
    payload = {
        "sub": user.username,
        "name": user.name,
        "role": user.role,
        "iat": now,
        "exp": now + settings.auth_token_ttl_seconds,
        "nonce": secrets.token_urlsafe(12),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_part = _base64url_encode(payload_bytes)
    signature = _sign(payload_part.encode("ascii"))
    return f"{payload_part}.{signature}"


def require_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized()
    token = authorization.removeprefix("Bearer ").strip()
    return verify_access_token(token)


def verify_access_token(token: str) -> AuthenticatedUser:
    try:
        payload_part, signature = token.split(".", 1)
    except ValueError as exc:
        raise _unauthorized() from exc

    expected_signature = _sign(payload_part.encode("ascii"))
    if not hmac.compare_digest(signature, expected_signature):
        raise _unauthorized()

    try:
        payload = json.loads(_base64url_decode(payload_part))
    except (ValueError, json.JSONDecodeError, binascii.Error) as exc:
        raise _unauthorized() from exc

    if not _is_valid_payload(payload):
        raise _unauthorized()
    if int(payload["exp"]) < int(time.time()):
        raise _unauthorized()
    if payload["sub"] != CURTIS_USER.username:
        raise _unauthorized()

    return AuthenticatedUser(username=payload["sub"], name=payload["name"], role=payload["role"])


def _verify_password(password: str, salt_b64: str, expected_hash_b64: str) -> bool:
    salt = _base64url_decode(salt_b64)
    expected = _base64url_decode(expected_hash_b64)
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return hmac.compare_digest(actual, expected)


def _sign(payload: bytes) -> str:
    digest = hmac.new(settings.auth_token_secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return _base64url_encode(digest)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _is_valid_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("sub"), str)
        and isinstance(payload.get("name"), str)
        and isinstance(payload.get("role"), str)
        and isinstance(payload.get("exp"), int)
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
