# models/__init__.py
# Import all models so they are registered with SQLAlchemy's metadata

from .user import User, Role, Permission, RolePermission
from .student import Student
from .faculty import Faculty
from .department import Department
from .subject import Subject, AcademicYear, Semester
from .class_section import ClassSection, FacultyAssignment, StudentEnrollment
from .attendance import AttendanceSession, AttendanceRecord
from .examination import Exam, Question, QuestionOption, ExamAttempt, AttemptAnswer
from .results import Result
from .fees import FeeRecord, FeePayment
from .assignments import Assignment, AssignmentSubmission, StudyMaterial
from .notifications import Notification
from .audit import AuditLog
from .documents import StudentDocument

# Aliases for cross-module compatibility
Attendance = AttendanceRecord
Payment = FeePayment
ExamQuestion = Question
ExamOption = QuestionOption

__all__ = [
    # User & Auth
    "User",
    "Role",
    "Permission",
    "RolePermission",
    # Academic Entities
    "Student",
    "Faculty",
    "Department",
    "AcademicYear",
    "Semester",
    "Subject",
    # Classes & Enrollment
    "ClassSection",
    "FacultyAssignment",
    "StudentEnrollment",
    # Attendance
    "AttendanceSession",
    "AttendanceRecord",
    # Examination
    "Exam",
    "Question",
    "QuestionOption",
    "ExamAttempt",
    "AttemptAnswer",
    # Results & Fees
    "Result",
    "FeeRecord",
    "FeePayment",
    # Assignments & Materials
    "Assignment",
    "AssignmentSubmission",
    "StudyMaterial",
    # Misc
    "Notification",
    "AuditLog",
    "StudentDocument",
]
