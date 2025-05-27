from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt # type: ignore
from src.config import Config
from src.db.redis import redis_service
from typing import Optional
from functools import wraps

async def get_token_from_header(request: Request) -> Optional[str]:
    """Extract JWT token from Authorization header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ")[1]

async def verify_and_decode_token(token: str) -> Optional[dict]:
    """Verify JWT token and check Redis for validity"""
    try:
        payload = jwt.decode(
            token,
            key=Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM],
        )
        
        # Verify token exists in Redis
        user_id = str(payload["user"]["user_id"])
        if not await redis_service.is_token_valid(user_id, token):
            return None
            
        return payload
    except JWTError:
        return None

async def get_current_user(request: Request) -> dict:
    """Dependency to get current user from valid JWT token"""
    token = await get_token_from_header(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )
    
    payload = await verify_and_decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return payload["user"]

def role_required(required_role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user') or args[0].user
            if current_user.get("role") != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role {required_role} is required"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator   

def permission_required(required_permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user") or args[0].user
            if required_permission not in current_user.get("permissions", []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission {required_permission} is required"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator 
