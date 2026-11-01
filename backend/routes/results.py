"""
Results REST API routes.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models.results import Result
from services.result_service import ResultService
from security.decorators import role_required

results_bp = Blueprint("results_bp", __name__, url_prefix="/results")


@results_bp.route("/student/<int:student_id>", methods=["GET"])
@login_required
def student_results(student_id: int):
    if current_user.role.name == "student" and (not current_user.student_profile or current_user.student_profile.id != student_id):
        return jsonify({"success": False, "message": "Access denied."}), 403

    semester_id = request.args.get("semester_id", type=int)
    summary = ResultService.get_student_academic_summary(student_id, semester_id=semester_id)
    return jsonify({"success": True, "academic_summary": summary})


@results_bp.route("/class/<int:class_section_id>/semester/<int:semester_id>", methods=["GET"])
@login_required
@role_required("admin", "faculty")
def class_results(class_section_id: int, semester_id: int):
    results = (
        Result.query.filter_by(semester_id=semester_id)
        .join(Result.student)
        .filter_by(current_class_section_id=class_section_id)
        .all()
    )
    return jsonify({
        "success": True,
        "results": [r.to_dict() for r in results],
    })


@results_bp.route("/publish", methods=["POST"])
@login_required
@role_required("admin", "faculty")
def publish():
    data = request.get_json() or {}
    semester_id = data.get("semester_id")
    subject_id = data.get("subject_id")
    academic_year_id = data.get("academic_year_id")

    if not semester_id:
        return jsonify({"success": False, "message": "semester_id is required."}), 400

    published_count = ResultService.publish_results(
        semester_id=semester_id,
        subject_id=subject_id,
        academic_year_id=academic_year_id,
    )

    return jsonify({"success": True, "published_count": published_count})
