from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from dataclasses import dataclass
import os

SECRET_KEY = os.getenv("JWT_SECRET", "changeme")
ALGORITHM = "HS256"
ISSUER = "library-auth"
AUDIENCE = "library-services"

bearer_scheme = HTTPBearer(auto_error=True)
bearer_scheme_optional = HTTPBearer(auto_error=False)

@dataclass
class UserPrincipal:
    user_id: int
    email: str
    role: str

def _decode(token: str) -> UserPrincipal:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
            issuer=ISSUER,
        )
        return UserPrincipal(
            user_id=int(payload["sub"]),
            email=payload["email"],
            role=payload["role"],
        )
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UserPrincipal:
    """Требует валидный JWT. Без токена → 401."""
    return _decode(credentials.credentials)

def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme_optional),
) -> UserPrincipal | None:
    """Токен опционален. Если есть — валидирует, нет — возвращает None."""
    if credentials is None:
        return None
    return _decode(credentials.credentials)

def require_admin(principal: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
    """Требует роль admin. Иначе → 403."""
    if principal.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return principal

def require_user(principal: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
    """Требует любую валидную роль (user или admin)."""
    return principal
