from passlib.context import CryptContext # type: ignore
from datetime import datetime, timedelta
from typing import Optional
import secrets
import logging
import jwt

from src.config import Config
from src.db.redis import redis_service

# Initialize password context for hashing
passwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_password_hash(password: str) -> str:
    return passwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return passwd_context.verify(plain_password, hashed_password)

def generate_password(length: int = 12) -> str:
    return secrets.token_urlsafe(length)[:length]

async def create_access_token(user_data: dict, expiry: Optional[timedelta] = None, refresh: bool = False) -> str:
    expires_delta = expiry or timedelta(minutes=15)
    expiration = datetime.utcnow() + expires_delta

    payload = {
        "user": user_data,
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
        logging.exception("Failed to store token in Redis", exc_info=e)

    return token

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            key=Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM]
        )
        return payload
    except jwt.PyJWTError as e:
        logging.exception("Token decoding failed", exc_info=e)
        return None
    
    
def generate_serial_token(length: int = 16) -> str:
    return secrets.token_urlsafe(length)[:length]    

async def create_refresh_token(user_data: dict) -> str:
    expires_delta = timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)
    return await create_access_token(user_data, expiry=expires_delta, refresh=True)
