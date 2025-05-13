from sqlalchemy.ext.asyncio import AsyncSession # type: ignore
from sqlalchemy import select # type: ignore
from src.db.models import User
from .schemas import UserCreate, AdminCreateUser, ChangePasswordModel, UpdateProfileModel
from fastapi import BackgroundTasks, HTTPException, status
from datetime import datetime
from .utils import (
    generate_password_hash,
    generate_password,
    verify_password,
    create_access_token,
    create_refresh_token
)
from ..mail import send_welcome_email
from src.db.redis import redis_service
from typing import Optional, Dict, Any
from src.config import Config

class AuthService:
    
    async def get_user_by_email(self, email: str, session: AsyncSession) -> Optional[User]:
        """Retrieve user by email"""
        result = await session.execute(select(User).where(User.email == email))
        return result.scalars().first()
    
    async def get_user_by_id(self, user_id: int, session: AsyncSession) -> Optional[User]:
        """Retrieve user by ID"""
        return await session.get(User, user_id)
    
    async def validate_user_credentials(self, email: str, password: str, session: AsyncSession) -> Optional[User]:
        """Validate user credentials and return user if valid"""
        user = await self.get_user_by_email(email, session)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
    
    async def create_user(self, user_data: UserCreate, session: AsyncSession) -> User:
        """Create a new user account"""
        # Validate required fields
        if not all([user_data.username, user_data.email, user_data.first_name, user_data.last_name]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All fields are required"
            )
            
        # Check if user already exists
        if await self.get_user_by_email(user_data.email, session):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
            
        # Validate password
        if not user_data.password or len(user_data.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
            
        # Create user object
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            password_hash=generate_password_hash(user_data.password),
            is_active=not user_data.disabled if user_data.disabled is not None else True,
            date_of_birth=user_data.date_of_birth,
            contact_number=user_data.contact_number,
            role=user_data.role if hasattr(user_data, 'role') else 'user'
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user
    
    async def create_user_by_admin(self, user_data: AdminCreateUser, background_tasks: BackgroundTasks, session: AsyncSession) -> User:
        """Admin creates a user with auto-generated password"""
        if await self.get_user_by_email(user_data.email, session):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
            
        # Generate random password
        plain_password = generate_password()
        
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            password_hash=generate_password_hash(plain_password),
            is_active=not user_data.disabled if user_data.disabled is not None else True,
            date_of_birth=user_data.date_of_birth,
            contact_number=user_data.contact_number,
            role=user_data.role
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        # Send welcome email with generated password
        background_tasks.add_task(
            send_welcome_email,
            email=new_user.email,
            password=plain_password
        )
        
        return new_user
    
    async def change_password(self, user_data: ChangePasswordModel, user_id: int, session: AsyncSession) -> User:
        """Change user password and invalidate all existing tokens"""
        user = await self.get_user_by_id(user_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Validate current password
        if not verify_password(user_data.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect current password"
            )
            
        # Validate new password
        if user_data.new_password != user_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match"
            )
            
        # Update password
        user.password_hash = generate_password_hash(user_data.new_password)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Invalidate all existing tokens
        await redis_service.revoke_all_tokens(str(user_id))
        
        return user
    
    async def update_user_profile(self, user_data: UpdateProfileModel, user_id: int, session: AsyncSession) -> User:
        """Update user profile information"""
        user = await self.get_user_by_id(user_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Update fields from the request data
        for field, value in user_data.dict(exclude_unset=True).items():
            setattr(user, field, value)
            
        user.updated_at = datetime.utcnow()
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    
    async def generate_tokens(self, user: User) -> Dict[str, Any]:
        """Generate access and refresh tokens for a user"""
        user_data = {
            "email": user.email,
            "user_id": str(user.id),
            "role": user.role.value if hasattr(user.role, 'value') else user.role
        }
        
        return {
            "access_token": create_access_token(user_data),
            "refresh_token": create_refresh_token(user_data),
            "token_type": "bearer",
            "expires_in": Config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    async def logout_user(self, user_id: str, token: str) -> None:
        """Invalidate a specific user token"""
        await redis_service.revoke_token(user_id, token)
    
    async def is_token_valid(self, user_id: str, token: str) -> bool:
        """Check if a token is still valid"""
        return await redis_service.is_token_valid(user_id, token)