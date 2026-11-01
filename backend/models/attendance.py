# models/attendance.py
from datetime import datetime
from extensions import db


class AttendanceSession(db.Model):
    """A single teaching session for which attendance is recorded."""

    __tablename__ = "attendance_sessions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
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
    faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_date = db.Column(db.Date, nullable=False)
    session_type = db.Column(
        db.String(20), default="lecture", nullable=False
    )  # lecture / lab / tutorial
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    academic_year_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
    )
    semester_id = db.Column(
        db.Integer,
        db.ForeignKey("semesters.id", ondelete="CASCADE"),
        nullable=False,
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    subject = db.relationship("Subject", back_populates="attendance_sessions")
    class_section = db.relationship(
        "ClassSection", back_populates="attendance_sessions"
    )
    faculty = db.relationship("Faculty", back_populates="attendance_sessions")
    academic_year = db.relationship("AcademicYear", back_populates="attendance_sessions")
    semester = db.relationship("Semester", back_populates="attendance_sessions")
    records = db.relationship(
        "AttendanceRecord",
        back_populates="session",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "subject_id",
            "class_section_id",
            "session_date",
            "session_type",
            name="uq_attendance_session",
        ),
    )

    def __repr__(self):
        return (
            f"<AttendanceSession id={self.id} subject_id={self.subject_id} "
            f"date={self.session_date}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "class_section_id": self.class_section_id,
            "faculty_id": self.faculty_id,
            "session_date": (
                self.session_date.isoformat() if self.session_date else None
            ),
            "session_type": self.session_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "academic_year_id": self.academic_year_id,
            "semester_id": self.semester_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AttendanceRecord(db.Model):
    """Attendance status of a single student for a given session."""

    __tablename__ = "attendance_records"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("attendance_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    # status: Present / Absent / Late / Leave
    status = db.Column(db.String(10), nullable=False, default="Absent")
    remarks = db.Column(db.String(255), nullable=True)
    marked_by_faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    session = db.relationship("AttendanceSession", back_populates="records")
    student = db.relationship("Student", back_populates="attendance_records")
    marked_by_faculty = db.relationship(
        "Faculty", back_populates="attendance_records_marked"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "session_id", "student_id", name="uq_attendance_record"
        ),
        db.Index("ix_attendance_records_student_session", "student_id", "session_id"),
    )

    def __repr__(self):
        return (
            f"<AttendanceRecord id={self.id} student_id={self.student_id} "
            f"session_id={self.session_id} status='{self.status}'>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "student_id": self.student_id,
            "status": self.status,
            "remarks": self.remarks,
            "marked_by_faculty_id": self.marked_by_faculty_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
