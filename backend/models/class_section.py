# models/class_section.py
from datetime import datetime, date
from extensions import db


class ClassSection(db.Model):
    """A class section groups students who share the same timetable."""

    __tablename__ = "class_sections"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    section_name = db.Column(db.String(30), nullable=False)  # e.g. "CS-A"
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
    academic_year_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
    )
    max_students = db.Column(db.Integer, default=60, nullable=False)
    room_number = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    department = db.relationship("Department", back_populates="class_sections")
    semester = db.relationship("Semester", back_populates="class_sections")
    academic_year = db.relationship("AcademicYear", back_populates="class_sections")

    faculty_assignments = db.relationship(
        "FacultyAssignment", back_populates="class_section", lazy="dynamic"
    )
    enrollments = db.relationship(
        "StudentEnrollment",
        back_populates="class_section",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    attendance_sessions = db.relationship(
        "AttendanceSession", back_populates="class_section", lazy="dynamic"
    )
    exams = db.relationship("Exam", back_populates="class_section", lazy="dynamic")
    assignments = db.relationship(
        "Assignment", back_populates="class_section", lazy="dynamic"
    )
    study_materials = db.relationship(
        "StudyMaterial", back_populates="class_section", lazy="dynamic"
    )
    targeted_notifications = db.relationship(
        "Notification", back_populates="target_class_section", lazy="dynamic"
    )

    # Students currently enrolled in THIS section (convenience)
    current_students = db.relationship(
        "Student",
        foreign_keys="Student.current_class_section_id",
        back_populates="current_class_section",
        lazy="dynamic",
    )

    def __repr__(self):
        return (
            f"<ClassSection id={self.id} name='{self.section_name}' "
            f"semester_id={self.semester_id}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "section_name": self.section_name,
            "department_id": self.department_id,
            "semester_id": self.semester_id,
            "academic_year_id": self.academic_year_id,
            "max_students": self.max_students,
            "room_number": self.room_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FacultyAssignment(db.Model):
    """Links a faculty member to a subject and class section for a given year."""

    __tablename__ = "faculty_assignments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    class_section_id = db.Column(
        db.Integer,
        db.ForeignKey("class_sections.id", ondelete="CASCADE"),
        nullable=False,
    )
    academic_year_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_date = db.Column(db.Date, default=date.today, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    faculty = db.relationship("Faculty", back_populates="assignments")
    subject = db.relationship("Subject", back_populates="faculty_assignments")
    class_section = db.relationship("ClassSection", back_populates="faculty_assignments")
    academic_year = db.relationship("AcademicYear", back_populates="faculty_assignments")

    __table_args__ = (
        db.UniqueConstraint(
            "faculty_id",
            "subject_id",
            "class_section_id",
            "academic_year_id",
            name="uq_faculty_assignment",
        ),
    )

    def __repr__(self):
        return (
            f"<FacultyAssignment id={self.id} faculty_id={self.faculty_id} "
            f"subject_id={self.subject_id} section_id={self.class_section_id}>"
        )


class StudentEnrollment(db.Model):
    """Records that a student is enrolled in a class section for an academic year."""

    __tablename__ = "student_enrollments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    class_section_id = db.Column(
        db.Integer,
        db.ForeignKey("class_sections.id", ondelete="CASCADE"),
        nullable=False,
    )
    academic_year_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
    )
    enrollment_date = db.Column(db.Date, default=date.today, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    student = db.relationship("Student", back_populates="enrollments")
    class_section = db.relationship("ClassSection", back_populates="enrollments")
    academic_year = db.relationship("AcademicYear", back_populates="student_enrollments")

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "class_section_id",
            "academic_year_id",
            name="uq_student_enrollment",
        ),
    )

    def __repr__(self):
        return (
            f"<StudentEnrollment id={self.id} student_id={self.student_id} "
            f"section_id={self.class_section_id}>"
        )
