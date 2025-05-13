from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession # type: ignore
from src.db.main import get_session
from src.db.models import User
from .service import AuthService
from .schemas import UserCreate, UserResponse, AdminCreateUser, LoginModel, TokenResponse, ChangePasswordModel, UpdateProfileModel
from .dependencies import get_current_user
from .utils import create_access_token, create_refresh_token, verify_password
from datetime import timedelta
from src.config import Config
from src.db.redis import redis_service

auth_router = APIRouter()
auth_service = AuthService()

@auth_router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED,responses={
                     400: {"description": "Invalid input"},
                     409: {"description": "User already exists"}
                })

async def signup(user_data: UserCreate,session: AsyncSession = Depends(get_session)):
    """
    Register a new user account
    
    - **username**: Unique username
    - **email**: Valid email address
    - **password**: At least 8 characters
    - **first_name**: User's first name
    - **last_name**: User's last name
    """
    if not user_data.password or len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    try:
        new_user = await auth_service.create_user(user_data, session)
        return new_user
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@auth_router.post("/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED,dependencies=[Depends(get_current_user)])

async def admin_create_user(user_data: AdminCreateUser,background_tasks: BackgroundTasks,session: AsyncSession = Depends(get_session)):
    """
    Admin endpoint to create new users (requires admin privileges)
    
    Generates a random password and emails it to the user
    """
    try:
        new_user = await auth_service.create_user_by_admin(user_data, background_tasks, session)
        return new_user
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@auth_router.post("/login", response_model=TokenResponse,responses={
                     400: {"description": "Missing credentials"},
                     401: {"description": "Invalid credentials"}
                 })
async def login(login_data: LoginModel,session: AsyncSession = Depends(get_session)):
    """
    Authenticate user and return JWT tokens
    
    - **email**: Registered email address
    - **password**: Account password
    
    Returns:
    - access_token: Short-lived token for API access
    - refresh_token: Long-lived token for renewing access
    """
    if not login_data.email or not login_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    
    try:
        user = await auth_service.validate_user_credentials(
            login_data.email, 
            login_data.password, 
            session
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        tokens = await auth_service.generate_tokens(user)
        return tokens
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@auth_router.post("/logout", status_code=status.HTTP_200_OK,dependencies=[Depends(get_current_user)])
async def logout(request: Request):
    """
    Log out the current user (invalidates the access token)
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        await auth_service.logout_user(request.state.user_id, token)
    
    return {"message": "Successfully logged out"}

@auth_router.post("/logout-all", 
                 status_code=status.HTTP_200_OK,
                 dependencies=[Depends(get_current_user)])
async def logout_all(current_user: dict = Depends(get_current_user)):
    """
    Log out from all devices (invalidates all tokens for the user)
    """
    await auth_service.logout_user(str(current_user["user_id"]))
    return {"message": "Successfully logged out from all devices"}

@auth_router.post("/change-password",
                 status_code=status.HTTP_200_OK,
                 dependencies=[Depends(get_current_user)])
async def change_password(user_data: ChangePasswordModel,current_user: dict = Depends(get_current_user),session: AsyncSession = Depends(get_session)):
    """
    Change account password
    
    - **old_password**: Current password
    - **new_password**: New password
    - **confirm_password**: Must match new_password
    
    Note: This will log you out from all devices
    """
    if user_data.new_password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match"
        )
    
    try:
        await auth_service.change_password(
            user_data,
            int(current_user["user_id"]),
            session
        )
        return {"message": "Password changed successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@auth_router.put("/profile",
                response_model=UserResponse,
                dependencies=[Depends(get_current_user)])
async def update_profile(user_data: UpdateProfileModel,current_user: dict = Depends(get_current_user),session: AsyncSession = Depends(get_session)):
    """
    Update user profile information
    
    - **email**: New email address
    - **username**: New username
    - **first_name**: Updated first name
    - **last_name**: Updated last name
    - **contact_number**: Updated phone number
    - **date_of_birth**: Updated birth date
    """
    try:
        updated_user = await auth_service.update_user_profile(
            user_data,
            int(current_user["user_id"]),
            session
        )
        return updated_user
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@auth_router.get("/me", 
                response_model=UserResponse,
                dependencies=[Depends(get_current_user)])
async def get_profile(current_user: dict = Depends(get_current_user),session: AsyncSession = Depends(get_session)):
    """
    Get current user profile information
    """
    try:
        user = await auth_service.get_user_by_id(int(current_user["user_id"]), session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )