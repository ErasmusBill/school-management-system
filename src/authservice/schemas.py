from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ConfigDict

# Role Enum Definition
class GenderEnum(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

class RoleEnum(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD"
    TEACHER = "TEACHER"
    TEACHER_AIDE = "TEACHER_AIDE"
    STUDENT = "STUDENT"
    PARENT = "PARENT"
    STAFF = "STAFF"
    LIBRARIAN = "LIBRARIAN"
    COUNSELOR = "COUNSELOR"
    ACCOUNTANT = "ACCOUNTANT"
    IT_ADMIN = "IT_ADMIN"

# Base User Schema
class UserBase(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        examples=["john_doe"],
        description="Unique username containing letters, numbers and underscores"
    )
    email: EmailStr = Field(
        ...,
        examples=["user@example.com"],
        description="Valid email address"
    )
    first_name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        examples=["John"],
        description="User's first name"
    )
    last_name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        examples=["Doe"],
        description="User's last name"
    )
    contact_number: Optional[str] = Field(
        None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        examples=["+1234567890"],
        description="Phone number in E.164 format (optional)"
    )
    date_of_birth: Optional[datetime] = Field(
        None,
        examples=["1990-01-01T00:00:00Z"],
        description="User's date of birth (optional)"
    )

    @field_validator("date_of_birth")
    def validate_date_of_birth(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value and value.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            raise ValueError("Date of birth cannot be in the future")
        return value

# User Creation Schema
class UserCreate(UserBase):
    password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        examples=["SecurePassword123!"],
        description="Password with at least 8 characters"
    )
    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        examples=["SecurePassword123!"],
        description="Must match password field"
    )
    role: RoleEnum = Field(
        default=RoleEnum.STUDENT,
        examples=["STUDENT"],
        description="User's role in the system"
    )
    
    gender:GenderEnum = Field(...,examples=["MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"])

    @field_validator("password")
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in value):
            raise ValueError("Password must contain at least one lowercase letter")
        return value

    @model_validator(mode='after')
    def passwords_match(self) -> 'UserCreate':
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

# Admin Create User Schema
class AdminCreateUser(UserBase):
    role: RoleEnum = Field(
        default=RoleEnum.STUDENT,
        examples=["TEACHER"],
        description="User's role in the system"
    )
    disabled: bool = Field(
        default=False,
        examples=[False],
        description="Whether the user account is disabled"
    )

# Update Profile Schema
class UpdateProfileModel(BaseModel):
    first_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        examples=["John"],
        description="User's first name"
    )
    last_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        examples=["Doe"],
        description="User's last name"
    )
    contact_number: Optional[str] = Field(
        None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        examples=["+1234567890"],
        description="Phone number in E.164 format"
    )
    date_of_birth: Optional[datetime] = Field(
        None,
        examples=["1990-01-01T00:00:00Z"],
        description="User's date of birth"
    )

    @field_validator("date_of_birth")
    def validate_date_of_birth(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value and value.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            raise ValueError("Date of birth cannot be in the future")
        return value

# User Response Schema
class UserResponse(UserBase):
    id: int = Field(..., examples=[1], description="Unique user ID")
    is_active: bool = Field(..., examples=[True], description="Account active status")
    roles: list[RoleEnum] = Field(
        ...,
        examples=[["STUDENT"]],
        description="List of roles assigned to the user"
    )
    created_at: datetime = Field(
        ...,
        examples=["2023-01-01T00:00:00Z"],
        description="Account creation timestamp"
    )
    updated_at: datetime = Field(
        ...,
        examples=["2023-01-01T00:00:00Z"],
        description="Last update timestamp"
    )

    model_config = ConfigDict(from_attributes=True)

# Login Schema
class LoginModel(BaseModel):
    email: EmailStr = Field(
        ...,
        examples=["user@example.com"],
        description="Registered email address"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        examples=["SecurePassword123!"],
        description="Account password"
    )

# Token Response Schema
class TokenResponse(BaseModel):
    access_token: str = Field(
        ...,
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
        description="JWT access token"
    )
    refresh_token: str = Field(
        ...,
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
        description="JWT refresh token"
    )
    token_type: str = Field(
        default="bearer",
        examples=["bearer"],
        description="Token type"
    )
    expires_in: int = Field(
        ...,
        examples=[3600],
        description="Token expiration time in seconds"
    )

# Password Change Schema
class ChangePasswordModel(BaseModel):
    current_password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        examples=["CurrentPassword123!"],
        description="Current account password"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        examples=["NewSecurePassword123!"],
        description="New password"
    )
    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        examples=["NewSecurePassword123!"],
        description="Must match new_password field"
    )

    @field_validator("new_password")
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in value):
            raise ValueError("Password must contain at least one lowercase letter")
        return value

    @model_validator(mode='after')
    def passwords_match(self) -> 'ChangePasswordModel':
        if self.new_password != self.confirm_password:
            raise ValueError("New passwords do not match")
        return self