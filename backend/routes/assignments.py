"""
Assignments and Submissions REST API routes.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models.assignments import Assignment, AssignmentSubmission
from services.s3_service import S3Service
from security.decorators import role_required

assignments_bp = Blueprint("assignments_bp", __name__, url_prefix="/assignments")


@assignments_bp.route("/class/<int:class_section_id>", methods=["GET"])
@login_required
def class_assignments(class_section_id: int):
    assignments = (
        Assignment.query.filter_by(class_section_id=class_section_id, status="published")
        .order_by(Assignment.due_date.asc())
        .all()
    )
    return jsonify({
        "success": True,
        "assignments": [a.to_dict() for a in assignments],
    })


@assignments_bp.route("/<int:assignment_id>/download", methods=["GET"])
@login_required
def download_assignment(assignment_id: int):
    assignment = Assignment.query.get_or_404(assignment_id)
    if not assignment.file_key:
        return jsonify({"success": False, "message": "No file attached."}), 404

    s3 = S3Service()
    url = s3.generate_presigned_url(assignment.file_key, expiry=1800)
    return jsonify({"success": True, "download_url": url})


@assignments_bp.route("/<int:assignment_id>/submissions", methods=["GET"])
@login_required
@role_required("admin", "faculty")
def get_submissions(assignment_id: int):
    assignment = Assignment.query.get_or_404(assignment_id)
    submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment.id).all()
    return jsonify({
        "success": True,
        "submissions": [s.to_dict() for s in submissions],
    })


@assignments_bp.route("/submission/<int:submission_id>/download", methods=["GET"])
@login_required
def download_submission(submission_id: int):
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    # Check access: faculty, admin, or own student
    if current_user.role.name == "student" and (not current_user.student_profile or current_user.student_profile.id != submission.student_id):
        return jsonify({"success": False, "message": "Access denied."}), 403

    s3 = S3Service()
    url = s3.generate_presigned_url(submission.file_key, expiry=1800)
    return jsonify({"success": True, "download_url": url})
