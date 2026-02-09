"""Authentication module - Built-in JWT (lightweight, no external service)."""

from src.api.auth.jwt_auth import (
    get_current_user,
    get_optional_user,
    AuthenticatedUser,
    AuthService,
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
    create_tokens,
    decode_token,
)

__all__ = [
    "get_current_user",
    "get_optional_user",
    "AuthenticatedUser",
    "AuthService",
    "UserCreate",
    "UserLogin",
    "TokenResponse",
    "UserResponse",
    "create_tokens",
    "decode_token",
]
