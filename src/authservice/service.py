from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import BackgroundTasks, HTTPException, status
from pydantic import ValidationError
import logging

from src.db.models import User, Role, RoleEnum
from .schemas import UserCreate, AdminCreateUser, ChangePasswordModel, UpdateProfileModel
from .utils import (
    generate_password_hash,
    generate_password,
    verify_password,
    create_access_token,
    create_refresh_token
)
from src.mail import send_welcome_email
from src.db.redis import redis_service
from src.config import Config

logger = logging.getLogger(__name__)

class AuthService:
    
    async def get_user_by_email(self, email: str, session: AsyncSession) -> Optional[User]:
        """Retrieve user by email with roles loaded"""
        try:
            result = await session.execute(
                select(User)
                .options(selectinload(User.roles))
                .where(User.email == email)
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            raise
    
    async def get_user_by_id(self, user_id: int, session: AsyncSession) -> Optional[User]:
        """Retrieve user by ID with roles loaded"""
        try:
            result = await session.execute(
                select(User)
                .options(selectinload(User.roles))
                .where(User.id == user_id)
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            raise
    
    async def validate_user_credentials(self, email: str, password: str, session: AsyncSession) -> Optional[User]:
        """Validate user credentials and return user if valid"""
        user = await self.get_user_by_email(email, session)
        if not user or not verify_password(password, user.password_hash):
            return None
        return user
    
    async def create_user(self, user_data: UserCreate, session: AsyncSession) -> User:
        """Create a new user account with specified role"""
        try:
            logger.info(f"Starting user creation for email: {user_data.email}")
            
            # Check if user already exists
            existing_user = await self.get_user_by_email(user_data.email, session)
            if existing_user:
                logger.warning(f"User with email {user_data.email} already exists")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )

            # Check if username already exists
            existing_username = await session.execute(
                select(User).where(User.username == user_data.username)
            )
            if existing_username.scalars().first():
                logger.warning(f"Username {user_data.username} already exists")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )

            logger.info(f"Looking for role: {user_data.role}")
            
            # Try to get the role from the database
            result = await session.execute(
                select(Role).where(Role.name == user_data.role)
            )
            role = result.scalars().first()

            # If role does not exist, create it
            if not role:
                logger.info(f"Role {user_data.role} not found, creating new role")
                role = Role(
                    name=user_data.role,
                    description=f"System {user_data.role.value} role",
                    is_default=(user_data.role == RoleEnum.STUDENT)
                )
                session.add(role)
                await session.flush()
                logger.info(f"Created new role: {role.name}")

            # Prepare user data
            user_data_dict = user_data.model_dump(
                exclude={'password', 'confirm_password', 'role'},
                exclude_unset=True
            )

            # Handle None contact_number
            if 'contact_number' in user_data_dict and user_data_dict['contact_number'] is None:
                del user_data_dict['contact_number']

            logger.info(f"Creating user with data: {list(user_data_dict.keys())}")

            # Create new user
            new_user = User(
                **user_data_dict,
                password_hash=generate_password_hash(user_data.password),
                is_active=True,
                roles=[role]
            )

            # Add user to session first
            session.add(new_user)
            await session.flush()  # This assigns an ID to the user
            
            logger.info(f"User created with ID: {new_user.id}")

            # Now assign the role
            # new_user.roles.append(role)
            
            # Commit the transaction
            await session.commit()
            
            # Refresh to get the complete user with relationships
            await session.refresh(new_user, ['roles'])
            
            logger.info(f"User creation successful for email: {user_data.email}, ID: {new_user.id}")
            return new_user

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            await session.rollback()
            raise
        except ValidationError as e:
            logger.error(f"Validation error during user creation: {e.errors()}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=e.errors()
            )
        except Exception as e:
            logger.exception(f"Unexpected error during user creation for {user_data.email}: {str(e)}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"User creation failed: {str(e)}"
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

            plain_password = generate_password()
            
            user_data_dict = user_data.model_dump(
                exclude={'disabled', 'role'},  
                exclude_unset=False
            )

            result = await session.execute(select(Role).where(Role.name == user_data.role))
            user_role = result.scalars().first()
            
            if not user_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role {user_data.role} not found in database"
                )
                
            new_user = User(
                username=user_data_dict['username'],
                email=user_data_dict['email'],
                first_name=user_data_dict['first_name'],
                last_name=user_data_dict['last_name'],
                contact_number=user_data_dict.get('contact_number'),
                date_of_birth=user_data_dict.get('date_of_birth'),
                password_hash=generate_password_hash(plain_password),
                is_active=not user_data.disabled
            )

            session.add(new_user)
            await session.flush()  
            
            new_user.roles.append(user_role)
            
            await session.commit()
            await session.refresh(new_user, ['roles'])
            
            background_tasks.add_task(
                self._send_welcome_email_task,
                email=new_user.email,
                password=plain_password
            )
            
            return new_user

        except HTTPException:
            await session.rollback()
            raise
        except ValidationError as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=e.errors()
            )
        except Exception as e:
            logger.exception(f"Admin user creation failed: {str(e)}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"User creation failed: {str(e)}"
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
    
    async def change_password(self, user_data: ChangePasswordModel, user_id: int, session: AsyncSession) -> User:
        """Change user password and invalidate all existing tokens"""
        try:
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
        except HTTPException:
            await session.rollback()
            raise
        except Exception as e:
            logger.exception(f"Password change failed: {str(e)}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password change failed"
            )
    
    async def update_user_profile(self, user_data: UpdateProfileModel, user_id: int, session: AsyncSession) -> User:
        """Update user profile information"""
        try:
            user = await self.get_user_by_id(user_id, session)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
                
            update_data = user_data.model_dump(
                exclude_unset=True,
                exclude={'password', 'confirm_password'}  
            )
            
            for field, value in update_data.items():
                setattr(user, field, value)
                
            user.updated_at = datetime.utcnow()
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
        except HTTPException:
            await session.rollback()
            raise
        except Exception as e:
            logger.exception(f"Profile update failed: {str(e)}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Profile update failed"
            )
    
    async def generate_tokens(self, user: User) -> Dict[str, Any]:
        """Generate access and refresh tokens"""
        # Get primary role (first role or most important one)
        primary_role = user.roles[0].name.value if user.roles else RoleEnum.STUDENT.value
        
        user_data = {
            "sub": str(user.id),
            "user_id": user.id,  # Add explicit user_id
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
    
    async def logout_user(self, user_id: str, token: str = None) -> None:
        """Invalidate user tokens - if no token provided, revoke all tokens"""
        try:
            if token:
                await redis_service.revoke_token(user_id, token)
            else:
                await redis_service.revoke_all_tokens(user_id)
        except Exception as e:
            logger.error(f"Logout failed for user {user_id}: {str(e)}")
            # Don't raise exception for logout failures
    
    async def is_token_valid(self, user_id: str, token: str) -> bool:
        """Check token validity"""
        try:
            return await redis_service.is_token_valid(user_id, token)
        except Exception as e:
            logger.error(f"Token validation failed: {str(e)}")
            return False
    
    async def get_role_by_name(self, role_name: RoleEnum, session: AsyncSession) -> Optional[Role]:
        """Get role by name"""
        result = await session.execute(select(Role).where(Role.name == role_name))
        return result.scalars().first()
    
    async def assign_role_to_user(self, user_id: int, role_name: RoleEnum, session: AsyncSession) -> User:
        """Assign a role to user"""
        try:
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
                await session.refresh(user, ['roles'])
                
            return user
        except HTTPException:
            await session.rollback()
            raise
        except Exception as e:
            logger.exception(f"Role assignment failed: {str(e)}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role assignment failed"
            )
    
    async def remove_role_from_user(self, user_id: int, role_name: RoleEnum, session: AsyncSession) -> User:
        """Remove a role from user"""
        try:
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
                await session.refresh(user, ['roles'])
                
            return user
        except HTTPException:
            await session.rollback()
            raise
        except Exception as e:
            logger.exception(f"Role removal failed: {str(e)}")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role removal failed"
            )