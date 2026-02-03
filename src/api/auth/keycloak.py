"""Keycloak authentication for FastAPI."""

from typing import Optional
import structlog
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

from src.api.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

security = HTTPBearer(auto_error=False)


class KeycloakUser(BaseModel):
    """Authenticated user from Keycloak."""

    sub: str  # User ID
    email: Optional[str] = None
    name: Optional[str] = None
    preferred_username: Optional[str] = None
    roles: list[str] = []
    
    @property
    def user_id(self) -> str:
        return self.sub


class KeycloakConfig:
    """Keycloak configuration and utilities."""

    def __init__(self):
        self.url = settings.keycloak_url
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self._public_key: Optional[str] = None

    @property
    def issuer(self) -> str:
        return f"{self.url}/realms/{self.realm}"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/certs"

    @property
    def token_url(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/token"

    async def get_public_key(self) -> str:
        """Fetch public key from Keycloak."""
        if self._public_key:
            return self._public_key

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                jwks = response.json()
                
                # Get the first RSA key
                for key in jwks.get("keys", []):
                    if key.get("use") == "sig" and key.get("kty") == "RSA":
                        # Convert JWK to PEM format
                        from jose import jwk
                        key_obj = jwk.construct(key)
                        self._public_key = key_obj.to_pem().decode("utf-8")
                        return self._public_key

                raise ValueError("No suitable signing key found in JWKS")

        except Exception as e:
            logger.error("Failed to fetch Keycloak public key", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable",
            )


keycloak_config = KeycloakConfig()


async def verify_token(token: str) -> KeycloakUser:
    """Verify JWT token from Keycloak."""
    try:
        public_key = await keycloak_config.get_public_key()
        
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.keycloak_client_id,
            issuer=keycloak_config.issuer,
        )

        # Extract roles from realm_access and resource_access
        roles = []
        if "realm_access" in payload:
            roles.extend(payload["realm_access"].get("roles", []))
        if "resource_access" in payload:
            client_roles = payload.get("resource_access", {}).get(
                settings.keycloak_client_id, {}
            )
            roles.extend(client_roles.get("roles", []))

        return KeycloakUser(
            sub=payload["sub"],
            email=payload.get("email"),
            name=payload.get("name"),
            preferred_username=payload.get("preferred_username"),
            roles=roles,
        )

    except JWTError as e:
        logger.warning("Invalid JWT token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> KeycloakUser:
    """Get current authenticated user (required)."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await verify_token(credentials.credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[KeycloakUser]:
    """Get current user if authenticated (optional)."""
    if not credentials:
        return None

    try:
        return await verify_token(credentials.credentials)
    except HTTPException:
        return None


def require_role(required_role: str):
    """Dependency to require a specific role."""

    async def role_checker(user: KeycloakUser = Depends(get_current_user)) -> KeycloakUser:
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return user

    return role_checker
