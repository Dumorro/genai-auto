"""Built-in JWT authentication - lightweight, no external service needed."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.storage.models import User

logger = structlog.get_logger()
settings = get_settings()

# Password hashing (using Argon2 - more secure and no length limit)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Bearer token security
security = HTTPBearer(auto_error=False)


# ============== Models ==============

class UserCreate(BaseModel):
    """User registration model."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2)


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # user_id
    email: str
    name: str
    type: str  # access or refresh
    exp: datetime
    iat: datetime


class AuthenticatedUser(BaseModel):
    """Authenticated user info."""
    user_id: str
    email: str
    name: str


# ============== Password Utils ==============

def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against Argon2 hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ============== Token Utils ==============

def create_token(user_id: str, email: str, name: str, token_type: str = "access") -> str:
    """Create a JWT token."""
    now = datetime.utcnow()
    
    if token_type == "access":
        expires = now + timedelta(minutes=settings.jwt_access_expire_minutes)
    else:  # refresh
        expires = now + timedelta(days=settings.jwt_refresh_expire_days)
    
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "type": token_type,
        "exp": expires,
        "iat": now,
    }
    
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(**payload)
    except JWTError as e:
        logger.warning("Invalid JWT token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_tokens(user_id: str, email: str, name: str) -> TokenResponse:
    """Create access and refresh tokens."""
    access_token = create_token(user_id, email, name, "access")
    refresh_token = create_token(user_id, email, name, "refresh")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


# ============== Auth Service ==============

class AuthService:
    """Authentication service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, user_data: UserCreate) -> TokenResponse:
        """Register a new user."""
        # Check if email exists
        result = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create user
        user = User(
            id=uuid4(),
            email=user_data.email,
            name=user_data.name,
            password_hash=hash_password(user_data.password),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info("User registered", user_id=str(user.id), email=user.email)

        return create_tokens(str(user.id), user.email, user.name)

    async def login(self, credentials: UserLogin) -> TokenResponse:
        """Authenticate user and return tokens."""
        result = await self.db.execute(
            select(User).where(User.email == credentials.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        logger.info("User logged in", user_id=str(user.id))

        return create_tokens(str(user.id), user.email, user.name)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Refresh access token."""
        payload = decode_token(refresh_token)
        
        if payload.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Verify user still exists
        result = await self.db.execute(
            select(User).where(User.id == payload.sub)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        return create_tokens(str(user.id), user.email, user.name)


# ============== Dependencies ==============

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthenticatedUser:
    """Get current authenticated user (required)."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    
    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    return AuthenticatedUser(
        user_id=payload.sub,
        email=payload.email,
        name=payload.name,
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthenticatedUser]:
    """Get current user if authenticated (optional)."""
    if not credentials:
        return None

    try:
        payload = decode_token(credentials.credentials)
        if payload.type != "access":
            return None
        return AuthenticatedUser(
            user_id=payload.sub,
            email=payload.email,
            name=payload.name,
        )
    except HTTPException:
        return None
