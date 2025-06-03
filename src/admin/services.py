from fastapi import status, HTTPException, Depends, BackgroundTasks
from src.db.models import *
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, or_
from fastapi.responses import JSONResponse
from src.mail import send_approve_admission_email, send_decline_admission_email


class AdminService:
    async def get_admin_by_id(self, admin_id: int, session: AsyncSession):
        """Get admin by ID"""
        query = select(Admin).where(Admin.id == admin_id)
        result = await session.execute(query)
        admin = result.scalars().first()
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Admin not found"
            )
        return admin

    async def get_admin_by_email(self, email: str, session: AsyncSession):
        """Get admin by email"""
        query = select(Admin).where(Admin.email == email)
        result = await session.execute(query)
        admin = result.scalars().first()
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Admin not found"
            )
        return admin
    
    async def get_all_admission(self, current_user:dict, session: AsyncSession):
        """Get all admission requests"""
        # Verify admin exists and has permission
        
        if current_user.get("role") != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You do not have permission to access this resource"
            )
        
        query = select(AdmissionForm)
        result = await session.execute(query)
        admissions = result.scalars().all()

        return admissions
    
    async def get_admission_by_id(self, current_user: dict, admission_id: int, session: AsyncSession):
        """Get admission by ID"""
        if current_user.get("role") != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You do not have permission to access this resource"
            )
        query = select(AdmissionForm).where(AdmissionForm.id == admission_id)
        result = await session.execute(query)
        admission = result.scalars().first()
        if not admission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Admission not found"
            )
        return admission
    
    async def verify_admission(self, current_user:dict, admission_id: int, background_tasks: BackgroundTasks, session: AsyncSession):
        """Verify an admission application"""
        # Verify admin exists and has permission
        if current_user.get("role") != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You do not have permission to access this resource"
            )
        
        # Get admission (this already includes admin permission check)
        admission = await self.get_admission_by_id(current_user, admission_id, session)
        
        # Check if admission is already processed
        if admission.status in [AdmissionStatus.VERIFIED, AdmissionStatus.DECLINED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Admission is already {admission.status.value.lower()}"
            )
        
        # Get user's email associated with this admission
        query = select(User.email).join(Student).where(Student.id == admission.student_id)
        result = await session.execute(query)
        user_email = result.scalar_one_or_none()
        
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User email not found"
            )
        
        # Update the admission status
        admission.status = AdmissionStatus.VERIFIED
        await session.commit()
        
        # Send email notification in the background
        background_tasks.add_task(
            send_approve_admission_email,
            email=user_email,
            admission_id=admission_id
        )
        
        return {
            "message": "Admission approved successfully",
            "admission": {
                "id": admission.id, 
                "status": admission.status.value,
                "student_id": admission.student_id
            }
        }
        
    async def decline_admission(self, current_user:dict, admission_id: int, background_tasks: BackgroundTasks, session: AsyncSession):
        """Decline an admission application"""
        if current_user.get("role") != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You do not have permission to access this resource"
            )
        
        # Get admission (this already includes admin permission check)
        admission = await self.get_admission_by_id(current_user, admission_id, session)
        
        # Check if admission is already processed
        if admission.status in [AdmissionStatus.VERIFIED, AdmissionStatus.DECLINED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Admission is already {admission.status.value.lower()}"
            )
        
        # Get user's email associated with this admission
        query = select(User.email).join(Student).where(Student.id == admission.student_id)
        result = await session.execute(query)
        user_email = result.scalar_one_or_none()
        
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User email not found"
            )
        
        # Update the admission status
        admission.status = AdmissionStatus.DECLINED
        await session.commit()
        
        # Send email notification in the background
        background_tasks.add_task(
            send_decline_admission_email,
            email=user_email,
            admission_id=admission_id
        )
        
        return {
            "message": "Admission declined successfully",
            "admission": {
                "id": admission.id, 
                "status": admission.status.value,
                "student_id": admission.student_id
            }
        }
        
    async def get_all_admission_records(self, current_user:dict, session: AsyncSession):
        """Get all academic records (admission records)"""
        if current_user.get("role") != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You do not have permission to access this resource"
            )
        
        query = select(AcademicRecord)
        result = await session.execute(query)
        records = result.scalars().all()
        
        return records
        
    async def get_academic_records_by_admin(self, current_user:dict, student_id: int, session: AsyncSession):
        """Get academic records for a specific student"""
        if current_user.get("role") != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You do not have permission to access this resource"
            )
        
        # Verify student exists
        student_query = select(Student).where(Student.id == student_id)
        student_result = await session.execute(student_query)
        student = student_result.scalars().first()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Student not found"
            )
        
        # Get academic records for the student
        records_query = select(AcademicRecord).where(AcademicRecord.student_id == student_id)
        records_result = await session.execute(records_query)
        records = records_result.scalars().all()
        
        return records
    
    async def get_admission_statistics(self, current_user:dict, session: AsyncSession):
        """Get admission statistics - bonus method for dashboard"""
        if current_user.get("role") != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You do not have permission to access this resource"
            )
        
        # Count admissions by status
        total_query = select(AdmissionForm)
        total_result = await session.execute(total_query)
        total_admissions = len(total_result.scalars().all())
        
        verified_query = select(AdmissionForm).where(AdmissionForm.status == AdmissionStatus.VERIFIED)
        verified_result = await session.execute(verified_query)
        verified_count = len(verified_result.scalars().all())
        
        declined_query = select(AdmissionForm).where(AdmissionForm.status == AdmissionStatus.DECLINED)
        declined_result = await session.execute(declined_query)
        declined_count = len(declined_result.scalars().all())
        
        pending_count = total_admissions - verified_count - declined_count
        
        return {
            "total_admissions": total_admissions,
            "verified": verified_count,
            "declined": declined_count,
            "pending": pending_count
        }