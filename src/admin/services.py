from fastapi import status, HTTPException, Depends, BackgroundTasks
from src.db.models import *
from sqlalchemy.ext.asyncio import AsyncSession # type: ignore
from sqlalchemy import select, exists, or_ # type: ignore
from fastapi.responses import JSONResponse
from src.mail import send_approve_admission_email, send_decline_admission_email


class AdminService:
    async def get_admin_by_id(self, admin_id: int, session: AsyncSession):
        """Get admin by ID"""
        query = select(Admin).where(Admin.id == admin_id)
        result = await session.execute(query)
        admin = result.scalars().first()
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
        return admin

    async def get_admin_by_email(self, email: str, session: AsyncSession):
        """Get admin by email"""
        query = select(Admin).where(Admin.email == email)
        result = await session.execute(query)
        admin = result.scalars().first()
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
        return admin
    
    async def get_all_admission(self, admin_id: int, session: AsyncSession):
        """Get all admission"""
        admin = await self.get_admin_by_id(admin_id, session)
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You don't have permission to view")
        
        query = select(AdmissionForm)
        result = await session.execute(query)
        admissions = result.scalars().all()
        if not admissions:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No admissions found")
        return admissions
    
    async def get_admission_by_id(self, admin_id: int, admission_id: int, session: AsyncSession):
        """Get admission by ID"""
        admin = await self.get_admin_by_id(admin_id, session)
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You don't have permission to view")
        
        query = select(AdmissionForm).where(AdmissionForm.id == admission_id)
        result = await session.execute(query)
        admission = result.scalars().first()
        if not admission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found")
        return admission
    
    async def verify_admission(self, admin_id: int, admission_id: int, background_tasks: BackgroundTasks, session: AsyncSession):
        """Verify an admission application"""
        admin = await self.get_admin_by_id(admin_id, session)
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You don't have permission to perform this action")
        
        admission = await self.get_admission_by_id(admin_id, admission_id, session)
        if not admission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found")
        
        # Get user's email associated with this admission
        query = select(User.email).join(Student).where(Student.id == admission.student_id)
        result = await session.execute(query)
        user_email = result.scalar_one_or_none()
        
        if not user_email:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User email not found")
        
        # Update the admission status
        admission.status = AdmissionStatus.VERIFIED
        await session.commit()
        
        # Send email notification in the background
        background_tasks.add_task(
            send_approve_admission_email,
            email=user_email,
            admission_id=admission_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Admission approved successfully",
                "admission": {"id": admission.id, "status": admission.status.value}
            }
        )
        
    async def decline_admission(self, admin_id: int, admission_id: int, background_tasks: BackgroundTasks, session: AsyncSession):
        """Decline an admission application"""
        admin = await self.get_admin_by_id(admin_id, session)
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You don't have permission to perform this action")
        
        admission = await self.get_admission_by_id(admin_id, admission_id, session)
        if not admission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found")
        
        # Get user's email associated with this admission
        query = select(User.email).join(Student).where(Student.id == admission.student_id)
        result = await session.execute(query)
        user_email = result.scalar_one_or_none()
        
        if not user_email:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User email not found")
        
        # Update the admission status
        admission.status = AdmissionStatus.DECLINED
        await session.commit()
        
        # Send email notification in the background
        background_tasks.add_task(
            send_decline_admission_email,
            email=user_email,
            admission_id=admission_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Admission declined successfully",
                "admission": {"id": admission.id, "status": admission.status.value}
            }
        )
        
    async def get_all_admission_records(self, admin_id: int, session: AsyncSession):
        """Get all admission records"""
        admin = await self.get_admin_by_id(admin_id, session)
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You don't have permission to view")
        
        query = select(AcademicRecord)
        result = await session.execute(query)
        records = result.scalars().all()
        
        if not records:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No records found")
        
        return records
        
    async def get_academic_records_by_admin(self, admin_id: int, student_id: int, session: AsyncSession):
        """Get academic records for a specific student"""
        admin = await self.get_admin_by_id(admin_id, session)
        
        if not admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You don't have permission to view")    
        
        statement = select(Student).join(User).where(User.id == student_id)
        result = await session.execute(statement)   
        student = result.scalars().first()
        
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
        
        statement = select(AcademicRecord).where(AcademicRecord.student_id == student_id)
        result = await session.execute(statement)
        records = result.scalars().all()
        
        if not records:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No academic records found for this student")
            
        return records