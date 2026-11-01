# models/subject.py
from datetime import datetime
from extensions import db


class AcademicYear(db.Model):
    """Represents a single academic year, e.g. '2024-25'."""

    __tablename__ = "academic_years"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year_label = db.Column(db.String(20), unique=True, nullable=False)  # e.g. "2024-25"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    semesters = db.relationship("Semester", back_populates="academic_year", lazy="dynamic")
    class_sections = db.relationship(
        "ClassSection", back_populates="academic_year", lazy="dynamic"
    )
    faculty_assignments = db.relationship(
        "FacultyAssignment", back_populates="academic_year", lazy="dynamic"
    )
    student_enrollments = db.relationship(
        "StudentEnrollment", back_populates="academic_year", lazy="dynamic"
    )
    attendance_sessions = db.relationship(
        "AttendanceSession", back_populates="academic_year", lazy="dynamic"
    )
    exams = db.relationship("Exam", back_populates="academic_year", lazy="dynamic")
    results = db.relationship("Result", back_populates="academic_year", lazy="dynamic")
    fee_records = db.relationship(
        "FeeRecord", back_populates="academic_year", lazy="dynamic"
    )

    def __repr__(self):
        return f"<AcademicYear id={self.id} label='{self.year_label}'>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "year_label": self.year_label,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_current": self.is_current,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Semester(db.Model):
    """A semester within a particular academic year and department."""

    __tablename__ = "semesters"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    semester_number = db.Column(db.Integer, nullable=False)  # 1 – 8
    semester_name = db.Column(db.String(80), nullable=True)  # e.g. "Even / Odd"
    academic_year_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    academic_year = db.relationship("AcademicYear", back_populates="semesters")
    department = db.relationship("Department", back_populates="semesters")
    subjects = db.relationship("Subject", back_populates="semester", lazy="dynamic")
    class_sections = db.relationship(
        "ClassSection", back_populates="semester", lazy="dynamic"
    )
    attendance_sessions = db.relationship(
        "AttendanceSession", back_populates="semester", lazy="dynamic"
    )
    exams = db.relationship("Exam", back_populates="semester", lazy="dynamic")
    results = db.relationship("Result", back_populates="semester", lazy="dynamic")
    fee_records = db.relationship(
        "FeeRecord", back_populates="semester", lazy="dynamic"
    )
    students_current = db.relationship(
        "Student",
        foreign_keys="Student.current_semester_id",
        back_populates="current_semester",
        lazy="dynamic",
    )

    def __repr__(self):
        return (
            f"<Semester id={self.id} number={self.semester_number} "
            f"academic_year_id={self.academic_year_id}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "semester_number": self.semester_number,
            "semester_name": self.semester_name,
            "academic_year_id": self.academic_year_id,
            "department_id": self.department_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_current": self.is_current,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Subject(db.Model):
    """A subject/course taught within a department during a semester."""

    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject_name = db.Column(db.String(120), nullable=False)
    subject_code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
    )
    semester_id = db.Column(
        db.Integer,
        db.ForeignKey("semesters.id", ondelete="CASCADE"),
        nullable=False,
    )
    credits = db.Column(db.Integer, nullable=True)
    max_internal_marks = db.Column(db.Float, default=40.0, nullable=False)
    max_external_marks = db.Column(db.Float, default=60.0, nullable=False)
    max_practical_marks = db.Column(db.Float, default=0.0, nullable=False)
    subject_type = db.Column(
        db.String(20), default="theory", nullable=False
    )  # theory / practical / both
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    department = db.relationship("Department", back_populates="subjects")
    semester = db.relationship("Semester", back_populates="subjects")
    faculty_assignments = db.relationship(
        "FacultyAssignment", back_populates="subject", lazy="dynamic"
    )
    attendance_sessions = db.relationship(
        "AttendanceSession", back_populates="subject", lazy="dynamic"
    )
    exams = db.relationship("Exam", back_populates="subject", lazy="dynamic")
    results = db.relationship("Result", back_populates="subject", lazy="dynamic")
    assignments = db.relationship(
        "Assignment", back_populates="subject", lazy="dynamic"
    )
    study_materials = db.relationship(
        "StudyMaterial", back_populates="subject", lazy="dynamic"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject_name": self.subject_name,
            "subject_code": self.subject_code,
            "department_id": self.department_id,
            "semester_id": self.semester_id,
            "credits": self.credits,
            "max_internal_marks": self.max_internal_marks,
            "max_external_marks": self.max_external_marks,
            "max_practical_marks": self.max_practical_marks,
            "subject_type": self.subject_type,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Subject id={self.id} code='{self.subject_code}' name='{self.subject_name}'>"
