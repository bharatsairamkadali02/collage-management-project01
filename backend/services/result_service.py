"""
services/result_service.py - Academic marks calculation, grading, and transcript compilation.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from extensions import db
from models.results import Result
from models.subject import Subject
from models.student import Student

logger = logging.getLogger(__name__)


class ResultService:
    """Service handling internal/external marks entry, grading algorithm, and publishing."""

    GRADE_SCALE = [
        (90.0, "O", 10.0),   # Outstanding
        (80.0, "A+", 9.0),   # Excellent
        (70.0, "A", 8.0),    # Very Good
        (60.0, "B+", 7.0),   # Good
        (50.0, "B", 6.0),    # Above Average
        (40.0, "C", 5.0),    # Average
        (35.0, "D", 4.0),    # Pass
        (0.0, "F", 0.0),     # Fail
    ]

    @classmethod
    def calculate_grade(cls, percentage: float) -> str:
        """Determine letter grade according to percentage."""
        for threshold, letter, _ in cls.GRADE_SCALE:
            if percentage >= threshold:
                return letter
        return "F"

    @classmethod
    def add_or_update_marks(
        cls,
        student_id: int,
        subject_id: int,
        semester_id: int,
        academic_year_id: int,
        internal_marks: float = 0.0,
        external_marks: float = 0.0,
        practical_marks: float = 0.0,
        faculty_id: Optional[int] = None,
        remarks: Optional[str] = None,
    ) -> Result:
        """Upsert marks for a student's subject in a given semester and calculate grade."""
        subject = Subject.query.get(subject_id)
        if not subject:
            raise ValueError("Subject not found.")

        max_internal = subject.max_internal_marks or 40.0
        max_external = subject.max_external_marks or 60.0
        max_practical = subject.max_practical_marks or 0.0
        max_total = max_internal + max_external + max_practical

        total_obtained = float(internal_marks) + float(external_marks) + float(practical_marks)
        percentage = round((total_obtained / max_total * 100.0), 2) if max_total > 0 else 0.0
        grade = cls.calculate_grade(percentage)
        is_passed = percentage >= 35.0 and float(external_marks) >= (max_external * 0.35)

        result = Result.query.filter_by(
            student_id=student_id,
            subject_id=subject_id,
            semester_id=semester_id,
            academic_year_id=academic_year_id,
        ).first()

        if not result:
            result = Result(
                student_id=student_id,
                subject_id=subject_id,
                semester_id=semester_id,
                academic_year_id=academic_year_id,
            )
            db.session.add(result)

        result.internal_marks = internal_marks
        result.external_marks = external_marks
        result.practical_marks = practical_marks
        result.total_marks = total_obtained
        result.max_total_marks = max_total
        result.percentage = percentage
        result.grade = grade
        result.is_passed = is_passed
        result.result_status = "pass" if is_passed else "fail"
        result.remarks = remarks
        result.entered_by_faculty_id = faculty_id
        result.updated_at = datetime.utcnow()

        db.session.commit()
        return result

    @staticmethod
    def publish_results(semester_id: int, subject_id: Optional[int] = None, academic_year_id: Optional[int] = None) -> int:
        """Publish draft results making them visible to students."""
        query = Result.query.filter_by(semester_id=semester_id, is_published=False)
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        if academic_year_id:
            query = query.filter_by(academic_year_id=academic_year_id)

        results = query.all()
        now = datetime.utcnow()
        for r in results:
            r.is_published = True
            r.published_at = now

        db.session.commit()
        return len(results)

    @classmethod
    def get_student_academic_summary(cls, student_id: int, semester_id: Optional[int] = None) -> Dict[str, Any]:
        """Aggregate student marks, compute SGPA/CGPA, total credits, and overall status."""
        query = Result.query.filter_by(student_id=student_id, is_published=True)
        if semester_id:
            query = query.filter_by(semester_id=semester_id)

        results = query.all()
        if not results:
            return {
                "total_subjects": 0,
                "total_marks": 0.0,
                "max_marks": 0.0,
                "percentage": 0.0,
                "overall_grade": "N/A",
                "all_passed": True,
                "results": [],
            }

        total_marks = sum(r.total_marks or 0.0 for r in results)
        max_marks = sum(r.max_total_marks or 100.0 for r in results)
        overall_pct = round((total_marks / max_marks * 100.0), 2) if max_marks > 0 else 0.0
        all_passed = all(r.is_passed for r in results)

        return {
            "total_subjects": len(results),
            "total_marks": total_marks,
            "max_marks": max_marks,
            "percentage": overall_pct,
            "overall_grade": cls.calculate_grade(overall_pct),
            "all_passed": all_passed,
            "results": [r.to_dict() for r in results],
        }
