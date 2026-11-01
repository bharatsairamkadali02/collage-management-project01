# models/department.py
from datetime import datetime
from extensions import db


class Department(db.Model):
    """An academic department within the college."""

    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    department_name = db.Column(db.String(120), unique=True, nullable=False)
    department_code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Head of Department – set after faculty rows exist, so nullable
    hod_faculty_id = db.Column(
        db.Integer,
        db.ForeignKey("faculty.id", ondelete="SET NULL", use_alter=True, name="fk_dept_hod"),
        nullable=True,
    )

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    hod = db.relationship(
        "Faculty",
        foreign_keys=[hod_faculty_id],
        back_populates="hod_department",
        uselist=False,
    )
    faculty_members = db.relationship(
        "Faculty",
        foreign_keys="Faculty.department_id",
        back_populates="department",
        lazy="dynamic",
    )
    students = db.relationship(
        "Student",
        foreign_keys="Student.department_id",
        back_populates="department",
        lazy="dynamic",
    )
    subjects = db.relationship(
        "Subject", back_populates="department", lazy="dynamic"
    )
    class_sections = db.relationship(
        "ClassSection", back_populates="department", lazy="dynamic"
    )
    semesters = db.relationship(
        "Semester", back_populates="department", lazy="dynamic"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "department_name": self.department_name,
            "department_code": self.department_code,
            "description": self.description,
            "hod_faculty_id": self.hod_faculty_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f"<Department id={self.id} code='{self.department_code}' "
            f"name='{self.department_name}'>"
        )
