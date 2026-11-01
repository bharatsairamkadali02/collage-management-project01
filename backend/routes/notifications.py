"""
Notifications REST API routes.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models.notifications import Notification

notifications_bp = Blueprint("notifications_bp", __name__, url_prefix="/notifications")


@notifications_bp.route("/my", methods=["GET"])
@login_required
def my_notifications():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = Notification.query.filter(
        (Notification.target_user_id == current_user.id)
        | (Notification.target_role.in_(["all", current_user.role.name]))
    ).order_by(Notification.created_at.desc())

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "success": True,
        "notifications": [n.to_dict() for n in paginated.items],
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages,
    })


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id: int):
    notif = Notification.query.get_or_404(notification_id)
    notif.mark_as_read()
    db.session.commit()
    return jsonify({"success": True})


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    now = datetime.utcnow()
    Notification.query.filter(
        (Notification.target_user_id == current_user.id)
        | (Notification.target_role.in_(["all", current_user.role.name])),
        Notification.is_read.is_(False),
    ).update({"is_read": True, "read_at": now}, synchronize_session=False)

    db.session.commit()
    return jsonify({"success": True})


@notifications_bp.route("/unread-count", methods=["GET"])
@login_required
def unread_count():
    count = Notification.query.filter(
        (Notification.target_user_id == current_user.id)
        | (Notification.target_role.in_(["all", current_user.role.name])),
        Notification.is_read.is_(False),
    ).count()

    return jsonify({"count": count})
