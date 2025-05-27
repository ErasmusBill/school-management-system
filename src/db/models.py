from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum, auto
import uuid
from sqlalchemy import (
    ForeignKey, 
    String, 
    Integer, 
    TIMESTAMP, 
    Float, 
    Enum as SQLEnum, 
    Column,
    Text,
    Boolean
)
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column
from sqlalchemy import Table

Base = declarative_base()

# Association tables for many-to-many relationships
role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True)
)

user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True)
)

class RoleEnum(str, Enum):
    """Extended system roles with more granular permissions"""
    SUPER_ADMIN = "SUPER_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD"
    TEACHER = "TEACHER"
    TEACHER_AIDE = "TEACHER_AIDE"
    STUDENT = "STUDENT"
    PARENT = "PARENT"
    STAFF = "STAFF"  # Non-teaching staff
    LIBRARIAN = "LIBRARIAN"
    COUNSELOR = "COUNSELOR"
    ACCOUNTANT = "ACCOUNTANT"
    IT_ADMIN = "IT_ADMIN"
    
class PermissionEnum(str, Enum):
    """Comprehensive permission system"""
    # User management
    MANAGE_USERS = "manage_users"
    VIEW_USERS = "view_users"
    
    # Student management
    MANAGE_STUDENTS = "manage_students"
    VIEW_ALL_STUDENTS = "view_all_students"
    VIEW_OWN_STUDENTS = "view_own_students"  # For teachers/parents
    
    # Academic operations
    MANAGE_ACADEMIC_RECORDS = "manage_academic_records"
    VIEW_ACADEMIC_RECORDS = "view_academic_records"
    GENERATE_REPORTS = "generate_reports"
    
    # Admission system
    MANAGE_ADMISSIONS = "manage_admissions"
    VIEW_ADMISSIONS = "view_admissions"
    APPROVE_ADMISSIONS = "approve_admissions"
    REJECT_ADMISSIONS = "reject_admissions"
    
    # Financial
    MANAGE_FEES = "manage_fees"
    VIEW_FINANCIALS = "view_financials"
    PROCESS_PAYMENTS = "process_payments"
    
    # Attendance
    MANAGE_ATTENDANCE = "manage_attendance"
    VIEW_ATTENDANCE = "view_attendance"
    
    # Classes and scheduling
    MANAGE_CLASSES = "manage_classes"
    MANAGE_SCHEDULE = "manage_schedule"
    
    # Content management
    MANAGE_COURSE_MATERIALS = "manage_course_materials"
    MANAGE_ASSIGNMENTS = "manage_assignments"
    GRADE_ASSIGNMENTS = "grade_assignments"
    
    # System administration
    MANAGE_SYSTEM_SETTINGS = "manage_system_settings"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    
    # Communication
    SEND_ANNOUNCEMENTS = "send_announcements"
    MANAGE_EVENTS = "manage_events"
    POST_COMMENTS = "post_comments"
    
    # Library
    MANAGE_LIBRARY = "manage_library"
    CHECKOUT_BOOKS = "checkout_books"
    
    # Counseling
    MANAGE_COUNSELING = "manage_counseling"
    VIEW_COUNSELING_RECORDS = "view_counseling_records"

class AdmissionStatus(str, Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    CONDITIONAL = "CONDITIONAL"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"

class FeeType(str, Enum):
    TUITION = "TUITION"
    ADMISSION = "ADMISSION"
    EXAM = "EXAM"
    ACTIVITY = "ACTIVITY"
    TRANSPORT = "TRANSPORT"
    HOSTEL = "HOSTEL"
    LIBRARY = "LIBRARY"
    UNIFORM = "UNIFORM"
    OTHER = "OTHER"

class FeeStatus(str, Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    PARTIAL = "PARTIAL"
    WAIVED = "WAIVED"
    REFUNDED = "REFUNDED"

class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"
    SUSPENDED = "SUSPENDED"
    HOLIDAY = "HOLIDAY"

class AssignmentStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"

class SubmissionStatus(str, Enum):
    NOT_SUBMITTED = "NOT_SUBMITTED"
    SUBMITTED = "SUBMITTED"
    LATE = "LATE"
    GRADED = "GRADED"

class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

def current_time():
    return datetime.now(timezone.utc)

class Role(Base):
    """Extended role model with hierarchical permissions"""
    __tablename__ = "roles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[RoleEnum] = mapped_column(SQLEnum(RoleEnum), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    permissions: Mapped[List[Permission]] = relationship(
        secondary=role_permission, 
        back_populates="roles"
    )
    users: Mapped[List[User]] = relationship(
        secondary=user_role,
        back_populates="roles"
    )

class Permission(Base):
    """Granular system permissions"""
    __tablename__ = "permissions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[PermissionEnum] = mapped_column(SQLEnum(PermissionEnum), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    roles: Mapped[List[Role]] = relationship(
        secondary=role_permission, 
        back_populates="permissions"
    )

