"""
Examinations REST API routes.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models.examination import Exam, Question, QuestionOption, ExamAttempt
from security.decorators import role_required

exam_bp = Blueprint("exam_bp", __name__, url_prefix="/exam")


@exam_bp.route("/list", methods=["GET"])
@login_required
def list_exams():
    query = Exam.query.filter(Exam.deleted_at.is_(None))
    if current_user.role.name == "student":
        student = current_user.student_profile
        if not student:
            return jsonify({"success": False, "exams": []})
        query = query.filter_by(class_section_id=student.current_class_section_id)
        query = query.filter(Exam.status.in_(["published", "active"]))

    exams = query.order_by(Exam.start_time.desc()).all()
    return jsonify({
        "success": True,
        "exams": [
            {
                "id": e.id,
                "title": e.title,
                "subject_name": e.subject.subject_name if e.subject else None,
                "duration_minutes": e.duration_minutes,
                "total_marks": e.total_marks,
                "start_time": e.start_time.isoformat() if e.start_time else None,
                "end_time": e.end_time.isoformat() if e.end_time else None,
                "status": e.status,
            }
            for e in exams
        ],
    })


@exam_bp.route("/<int:exam_id>/details", methods=["GET"])
@login_required
def exam_details(exam_id: int):
    exam = Exam.query.get_or_404(exam_id)
    return jsonify({
        "success": True,
        "exam": {
            "id": exam.id,
            "title": exam.title,
            "description": exam.description,
            "instructions": exam.instructions,
            "duration_minutes": exam.duration_minutes,
            "total_marks": exam.total_marks,
            "passing_marks": exam.passing_marks,
            "status": exam.status,
            "questions_count": len(exam.questions),
        },
    })


@exam_bp.route("/<int:exam_id>/questions", methods=["GET"])
@login_required
@role_required("admin", "faculty")
def exam_questions_admin(exam_id: int):
    exam = Exam.query.get_or_404(exam_id)
    return jsonify({
        "success": True,
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "marks": q.marks,
                "options": [
                    {
                        "id": opt.id,
                        "option_text": opt.option_text,
                        "is_correct": opt.is_correct,
                    }
                    for opt in q.options
                ],
            }
            for q in exam.questions
        ],
    })


@exam_bp.route("/<int:exam_id>/results", methods=["GET"])
@login_required
@role_required("admin", "faculty")
def exam_results(exam_id: int):
    exam = Exam.query.get_or_404(exam_id)
    attempts = ExamAttempt.query.filter_by(exam_id=exam.id).all()
    return jsonify({
        "success": True,
        "attempts": [
            {
                "id": a.id,
                "student_name": a.student.user.get_full_name() if a.student and a.student.user else "N/A",
                "roll_number": a.student.student_roll_number if a.student else None,
                "score": a.score_obtained,
                "total": a.total_marks_attempted,
                "percentage": a.percentage,
                "is_passed": a.is_passed,
                "status": a.status,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
            }
            for a in attempts
        ],
    })
