from sqlalchemy.ext.asyncio import AsyncSession # type: ignore
from sqlalchemy import select, exists, or_ # type: ignore
from src.db.models import (PurchaseAdmissionForm,AdmissionForm,Student,Parent,User,Fee,AcademicRecord)
from .schemas import (PurchaseAdmissionFormCreate,PurchaseAdmissionFormResponse,ApplicationFormCreate,ApplicationFormResponse,StudentInfo,ParentInfo, StudentResponse,FeeResponse,AcademicRecordResponse)
from fastapi import HTTPException, status
from datetime import datetime
import uuid
import logging
from typing import List, Optional
from fastapi import BackgroundTasks
from src.mail import send_serial_token

logger = logging.getLogger(__name__)

class AdmissionService:
    
    async def purchase_admission(self,form_data: PurchaseAdmissionFormCreate,background_tasks: BackgroundTasks,session:AsyncSession) -> PurchaseAdmissionFormResponse:
        """Process admission form purchase"""
        
        purchase = PurchaseAdmissionForm(
                first_name=form_data.first_name,
                last_name=form_data.last_name,
                contact=form_data.contact,
                email=form_data.email,
                amount=form_data.amount,
                serial_token=str(uuid.uuid4()),
                purchase_date=datetime.utcnow()
            )
            
        session.add(purchase)
        await session.commit()
        await session.refresh(purchase)
        
        # Send serial token email
        background_tasks.add_task(
            send_serial_token,
            email=purchase.email,
            
        )
        
            
        logger.info(f"New admission form purchased: {purchase.id}")
            
        return PurchaseAdmissionFormResponse(
                id=purchase.id,
                first_name=purchase.first_name,
                last_name=purchase.last_name,
                contact=purchase.contact,
                email=purchase.email,
                amount=purchase.amount,
                serial_token=purchase.serial_token,
                purchase_date=purchase.purchase_date,
                form_id=str(uuid.uuid4())
        )
            
      
    async def apply_for_admission(self,form_data: ApplicationFormCreate,session: AsyncSession) -> ApplicationFormResponse:
        """Process admission application"""
        try:
            # Verify purchase token
            purchase = await self._verify_purchase_token(form_data.purchase_token, session)
            
            # Check if student exists
            student = await self._find_existing_student(form_data.student, session)
            
            # Validate or create parent
            parent = await self._validate_or_create_parent(form_data.parent, session)
            
            # Create admission form
            admission_form = await self._create_admission_form(
                form_data, 
                purchase.id, 
                student.id if student else None,
                parent.id,
                session
            )
            
            return await self._build_application_response(admission_form, form_data)
            
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Application failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process application"
            )

    async def _verify_purchase_token(self, token: str, session: AsyncSession) -> PurchaseAdmissionForm:
        """Verify purchase token is valid and unused"""
        purchase = await session.execute(
            select(PurchaseAdmissionForm).where(PurchaseAdmissionForm.serial_token == token).where(~exists().where(AdmissionForm.purchase_id == PurchaseAdmissionForm.id)))
        purchase = purchase.scalars().first()
        
        if not purchase:
            logger.warning(f"Invalid purchase token attempt: {token}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or already used purchase token"
            )
        return purchase

    async def _find_existing_student(self,student_info: StudentInfo,session: AsyncSession)-> Optional[Student]:
        """Find existing student by email or enrollment number"""
        if not student_info.email:
            return None
            
        query = select(Student).join(User).where(User.email == student_info.email)
        
        if student_info.enrollment_number:
            query = query.where(or_(User.email == student_info.email,Student.enrollment_number == student_info.enrollment_number))
            
        result = await session.execute(query)
        return result.scalars().first()

    async def _validate_or_create_parent(self,parent_info: ParentInfo,session: AsyncSession) -> Parent:
        """Validate or create parent record"""
        parent = await session.execute(select(Parent).join(User).where(User.email == parent_info.email))
        
        parent = parent.scalars().first()
        
        if not parent:
            # Create new parent user
            parent_user = User(
                first_name=parent_info.first_name,
                last_name=parent_info.last_name,
                contact_number=parent_info.contact_number,
                email=parent_info.email,
                username=parent_info.email,
                password_hash="",  # Temporary empty password
                role="parent",
                is_active=False
            )
            session.add(parent_user)
            await session.flush()
            
            parent = Parent(user_id=parent_user.id,relationship_type=parent_info.relationship)
            session.add(parent)
            await session.flush()
        
        return parent

    async def _create_admission_form(self,form_data: ApplicationFormCreate,purchase_id: int,student_id: Optional[int], parent_id: int,session: AsyncSession) -> AdmissionForm:
        """Create new admission form record"""
        form = AdmissionForm(
            form_id=str(uuid.uuid4()),
            purchase_id=purchase_id,
            student_id=student_id,
            parent_id=parent_id,
            student_first_name=form_data.student.first_name,
            student_last_name=form_data.student.last_name,
            student_dob=form_data.student.date_of_birth,
            student_contact=form_data.student.contact_number,
            student_email=form_data.student.email,
            parent_first_name=form_data.parent.first_name,
            parent_last_name=form_data.parent.last_name,
            parent_relationship=form_data.parent.relationship,
            parent_contact=form_data.parent.contact_number,
            parent_email=form_data.parent.email,
            intended_grade=form_data.intended_grade,
            previous_school=form_data.previous_school,
            medical_conditions=form_data.medical_conditions,
            status="pending",
            submission_date=datetime.utcnow()
        )
        
        session.add(form)
        await session.commit()
        await session.refresh(form)
        return form

    async def _build_application_response(self,admission_form: AdmissionForm,form_data: ApplicationFormCreate) -> ApplicationFormResponse:
        """Build the application response"""
        return ApplicationFormResponse(
            id=admission_form.id,
            form_id=admission_form.form_id,
            status=admission_form.status,
            submission_date=admission_form.submission_date,
            student=form_data.student,
            parent=form_data.parent,
            intended_grade=form_data.intended_grade,
            previous_school=form_data.previous_school,
            medical_conditions=form_data.medical_conditions
        )

    async def get_student_by_parent(self,parent_id: int,session: AsyncSession) -> StudentResponse:
        """Retrieve student by parent ID"""
        try:
            result = await session.execute(
                select(Student).where(Student.parent_id == parent_id).limit(1))
            
            student = result.scalars().first()
            
            if not student:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No student found for this parent"
                )
                
            return StudentResponse(
                id=student.id,
                first_name=student.user.first_name,
                last_name=student.user.last_name,
                date_of_birth=student.user.date_of_birth,
                contact_number=student.user.contact_number,
                email=student.user.email,
                enrollment_number=student.enrollment_number,
                created_at=student.user.created_at,
                updated_at=student.user.updated_at
            )
            
        except Exception as e:
            logger.error(f"Error fetching student: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve student information"
            )

    async def get_fees_by_parent(self,parent_id: int,session: AsyncSession) -> List[FeeResponse]:
        """Retrieve all fees for parent"""
        try:
            result = await session.execute(select(Fee).where(Fee.parent_id == parent_id).order_by(Fee.due_date.desc()))
            
            fees = result.scalars().all()
            
            return [
                FeeResponse(
                    id=fee.id,
                    amount=fee.amount,
                    fee_type=fee.fee_type,
                    due_date=fee.due_date,
                    status=fee.status,
                    payment_date=fee.payment_date,
                    transaction_reference=fee.transaction_reference
                )
                for fee in fees
            ]
            
        except Exception as e:
            logger.error(f"Error fetching fees: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve fee information"
            )

    async def get_academic_records(self,student_id: int,parent_id: int,session: AsyncSession) -> List[AcademicRecordResponse]:
        """Retrieve academic records with parent authorization"""
        try:
            # Verify parent-student relationship
            student_exists = await session.execute(
                select(Student.id).where(Student.id == student_id).where(Student.parent_id== parent_id).exists().select())
            
            if not await session.scalar(student_exists):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access these records"
                )
                
            # Get records
            result = await session.execute(
                select(AcademicRecord).where(AcademicRecord.student_id == student_id).order_by(AcademicRecord.recorded_date.desc())
            )
            records = result.scalars().all()
            
            return [
                AcademicRecordResponse(
                    id=record.id,
                    subject=record.subject,
                    grade=record.grade,
                    term=record.term,
                    academic_year=record.academic_year,
                    comments=record.comments,
                    recorded_date=record.recorded_date
                )
                for record in records
            ]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching academic records: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve academic records"
            )