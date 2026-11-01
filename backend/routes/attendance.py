"""
Attendance REST API routes.
"""

from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models.attendance import AttendanceSession, AttendanceRecord
from services.attendance_service import AttendanceService
from security.decorators import role_required

attendance_bp = Blueprint("attendance_bp", __name__, url_prefix="/attendance")


@attendance_bp.route("/sessions", methods=["GET"])
@login_required
@role_required("admin", "faculty")
def list_sessions():
    subject_id = request.args.get("subject_id", type=int)
    class_id = request.args.get("class_section_id", type=int)

    query = AttendanceSession.query
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    if class_id:
        query = query.filter_by(class_section_id=class_id)

    sessions = query.order_by(AttendanceSession.session_date.desc()).limit(50).all()
    return jsonify({
        "success": True,
        "sessions": [
            {
                "id": s.id,
                "session_date": s.session_date.isoformat(),
                "session_type": s.session_type,
                "subject_name": s.subject.subject_name if s.subject else None,
                "class_section_name": s.class_section.section_name if s.class_section else None,
                "records_count": len(s.records),
            }
            for s in sessions
        ],
    })


@attendance_bp.route("/sessions/create", methods=["POST"])
@login_required
@role_required("admin", "faculty")
def create_session():
    data = request.get_json() or {}
    subject_id = data.get("subject_id")
    class_section_id = data.get("class_section_id")
    date_str = data.get("session_date")
    session_type = data.get("session_type", "lecture")

    if not all([subject_id, class_section_id, date_str]):
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    faculty_id = current_user.faculty_profile.id if current_user.faculty_profile else None
    session_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    session = AttendanceService.create_session(
        subject_id=subject_id,
        class_section_id=class_section_id,
        faculty_id=faculty_id,
        session_date=session_date,
        session_type=session_type,
        notes=data.get("notes"),
    )

    return jsonify({"success": True, "session_id": session.id})


@attendance_bp.route("/sessions/<int:session_id>/records", methods=["GET"])
@login_required
@role_required("admin", "faculty")
def get_session_records(session_id: int):
    session = AttendanceSession.query.get_or_404(session_id)
    records = AttendanceRecord.query.filter_by(session_id=session_id).all()
    return jsonify({
        "success": True,
        "records": [
            {
                "id": r.id,
                "student_id": r.student_id,
                "student_name": r.student.user.get_full_name() if r.student and r.student.user else "N/A",
                "roll_number": r.student.student_roll_number if r.student else None,
                "status": r.status,
                "remarks": r.remarks,
            }
            for r in records
        ],
    })


@attendance_bp.route("/records/<int:record_id>", methods=["PUT"])
@login_required
@role_required("admin", "faculty")
def update_record(record_id: int):
    record = AttendanceRecord.query.get_or_404(record_id)
    data = request.get_json() or {}
    new_status = data.get("status")

    if new_status in ("Present", "Absent", "Late", "Leave"):
        record.status = new_status
        if "remarks" in data:
            record.remarks = data["remarks"]
        db.session.commit()
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Invalid status."}), 400


@attendance_bp.route("/report/student/<int:student_id>", methods=["GET"])
@login_required
def student_report(student_id: int):
    # Student can only view their own; admin & faculty can view any
    if current_user.role.name == "student" and (not current_user.student_profile or current_user.student_profile.id != student_id):
        return jsonify({"success": False, "message": "Access denied."}), 403

    subject_id = request.args.get("subject_id", type=int)
    stats = AttendanceService.calculate_attendance_percentage(student_id, subject_id=subject_id)
    return jsonify({"success": True, "report": stats})


@attendance_bp.route("/report/class/<int:class_section_id>", methods=["GET"])
@login_required
@role_required("admin", "faculty")
def class_report(class_section_id: int):
    subject_id = request.args.get("subject_id", type=int)
    report = AttendanceService.get_class_attendance_report(class_section_id, subject_id=subject_id)
    return jsonify({"success": True, "report": report})
