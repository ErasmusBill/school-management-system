from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import (
    PurchaseAdmissionFormCreate,
    PurchaseAdmissionFormResponse,
    ApplicationFormCreate,
    ApplicationFormResponse,
    StudentResponse,
    FeeListResponse,
    AcademicRecordListResponse
)
from .services import AdmissionService
from src.db.main import get_session
from typing import List
from fastapi import BackgroundTasks

admission_router = APIRouter()
admission_service = AdmissionService()

@admission_router.post("/purchase",response_model=PurchaseAdmissionFormResponse,status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid input"},
        500: {"description": "Database error"}
    }
)
async def purchase_admission(form_data: PurchaseAdmissionFormCreate,background_tasks:BackgroundTasks,session: AsyncSession = Depends(get_session)):
    """
    Purchase an admission form
    
    - **first_name**: Applicant's first name
    - **last_name**: Applicant's last name  
    - **contact**: Contact number
    - **email**: Email address
    - **amount**: Payment amount
    """
    return await admission_service.purchase_admission(form_data, background_tasks,session)

@admission_router.post("/apply",response_model=ApplicationFormResponse,status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid input"},
        404: {"description": "Purchase token not found"},
        500: {"description": "Database error"}
    }
)
async def apply_admission(form_data: ApplicationFormCreate,session: AsyncSession = Depends(get_session)):
    """
    Submit admission application
    
    Requires:
    - Valid purchase token
    - Complete student information  
    - Complete parent/guardian information
    - Intended grade level
    """
    return await admission_service.apply_for_admission(form_data, session)

@admission_router.get("/ward/{parent_id}",response_model=StudentResponse,
    responses={
        404: {"description": "Student not found"},
        500: {"description": "Database error"}  
    }
)
async def get_student_by_parent(parent_id: int,session: AsyncSession = Depends(get_session)):
    """Get student details by parent ID"""
    student = await admission_service.get_student_by_parent(parent_id, session)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    return student

@admission_router.get("/fees/{parent_id}",response_model=FeeListResponse,
    responses={
        404: {"description": "No fees found"},
        500: {"description": "Database error"}
    }
)
async def get_fees_by_parent(parent_id: int,session: AsyncSession = Depends(get_session)):
    """Get all fee records for parent"""
    fees = await admission_service.get_fees_by_parent(parent_id, session)
    if not fees:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fees found"
        )
    return {"fees": fees}

@admission_router.get("/academics/{student_id}/{parent_id}",response_model=AcademicRecordListResponse,
    responses={
        403: {"description": "Unauthorized access"},
        404: {"description": "Records not found"},
        500: {"description": "Database error"}
    }
)

async def get_academic_records(student_id: int,parent_id: int,session: AsyncSession = Depends(get_session)):
    """Get academic records with parent verification"""
    records = await admission_service.get_academic_records(student_id, parent_id, session)
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Academic records not found"
        )
    return {"records": records}