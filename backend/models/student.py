# models/student.py
from datetime import datetime
from extensions import db


class Student(db.Model):
    """Student profile linked to a User account."""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    student_roll_number = db.Column(
        db.String(30), unique=True, nullable=False, index=True
    )
    registration_number = db.Column(db.String(50), unique=True, nullable=False)

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_semester_id = db.Column(
        db.Integer,
        db.ForeignKey("semesters.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_class_section_id = db.Column(
        db.Integer,
        db.ForeignKey("class_sections.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Personal details
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)  # M / F / Other
    blood_group = db.Column(db.String(5), nullable=True)

    # Contact / address
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(60), nullable=True)
    state = db.Column(db.String(60), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)
    country = db.Column(db.String(60), default="India", nullable=True)

    # Guardian info
    guardian_name = db.Column(db.String(100), nullable=True)
    guardian_phone = db.Column(db.String(20), nullable=True)
    guardian_email = db.Column(db.String(120), nullable=True)
    guardian_relation = db.Column(db.String(30), nullable=True)

    # Academic
    admission_date = db.Column(db.Date, nullable=True)
    academic_status = db.Column(
        db.String(20), default="active", nullable=False
    )  # active / suspended / graduated / dropped
    profile_photo_key = db.Column(db.String(512), nullable=True)  # S3 key

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    user = db.relationship("User", back_populates="student_profile")
    department = db.relationship(
        "Department",
        foreign_keys=[department_id],
        back_populates="students",
    )
    current_semester = db.relationship(
        "Semester",
        foreign_keys=[current_semester_id],
        back_populates="students_current",
    )
    current_class_section = db.relationship(
        "ClassSection",
        foreign_keys=[current_class_section_id],
        back_populates="current_students",
    )
    enrollments = db.relationship(
        "StudentEnrollment",
        back_populates="student",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    attendance_records = db.relationship(
        "AttendanceRecord",
        back_populates="student",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    exam_attempts = db.relationship(
        "ExamAttempt",
        back_populates="student",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    results = db.relationship(
        "Result",
        back_populates="student",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    fee_records = db.relationship(
        "FeeRecord",
        back_populates="student",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    assignment_submissions = db.relationship(
        "AssignmentSubmission",
        back_populates="student",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    documents = db.relationship(
        "StudentDocument",
        back_populates="student",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    notifications = db.relationship(
        "Notification",
        foreign_keys="Notification.target_user_id",
        primaryjoin="Notification.target_user_id == Student.user_id",
        lazy="dynamic",
        viewonly=True,
    )

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def get_attendance_percentage(self, subject_id: int | None = None) -> float:
        """
        Calculate the overall attendance percentage for this student.
        If *subject_id* is provided, filter to that subject only.
        Returns a float between 0.0 and 100.0.
        """
        from .attendance import AttendanceRecord, AttendanceSession

        query = (
            db.session.query(AttendanceRecord)
            .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
            .filter(AttendanceRecord.student_id == self.id)
        )
        if subject_id is not None:
            query = query.filter(AttendanceSession.subject_id == subject_id)

        records = query.all()
        if not records:
            return 0.0

        present_count = sum(
            1 for r in records if r.status in ("Present", "Late")
        )
        return round((present_count / len(records)) * 100, 2)

    def to_dict(self) -> dict:
        user_data = self.user.to_dict() if self.user else {}
        return {
            "id": self.id,
            "user_id": self.user_id,
            "student_roll_number": self.student_roll_number,
            "registration_number": self.registration_number,
            "department_id": self.department_id,
            "current_semester_id": self.current_semester_id,
            "current_class_section_id": self.current_class_section_id,
            "date_of_birth": (
                self.date_of_birth.isoformat() if self.date_of_birth else None
            ),
            "gender": self.gender,
            "blood_group": self.blood_group,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "pincode": self.pincode,
            "country": self.country,
            "guardian_name": self.guardian_name,
            "guardian_phone": self.guardian_phone,
            "guardian_email": self.guardian_email,
            "guardian_relation": self.guardian_relation,
            "admission_date": (
                self.admission_date.isoformat() if self.admission_date else None
            ),
            "academic_status": self.academic_status,
            "profile_photo_key": self.profile_photo_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            **user_data,
        }

    def __repr__(self):
        return (
            f"<Student id={self.id} roll='{self.student_roll_number}' "
            f"user_id={self.user_id}>"
        )
