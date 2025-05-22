from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import logging
import jwt
from src.config import Config
from src.db.redis import redis_service

# Password hashing context
passwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_password_hash(password: str) -> str:
    """Generate secure password hash"""
    return passwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored hash"""
    return passwd_context.verify(plain_password, hashed_password)

def generate_password(length: int = 12) -> str:
    """Generate random password"""
    return secrets.token_urlsafe(length)[:length]

async def create_access_token(user_data: dict, expiry: Optional[timedelta] = None, refresh: bool = False) -> str:
    """Create JWT access token and store in Redis"""
    expires_delta = expiry or timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    expiration = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": str(user_data.get("user_id")),  # Standard JWT subject claim
        "email": user_data.get("email"),
        "role": user_data.get("role"),
        "exp": expiration,
        "refresh": refresh
    }

    token = jwt.encode(
        payload,
        key=Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM
    )

    try:
        await redis_service.add_token(
            user_id=str(user_data.get("user_id")),
            token=token,
            expires=int(expires_delta.total_seconds())
        )
    except Exception as e:
        logging.error(f"Redis token storage failed: {str(e)}")
        # Don't fail if Redis is down, but log it

    return token

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            key=Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logging.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logging.warning(f"Invalid token: {str(e)}")
        return None

async def create_refresh_token(user_data: dict) -> str:
    """Create refresh token with longer expiration"""
    expires_delta = timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)
    return await create_access_token(user_data, expiry=expires_delta, refresh=True)

def generate_serial_token(length: int = 16) -> str:
    """Generate random serial token"""
    return secrets.token_urlsafe(length)[:length]