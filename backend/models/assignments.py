# models/assignments.py
from datetime import datetime
from extensions import db


class Assignment(db.Model):
    """Assignments created by Faculty or Admin for specific classes and subjects."""

    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject_id = db.Column(
        db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    class_section_id = db.Column(
        db.Integer, db.ForeignKey("class_sections.id", ondelete="CASCADE"), nullable=False
    )
    faculty_id = db.Column(
        db.Integer, db.ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False
    )

    due_date = db.Column(db.DateTime, nullable=False)
    max_marks = db.Column(db.Integer, nullable=False, default=100)
    instructions = db.Column(db.Text, nullable=True)

    file_key = db.Column(db.String(512), nullable=True)  # S3 Key for attachment
    file_name = db.Column(db.String(255), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)

    status = db.Column(
        db.Enum("draft", "published", "closed", name="assignment_status_enum"),
        default="published",
        nullable=False,
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete

    # Relationships
    subject = db.relationship("Subject")
    class_section = db.relationship("ClassSection")
    faculty = db.relationship("Faculty")
    submissions = db.relationship(
        "AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "subject_id": self.subject_id,
            "subject_name": self.subject.subject_name if self.subject else None,
            "class_section_id": self.class_section_id,
            "class_section_name": self.class_section.section_name if self.class_section else None,
            "faculty_name": self.faculty.user.get_full_name() if self.faculty and self.faculty.user else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "max_marks": self.max_marks,
            "file_key": self.file_key,
            "file_name": self.file_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AssignmentSubmission(db.Model):
    """Submissions uploaded by students in response to an Assignment."""

    __tablename__ = "assignment_submissions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False
    )
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )

    file_key = db.Column(db.String(512), nullable=False)  # S3 Key for student work
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)

    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    marks_obtained = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)

    submission_status = db.Column(
        db.Enum("submitted", "late", "graded", name="submission_status_enum"),
        default="submitted",
        nullable=False,
    )
    graded_by_faculty_id = db.Column(
        db.Integer, db.ForeignKey("faculty.id", ondelete="SET NULL"), nullable=True
    )
    graded_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student"),
    )

    # Relationships
    assignment = db.relationship("Assignment", back_populates="submissions")
    student = db.relationship("Student")
    graded_by = db.relationship("Faculty")

    def to_dict(self):
        return {
            "id": self.id,
            "assignment_id": self.assignment_id,
            "student_id": self.student_id,
            "student_name": self.student.user.get_full_name() if self.student and self.student.user else None,
            "student_roll": self.student.student_roll_number if self.student else None,
            "file_key": self.file_key,
            "file_name": self.file_name,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "marks_obtained": self.marks_obtained,
            "feedback": self.feedback,
            "submission_status": self.submission_status,
        }


class StudyMaterial(db.Model):
    """Course syllabus, notes, lectures, and resources uploaded to S3."""

    __tablename__ = "study_materials"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject_id = db.Column(
        db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    class_section_id = db.Column(
        db.Integer, db.ForeignKey("class_sections.id", ondelete="SET NULL"), nullable=True
    )
    faculty_id = db.Column(
        db.Integer, db.ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False
    )

    file_key = db.Column(db.String(512), nullable=False)  # S3 Key
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    file_type = db.Column(db.String(50), nullable=True)

    material_type = db.Column(
        db.Enum("notes", "video_link", "reference", "question_bank", "syllabus", name="material_type_enum"),
        default="notes",
        nullable=False,
    )
    is_visible = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    subject = db.relationship("Subject")
    class_section = db.relationship("ClassSection")
    faculty = db.relationship("Faculty")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "subject_id": self.subject_id,
            "subject_name": self.subject.subject_name if self.subject else None,
            "faculty_name": self.faculty.user.get_full_name() if self.faculty and self.faculty.user else None,
            "file_key": self.file_key,
            "file_name": self.file_name,
            "material_type": self.material_type,
            "is_visible": self.is_visible,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
