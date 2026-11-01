# models/results.py
from datetime import datetime
from extensions import db


class Result(db.Model):
    """Final academic result of a student in a subject for a semester."""

    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    subject_id = db.Column(
        db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    semester_id = db.Column(
        db.Integer, db.ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False
    )
    academic_year_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Marks breakdown
    internal_marks = db.Column(db.Float, nullable=True, default=0.0)
    external_marks = db.Column(db.Float, nullable=True, default=0.0)
    practical_marks = db.Column(db.Float, nullable=True, default=0.0)
    total_marks = db.Column(db.Float, nullable=True)
    max_total_marks = db.Column(db.Float, nullable=True)
    percentage = db.Column(db.Float, nullable=True)
    grade = db.Column(db.String(5), nullable=True)  # O / A+ / A / B+ / B / C / F

    is_passed = db.Column(db.Boolean, nullable=True)
    # pass / fail / absent / withheld
    result_status = db.Column(db.String(20), default="pass", nullable=True)

    is_published = db.Column(db.Boolean, default=False, nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    entered_by_faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    student = db.relationship("Student", back_populates="results")
    subject = db.relationship("Subject", back_populates="results")
    semester = db.relationship("Semester", back_populates="results")
    academic_year = db.relationship("AcademicYear", back_populates="results")
    entered_by_faculty = db.relationship("Faculty", back_populates="results_entered")

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "subject_id",
            "semester_id",
            "academic_year_id",
            name="uq_result",
        ),
    )

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    _GRADE_THRESHOLDS = [
        (90, "O"),
        (80, "A+"),
        (70, "A"),
        (60, "B+"),
        (50, "B"),
        (40, "C"),
        (0, "F"),
    ]

    def calculate_grade(self) -> str:
        """Derive letter grade from percentage. Updates self.grade and returns it."""
        if self.percentage is None:
            self.grade = "NA"
            return self.grade
        for threshold, letter in self._GRADE_THRESHOLDS:
            if self.percentage >= threshold:
                self.grade = letter
                return letter
        self.grade = "F"
        return "F"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "subject_id": self.subject_id,
            "semester_id": self.semester_id,
            "academic_year_id": self.academic_year_id,
            "internal_marks": self.internal_marks,
            "external_marks": self.external_marks,
            "practical_marks": self.practical_marks,
            "total_marks": self.total_marks,
            "max_total_marks": self.max_total_marks,
            "percentage": self.percentage,
            "grade": self.grade,
            "is_passed": self.is_passed,
            "result_status": self.result_status,
            "is_published": self.is_published,
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "remarks": self.remarks,
            "entered_by_faculty_id": self.entered_by_faculty_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f"<Result id={self.id} student_id={self.student_id} "
            f"subject_id={self.subject_id} grade='{self.grade}'>"
        )
