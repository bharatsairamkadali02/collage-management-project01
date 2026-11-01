"""
security/permissions.py - RBAC permission constants and helper functions.

All permission strings are defined as module-level constants so they can be
imported by decorators, blueprints, and service layers without hard-coding
raw strings.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User  # pragma: no cover

# --------------------------------------------------------------------------- #
# ── Student permissions ────────────────────────────────────────────────────── #
# --------------------------------------------------------------------------- #

VIEW_STUDENTS = "view_students"
MANAGE_STUDENTS = "manage_students"
CREATE_STUDENT = "create_student"
EDIT_STUDENT = "edit_student"
DELETE_STUDENT = "delete_student"
EXPORT_STUDENTS = "export_students"
VIEW_OWN_PROFILE = "view_own_profile"
EDIT_OWN_PROFILE = "edit_own_profile"

# --------------------------------------------------------------------------- #
# ── Faculty permissions ────────────────────────────────────────────────────── #
# --------------------------------------------------------------------------- #

VIEW_FACULTY = "view_faculty"
MANAGE_FACULTY = "manage_faculty"
CREATE_FACULTY = "create_faculty"
EDIT_FACULTY = "edit_faculty"
DELETE_FACULTY = "delete_faculty"
EXPORT_FACULTY = "export_faculty"

# --------------------------------------------------------------------------- #
# ── Course / Subject permissions ──────────────────────────────────────────── #
# --------------------------------------------------------------------------- #

VIEW_COURSES = "view_courses"
MANAGE_COURSES = "manage_courses"
CREATE_COURSE = "create_course"
EDIT_COURSE = "edit_course"
DELETE_COURSE = "delete_course"

VIEW_SUBJECTS = "view_subjects"
MANAGE_SUBJECTS = "manage_subjects"
CREATE_SUBJECT = "create_subject"
EDIT_SUBJECT = "edit_subject"
DELETE_SUBJECT = "delete_subject"

# --------------------------------------------------------------------------- #
# ── Attendance permissions ────────────────────────────────────────────────── #
# --------------------------------------------------------------------------- #

VIEW_ATTENDANCE = "view_attendance"
MANAGE_ATTENDANCE = "manage_attendance"
MARK_ATTENDANCE = "mark_attendance"
EDIT_ATTENDANCE = "edit_attendance"
DELETE_ATTENDANCE = "delete_attendance"
VIEW_OWN_ATTENDANCE = "view_own_attendance"
EXPORT_ATTENDANCE = "export_attendance"

# --------------------------------------------------------------------------- #
# ── Examination permissions ───────────────────────────────────────────────── #
# --------------------------------------------------------------------------- #

VIEW_EXAMS = "view_exams"
MANAGE_EXAMS = "manage_exams"
CREATE_EXAM = "create_exam"
EDIT_EXAM = "edit_exam"
DELETE_EXAM = "delete_exam"
PUBLISH_EXAM = "publish_exam"
TAKE_EXAM = "take_exam"
VIEW_OWN_EXAM_RESULT = "view_own_exam_result"

# --------------------------------------------------------------------------- #
# ── Results permissions ───────────────────────────────────────────────────── #
# --------------------------------------------------------------------------- #

VIEW_RESULTS = "view_results"
MANAGE_RESULTS = "manage_results"
ENTER_MARKS = "enter_marks"
EDIT_MARKS = "edit_marks"
PUBLISH_RESULTS = "publish_results"
VIEW_OWN_RESULTS = "view_own_results"
EXPORT_RESULTS = "export_results"

# --------------------------------------------------------------------------- #
# ── Fees permissions ──────────────────────────────────────────────────────── #
# --------------------------------------------------------------------------- #

VIEW_FEES = "view_fees"
MANAGE_FEES = "manage_fees"
COLLECT_FEES = "collect_fees"
WAIVE_FEES = "waive_fees"
VIEW_OWN_FEES = "view_own_fees"
EXPORT_FEES = "export_fees"

# --------------------------------------------------------------------------- #
# ── Assignment permissions ────────────────────────────────────────────────── #
# --------------------------------------------------------------------------- #

VIEW_ASSIGNMENTS = "view_assignments"
MANAGE_ASSIGNMENTS = "manage_assignments"
CREATE_ASSIGNMENT = "create_assignment"
EDIT_ASSIGNMENT = "edit_assignment"
DELETE_ASSIGNMENT = "delete_assignment"
SUBMIT_ASSIGNMENT = "submit_assignment"
GRADE_ASSIGNMENT = "grade_assignment"
VIEW_OWN_ASSIGNMENTS = "view_own_assignments"

# --------------------------------------------------------------------------- #
# ── Notification permissions ──────────────────────────────────────────────── #
# --------------------------------------------------------------------------- #

VIEW_NOTIFICATIONS = "view_notifications"
SEND_NOTIFICATIONS = "send_notifications"
MANAGE_NOTIFICATIONS = "manage_notifications"
VIEW_OWN_NOTIFICATIONS = "view_own_notifications"

# --------------------------------------------------------------------------- #
# ── System / Admin permissions ────────────────────────────────────────────── #
# --------------------------------------------------------------------------- #

VIEW_AUDIT_LOG = "view_audit_log"
MANAGE_ROLES = "manage_roles"
MANAGE_DEPARTMENTS = "manage_departments"
MANAGE_SETTINGS = "manage_settings"
VIEW_REPORTS = "view_reports"
GENERATE_REPORTS = "generate_reports"
MANAGE_TIMETABLE = "manage_timetable"
VIEW_TIMETABLE = "view_timetable"
MANAGE_CLASSES = "manage_classes"

# --------------------------------------------------------------------------- #
# ── Collected permission sets per role ────────────────────────────────────── #
# --------------------------------------------------------------------------- #

ADMIN_PERMISSIONS: frozenset = frozenset(
    {
        # Students
        VIEW_STUDENTS, MANAGE_STUDENTS, CREATE_STUDENT, EDIT_STUDENT,
        DELETE_STUDENT, EXPORT_STUDENTS,
        # Faculty
        VIEW_FACULTY, MANAGE_FACULTY, CREATE_FACULTY, EDIT_FACULTY,
        DELETE_FACULTY, EXPORT_FACULTY,
        # Courses & Subjects
        VIEW_COURSES, MANAGE_COURSES, CREATE_COURSE, EDIT_COURSE, DELETE_COURSE,
        VIEW_SUBJECTS, MANAGE_SUBJECTS, CREATE_SUBJECT, EDIT_SUBJECT, DELETE_SUBJECT,
        # Attendance
        VIEW_ATTENDANCE, MANAGE_ATTENDANCE, MARK_ATTENDANCE, EDIT_ATTENDANCE,
        DELETE_ATTENDANCE, EXPORT_ATTENDANCE,
        # Exams
        VIEW_EXAMS, MANAGE_EXAMS, CREATE_EXAM, EDIT_EXAM, DELETE_EXAM,
        PUBLISH_EXAM,
        # Results
        VIEW_RESULTS, MANAGE_RESULTS, ENTER_MARKS, EDIT_MARKS, PUBLISH_RESULTS,
        EXPORT_RESULTS,
        # Fees
        VIEW_FEES, MANAGE_FEES, COLLECT_FEES, WAIVE_FEES, EXPORT_FEES,
        # Assignments
        VIEW_ASSIGNMENTS, MANAGE_ASSIGNMENTS, CREATE_ASSIGNMENT, EDIT_ASSIGNMENT,
        DELETE_ASSIGNMENT, GRADE_ASSIGNMENT,
        # Notifications
        VIEW_NOTIFICATIONS, SEND_NOTIFICATIONS, MANAGE_NOTIFICATIONS,
        # System
        VIEW_AUDIT_LOG, MANAGE_ROLES, MANAGE_DEPARTMENTS, MANAGE_SETTINGS,
        VIEW_REPORTS, GENERATE_REPORTS, MANAGE_TIMETABLE, VIEW_TIMETABLE,
        MANAGE_CLASSES,
    }
)

FACULTY_PERMISSIONS: frozenset = frozenset(
    {
        # Own profile
        VIEW_OWN_PROFILE, EDIT_OWN_PROFILE,
        # Students (read only)
        VIEW_STUDENTS,
        # Attendance – own subjects
        VIEW_ATTENDANCE, MARK_ATTENDANCE, EDIT_ATTENDANCE, EXPORT_ATTENDANCE,
        # Exams – own subjects
        VIEW_EXAMS, CREATE_EXAM, EDIT_EXAM, PUBLISH_EXAM,
        # Results – own subjects
        VIEW_RESULTS, ENTER_MARKS, EDIT_MARKS, PUBLISH_RESULTS,
        # Assignments – own subjects
        VIEW_ASSIGNMENTS, CREATE_ASSIGNMENT, EDIT_ASSIGNMENT, DELETE_ASSIGNMENT,
        GRADE_ASSIGNMENT,
        # Notifications
        VIEW_NOTIFICATIONS, SEND_NOTIFICATIONS, VIEW_OWN_NOTIFICATIONS,
        # Timetable (read only)
        VIEW_TIMETABLE,
        # Reports (read only)
        VIEW_REPORTS,
    }
)

STUDENT_PERMISSIONS: frozenset = frozenset(
    {
        # Own profile
        VIEW_OWN_PROFILE, EDIT_OWN_PROFILE,
        # Attendance (own only)
        VIEW_OWN_ATTENDANCE,
        # Exams (take + view own result)
        VIEW_EXAMS, TAKE_EXAM, VIEW_OWN_EXAM_RESULT,
        # Results (own only)
        VIEW_OWN_RESULTS,
        # Fees (own only)
        VIEW_OWN_FEES,
        # Assignments (own only)
        VIEW_OWN_ASSIGNMENTS, SUBMIT_ASSIGNMENT,
        # Notifications (own only)
        VIEW_OWN_NOTIFICATIONS,
        # Timetable (read only)
        VIEW_TIMETABLE,
    }
)

# Mapping of role name → permissions frozenset used by seed_roles()
ROLE_PERMISSIONS: dict[str, frozenset] = {
    "Admin": ADMIN_PERMISSIONS,
    "Faculty": FACULTY_PERMISSIONS,
    "Student": STUDENT_PERMISSIONS,
}


# --------------------------------------------------------------------------- #
# ── Helper functions ──────────────────────────────────────────────────────── #
# --------------------------------------------------------------------------- #

def get_user_permissions(user: "User") -> frozenset:
    """
    Return the complete set of permission strings for the given user.

    Resolution order:
    1. If the user has no role → empty set.
    2. Look up the role's permission set from ROLE_PERMISSIONS.
    3. Merge with any additional per-user permissions stored on the user model.

    Args:
        user: An authenticated User model instance.

    Returns:
        frozenset of permission strings.
    """
    if user is None or not hasattr(user, "role") or user.role is None:
        return frozenset()

    base_permissions: frozenset = ROLE_PERMISSIONS.get(user.role.name, frozenset())

    # Per-user extra permissions (stored as a comma-separated string on the model)
    extra: frozenset = frozenset()
    if hasattr(user, "extra_permissions") and user.extra_permissions:
        extra = frozenset(
            p.strip() for p in user.extra_permissions.split(",") if p.strip()
        )

    return base_permissions | extra


def has_permission(user: "User", permission: str) -> bool:
    """
    Check whether *user* holds the given *permission* string.

    Args:
        user: An authenticated User model instance (may be AnonymousUser).
        permission: One of the permission constants defined in this module.

    Returns:
        True if the user has the permission; False otherwise.
    """
    if user is None:
        return False

    # Flask-Login's AnonymousUser has no role
    if not hasattr(user, "is_authenticated") or not user.is_authenticated:
        return False

    # Inactive users have no permissions
    if hasattr(user, "is_active") and not user.is_active:
        return False

    return permission in get_user_permissions(user)
