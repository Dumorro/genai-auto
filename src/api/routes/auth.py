"""Authentication endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import (
    AuthService,
    UserCreate,
    UserLogin,
    TokenResponse,
    get_current_user,
    AuthenticatedUser,
)
from src.storage.database import get_db

router = APIRouter()


@router.post("/auth/register", response_model=TokenResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user."""
    auth_service = AuthService(db)
    return await auth_service.register(user_data)


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Login and get access tokens."""
    auth_service = AuthService(db)
    return await auth_service.login(credentials)


class RefreshRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token."""
    auth_service = AuthService(db)
    return await auth_service.refresh(request.refresh_token)


@router.get("/auth/me")
async def get_me(user: AuthenticatedUser = Depends(get_current_user)):
    """Get current user info."""
    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
    }
