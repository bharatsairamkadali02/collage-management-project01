"""
Student routes for the College Management System.
All routes require authentication + student role.
"""

import os
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
    abort,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import (
    User,
    Student,
    AttendanceRecord,
    AttendanceSession,
    Exam,
    ExamAttempt,
    AttemptAnswer,
    Question,
    QuestionOption,
    Result,
    FeeRecord,
    FeePayment,
    Assignment,
    AssignmentSubmission,
    StudyMaterial,
    Notification,
    StudentDocument,
)
from security.decorators import student_required
from services.s3_service import S3Service
from services.exam_service import ExamService
from services.attendance_service import AttendanceService
from services.result_service import ResultService

student_bp = Blueprint("student", __name__, url_prefix="/student")


def _get_current_student() -> Student:
    """Retrieve the Student profile of the logged-in user or abort 404."""
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        abort(404, description="Student profile not found.")
    return student


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@student_bp.route("/dashboard")
@login_required
@student_required
def dashboard():
    student = _get_current_student()

    # 1. Attendance Summary
    att_summary = AttendanceService.calculate_attendance_percentage(student.id)

    # 2. Upcoming Active Exams
    now = datetime.utcnow()
    upcoming_exams = (
        Exam.query.filter(
            Exam.class_section_id == student.current_class_section_id,
            Exam.status.in_(["published", "active"]),
            Exam.deleted_at.is_(None),
        )
        .order_by(Exam.start_time.asc())
        .limit(5)
        .all()
    )

    # 3. Latest Results
    latest_results = (
        Result.query.filter_by(student_id=student.id, is_published=True)
        .order_by(Result.updated_at.desc())
        .limit(6)
        .all()
    )

    # 4. Pending Assignments
    submitted_assignment_ids = (
        db.session.query(AssignmentSubmission.assignment_id)
        .filter(AssignmentSubmission.student_id == student.id)
        .subquery()
    )
    pending_assignments = (
        Assignment.query.filter(
            Assignment.class_section_id == student.current_class_section_id,
            Assignment.status == "published",
            Assignment.due_date >= now,
            ~Assignment.id.in_(submitted_assignment_ids),
        )
        .order_by(Assignment.due_date.asc())
        .limit(5)
        .all()
    )

    # 5. Fee Status
    fees = FeeRecord.query.filter_by(student_id=student.id).all()
    total_fee = sum(float(f.total_amount or 0) for f in fees)
    paid_fee = sum(float(f.amount_paid or 0) for f in fees)
    fee_balance = max(0.0, total_fee - paid_fee)

    # 6. Recent Notifications
    notifications = (
        Notification.query.filter(
            (Notification.target_user_id == current_user.id)
            | (Notification.target_role.in_(["all", "student"]))
            | (Notification.target_class_section_id == student.current_class_section_id)
        )
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "student/dashboard.html",
        student=student,
        att_summary=att_summary,
        upcoming_exams=upcoming_exams,
        latest_results=latest_results,
        pending_assignments=pending_assignments,
        fee_balance=fee_balance,
        notifications=notifications,
    )


# ---------------------------------------------------------------------------
# Profile & Photo Upload
# ---------------------------------------------------------------------------
@student_bp.route("/profile")
@login_required
@student_required
def profile():
    student = _get_current_student()
    s3 = S3Service()
    photo_url = s3.generate_presigned_url(student.profile_photo_key) if student.profile_photo_key else None
    return render_template("student/profile.html", student=student, photo_url=photo_url)


