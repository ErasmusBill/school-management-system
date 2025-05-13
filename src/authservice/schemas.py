from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr

class UserBase(BaseModel):
    """Base schema with common user fields"""
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8, max_length=50, description="User password")
    confirm_password: str = Field(..., min_length=8, max_length=50, description="Confirmation of the password")
    disabled: Optional[bool] = False


class UpdateProfileModel(BaseModel):
    """Schema for updating user profile"""
    username: str
    email: EmailStr
    first_name: str
    last_name: str


class AdminCreateUser(UserBase):
    """Schema for admin creating a user"""
    disabled: Optional[bool] = False


class UserResponse(UserBase):
    """Schema for user data response"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user data"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=50)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    disabled: Optional[bool] = None


class LoginModel(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)


class EmailModel(BaseModel):
    """Schema for email operations"""
    email: List[EmailStr]


class TokenResponse(BaseModel):
    """Schema for authentication token response"""
    message: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class ChangePasswordModel(BaseModel):
    """Schema for password change"""
    old_password: str = Field(..., min_length=8, max_length=50)
    new_password: str = Field(..., min_length=8, max_length=50)
    confirm_password: str = Field(..., min_length=8, max_length=50)