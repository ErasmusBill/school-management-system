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

import secrets
import string
from typing import Optional, Set

def generate_student_enrollment_number(
    length: int = 10,
    existing_numbers: Optional[Set[str]] = None,
    max_attempts: int = 10
) -> str:
    """
    Generates a student enrollment number in STU-XXXXX format.
    
    Enhanced version that:
    - Uses only uppercase letters and digits (no confusing characters)
    - Guarantees uniqueness against existing numbers
    - Has configurable length
    - Includes safety limits
    
    Args:
        length: Length of random part (default 8, min 6)
        existing_numbers: Set of existing numbers to avoid
        max_attempts: Maximum generation attempts (default 10)
        
    Returns:
        Enrollment number in format "STU-XXXXXX"
        
    Raises:
        ValueError: If invalid length
        RuntimeError: If can't generate unique number
        
    Example:
        >>> generate_student_enrollment_number()
        'STU-A1B2C3D4'
    """
    # Validation
    if length < 6:
        raise ValueError("Length must be at least 6 characters")
    if existing_numbers is None:
        existing_numbers = set()
    
    # Character set without confusing characters (no 0/O, 1/I/L etc.)
    clean_alphabet = (
        string.ascii_uppercase.replace("O", "").replace("I", "").replace("L", "") + 
        string.digits.replace("0", "").replace("1", "")
    )
    
    for _ in range(max_attempts):
        # Generate random part
        random_part = ''.join(secrets.choice(clean_alphabet) for _ in range(length))
        enrollment_number = f"STU-{random_part}"
        
        # Check uniqueness
        if enrollment_number not in existing_numbers:
            return enrollment_number
    
    raise RuntimeError(
        f"Failed to generate unique enrollment number after {max_attempts} attempts. "
        "Consider increasing length or clearing existing numbers."
    )

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