# models/faculty.py
from datetime import datetime
from extensions import db


class Faculty(db.Model):
    """Faculty / staff member profile linked to a User account."""

    __tablename__ = "faculty"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    employee_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    designation = db.Column(db.String(80), nullable=True)       # e.g. "Associate Professor"
    specialization = db.Column(db.String(120), nullable=True)
    qualification = db.Column(db.String(120), nullable=True)
    date_of_joining = db.Column(db.Date, nullable=True)
    employment_type = db.Column(
        db.String(20), default="full-time", nullable=False
    )  # full-time / part-time / visiting
    experience_years = db.Column(db.Float, default=0.0, nullable=True)
    profile_photo_key = db.Column(db.String(512), nullable=True)  # S3 object key
    is_hod = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = db.relationship("User", back_populates="faculty_profile")
    department = db.relationship(
        "Department",
        foreign_keys=[department_id],
        back_populates="faculty_members",
    )
    # Back-reference for the department this faculty is HoD of
    hod_department = db.relationship(
        "Department",
        foreign_keys="Department.hod_faculty_id",
        back_populates="hod",
        uselist=False,
    )
    assignments = db.relationship(
        "FacultyAssignment", back_populates="faculty", lazy="dynamic"
    )
    attendance_sessions = db.relationship(
        "AttendanceSession", back_populates="faculty", lazy="dynamic"
    )
    attendance_records_marked = db.relationship(
        "AttendanceRecord",
        foreign_keys="AttendanceRecord.marked_by_faculty_id",
        back_populates="marked_by_faculty",
        lazy="dynamic",
    )
    exams_created = db.relationship(
        "Exam", back_populates="created_by_faculty", lazy="dynamic"
    )
    results_entered = db.relationship(
        "Result", back_populates="entered_by_faculty", lazy="dynamic"
    )
    assignments_given = db.relationship(
        "Assignment", back_populates="faculty", lazy="dynamic"
    )
    submissions_graded = db.relationship(
        "AssignmentSubmission",
        foreign_keys="AssignmentSubmission.graded_by_faculty_id",
        back_populates="graded_by_faculty",
        lazy="dynamic",
    )
    study_materials = db.relationship(
        "StudyMaterial", back_populates="faculty", lazy="dynamic"
    )

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def get_assigned_subjects(self) -> list:
        """Return a list of active Subject objects assigned to this faculty."""
        from .class_section import FacultyAssignment  # avoid circular at module load
        from .subject import Subject

        active_assignments = (
            FacultyAssignment.query.filter_by(faculty_id=self.id, is_active=True).all()
        )
        subjects = [a.subject for a in active_assignments if a.subject]
        # De-duplicate by id
        seen = set()
        unique_subjects = []
        for s in subjects:
            if s.id not in seen:
                seen.add(s.id)
                unique_subjects.append(s)
        return unique_subjects

    def to_dict(self) -> dict:
        user_data = self.user.to_dict() if self.user else {}
        return {
            "id": self.id,
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "department_id": self.department_id,
            "designation": self.designation,
            "specialization": self.specialization,
            "qualification": self.qualification,
            "date_of_joining": (
                self.date_of_joining.isoformat() if self.date_of_joining else None
            ),
            "employment_type": self.employment_type,
            "experience_years": self.experience_years,
            "profile_photo_key": self.profile_photo_key,
            "is_hod": self.is_hod,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            **user_data,
        }

    def __repr__(self):
        return (
            f"<Faculty id={self.id} employee_id='{self.employee_id}' "
            f"user_id={self.user_id}>"
        )
