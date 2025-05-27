from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import BackgroundTasks, HTTPException, status
from pydantic import ValidationError

from src.db.models import User, Role, RoleEnum
from .schemas import UserCreate, AdminCreateUser, ChangePasswordModel, UpdateProfileModel
from .utils import (
    generate_password_hash,
    generate_password,
    verify_password,
    create_access_token,
    create_refresh_token
)
from ..mail import send_welcome_email
from src.db.redis import redis_service
from src.config import Config

class AuthService:
    
    async def get_user_by_email(self, email: str, session: AsyncSession) -> Optional[User]:
        """Retrieve user by email with roles loaded"""
        result = await session.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.email == email)
        )
        return result.scalars().first()
    
    async def get_user_by_id(self, user_id: int, session: AsyncSession) -> Optional[User]:
        """Retrieve user by ID with roles loaded"""
        result = await session.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        return result.scalars().first()
    
    async def validate_user_credentials(self, email: str, password: str, session: AsyncSession) -> Optional[User]:
        """Validate user credentials and return user if valid"""
        user = await self.get_user_by_email(email, session)
        if not user or not verify_password(password, user.password_hash):
            return None
        return user
    
    async def create_user(self, user_data: UserCreate, session: AsyncSession) -> User:
        """Create a new user account with specified role"""
        try:
            # Check if user exists
            if await self.get_user_by_email(user_data.email, session):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )

            # Get or create the specified role
            result = await session.execute(
                select(Role).where(Role.name == user_data.role)
            )
            role = result.scalars().first()
            
            if not role:
                # Create the role if it doesn't exist
                role = Role(
                    name=user_data.role,
                    description=f"System {user_data.role.value} role",
                    is_default=(user_data.role == RoleEnum.STUDENT)
                )
                session.add(role)
                await session.flush()

            # Prepare user data
            user_data_dict = user_data.model_dump(
                exclude={'password', 'confirm_password', 'role'},
                exclude_unset=True
            )

            # Handle optional fields
            if 'contact_number' in user_data_dict and user_data_dict['contact_number'] is None:
                del user_data_dict['contact_number']

            # Create the user
            new_user = User(
                **user_data_dict,
                password_hash=generate_password_hash(user_data.password),
                is_active=True
            )
            session.add(new_user)
            await session.flush()  
            
            # Assign the role
            new_user.roles.append(role)
            
            await session.commit()
            await session.refresh(new_user)
            return new_user

        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=e.errors()
            )
    
    async def create_user_by_admin(self, user_data: AdminCreateUser, 
                                 background_tasks: BackgroundTasks, 
                                 session: AsyncSession) -> User:
        """Admin creates a user with specified role and generated password"""
        try:
            if await self.get_user_by_email(user_data.email, session):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )

            # Generate random password and hash
            plain_password = generate_password()
            
            user_data_dict = user_data.model_dump(
                exclude={'disabled', 'role'},  # Exclude role and disabled fields
                exclude_unset=False
            )

            # Get the specified role from database
            result = await session.execute(select(Role).where(Role.name == user_data.role))
            user_role = result.scalars().first()
            
            if not user_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role {user_data.role} not found in database"
                )

            # Create user without roles first
            new_user = User(
                username=user_data_dict['username'],
                email=user_data_dict['email'],
                first_name=user_data_dict['first_name'],
                last_name=user_data_dict['last_name'],
                contact_number=user_data_dict['contact_number'],
                date_of_birth=user_data_dict['date_of_birth'],
                password_hash=generate_password_hash(plain_password),
                is_active=not user_data.disabled
            )

            session.add(new_user)
            await session.flush()  # Flush to get the user ID
            
            # Now assign the role
            new_user.roles.append(user_role)
            
            await session.commit()
            await session.refresh(new_user)
            
            # Send welcome email with plain text password
            # Pass only serializable data to background task
            background_tasks.add_task(
                self._send_welcome_email_task,
                email=new_user.email,
                password=plain_password
            )
            
            return new_user

        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=e.errors()
            )
    
    def _send_welcome_email_task(self, email: str, password: str):
        """Synchronous wrapper for sending welcome email in background task"""
        import asyncio
        try:
            # Create new event loop for background task if needed
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async email function
        loop.run_until_complete(send_welcome_email(email, password))
    
    async def change_password(self, user_data: ChangePasswordModel, 
                            user_id: int, session: AsyncSession) -> User:
        """Change user password and invalidate all existing tokens"""
        user = await self.get_user_by_id(user_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        if not verify_password(user_data.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect current password"
            )
            
        if user_data.new_password != user_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match"
            )
            
        user.password_hash = generate_password_hash(user_data.new_password)
        user.updated_at = datetime.utcnow()
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        await redis_service.revoke_all_tokens(str(user_id))
        return user
    
    async def update_user_profile(self, user_data: UpdateProfileModel, 
                                user_id: int, session: AsyncSession) -> User:
        """Update user profile information"""
        user = await self.get_user_by_id(user_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        update_data = user_data.model_dump(
            exclude_unset=True,
            exclude={'password', 'confirm_password'}  # Prevent accidental password updates
        )
        
        for field, value in update_data.items():
            setattr(user, field, value)
            
        user.updated_at = datetime.utcnow()
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    
    async def generate_tokens(self, user: User) -> Dict[str, Any]:
        """Generate access and refresh tokens"""
        # Get primary role (first role or most important one)
        primary_role = user.roles[0].name.value if user.roles else RoleEnum.STUDENT.value
        
        user_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": primary_role,
            "roles": [role.name.value for role in user.roles]  # Include all roles
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
        """Check token validity"""
        return await redis_service.is_token_valid(user_id, token)
    
    async def get_role_by_name(self, role_name: RoleEnum, session: AsyncSession) -> Optional[Role]:
        """Get role by name"""
        result = await session.execute(select(Role).where(Role.name == role_name))
        return result.scalars().first()
    
    async def assign_role_to_user(self, user_id: int, role_name: RoleEnum, session: AsyncSession) -> User:
        """Assign a role to user"""
        user = await self.get_user_by_id(user_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        role = await self.get_role_by_name(role_name, session)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role {role_name} not found"
            )
            
        if role not in user.roles:
            user.roles.append(role)
            await session.commit()
            await session.refresh(user)
            
        return user
    
    async def remove_role_from_user(self, user_id: int, role_name: RoleEnum, session: AsyncSession) -> User:
        """Remove a role from user"""
        user = await self.get_user_by_id(user_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        role = await self.get_role_by_name(role_name, session)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role {role_name} not found"
            )
            
        if role in user.roles:
            user.roles.remove(role)
            await session.commit()
            await session.refresh(user)
            
        return user