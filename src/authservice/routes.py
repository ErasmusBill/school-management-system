from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging

from src.db.main import get_session
from src.db.models import User
from .service import AuthService
from .schemas import (
    UserCreate, 
    UserResponse, 
    AdminCreateUser, 
    LoginModel, 
    TokenResponse, 
    ChangePasswordModel, 
    UpdateProfileModel
)
from .dependencies import get_current_user
from src.config import Config
from .service import create_access_token, create_refresh_token


auth_router = APIRouter()
auth_service = AuthService()

@auth_router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED,summary="Register new user",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input or user already exists"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def signup(user_data: UserCreate,session: AsyncSession = Depends(get_session)) -> UserResponse:
    """
    Register a new user account
    
    **Required fields:**
    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Strong password (minimum 8 characters)
    - **confirm_password**: Must match password
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **role**: User role (STUDENT, TEACHER, ADMIN)
    
    **Optional fields:**
    - **contact_number**: Phone numbe'r
    - **date_of_birth**: Birth date
    """
    try:
        if  not user_data.password or len(user_data.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        if user_data.password != user_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password and confirmation do not match"
            )

        new_user = await auth_service.create_user(user_data, session)
        
        return UserResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            contact_number=new_user.contact_number,
            date_of_birth=new_user.date_of_birth,
            is_active=new_user.is_active,
            roles=[role.name.value for role in new_user.roles],
            created_at=new_user.created_at,
            updated_at=new_user.updated_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"User registration failed for email: {user_data.email if hasattr(user_data, 'email') else 'unknown'}")
        # More specific error logging
        logging.error(f"Registration error details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )

@auth_router.post("/admin/users", response_model=UserResponse,status_code=status.HTTP_201_CREATED,summary="Admin creates user",dependencies=[Depends(get_current_user)],
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input or user already exists"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def admin_create_user(user_data: AdminCreateUser,background_tasks:BackgroundTasks,current_user: Dict[str, Any] = Depends(get_current_user),session: AsyncSession = Depends(get_session)
) -> UserResponse:
    """
    Create user account with admin privileges
    
    **Admin only endpoint** - Creates user and sends welcome email with generated password
    
    **Required fields:**
    - **username**: Unique username
    - **email**: Valid email address  
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **role**: User role to assign
    
    **Optional fields:**
    - **contact_number**: Phone number
    - **date_of_birth**: Birth date
    - **disabled**: Whether account is disabled (default: false)
    """
    try:
        # Verify admin role
        if "ADMIN" not in current_user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        # Validate role is provided
        if not user_data.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role is required"
            )
            
        new_user = await auth_service.create_user_by_admin(
            user_data, 
            background_tasks, 
            session
        )
        return new_user
        
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"Admin user creation failed for email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User creation failed. Please try again."
        )