@student_bp.route("/profile/upload-photo", methods=["POST"])
@login_required
@student_required
def upload_photo():
    student = _get_current_student()
    if "photo" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files["photo"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected"}), 400

    s3 = S3Service()
    try:
        key = s3.upload_student_photo(file, student.id)
        student.profile_photo_key = key
        current_user.profile_photo_key = key
        db.session.commit()
        url = s3.generate_presigned_url(key)
        return jsonify({"success": True, "message": "Photo uploaded successfully", "url": url})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------
@student_bp.route("/attendance")
@login_required
@student_required
def attendance():
    student = _get_current_student()
    summary = AttendanceService.calculate_attendance_percentage(student.id)

    # Subject-wise attendance
    records = (
        db.session.query(AttendanceRecord)
        .join(AttendanceSession)
        .filter(AttendanceRecord.student_id == student.id)
        .order_by(AttendanceSession.session_date.desc())
        .all()
    )

    # Group by subject
    subjects_map = {}
    for r in records:
        sub = r.session.subject
        if sub.id not in subjects_map:
            subjects_map[sub.id] = {
                "subject": sub,
                "total": 0,
                "present": 0,
                "absent": 0,
                "late": 0,
                "leave": 0,
                "records": [],
            }
        subjects_map[sub.id]["total"] += 1
        if r.status == "Present":
            subjects_map[sub.id]["present"] += 1
        elif r.status == "Late":
            subjects_map[sub.id]["late"] += 1
        elif r.status == "Absent":
            subjects_map[sub.id]["absent"] += 1
        elif r.status == "Leave":
            subjects_map[sub.id]["leave"] += 1
        subjects_map[sub.id]["records"].append(r)

    subject_stats = []
    for s_data in subjects_map.values():
        tot = s_data["total"]
        pct = round(((s_data["present"] + s_data["late"]) / tot * 100.0), 2) if tot > 0 else 0.0
        s_data["percentage"] = pct
        subject_stats.append(s_data)

    return render_template(
        "student/attendance.html",
        student=student,
        summary=summary,
        subject_stats=subject_stats,
    )


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@student_bp.route("/results")
@login_required
@student_required
def results():
    student = _get_current_student()
    summary = ResultService.get_student_academic_summary(student.id)

    # MCQ Exam past attempts
    attempts = (
        ExamAttempt.query.filter_by(student_id=student.id)
        .order_by(ExamAttempt.created_at.desc())
        .all()
    )

    return render_template(
        "student/results.html",
        student=student,
        summary=summary,
        attempts=attempts,
    )


# ---------------------------------------------------------------------------
# Examinations
# ---------------------------------------------------------------------------
@student_bp.route("/examinations")
@login_required
@student_required
def examinations():
    student = _get_current_student()
    now = datetime.utcnow()

    # Active / available exams
    available_exams = (
        Exam.query.filter(
            Exam.class_section_id == student.current_class_section_id,
            Exam.status.in_(["published", "active"]),
            Exam.deleted_at.is_(None),
            Exam.end_time >= now,
        )
        .order_by(Exam.start_time.asc())
        .all()
    )

    # Exam attempts history
    past_attempts = (
        ExamAttempt.query.filter_by(student_id=student.id)
        .order_by(ExamAttempt.created_at.desc())
        .all()
    )

    return render_template(
        "student/examinations.html",
        student=student,
        available_exams=available_exams,
        past_attempts=past_attempts,
        now=now,
    )


@student_bp.route("/examinations/<int:exam_id>/take")
@login_required
@student_required
def take_exam(exam_id: int):
    student = _get_current_student()
    exam = Exam.query.get_or_404(exam_id)

    # Check eligibility
    eligible, reason = ExamService.check_exam_eligibility(exam.id, student.id)
    if not eligible:
        flash(reason, "danger")
        return redirect(url_for("student.examinations"))

    # Start or resume attempt
    attempt, msg = ExamService.start_attempt(exam.id, student.id, request.remote_addr)
    if not attempt:
        flash(msg, "danger")
        return redirect(url_for("student.examinations"))

    questions = ExamService.get_exam_questions_for_student(exam.id, shuffle=exam.shuffle_questions)

    # Calculate remaining time in seconds
    now = datetime.utcnow()
    elapsed_seconds = (now - attempt.started_at).total_seconds()
    total_seconds = exam.duration_minutes * 60
    remaining_seconds = max(0, int(total_seconds - elapsed_seconds))

    return render_template(
        "student/mcq_exam.html",
        student=student,
        exam=exam,
        attempt=attempt,
        questions=questions,
        remaining_seconds=remaining_seconds,
    )


@student_bp.route("/api/exam/<int:exam_id>/start", methods=["POST"])
@login_required
@student_required
def api_start_exam(exam_id: int):
    student = _get_current_student()
    attempt, msg = ExamService.start_attempt(exam_id, student.id, request.remote_addr)
    if not attempt:
        return jsonify({"success": False, "message": msg}), 400

    questions = ExamService.get_exam_questions_for_student(exam_id)
    return jsonify({
        "success": True,
        "attempt_id": attempt.id,
        "questions": questions,
        "duration_minutes": attempt.exam.duration_minutes,
    })


@student_bp.route("/api/exam/attempt/<int:attempt_id>/answer", methods=["POST"])
@login_required
@student_required
def api_save_answer(attempt_id: int):
    student = _get_current_student()
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != student.id:
        return jsonify({"success": False, "message": "Unauthorized attempt."}), 403

    data = request.get_json() or {}
    question_id = data.get("question_id")
    option_id = data.get("option_id")

    if not question_id:
        return jsonify({"success": False, "message": "question_id is required"}), 400

    try:
        ExamService.save_answer(attempt_id, question_id, option_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@student_bp.route("/api/exam/attempt/<int:attempt_id>/submit", methods=["POST"])
@login_required
@student_required
def api_submit_exam(attempt_id: int):
    student = _get_current_student()
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != student.id:
        return jsonify({"success": False, "message": "Unauthorized attempt."}), 403

    data = request.get_json() or {}
    is_auto = data.get("is_auto_submit", False)

    ExamService.submit_attempt(attempt_id, is_auto_submit=is_auto)

    return jsonify({
        "success": True,
        "message": "Exam submitted successfully.",
        "score": attempt.score_obtained,
        "percentage": attempt.percentage,
        "is_passed": attempt.is_passed,
    })


@student_bp.route("/api/exam/attempt/<int:attempt_id>/result")
@login_required
@student_required
def api_exam_result(attempt_id: int):
    student = _get_current_student()
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != student.id:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    return jsonify({
        "success": True,
        "exam_title": attempt.exam.title,
        "score": attempt.score_obtained,
        "total_marks": attempt.total_marks_attempted,
        "percentage": attempt.percentage,
        "is_passed": attempt.is_passed,
        "status": attempt.status,
    })


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------
@student_bp.route("/assignments")
@login_required
@student_required
def assignments():
    student = _get_current_student()
    assignments_list = (
        Assignment.query.filter_by(
            class_section_id=student.current_class_section_id, status="published"
        )
        .order_by(Assignment.due_date.asc())
        .all()
    )

    # Map student's submissions
    submissions = {
        s.assignment_id: s
        for s in AssignmentSubmission.query.filter_by(student_id=student.id).all()
    }

    return render_template(
        "student/assignments.html",
        student=student,
        assignments=assignments_list,
        submissions=submissions,
        now=datetime.utcnow(),
    )


@student_bp.route("/assignments/<int:assignment_id>/submit", methods=["POST"])
@login_required
@student_required
def submit_assignment(assignment_id: int):
    student = _get_current_student()
    assignment = Assignment.query.get_or_404(assignment_id)

    if "file" not in request.files:
        flash("No file attached for submission.", "danger")
        return redirect(url_for("student.assignments"))

    file = request.files["file"]
    if file.filename == "":
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("student.assignments"))

    s3 = S3Service()
    try:
        key = s3.upload_assignment(file, assignment.id, file.filename)
        submission = AssignmentSubmission.query.filter_by(
            assignment_id=assignment.id, student_id=student.id
        ).first()

        now = datetime.utcnow()
        is_late = now > assignment.due_date

        if not submission:
            submission = AssignmentSubmission(
                assignment_id=assignment.id,
                student_id=student.id,
                file_key=key,
                file_name=file.filename,
                submitted_at=now,
                submission_status="late" if is_late else "submitted",
            )
            db.session.add(submission)
        else:
            submission.file_key = key
            submission.file_name = file.filename
            submission.submitted_at = now
            submission.submission_status = "late" if is_late else "submitted"

        db.session.commit()
        flash("Assignment submitted successfully!", "success")
    except Exception as e:
        flash(f"Upload failed: {str(e)}", "danger")

    return redirect(url_for("student.assignments"))


# ---------------------------------------------------------------------------
# Study Materials
# ---------------------------------------------------------------------------
@student_bp.route("/materials")
@login_required
@student_required
def materials():
    student = _get_current_student()
    materials_list = (
        StudyMaterial.query.filter(
            (StudyMaterial.class_section_id == student.current_class_section_id)
            | (StudyMaterial.class_section_id.is_(None)),
            StudyMaterial.is_visible.is_(True),
        )
        .order_by(StudyMaterial.created_at.desc())
        .all()
    )
    return render_template("student/materials.html", student=student, materials=materials_list)


@student_bp.route("/materials/<int:material_id>/download")
@login_required
@student_required
def download_material(material_id: int):
    material = StudyMaterial.query.get_or_404(material_id)
    s3 = S3Service()
    url = s3.generate_presigned_url(material.file_key, expiry=1800)
    if not url:
        return jsonify({"success": False, "message": "File could not be accessed."}), 404
    return jsonify({"success": True, "download_url": url})


# ---------------------------------------------------------------------------
# Fees
# ---------------------------------------------------------------------------
@student_bp.route("/fees")
@login_required
@student_required
def fees():
    student = _get_current_student()
    fee_records = (
        FeeRecord.query.filter_by(student_id=student.id)
        .order_by(FeeRecord.due_date.asc())
        .all()
    )

    total_due = sum(float(f.total_amount or 0) for f in fee_records)
    total_paid = sum(float(f.amount_paid or 0) for f in fee_records)
    total_balance = max(0.0, total_due - total_paid)

    return render_template(
        "student/fees.html",
        student=student,
        fee_records=fee_records,
        total_due=total_due,
        total_paid=total_paid,
        total_balance=total_balance,
    )


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
@student_bp.route("/notifications")
@login_required
@student_required
def notifications():
    student = _get_current_student()
    notifs = (
        Notification.query.filter(
            (Notification.target_user_id == current_user.id)
            | (Notification.target_role.in_(["all", "student"]))
            | (Notification.target_class_section_id == student.current_class_section_id)
        )
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template("student/notifications.html", student=student, notifications=notifs)
