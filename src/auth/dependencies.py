from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str | None:
    """
    Extract user ID from authorization header.

    Returns None if no credentials provided (public endpoints).
    Override this in production with actual auth validation.
    """
    if credentials is None:
        return None

    return credentials.credentials


async def require_user(
    user_id: str | None = Depends(get_current_user),
) -> str:
    """
    Require authenticated user.

    Raises HTTPException if no user is authenticated.
    """
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id
