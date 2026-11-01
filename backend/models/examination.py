# models/examination.py
from datetime import datetime
from extensions import db


class Exam(db.Model):
    """An online exam or quiz created by faculty."""

    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    subject_id = db.Column(
        db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    class_section_id = db.Column(
        db.Integer,
        db.ForeignKey("class_sections.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.id", ondelete="SET NULL"),
        nullable=True,
    )
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

    exam_type = db.Column(db.String(20), default="MCQ", nullable=False)  # MCQ / descriptive
    duration_minutes = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)

    total_marks = db.Column(db.Float, nullable=False, default=0.0)
    passing_marks = db.Column(db.Float, nullable=True)
    max_attempts = db.Column(db.Integer, default=1, nullable=False)

    # draft / published / active / closed
    status = db.Column(db.String(20), default="draft", nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    shuffle_questions = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    deleted_at = db.Column(db.DateTime, nullable=True)  # soft delete

    # Relationships
    subject = db.relationship("Subject", back_populates="exams")
    class_section = db.relationship("ClassSection", back_populates="exams")
    created_by_faculty = db.relationship("Faculty", back_populates="exams_created")
    academic_year = db.relationship("AcademicYear", back_populates="exams")
    semester = db.relationship("Semester", back_populates="exams")

    questions = db.relationship(
        "Question",
        back_populates="exam",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    attempts = db.relationship(
        "ExamAttempt",
        back_populates="exam",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Exam id={self.id} title='{self.title}' status='{self.status}'>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "subject_id": self.subject_id,
            "class_section_id": self.class_section_id,
            "created_by_faculty_id": self.created_by_faculty_id,
            "academic_year_id": self.academic_year_id,
            "semester_id": self.semester_id,
            "exam_type": self.exam_type,
            "duration_minutes": self.duration_minutes,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_marks": self.total_marks,
            "passing_marks": self.passing_marks,
            "max_attempts": self.max_attempts,
            "status": self.status,
            "instructions": self.instructions,
            "shuffle_questions": self.shuffle_questions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Question(db.Model):
    """A single question belonging to an Exam."""

    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(
        db.Integer,
        db.ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(
        db.String(20), default="MCQ", nullable=False
    )  # MCQ / true_false
    marks = db.Column(db.Float, default=1.0, nullable=False)
    order_number = db.Column(db.Integer, nullable=True)
    explanation = db.Column(db.Text, nullable=True)  # Shown after result

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    exam = db.relationship("Exam", back_populates="questions")
    options = db.relationship(
        "QuestionOption",
        back_populates="question",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    attempt_answers = db.relationship(
        "AttemptAnswer", back_populates="question", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Question id={self.id} exam_id={self.exam_id} type='{self.question_type}'>"


class QuestionOption(db.Model):
    """One of the selectable options for a Question."""

    __tablename__ = "question_options"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    order_number = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    question = db.relationship("Question", back_populates="options")
    attempt_answers = db.relationship(
        "AttemptAnswer", back_populates="selected_option", lazy="dynamic"
    )

    def __repr__(self):
        return (
            f"<QuestionOption id={self.id} question_id={self.question_id} "
            f"is_correct={self.is_correct}>"
        )


class ExamAttempt(db.Model):
    """Tracks a student's single attempt at an Exam."""

    __tablename__ = "exam_attempts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exam_id = db.Column(
        db.Integer, db.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)
    time_taken_minutes = db.Column(db.Float, nullable=True)

    score_obtained = db.Column(db.Float, nullable=True)
    total_marks_attempted = db.Column(db.Float, nullable=True)
    percentage = db.Column(db.Float, nullable=True)
    is_passed = db.Column(db.Boolean, nullable=True)

    # in_progress / submitted / auto_submitted
    status = db.Column(db.String(20), default="in_progress", nullable=False)
    attempt_number = db.Column(db.Integer, default=1, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    exam = db.relationship("Exam", back_populates="attempts")
    student = db.relationship("Student", back_populates="exam_attempts")
    answers = db.relationship(
        "AttemptAnswer",
        back_populates="attempt",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "exam_id", "student_id", "attempt_number", name="uq_exam_attempt"
        ),
    )

    def __repr__(self):
        return (
            f"<ExamAttempt id={self.id} exam_id={self.exam_id} "
            f"student_id={self.student_id} attempt={self.attempt_number}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "exam_id": self.exam_id,
            "student_id": self.student_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "submitted_at": (
                self.submitted_at.isoformat() if self.submitted_at else None
            ),
            "time_taken_minutes": self.time_taken_minutes,
            "score_obtained": self.score_obtained,
            "total_marks_attempted": self.total_marks_attempted,
            "percentage": self.percentage,
            "is_passed": self.is_passed,
            "status": self.status,
            "attempt_number": self.attempt_number,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AttemptAnswer(db.Model):
    """Records the answer chosen by a student for one question in an attempt."""

    __tablename__ = "attempt_answers"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    attempt_id = db.Column(
        db.Integer,
        db.ForeignKey("exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    selected_option_id = db.Column(
        db.Integer,
        db.ForeignKey("question_options.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_correct = db.Column(db.Boolean, nullable=True)
    marks_obtained = db.Column(db.Float, default=0.0, nullable=True)
    answered_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    attempt = db.relationship("ExamAttempt", back_populates="answers")
    question = db.relationship("Question", back_populates="attempt_answers")
    selected_option = db.relationship("QuestionOption", back_populates="attempt_answers")

    def __repr__(self):
        return (
            f"<AttemptAnswer id={self.id} attempt_id={self.attempt_id} "
            f"question_id={self.question_id} correct={self.is_correct}>"
        )
