"""
Authentication routes for the College Management System.
Handles login, logout, password reset, and password change.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app, abort
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import User
from security.decorators import admin_required, faculty_required, student_required, permission_required
import secrets
import datetime

auth = Blueprint('auth', __name__, url_prefix='/auth')


def _redirect_by_role(user):
    """Return the appropriate redirect response based on user role."""
    role = user.role.name if user.role else ''
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'faculty':
        return redirect(url_for('faculty.dashboard'))
    elif role == 'student':
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))


# ---------------------------------------------------------------------------
# GET/POST /auth/login
# ---------------------------------------------------------------------------
@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Login form. Validates credentials and redirects by role."""
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == 'POST':
        # Basic CSRF token validation (assumes WTForms / Flask-WTF middleware)
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember_me') == 'on'

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email, is_active=True).first()

        if user is None or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            current_app.logger.warning('Failed login attempt for email: %s', email)
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        current_app.logger.info('User %s logged in successfully.', user.id)

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return _redirect_by_role(user)

    return render_template('auth/login.html')


# ---------------------------------------------------------------------------
# GET /auth/logout
# ---------------------------------------------------------------------------
@auth.route('/logout')
@login_required
def logout():
    """Log the current user out and redirect to the login page."""
    current_app.logger.info('User %s logged out.', current_user.id)
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


# ---------------------------------------------------------------------------
# GET/POST /auth/forgot-password
# ---------------------------------------------------------------------------
@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Generate a password reset token, store it in the session with a 1-hour
    expiry, and display an 'email sent' confirmation message.
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Please enter your email address.', 'danger')
            return render_template('auth/forgot-password.html')

        user = User.query.filter_by(email=email, is_active=True).first()

        # Always show the same message to prevent user enumeration.
        if user:
            token = secrets.token_urlsafe(48)
            expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

            # Store token keyed by token so multiple outstanding resets work.
            reset_tokens = session.get('password_reset_tokens', {})
            reset_tokens[token] = {
                'user_id': user.id,
                'expires': expiry.isoformat(),
            }
            session['password_reset_tokens'] = reset_tokens
            session.modified = True

            reset_url = url_for('auth.reset_password', token=token, _external=True)
            current_app.logger.info(
                'Password reset token generated for user %s. Reset URL: %s',
                user.id, reset_url
            )
            # TODO: Replace with actual email sending via Flask-Mail / SES.
            # send_reset_email(user, reset_url)

        flash(
            'If an account with that email exists, a password reset link has been sent.',
            'info'
        )
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot-password.html')


# ---------------------------------------------------------------------------
# GET/POST /auth/reset-password/<token>
# ---------------------------------------------------------------------------
@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Validate the reset token and allow the user to set a new password."""
    reset_tokens = session.get('password_reset_tokens', {})
    token_data = reset_tokens.get(token)

    if not token_data:
        flash('Invalid or expired password reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    expiry = datetime.datetime.fromisoformat(token_data['expires'])
    if datetime.datetime.utcnow() > expiry:
        # Clean up expired token.
        reset_tokens.pop(token, None)
        session['password_reset_tokens'] = reset_tokens
        session.modified = True
        flash('This password reset link has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not new_password or len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth/reset-password.html', token=token)

        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset-password.html', token=token)

        user = User.query.get(token_data['user_id'])
        if not user:
            abort(404)

        user.set_password(new_password)
        db.session.commit()

        # Invalidate the token after successful use.
        reset_tokens.pop(token, None)
        session['password_reset_tokens'] = reset_tokens
        session.modified = True

        current_app.logger.info('Password reset successfully for user %s.', user.id)
        flash('Your password has been reset. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset-password.html', token=token)


# ---------------------------------------------------------------------------
# POST /auth/api/change-password
# ---------------------------------------------------------------------------
@auth.route('/api/change-password', methods=['POST'])
@login_required
def api_change_password():
    """
    JSON API for authenticated users to change their own password.

    Request body:
        {
            "old_password": "...",
            "new_password": "..."
        }

    Response:
        200: {"message": "Password updated successfully."}
        400: {"error": "..."}
        401: {"error": "Current password is incorrect."}
    """
    data = request.get_json(silent=True) or {}
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'error': 'old_password and new_password are required.'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'New password must be at least 8 characters long.'}), 400

    if not current_user.check_password(old_password):
        return jsonify({'error': 'Current password is incorrect.'}), 401

    current_user.set_password(new_password)
    db.session.commit()

    current_app.logger.info('User %s changed their password.', current_user.id)
    return jsonify({'message': 'Password updated successfully.'}), 200
