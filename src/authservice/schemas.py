from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator
from src.db.models import Role
from enum import Enum


class Role(str, Enum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    ADMIN = "ADMIN"
    PARENT = "PARENT"
class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    contact_number: Optional[str] = Field(  # Made optional
        None,
        pattern=r'^\+?[1-9]\d{1,14}$',
        description="Optional phone number in E.164 format"
    )
    date_of_birth: Optional[datetime] = None

class UserCreate(UserBase):
    """User registration schema"""
    password: str = Field(..., min_length=8, max_length=50)
    confirm_password: str = Field(..., min_length=8, max_length=50)

    @field_validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values.data and v != values.data['password']:
            raise ValueError("Passwords do not match")
        return v
class AdminCreateUser(UserBase):
    """Admin user creation schema"""
    role: Role
    disabled: bool = False

class UserResponse(UserBase):
    """User response schema"""
    id: int
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UpdateProfileModel(UserBase):
    """Profile update schema"""
    pass

class LoginModel(BaseModel):
    """Login credentials schema"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)

class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

class ChangePasswordModel(BaseModel):
    """Password change schema"""
    old_password: str = Field(..., min_length=8, max_length=50)
    new_password: str = Field(..., min_length=8, max_length=50)
    confirm_password: str = Field(..., min_length=8, max_length=50)

    @field_validator('confirm_password')
    def new_passwords_match(cls, v, values):
        if 'new_password' in values.data and v != values.data['new_password']:
            raise ValueError("New passwords do not match")
        return v