@auth_router.post("/login", response_model=TokenResponse,summary="User login",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def login(login_data: LoginModel, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens
    
    **Required fields:**
    - **email**: User's email address
    - **password**: User's password
    
    **Returns:**
    - **access_token**: JWT access token for API authentication
    - **refresh_token**: JWT refresh token for token renewal
    - **token_type**: Always "bearer"
    - **expires_in**: Token expiration time in seconds
    """
    try:
        # Validate credentials
        user = await auth_service.validate_user_credentials(
            login_data.email, 
            login_data.password, 
            session
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled. Contact administrator."
        )

        access_token = await create_access_token(user)
        refresh_token = await create_refresh_token(user)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=3600
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"Login failed for email: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed. Please try again."
        )


@auth_router.post("/logout", status_code=status.HTTP_200_OK,summary="User logout",dependencies=[Depends(get_current_user)],
    responses={
        200: {"description": "Logout successful"},
        401: {"description": "Not authenticated"}
    }
)
async def logout(request: Request,current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, str]:
    """
    Log out current user (invalidates the current access token)
    
    **Requires:** Bearer token in Authorization header
    """
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            await auth_service.logout_user(str(current_user["user_id"]), token)
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logging.exception(f"Logout failed for user: {current_user.get('user_id')}")
        # Don't raise error for logout - just return success
        return {"message": "Logged out"}


@auth_router.post("/logout-all", status_code=status.HTTP_200_OK,summary="Logout from all devices",dependencies=[Depends(get_current_user)],
    responses={
        200: {"description": "Logout successful"},
        401: {"description": "Not authenticated"}
    }
)
async def logout_all(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, str]:
    """
    Log out from all devices (invalidates all tokens for the user)
    
    **Requires:** Bearer token in Authorization header
    """
    try:
        await auth_service.logout_user(str(current_user["user_id"]))
        return {"message": "Successfully logged out from all devices"}
        
    except Exception as e:
        logging.exception(f"Logout all failed for user: {current_user.get('user_id')}")
        # Don't raise error for logout - just return success
        return {"message": "Logged out from all devices"}


@auth_router.post("/change-password",status_code=status.HTTP_200_OK,summary="Change password",dependencies=[Depends(get_current_user)],
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Invalid input"},
        401: {"description": "Not authenticated or incorrect current password"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def change_password(password_data: ChangePasswordModel,current_user: Dict[str, Any] = Depends(get_current_user),session: AsyncSession = Depends(get_session)) -> Dict[str, str]:
    """
    Change account password
    
    **Required fields:**
    - **old_password**: Current password
    - **new_password**: New password (minimum 8 characters)
    - **confirm_password**: Must match new_password
    
    **Note:** This will invalidate all existing tokens and log you out from all devices
    """
    try:
        # Validate password confirmation
        if password_data.new_password != password_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match"
            )
        
        # Validate new password strength
        if len(password_data.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long"
            )
        
        await auth_service.change_password(
            password_data,
            int(current_user["user_id"]),
            session
        )
        
        return {"message": "Password changed successfully. Please log in again."}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"Password change failed for user: {current_user.get('user_id')}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed. Please try again."
        )


@auth_router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update profile",
    dependencies=[Depends(get_current_user)],
    responses={
        200: {"description": "Profile updated successfully"},
        400: {"description": "Invalid input"},
        401: {"description": "Not authenticated"},
        404: {"description": "User not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def update_profile(profile_data: UpdateProfileModel,current_user: Dict[str, Any] = Depends(get_current_user),session: AsyncSession = Depends(get_session)) -> UserResponse:
    """
    Update user profile information
    
    **Optional fields (only provided fields will be updated):**
    - **email**: New email address
    - **username**: New username
    - **first_name**: Updated first name
    - **last_name**: Updated last name
    - **contact_number**: Updated phone number
    - **date_of_birth**: Updated birth date
    """
    try:
        updated_user = await auth_service.update_user_profile(
            profile_data,
            int(current_user["user_id"]),
            session
        )
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"Profile update failed for user: {current_user.get('user_id')}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed. Please try again."
        )


@auth_router.get("/me", response_model=UserResponse,summary="Get current user profile",dependencies=[Depends(get_current_user)],
    responses={
        200: {"description": "Profile retrieved successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user),session: AsyncSession = Depends(get_session)
) -> UserResponse:
    """
    Get current authenticated user's profile information
    
    **Requires:** Bearer token in Authorization header
    
    **Returns:** Complete user profile with roles
    """
    try:
        user = await auth_service.get_user_by_id(
            int(current_user["user_id"]), 
            session
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
            
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"Get profile failed for user: {current_user.get('user_id')}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile. Please try again."
        )


@auth_router.post("/refresh",response_model=TokenResponse,summary="Refresh access token",
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid refresh token"},
        500: {"description": "Internal server error"}
    }
)
async def refresh_token(request: Request,session: AsyncSession = Depends(get_session)) -> TokenResponse:
    """
    Refresh access token using refresh token
    
    **Requires:** Valid refresh token in request body or Authorization header
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh endpoint not yet implemented"
    )


@auth_router.get("/health",summary="Auth service health check",
    responses={
        200: {"description": "Service is healthy"}
    }
)
async def health_check() -> Dict[str, str]:
    """Check if authentication service is running"""
    return {
        "status": "healthy",
        "service": "authentication",
        "version": "1.0.0"
    }