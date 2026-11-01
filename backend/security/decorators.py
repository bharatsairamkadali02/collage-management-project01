"""
security/decorators.py - RBAC decorators for Flask route protection.

Usage::

    from security.decorators import permission_required, admin_required

    @app.route('/admin/students')
    @login_required
    @admin_required
    def students():
        ...
"""

import logging
from functools import wraps
from typing import Callable

from flask import abort, jsonify, redirect, request, url_for, flash
from flask_login import current_user, login_required  # noqa: re-exported for convenience

from security.permissions import has_permission

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Private helpers
# --------------------------------------------------------------------------- #

def _wants_json() -> bool:
    """Return True when the client expects a JSON response."""
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return best == "application/json" or request.path.startswith("/api/")


def _deny(message: str, status: int = 403):
    """Return a 403 JSON response or abort for HTML clients."""
    _write_audit_log(message, status)
    if _wants_json():
        return jsonify({"error": "Forbidden", "message": message, "status": status}), status
    flash(message, "danger")
    abort(status)


def _write_audit_log(reason: str, status: int) -> None:
    """
    Record a permission-denial event to the audit log table.

    Failures here are silently swallowed so they never break the request flow.
    """
    try:
        from extensions import db
        from models.audit_log import AuditLog  # imported lazily to avoid circular deps

        user_id = current_user.get_id() if current_user and current_user.is_authenticated else None
        entry = AuditLog(
            user_id=user_id,
            action="PERMISSION_DENIED",
            resource=request.path,
            method=request.method,
            status_code=status,
            details=reason,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:255] if request.user_agent else None,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as exc:  # pragma: no cover
        logger.debug("Could not write audit log entry: %s", exc)


# --------------------------------------------------------------------------- #
# Core decorators
# --------------------------------------------------------------------------- #

def permission_required(permission: str) -> Callable:
    """
    Decorator that enforces a single permission string.

    The decorated view is only reached if:
    1. The user is authenticated (via @login_required).
    2. The user holds the specified permission.

    Args:
        permission: A permission constant from ``security.permissions``.

    Example::

        @bp.route('/students/create')
        @login_required
        @permission_required(CREATE_STUDENT)
        def create_student():
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.path))

            if not has_permission(current_user, permission):
                logger.warning(
                    "Permission denied: user=%s required=%s path=%s",
                    current_user.get_id(),
                    permission,
                    request.path,
                )
                return _deny(
                    f"You do not have the required permission: '{permission}'."
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def role_required(*roles: str) -> Callable:
    """
    Decorator that restricts access to users whose role name is in *roles*.

    Args:
        *roles: One or more role name strings (e.g. ``'Admin'``, ``'Faculty'``).

    Example::

        @bp.route('/admin/settings')
        @login_required
        @role_required('Admin')
        def settings():
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.path))

            user_role = getattr(getattr(current_user, "role", None), "name", None)
            if user_role not in roles:
                logger.warning(
                    "Role denied: user=%s role=%s required_one_of=%s path=%s",
                    current_user.get_id(),
                    user_role,
                    roles,
                    request.path,
                )
                return _deny(
                    f"Access restricted. Required role(s): {', '.join(roles)}."
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# --------------------------------------------------------------------------- #
# Convenience shortcuts
# --------------------------------------------------------------------------- #

def admin_required(fn: Callable) -> Callable:
    """
    Shortcut decorator – restricts the view to Admin role only.

    Equivalent to ``@role_required('Admin')``.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))

        user_role = getattr(getattr(current_user, "role", None), "name", None)
        if user_role != "Admin":
            logger.warning(
                "Admin access denied: user=%s role=%s path=%s",
                current_user.get_id(),
                user_role,
                request.path,
            )
            return _deny("Administrator access required.")
        return fn(*args, **kwargs)
    return wrapper


def faculty_required(fn: Callable) -> Callable:
    """
    Shortcut decorator – restricts the view to Faculty and Admin roles.

    Admins are also allowed because they have a superset of permissions.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))

        user_role = getattr(getattr(current_user, "role", None), "name", None)
        if user_role not in ("Faculty", "Admin"):
            logger.warning(
                "Faculty access denied: user=%s role=%s path=%s",
                current_user.get_id(),
                user_role,
                request.path,
            )
            return _deny("Faculty or Administrator access required.")
        return fn(*args, **kwargs)
    return wrapper


def student_required(fn: Callable) -> Callable:
    """
    Shortcut decorator – restricts the view to Student role only.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))

        user_role = getattr(getattr(current_user, "role", None), "name", None)
        if user_role != "Student":
            logger.warning(
                "Student access denied: user=%s role=%s path=%s",
                current_user.get_id(),
                user_role,
                request.path,
            )
            return _deny("Student access required.")
        return fn(*args, **kwargs)
    return wrapper


def active_user_required(fn: Callable) -> Callable:
    """
    Decorator that ensures the current user's account is active.

    Should be combined with @login_required.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        if not getattr(current_user, "is_active", False):
            logger.warning(
                "Inactive account access attempt: user=%s path=%s",
                current_user.get_id(),
                request.path,
            )
            return _deny("Your account has been deactivated. Please contact the administrator.")
        return fn(*args, **kwargs)
    return wrapper