class User(Base):
    """Enhanced user model with multiple roles and detailed attributes"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[Gender] = mapped_column(SQLEnum(Gender))
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    contact_number: Mapped[str] = mapped_column(String(20), nullable=False)
    alternate_contact: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_picture: Mapped[Optional[str]] = mapped_column(String(255))
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(50))
    state: Mapped[Optional[str]] = mapped_column(String(50))
    country: Mapped[Optional[str]] = mapped_column(String(50))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=current_time,
        onupdate=current_time
    )
    
    # Relationships
    roles: Mapped[List[Role]] = relationship(
        secondary=user_role,
        back_populates="users"
    )
    student: Mapped[Optional[Student]] = relationship(back_populates="user", uselist=False)
    teacher: Mapped[Optional[Teacher]] = relationship(back_populates="user", uselist=False)
    admin: Mapped[Optional[Admin]] = relationship(back_populates="user", uselist=False)
    parent: Mapped[Optional[Parent]] = relationship(back_populates="user", uselist=False)
    staff: Mapped[Optional[Staff]] = relationship(back_populates="user", uselist=False)
    comments: Mapped[List[Comment]] = relationship(back_populates="user")
    assignments: Mapped[List[Assignment]] = relationship(back_populates="creator")

    def has_role(self, role_name: RoleEnum) -> bool:
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission_name: PermissionEnum) -> bool:
        for role in self.roles:
            if any(perm.name == permission_name for perm in role.permissions):
                return True
        return False

class Student(Base):
    """Enhanced student model with academic tracking"""
    __tablename__ = "students"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    grade_level: Mapped[str] = mapped_column(String(20), nullable=False)
    section: Mapped[Optional[str]] = mapped_column(String(10))
    enrollment_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    graduation_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    is_active: Mapped[bool] = mapped_column(default=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"))
    
    # Relationships
    user: Mapped[User] = relationship(back_populates="student")
    parent: Mapped[Parent] = relationship(back_populates="students")
    fees: Mapped[List[Fee]] = relationship(back_populates="student")
    academic_records: Mapped[List[AcademicRecord]] = relationship(back_populates="student")
    attendance_records: Mapped[List[Attendance]] = relationship(back_populates="student")
    class_enrollments: Mapped[List[ClassEnrollment]] = relationship(back_populates="student")
    admission_forms: Mapped[List[AdmissionForm]] = relationship(back_populates="student")
    submissions: Mapped[List[Submission]] = relationship(back_populates="student")

class Teacher(Base):
    """Enhanced teacher model with department support"""
    __tablename__ = "teachers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_specialization: Mapped[str] = mapped_column(String(100), nullable=False)
    qualification: Mapped[Optional[str]] = mapped_column(String(100))
    hire_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    termination_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    is_active: Mapped[bool] = mapped_column(default=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    
    # Relationships
    user: Mapped[User] = relationship(back_populates="teacher")
    academic_records: Mapped[List[AcademicRecord]] = relationship(back_populates="teacher")
    classes: Mapped[List[Class]] = relationship(back_populates="teacher")
    assignments: Mapped[List[Assignment]] = relationship(back_populates="teacher")

class Admin(Base):
    """Admin model with department-specific administration"""
    __tablename__ = "admins"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    hire_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    is_active: Mapped[bool] = mapped_column(default=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    
    # Relationships
    user: Mapped[User] = relationship(back_populates="admin")
    events: Mapped[List[Event]] = relationship(back_populates="admin")
    admission_forms: Mapped[List[AdmissionForm]] = relationship(back_populates="processed_by")

class Staff(Base):
    """Non-teaching staff model"""
    __tablename__ = "staff"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    hire_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    is_active: Mapped[bool] = mapped_column(default=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    
    # Relationships
    user: Mapped[User] = relationship(back_populates="staff")

class Parent(Base):
    """Enhanced parent model with multiple student support"""
    __tablename__ = "parents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    relationship_type: Mapped[str] = mapped_column(String(20), nullable=False)
    occupation: Mapped[Optional[str]] = mapped_column(String(100))
    employer: Mapped[Optional[str]] = mapped_column(String(100))
    is_primary: Mapped[bool] = mapped_column(default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    
    # Relationships
    user: Mapped[User] = relationship(back_populates="parent")
    students: Mapped[List[Student]] = relationship(back_populates="parent")
    fees: Mapped[List[Fee]] = relationship(back_populates="parent")
    admission_forms: Mapped[List[AdmissionForm]] = relationship(back_populates="parent")

class PurchaseAdmissionForm(Base):
    """Model for tracking admission form purchases"""
    __tablename__ = "purchase_admission_forms"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    contact: Mapped[str] = mapped_column(String(15), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    serial_token: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    purchase_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    
    admission_form: Mapped[Optional[AdmissionForm]] = relationship(back_populates="purchase")

class AdmissionForm(Base):
    """Model for student admission applications"""
    __tablename__ = "admission_forms"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id"))
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"))
    purchase_id: Mapped[Optional[int]] = mapped_column(ForeignKey("purchase_admission_forms.id"))
    
    student_first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    student_last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    student_dob: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    student_contact: Mapped[str] = mapped_column(String(20), nullable=False)
    student_email: Mapped[str] = mapped_column(String(100), nullable=False)
    
    parent_first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    parent_last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    parent_relationship: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_contact: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_email: Mapped[str] = mapped_column(String(100), nullable=False)
    
    intended_grade: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_school: Mapped[Optional[str]] = mapped_column(String(100))
    medical_conditions: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[AdmissionStatus] = mapped_column(SQLEnum(AdmissionStatus), default=AdmissionStatus.PENDING)
    submission_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    processed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admins.id"))
    
    student: Mapped[Optional[Student]] = relationship(back_populates="admission_forms")
    parent: Mapped[Parent] = relationship(back_populates="admission_forms")
    purchase: Mapped[Optional[PurchaseAdmissionForm]] = relationship(back_populates="admission_form")
    fee: Mapped[Optional[Fee]] = relationship(back_populates="admission_form")
    processed_by: Mapped[Optional[Admin]] = relationship(back_populates="admission_forms")

class Fee(Base):
    """Model for tracking student fees and payments"""
    __tablename__ = "fees"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"))
    admission_form_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admission_forms.id"))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    fee_type: Mapped[FeeType] = mapped_column(SQLEnum(FeeType), nullable=False)
    due_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    status: Mapped[FeeStatus] = mapped_column(SQLEnum(FeeStatus), default=FeeStatus.UNPAID)
    payment_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(50))
    
    student: Mapped[Student] = relationship(back_populates="fees")
    parent: Mapped[Parent] = relationship(back_populates="fees")
    admission_form: Mapped[Optional[AdmissionForm]] = relationship(back_populates="fee")

class AcademicRecord(Base):
    """Model for tracking student academic performance"""
    __tablename__ = "academic_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    subject: Mapped[str] = mapped_column(String(50), nullable=False)
    grade: Mapped[str] = mapped_column(String(10), nullable=False)
    term: Mapped[str] = mapped_column(String(20), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(10), nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(String(200))
    recorded_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    
    student: Mapped[Student] = relationship(back_populates="academic_records")
    teacher: Mapped[Teacher] = relationship(back_populates="academic_records")

class Attendance(Base):
    """Model for tracking student attendance"""
    __tablename__ = "attendance"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    status: Mapped[AttendanceStatus] = mapped_column(SQLEnum(AttendanceStatus), default=AttendanceStatus.PRESENT)
    remarks: Mapped[Optional[str]] = mapped_column(String(100))
    
    student: Mapped[Student] = relationship(back_populates="attendance_records")

class Class(Base):
    """Model for school classes"""
    __tablename__ = "classes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    grade_level: Mapped[str] = mapped_column(String(20), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    academic_year: Mapped[str] = mapped_column(String(10), nullable=False)
    
    teacher: Mapped[Teacher] = relationship(back_populates="classes")
    students: Mapped[List[ClassEnrollment]] = relationship(back_populates="class_")

class ClassEnrollment(Base):
    """Model for student enrollment in classes"""
    __tablename__ = "class_enrollments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    enrollment_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    
    student: Mapped[Student] = relationship(back_populates="class_enrollments")
    class_: Mapped[Class] = relationship(back_populates="students")
    
class Event(Base):
    """Model for school events"""
    __tablename__ = "events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(50), nullable=False)    
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    datetime: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(100))
    admin_id: Mapped[int] = mapped_column(ForeignKey("admins.id"))
    
    admin: Mapped[Admin] = relationship(back_populates="events")
    comments: Mapped[List[Comment]] = relationship(back_populates="event")

class Comment(Base):
    """Model for comments on events"""
    __tablename__ = "comments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    
    user: Mapped[User] = relationship(back_populates="comments")
    event: Mapped[Event] = relationship(back_populates="comments")

class Assignment(Base):
    """Model for school assignments"""
    __tablename__ = "assignments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    max_grade: Mapped[float] = mapped_column(Float)
    status: Mapped[AssignmentStatus] = mapped_column(SQLEnum(AssignmentStatus), default=AssignmentStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    teacher: Mapped[Teacher] = relationship(back_populates="assignments")
    creator: Mapped[User] = relationship(back_populates="assignments")
    submissions: Mapped[List[Submission]] = relationship(back_populates="assignment")

class Submission(Base):
    """Model for student assignment submissions"""
    __tablename__ = "submissions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"))
    submission_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=current_time)
    status: Mapped[SubmissionStatus] = mapped_column(SQLEnum(SubmissionStatus), default=SubmissionStatus.SUBMITTED)
    file_path: Mapped[str] = mapped_column(String(255))
    grade: Mapped[Optional[float]] = mapped_column(Float)
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    
    student: Mapped[Student] = relationship(back_populates="submissions")
    assignment: Mapped[Assignment] = relationship(back_populates="submissions")