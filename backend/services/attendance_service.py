"""
services/attendance_service.py - Attendance tracking and percentage calculation service.
"""

import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from extensions import db
from models.attendance import AttendanceSession, AttendanceRecord
from models.student import Student
from models.class_section import StudentEnrollment

logger = logging.getLogger(__name__)


class AttendanceService:
    """Service handling attendance sessions, marking, and analytical reports."""

    @staticmethod
    def create_session(
        subject_id: int,
        class_section_id: int,
        faculty_id: int,
        session_date: date,
        session_type: str = "lecture",
        start_time=None,
        end_time=None,
        notes: Optional[str] = None,
        academic_year_id: Optional[int] = None,
        semester_id: Optional[int] = None,
    ) -> AttendanceSession:
        """Create or retrieve an attendance session for a class, subject, and date."""
        session = AttendanceSession.query.filter_by(
            subject_id=subject_id,
            class_section_id=class_section_id,
            session_date=session_date,
            session_type=session_type,
        ).first()

        if session:
            return session

        session = AttendanceSession(
            subject_id=subject_id,
            class_section_id=class_section_id,
            faculty_id=faculty_id,
            session_date=session_date,
            session_type=session_type,
            start_time=start_time,
            end_time=end_time,
            notes=notes,
            academic_year_id=academic_year_id,
            semester_id=semester_id,
        )
        db.session.add(session)
        db.session.commit()
        return session

    @staticmethod
    def mark_attendance(
        session_id: int,
        student_id: int,
        status: str,
        faculty_id: Optional[int] = None,
        remarks: Optional[str] = None,
    ) -> AttendanceRecord:
        """Mark or update a student's attendance record in a session."""
        valid_statuses = {"Present", "Absent", "Late", "Leave"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of {valid_statuses}")

        record = AttendanceRecord.query.filter_by(
            session_id=session_id, student_id=student_id
        ).first()

        if record:
            record.status = status
            record.remarks = remarks
            if faculty_id:
                record.marked_by_faculty_id = faculty_id
            record.updated_at = datetime.utcnow()
        else:
            record = AttendanceRecord(
                session_id=session_id,
                student_id=student_id,
                status=status,
                remarks=remarks,
                marked_by_faculty_id=faculty_id,
            )
            db.session.add(record)

        db.session.commit()
        return record

    @classmethod
    def bulk_mark_attendance(
        cls,
        session_id: int,
        records_data: List[Dict[str, Any]],
        faculty_id: Optional[int] = None,
    ) -> int:
        """Mark attendance for multiple students simultaneously."""
        count = 0
        for item in records_data:
            student_id = item.get("student_id")
            status = item.get("status", "Present")
            remarks = item.get("remarks")
            if student_id:
                cls.mark_attendance(session_id, student_id, status, faculty_id, remarks)
                count += 1
        return count

    @staticmethod
    def calculate_attendance_percentage(
        student_id: int,
        subject_id: Optional[int] = None,
        semester_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculate total sessions, present, absent, late, leave and overall attendance percentage.
        Late counts as partial or present depending on college policy (counted here as present).
        """
        query = db.session.query(AttendanceRecord).join(AttendanceSession)
        query = query.filter(AttendanceRecord.student_id == student_id)

        if subject_id:
            query = query.filter(AttendanceSession.subject_id == subject_id)
        if semester_id:
            query = query.filter(AttendanceSession.semester_id == semester_id)

        records = query.all()
        total = len(records)
        if total == 0:
            return {
                "total": 0,
                "present": 0,
                "absent": 0,
                "late": 0,
                "leave": 0,
                "percentage": 0.0,
                "status": "No records",
            }

        present = sum(1 for r in records if r.status == "Present")
        late = sum(1 for r in records if r.status == "Late")
        absent = sum(1 for r in records if r.status == "Absent")
        leave = sum(1 for r in records if r.status == "Leave")

        # In standard academic rules: (Present + Late) / Total * 100
        effective_attended = present + late
        percentage = round((effective_attended / total) * 100.0, 2)

        return {
            "total": total,
            "present": present,
            "absent": absent,
            "late": late,
            "leave": leave,
            "percentage": percentage,
            "status": "Safe" if percentage >= 75.0 else ("Warning" if percentage >= 60.0 else "Critical"),
        }

    @staticmethod
    def get_class_attendance_report(
        class_section_id: int, subject_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get attendance summary for every student enrolled in a class section."""
        enrollments = StudentEnrollment.query.filter_by(
            class_section_id=class_section_id, is_active=True
        ).all()

        report = []
        for enr in enrollments:
            student = enr.student
            stats = AttendanceService.calculate_attendance_percentage(
                student.id, subject_id=subject_id
            )
            report.append({
                "student_id": student.id,
                "roll_number": student.student_roll_number,
                "name": student.user.get_full_name() if student.user else "N/A",
                **stats,
            })

        return sorted(report, key=lambda x: x["roll_number"] or "")
