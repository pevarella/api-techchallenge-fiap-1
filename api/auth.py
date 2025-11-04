"""Authentication helpers using JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import Settings, get_settings

TokenPayload = Dict[str, Any]
_security_scheme = HTTPBearer(auto_error=False)


class TokenType:
    """String constants describing JWT token types."""

    ACCESS = "access"
    REFRESH = "refresh"


def authenticate_user(username: str, password: str, settings: Settings) -> bool:
    """Return True when provided credentials match configured values."""

    return username == settings.auth_username and password == settings.auth_password


def create_token_pair(username: str, settings: Settings) -> Tuple[str, str]:
    """Create a fresh pair of access and refresh tokens for the given user."""

    access_token = _create_token(
        subject=username,
        token_type=TokenType.ACCESS,
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.jwt_access_token_exp_minutes,
    )
    refresh_token = _create_token(
        subject=username,
        token_type=TokenType.REFRESH,
        secret=settings.jwt_refresh_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.jwt_refresh_token_exp_minutes,
    )
    return access_token, refresh_token


def verify_refresh_token(token: str, settings: Settings) -> TokenPayload:
    """Decode and validate a refresh token, raising HTTP 401 on failure."""

    payload = _decode_token(token, settings.jwt_refresh_secret_key, settings.jwt_algorithm)
    if payload.get("type") != TokenType.REFRESH:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return payload


def require_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security_scheme),
    settings: Settings = Depends(get_settings),
) -> TokenPayload:
    """Dependency that validates the Authorization header and returns token claims."""

    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = _decode_token(credentials.credentials, settings.jwt_secret_key, settings.jwt_algorithm)
    if payload.get("type") != TokenType.ACCESS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    return payload


def _create_token(
    *,
    subject: str,
    token_type: str,
    secret: str,
    algorithm: str,
    expires_minutes: int,
) -> str:
    issued_at = datetime.utcnow()
    expire_at = issued_at + timedelta(minutes=expires_minutes)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": issued_at,
        "exp": expire_at,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def _decode_token(token: str, secret: str, algorithm: str) -> TokenPayload:
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError as exc:  # Includes expired signatures and malformed tokens
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc