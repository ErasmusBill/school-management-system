from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks
from .services import AdminService
from src.db.models import *
from src.db.main import get_session
from sqlalchemy.ext.asyncio.session import AsyncSession
from . import schemas
from src.authservice.dependencies import get_current_user  

admin_router = APIRouter()
admin_service = AdminService()

@admin_router.get("/admission-request")
async def get_all_admission_request(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    # Optionally check if current_user["role"] == "ADMIN"
    admissions = await AdminService().get_all_admission(current_user, session)
    return {"admissions": admissions}

@admin_router.get("/get_admission/{admission_id}")
async def get_admission(
    admission_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    try:
        admission = await AdminService().get_admission_by_id(current_user, admission_id, session)
        return {"admission": admission}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the admission"
        )

@admin_router.post("/verify-admission/{admission_id}")
async def verify_admission(
    admission_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    """Verify admission"""
    try:
        result = await admin_service.verify_admission(
            current_user, admission_id, background_tasks, session
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while verifying the admission"
        )

@admin_router.post("/decline-admission/{admission_id}")
async def decline_admission(
    admission_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    """Decline admission"""
    try:
        result = await admin_service.decline_admission(
            current_user, admission_id, background_tasks, session
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while declining the admission"
        )

@admin_router.get("/admission-records")
async def get_all_admission_records(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
    
):
    """Get all admission records"""
    try:
        records = await admin_service.get_all_admission_records(current_user, session)
        return {"records": records}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching admission records"
        )

@admin_router.get("/academic-records/{student_id}")
async def get_academic_records_by_student(
    student_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user)
):
    """Get academic records for a specific student"""
    try:
        records = await admin_service.get_academic_records_by_admin(
            current_user, student_id, session
        )
        return {"records": records}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching academic records"
        )