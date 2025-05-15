from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum
import uuid
from sqlalchemy import ForeignKey, String, Integer, DateTime, Float, Enum as SQLEnum # type: ignore
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column # type: ignore

Base = declarative_base()

if TYPE_CHECKING:
    from .models import Student, Teacher, Admin, Parent, Fee, AcademicRecord, Attendance, Class, ClassEnrollment, Event, Comment

class Role(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    PARENT = "parent"

class AdmissionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

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

class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(DateTime)
    contact_number: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SQLEnum(Role), default=Role.STUDENT)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    student: Mapped[Optional["Student"]] = relationship(back_populates="user", uselist=False)
    teacher: Mapped[Optional["Teacher"]] = relationship(back_populates="user", uselist=False)
    admin: Mapped[Optional["Admin"]] = relationship(back_populates="user", uselist=False)
    parent: Mapped[Optional["Parent"]] = relationship(back_populates="user", uselist=False)
    comments: Mapped[List["Comment"]] = relationship(back_populates="user")

class Student(Base):
    __tablename__ = "students"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_number: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True)
    grade_level: Mapped[str] = mapped_column(String(20))
    enrollment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"))
    
    user: Mapped["User"] = relationship(back_populates="student")
    parent: Mapped["Parent"] = relationship(back_populates="students")
    fees: Mapped[List["Fee"]] = relationship(back_populates="student")
    academic_records: Mapped[List["AcademicRecord"]] = relationship(back_populates="student")
    attendance_records: Mapped[List["Attendance"]] = relationship(back_populates="student")
    class_enrollments: Mapped[List["ClassEnrollment"]] = relationship(back_populates="student")
    admission_forms: Mapped[List["AdmissionForm"]] = relationship(back_populates="student")

class Teacher(Base):
    __tablename__ = "teachers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    subject_specialization: Mapped[str] = mapped_column(String(100))
    hire_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    
    user: Mapped["User"] = relationship(back_populates="teacher")
    academic_records: Mapped[List["AcademicRecord"]] = relationship(back_populates="teacher")
    classes: Mapped[List["Class"]] = relationship(back_populates="teacher")

class Admin(Base):
    __tablename__ = "admins"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    department: Mapped[str] = mapped_column(String(100))
    hire_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    
    user: Mapped["User"] = relationship(back_populates="admin")
    events: Mapped[List["Event"]] = relationship(back_populates="admin")

class Parent(Base):
    __tablename__ = "parents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    relationship_type: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    
    user: Mapped["User"] = relationship(back_populates="parent")
    students: Mapped[List["Student"]] = relationship(back_populates="parent")
    fees: Mapped[List["Fee"]] = relationship(back_populates="parent")
    admission_forms: Mapped[List["AdmissionForm"]] = relationship(back_populates="parent")

class PurchaseAdmissionForm(Base):
    __tablename__ = "purchase_admission_forms"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    contact: Mapped[str] = mapped_column(String(15))
    email: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    serial_token: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    purchase_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    admission_form: Mapped[Optional["AdmissionForm"]] = relationship(back_populates="purchase")

class AdmissionForm(Base):
    __tablename__ = "admission_forms"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id"))
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"))
    purchase_id: Mapped[Optional[int]] = mapped_column(ForeignKey("purchase_admission_forms.id"))
    
    student_first_name: Mapped[str] = mapped_column(String(50))
    student_last_name: Mapped[str] = mapped_column(String(50))
    student_dob: Mapped[Optional[datetime]] = mapped_column(DateTime)
    student_contact: Mapped[str] = mapped_column(String(20))
    student_email: Mapped[str] = mapped_column(String(100))
    
    parent_first_name: Mapped[str] = mapped_column(String(50))
    parent_last_name: Mapped[str] = mapped_column(String(50))
    parent_relationship: Mapped[str] = mapped_column(String(20))
    parent_contact: Mapped[str] = mapped_column(String(20))
    parent_email: Mapped[str] = mapped_column(String(100))
    
    intended_grade: Mapped[str] = mapped_column(String(20))
    previous_school: Mapped[Optional[str]] = mapped_column(String(100))
    medical_conditions: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[AdmissionStatus] = mapped_column(SQLEnum(AdmissionStatus), default=AdmissionStatus.PENDING)
    submission_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    student: Mapped[Optional["Student"]] = relationship(back_populates="admission_forms")
    parent: Mapped["Parent"] = relationship(back_populates="admission_forms")
    purchase: Mapped[Optional["PurchaseAdmissionForm"]] = relationship(back_populates="admission_form")
    fee: Mapped[Optional["Fee"]] = relationship(back_populates="admission_form")

class Fee(Base):
    __tablename__ = "fees"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"))
    admission_form_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admission_forms.id"))
    amount: Mapped[float] = mapped_column(Float)
    fee_type: Mapped[FeeType] = mapped_column(SQLEnum(FeeType))
    due_date: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[FeeStatus] = mapped_column(SQLEnum(FeeStatus), default=FeeStatus.UNPAID)
    payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(50))
    
    student: Mapped["Student"] = relationship(back_populates="fees")
    parent: Mapped["Parent"] = relationship(back_populates="fees")
    admission_form: Mapped[Optional["AdmissionForm"]] = relationship(back_populates="fee")

class AcademicRecord(Base):
    __tablename__ = "academic_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    subject: Mapped[str] = mapped_column(String(50))
    grade: Mapped[str] = mapped_column(String(10))
    term: Mapped[str] = mapped_column(String(20))
    academic_year: Mapped[str] = mapped_column(String(10))
    comments: Mapped[Optional[str]] = mapped_column(String(200))
    recorded_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    student: Mapped["Student"] = relationship(back_populates="academic_records")
    teacher: Mapped["Teacher"] = relationship(back_populates="academic_records")

class Attendance(Base):
    __tablename__ = "attendance"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[AttendanceStatus] = mapped_column(SQLEnum(AttendanceStatus), default=AttendanceStatus.PRESENT)
    remarks: Mapped[Optional[str]] = mapped_column(String(100))
    
    student: Mapped["Student"] = relationship(back_populates="attendance_records")

class Class(Base):
    __tablename__ = "classes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    grade_level: Mapped[str] = mapped_column(String(20))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    academic_year: Mapped[str] = mapped_column(String(10))
    
    teacher: Mapped["Teacher"] = relationship(back_populates="classes")
    students: Mapped[List["ClassEnrollment"]] = relationship(back_populates="class_")

class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    enrollment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    student: Mapped["Student"] = relationship(back_populates="class_enrollments")
    class_: Mapped["Class"] = relationship(back_populates="students")
    
class Event(Base):
    __tablename__ = "events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(50))    
    description: Mapped[str] = mapped_column(String(500))
    datetime: Mapped[datetime] = mapped_column(DateTime)
    location: Mapped[Optional[str]] = mapped_column(String(100))
    admin_id: Mapped[int] = mapped_column(ForeignKey("admins.id"))
    
    admin: Mapped["Admin"] = relationship(back_populates="events")
    comments: Mapped[List["Comment"]] = relationship(back_populates="event")
    
class Comment(Base):
    __tablename__ = "comments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    
    user: Mapped["User"] = relationship(back_populates="comments")
    event: Mapped["Event"] = relationship(back_populates="comments")