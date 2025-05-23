from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from enum import Enum
from typing import Optional, List

class AdmissionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"

class FeeType(str, Enum):
    TUITION = "tuition"
    ADMISSION = "admission" 
    EXAM = "exam"
    ACTIVITY = "activity"
    TRANSPORT = "transport"

class FeeStatus(str, Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    OVERDUE = "overdue"
    PARTIAL = "partial"

class Role(str, Enum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    ADMIN = "ADMIN"
    PARENT = "PARENT"

class StudentInfo(BaseModel):
    first_name: str = Field(..., example="John")
    last_name: str = Field(..., example="Doe")
    date_of_birth: Optional[datetime] = Field(None, example="2010-05-15T00:00:00")
    contact_number: str = Field(..., example="1234567890")
    email: EmailStr = Field(..., example="john.doe@example.com")
    enrollment_number: Optional[str] = Field(None, example="STU20230001")

    @validator('enrollment_number')
    def validate_enrollment_number(cls, v):
        if v and not v.startswith('STU'):
            raise ValueError("Enrollment number must start with 'STU'")
        return v

class ParentInfo(BaseModel):
    first_name: str = Field(..., example="Jane")
    last_name: str = Field(..., example="Doe")
    relationship: str = Field(..., example="mother")
    contact_number: str = Field(..., example="0987654321")
    email: EmailStr = Field(..., example="jane.doe@example.com")

class PurchaseAdmissionFormBase(BaseModel):
    first_name: str = Field(..., example="John")
    last_name: str = Field(..., example="Doe")
    contact: str = Field(..., example="1234567890")
    email: EmailStr = Field(..., example="john.doe@example.com")
    amount: float = Field(..., description="Amount paid for the form", example=5000.00)

class PurchaseAdmissionFormCreate(PurchaseAdmissionFormBase):
    pass

class PurchaseAdmissionFormResponse(PurchaseAdmissionFormBase):
    id: int
    serial_token: str
    purchase_date: datetime
    form_id: str

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ApplicationFormCreate(BaseModel):
    student: StudentInfo
    parent: ParentInfo
    intended_grade: str = Field(..., example="Grade 5")
    previous_school: Optional[str] = Field(None, example="XYZ Academy")
    medical_conditions: Optional[str] = Field(
        None, 
        example="Asthma, needs inhaler"
    )
    purchase_token: str = Field(..., description="Serial token from purchased form")

class ApplicationFormResponse(BaseModel):
    id: int
    form_id: str
    status: AdmissionStatus
    submission_date: datetime
    student: StudentInfo
    parent: ParentInfo
    intended_grade: str
    previous_school: Optional[str] = None
    medical_conditions: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class StudentResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    date_of_birth: Optional[datetime]
    contact_number: str
    email: EmailStr
    enrollment_number: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
class FeeResponse(BaseModel):
    id: int
    amount: float
    fee_type: FeeType
    due_date: datetime
    status: FeeStatus
    payment_date: Optional[datetime] = None
    transaction_reference: Optional[str] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
class FeeListResponse(BaseModel):
    fees: List[FeeResponse]
    
    class Config:
        from_attributes = True

class AcademicRecordResponse(BaseModel):
    id: int
    subject: str
    grade: str
    term: str
    academic_year: str
    comments: Optional[str] = None
    recorded_date: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
class AcademicRecordListResponse(BaseModel):
    records: List[AcademicRecordResponse]
    
    class Config:
        from_attributes = True