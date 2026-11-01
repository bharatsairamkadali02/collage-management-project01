"""
Admin routes for the College Management System.
All routes require authentication + admin role.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app, abort
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash
from extensions import db
from models import (
    User, Student, Faculty, Department, Subject, Semester, AcademicYear,
    ClassSection, FacultyAssignment, Attendance, AttendanceSession, Exam,
    Result, FeeRecord, Payment, StudyMaterial, Notification, AuditLog,
    Role, Permission
)
from security.decorators import admin_required, faculty_required, student_required, permission_required
from security.permissions import MANAGE_STUDENTS, MANAGE_FACULTY, MANAGE_DEPARTMENTS
import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_students = Student.query.filter_by(academic_status='active').count()
    total_faculty = Faculty.query.count()
    total_departments = Department.query.count()
    total_subjects = Subject.query.filter_by(is_active=True).count()

    recent_registrations = (
        Student.query
        .join(User)
        .order_by(User.created_at.desc())
        .limit(10)
        .all()
    )

    today = datetime.date.today()
    upcoming_exams = (
        Exam.query
        .filter(Exam.exam_date >= today, Exam.status == 'published')
        .order_by(Exam.exam_date.asc())
        .limit(5)
        .all()
    )

    total_fees_due = db.session.query(db.func.sum(FeeRecord.amount_due)).scalar() or 0
    total_fees_paid = db.session.query(db.func.sum(FeeRecord.amount_paid)).scalar() or 0
    fee_summary = {
        'due': float(total_fees_due),
        'paid': float(total_fees_paid),
        'pending': float(total_fees_due - total_fees_paid),
    }

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_faculty=total_faculty,
        total_departments=total_departments,
        total_subjects=total_subjects,
        recent_registrations=recent_registrations,
        upcoming_exams=upcoming_exams,
        fee_summary=fee_summary,
    )


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
@admin_bp.route('/students')
@login_required
@admin_required
def students():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    department_id = request.args.get('department_id', type=int)
    status = request.args.get('status', '')

    query = Student.query.join(User)

    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.email.ilike(like),
                Student.enrollment_number.ilike(like),
            )
        )
    if department_id:
        query = query.filter(Student.department_id == department_id)
    if status:
        query = query.filter(Student.academic_status == status)

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    departments = Department.query.order_by(Department.name).all()

    return render_template(
        'admin/students.html',
        pagination=pagination,
        students=pagination.items,
        departments=departments,
        search=search,
    )


@admin_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    departments = Department.query.order_by(Department.name).all()
    class_sections = ClassSection.query.order_by(ClassSection.name).all()

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        enrollment_number = request.form.get('enrollment_number', '').strip()
        department_id = request.form.get('department_id', type=int)
        class_section_id = request.form.get('class_section_id', type=int)
        date_of_birth = request.form.get('date_of_birth')

        if not all([first_name, last_name, email, password, enrollment_number, department_id]):
            flash('All required fields must be filled.', 'danger')
            return render_template('admin/add-student.html', departments=departments, class_sections=class_sections)

        if User.query.filter_by(email=email).first():
            flash('A user with this email already exists.', 'danger')
            return render_template('admin/add-student.html', departments=departments, class_sections=class_sections)

        if Student.query.filter_by(enrollment_number=enrollment_number).first():
            flash('Enrollment number already exists.', 'danger')
            return render_template('admin/add-student.html', departments=departments, class_sections=class_sections)

        student_role = Role.query.filter_by(name='student').first()
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            role=student_role,
            is_active=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        dob = datetime.date.fromisoformat(date_of_birth) if date_of_birth else None
        student = Student(
            user_id=user.id,
            enrollment_number=enrollment_number,
            department_id=department_id,
            class_section_id=class_section_id,
            date_of_birth=dob,
            academic_status='active',
        )
        db.session.add(student)
        db.session.commit()

        flash(f'Student {first_name} {last_name} added successfully.', 'success')
        return redirect(url_for('admin_bp.students'))

    return render_template('admin/add-student.html', departments=departments, class_sections=class_sections)


@admin_bp.route('/students/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_student(id):
    student = Student.query.get_or_404(id)
    departments = Department.query.order_by(Department.name).all()
    class_sections = ClassSection.query.order_by(ClassSection.name).all()

    if request.method == 'POST':
        student.user.first_name = request.form.get('first_name', student.user.first_name).strip()
        student.user.last_name = request.form.get('last_name', student.user.last_name).strip()
        student.user.phone = request.form.get('phone', student.user.phone).strip()
        student.department_id = request.form.get('department_id', student.department_id, type=int)
        student.class_section_id = request.form.get('class_section_id', student.class_section_id, type=int)
        student.academic_status = request.form.get('academic_status', student.academic_status)

        date_of_birth = request.form.get('date_of_birth')
        if date_of_birth:
            student.date_of_birth = datetime.date.fromisoformat(date_of_birth)

        db.session.commit()
        flash('Student updated successfully.', 'success')
        return redirect(url_for('admin_bp.students'))

    return render_template(
        'admin/edit-student.html',
        student=student,
        departments=departments,
        class_sections=class_sections,
    )


@admin_bp.route('/students/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    student.academic_status = 'dropped'
    db.session.commit()
    return jsonify({'message': 'Student has been dropped (soft deleted).', 'student_id': id}), 200


@admin_bp.route('/students/<int:id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_student_status(id):
    student = Student.query.get_or_404(id)
    student.user.is_active = not student.user.is_active
    db.session.commit()
    status = 'activated' if student.user.is_active else 'deactivated'
    return jsonify({'message': f'Student account {status}.', 'is_active': student.user.is_active}), 200


# ---------------------------------------------------------------------------
# Faculty
# ---------------------------------------------------------------------------
@admin_bp.route('/faculty')
@login_required
@admin_required
def faculty():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    department_id = request.args.get('department_id', type=int)

    query = Faculty.query.join(User)

    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.email.ilike(like),
                Faculty.employee_id.ilike(like),
            )
        )
    if department_id:
        query = query.filter(Faculty.department_id == department_id)

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    departments = Department.query.order_by(Department.name).all()

    return render_template(
        'admin/faculty.html',
        pagination=pagination,
        faculty_list=pagination.items,
        departments=departments,
        search=search,
    )


@admin_bp.route('/faculty/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_faculty():
    departments = Department.query.order_by(Department.name).all()

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        employee_id = request.form.get('employee_id', '').strip()
        department_id = request.form.get('department_id', type=int)
        designation = request.form.get('designation', '').strip()
        qualification = request.form.get('qualification', '').strip()

        if not all([first_name, last_name, email, password, employee_id, department_id]):
            flash('All required fields must be filled.', 'danger')
            return render_template('admin/add-faculty.html', departments=departments)

        if User.query.filter_by(email=email).first():
            flash('A user with this email already exists.', 'danger')
            return render_template('admin/add-faculty.html', departments=departments)

        if Faculty.query.filter_by(employee_id=employee_id).first():
            flash('Employee ID already exists.', 'danger')
            return render_template('admin/add-faculty.html', departments=departments)

        faculty_role = Role.query.filter_by(name='faculty').first()
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            role=faculty_role,
            is_active=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        faculty_member = Faculty(
            user_id=user.id,
            employee_id=employee_id,
            department_id=department_id,
            designation=designation,
            qualification=qualification,
        )
        db.session.add(faculty_member)
        db.session.commit()

        flash(f'Faculty member {first_name} {last_name} added successfully.', 'success')
        return redirect(url_for('admin_bp.faculty'))

    return render_template('admin/add-faculty.html', departments=departments)


@admin_bp.route('/faculty/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_faculty(id):
    faculty_member = Faculty.query.get_or_404(id)
    departments = Department.query.order_by(Department.name).all()

    if request.method == 'POST':
        faculty_member.user.first_name = request.form.get('first_name', faculty_member.user.first_name).strip()
        faculty_member.user.last_name = request.form.get('last_name', faculty_member.user.last_name).strip()
        faculty_member.user.phone = request.form.get('phone', faculty_member.user.phone).strip()
        faculty_member.department_id = request.form.get('department_id', faculty_member.department_id, type=int)
        faculty_member.designation = request.form.get('designation', faculty_member.designation).strip()
        faculty_member.qualification = request.form.get('qualification', faculty_member.qualification).strip()
        db.session.commit()

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'message': 'Faculty updated successfully.'}), 200

        flash('Faculty updated successfully.', 'success')
        return redirect(url_for('admin_bp.faculty'))

    return render_template(
        'admin/edit-faculty.html',
        faculty_member=faculty_member,
        departments=departments,
    )


@admin_bp.route('/faculty/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_faculty(id):
    faculty_member = Faculty.query.get_or_404(id)
    faculty_member.user.is_active = False
    db.session.commit()
    return jsonify({'message': 'Faculty member deleted (deactivated).', 'faculty_id': id}), 200


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------
@admin_bp.route('/departments')
@login_required
@admin_required
def departments():
    all_departments = Department.query.order_by(Department.name).all()
    return render_template('admin/departments.html', departments=all_departments)


@admin_bp.route('/departments/add', methods=['POST'])
@login_required
@admin_required
def add_department():
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    code = (data.get('code') or '').strip().upper()
    description = (data.get('description') or '').strip()
    hod_id = data.get('hod_id', type=int) if hasattr(data, 'get') else None

    if not name or not code:
        return jsonify({'error': 'Department name and code are required.'}), 400

    if Department.query.filter_by(code=code).first():
        return jsonify({'error': 'Department code already exists.'}), 409

    dept = Department(name=name, code=code, description=description, hod_id=hod_id)
    db.session.add(dept)
    db.session.commit()
    return jsonify({'message': 'Department added.', 'department_id': dept.id}), 201


@admin_bp.route('/departments/<int:id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_department(id):
    dept = Department.query.get_or_404(id)
    data = request.get_json(silent=True) or request.form

    dept.name = (data.get('name') or dept.name).strip()
    dept.code = (data.get('code') or dept.code).strip().upper()
    dept.description = (data.get('description') or dept.description or '').strip()
    if data.get('hod_id'):
        dept.hod_id = int(data.get('hod_id'))

    db.session.commit()
    return jsonify({'message': 'Department updated.'}), 200


@admin_bp.route('/departments/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_department(id):
    dept = Department.query.get_or_404(id)
    if dept.students or dept.faculty:
        return jsonify({'error': 'Cannot delete department with assigned students or faculty.'}), 409
    db.session.delete(dept)
    db.session.commit()
    return jsonify({'message': 'Department deleted.'}), 200


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------
@admin_bp.route('/subjects')
@login_required
@admin_required
def subjects():
    all_subjects = Subject.query.order_by(Subject.name).all()
    departments = Department.query.order_by(Department.name).all()
    return render_template('admin/subjects.html', subjects=all_subjects, departments=departments)


@admin_bp.route('/subjects/add', methods=['POST'])
@login_required
@admin_required
def add_subject():
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    code = (data.get('code') or '').strip().upper()
    department_id = int(data.get('department_id', 0))
    credits = int(data.get('credits', 3))
    subject_type = (data.get('subject_type') or 'theory').strip()
    description = (data.get('description') or '').strip()

    if not name or not code or not department_id:
        return jsonify({'error': 'Subject name, code, and department are required.'}), 400

    if Subject.query.filter_by(code=code).first():
        return jsonify({'error': 'Subject code already exists.'}), 409

    subject = Subject(
        name=name,
        code=code,
        department_id=department_id,
        credits=credits,
        subject_type=subject_type,
        description=description,
        is_active=True,
    )
    db.session.add(subject)
    db.session.commit()
    return jsonify({'message': 'Subject added.', 'subject_id': subject.id}), 201


@admin_bp.route('/subjects/<int:id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_subject(id):
    subject = Subject.query.get_or_404(id)
    data = request.get_json(silent=True) or request.form

    subject.name = (data.get('name') or subject.name).strip()
    subject.credits = int(data.get('credits', subject.credits))
    subject.subject_type = (data.get('subject_type') or subject.subject_type).strip()
    subject.description = (data.get('description') or subject.description or '').strip()
    if data.get('department_id'):
        subject.department_id = int(data.get('department_id'))

    db.session.commit()
    return jsonify({'message': 'Subject updated.'}), 200


@admin_bp.route('/subjects/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_subject(id):
    subject = Subject.query.get_or_404(id)
    subject.is_active = False
    db.session.commit()
    return jsonify({'message': 'Subject deactivated (soft deleted).'}), 200


# ---------------------------------------------------------------------------
# Semesters & Academic Years
# ---------------------------------------------------------------------------
@admin_bp.route('/semesters')
@login_required
@admin_required
def semesters():
    academic_years = AcademicYear.query.order_by(AcademicYear.start_date.desc()).all()
    all_semesters = Semester.query.order_by(Semester.name).all()
    return render_template('admin/semesters.html', academic_years=academic_years, semesters=all_semesters)


@admin_bp.route('/academic-years/add', methods=['POST'])
@login_required
@admin_required
def add_academic_year():
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    is_current = bool(data.get('is_current', False))

    if not name or not start_date or not end_date:
        return jsonify({'error': 'name, start_date, and end_date are required.'}), 400

    if is_current:
        AcademicYear.query.update({'is_current': False})

    year = AcademicYear(
        name=name,
        start_date=datetime.date.fromisoformat(start_date),
        end_date=datetime.date.fromisoformat(end_date),
        is_current=is_current,
    )
    db.session.add(year)
    db.session.commit()
    return jsonify({'message': 'Academic year added.', 'academic_year_id': year.id}), 201


@admin_bp.route('/semesters/add', methods=['POST'])
@login_required
@admin_required
def add_semester():
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    academic_year_id = int(data.get('academic_year_id', 0))
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    is_current = bool(data.get('is_current', False))

    if not name or not academic_year_id:
        return jsonify({'error': 'name and academic_year_id are required.'}), 400

    if is_current:
        Semester.query.update({'is_current': False})

    semester = Semester(
        name=name,
        academic_year_id=academic_year_id,
        start_date=datetime.date.fromisoformat(start_date) if start_date else None,
        end_date=datetime.date.fromisoformat(end_date) if end_date else None,
        is_current=is_current,
    )
    db.session.add(semester)
    db.session.commit()
    return jsonify({'message': 'Semester added.', 'semester_id': semester.id}), 201


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------
@admin_bp.route('/attendance')
@login_required
@admin_required
def attendance():
    class_sections = ClassSection.query.order_by(ClassSection.name).all()
    subjects = Subject.query.filter_by(is_active=True).order_by(Subject.name).all()
    return render_template('admin/attendance.html', class_sections=class_sections, subjects=subjects)


# ---------------------------------------------------------------------------
# Examinations
# ---------------------------------------------------------------------------
@admin_bp.route('/examinations')
@login_required
@admin_required
def examinations():
    page = request.args.get('page', 1, type=int)
    exams = Exam.query.order_by(Exam.exam_date.desc()).paginate(page=page, per_page=20)
    return render_template('admin/examinations.html', exams=exams)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@admin_bp.route('/results')
@login_required
@admin_required
def results():
    semesters = Semester.query.order_by(Semester.name).all()
    departments = Department.query.order_by(Department.name).all()
    return render_template('admin/results.html', semesters=semesters, departments=departments)


# ---------------------------------------------------------------------------
# Fees
# ---------------------------------------------------------------------------
@admin_bp.route('/fees')
@login_required
@admin_required
def fees():
    page = request.args.get('page', 1, type=int)
    fee_records = FeeRecord.query.order_by(FeeRecord.due_date.asc()).paginate(page=page, per_page=25)
    return render_template('admin/fees.html', fee_records=fee_records)


@admin_bp.route('/fees/add-record', methods=['POST'])
@login_required
@admin_required
def add_fee_record():
    data = request.get_json(silent=True) or request.form
    student_id = int(data.get('student_id', 0))
    fee_type = (data.get('fee_type') or '').strip()
    amount_due = float(data.get('amount_due', 0))
    due_date = data.get('due_date')
    academic_year_id = int(data.get('academic_year_id', 0))
    semester_id = data.get('semester_id')
    description = (data.get('description') or '').strip()

    if not all([student_id, fee_type, amount_due, due_date, academic_year_id]):
        return jsonify({'error': 'student_id, fee_type, amount_due, due_date, and academic_year_id are required.'}), 400

    student = Student.query.get_or_404(student_id)
    record = FeeRecord(
        student_id=student_id,
        fee_type=fee_type,
        amount_due=amount_due,
        amount_paid=0.0,
        due_date=datetime.date.fromisoformat(due_date),
        academic_year_id=academic_year_id,
        semester_id=int(semester_id) if semester_id else None,
        description=description,
        status='pending',
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({'message': 'Fee record added.', 'record_id': record.id}), 201


@admin_bp.route('/fees/record-payment', methods=['POST'])
@login_required
@admin_required
def record_fee_payment():
    data = request.get_json(silent=True) or request.form
    fee_record_id = int(data.get('fee_record_id', 0))
    amount = float(data.get('amount', 0))
    payment_method = (data.get('payment_method') or 'cash').strip()
    transaction_id = (data.get('transaction_id') or '').strip()

    if not fee_record_id or amount <= 0:
        return jsonify({'error': 'fee_record_id and a positive amount are required.'}), 400

    fee_record = FeeRecord.query.get_or_404(fee_record_id)
    fee_record.amount_paid = (fee_record.amount_paid or 0) + amount
    if fee_record.amount_paid >= fee_record.amount_due:
        fee_record.status = 'paid'
    else:
        fee_record.status = 'partial'

    payment = Payment(
        fee_record_id=fee_record_id,
        amount=amount,
        payment_method=payment_method,
        transaction_id=transaction_id,
        received_by_id=current_user.id,
        payment_date=datetime.datetime.utcnow(),
    )
    db.session.add(payment)
    db.session.commit()
    return jsonify({'message': 'Payment recorded.', 'payment_id': payment.id}), 201


# ---------------------------------------------------------------------------
# Study Materials
# ---------------------------------------------------------------------------
@admin_bp.route('/materials')
@login_required
@admin_required
def materials():
    page = request.args.get('page', 1, type=int)
    all_materials = StudyMaterial.query.order_by(StudyMaterial.uploaded_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/materials.html', materials=all_materials)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
@admin_bp.route('/notifications')
@login_required
@admin_required
def notifications():
    page = request.args.get('page', 1, type=int)
    all_notifications = Notification.query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=25)
    return render_template('admin/notifications.html', notifications=all_notifications)


@admin_bp.route('/notifications/send', methods=['POST'])
@login_required
@admin_required
def send_notification():
    data = request.get_json(silent=True) or request.form
    title = (data.get('title') or '').strip()
    message = (data.get('message') or '').strip()
    target_role = (data.get('target_role') or '').strip()   # 'all', 'student', 'faculty'
    recipient_ids = data.get('recipient_ids', [])           # explicit list of user IDs

    if not title or not message:
        return jsonify({'error': 'title and message are required.'}), 400

    created_notifications = []

    if recipient_ids:
        recipients = User.query.filter(User.id.in_(recipient_ids), User.is_active == True).all()
    elif target_role == 'all':
        recipients = User.query.filter_by(is_active=True).all()
    elif target_role in ('student', 'faculty'):
        recipients = User.query.join(Role).filter(Role.name == target_role, User.is_active == True).all()
    else:
        return jsonify({'error': 'Provide target_role or recipient_ids.'}), 400

    for recipient in recipients:
        notif = Notification(
            user_id=recipient.id,
            title=title,
            message=message,
            sent_by_id=current_user.id,
            is_read=False,
        )
        db.session.add(notif)
        created_notifications.append(recipient.id)

    db.session.commit()
    return jsonify({'message': f'Notification sent to {len(created_notifications)} user(s).'}), 201


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = User.query
    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(User.first_name.ilike(like), User.last_name.ilike(like), User.email.ilike(like))
        )
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=25)
    return render_template('admin/users.html', pagination=pagination, users=pagination.items)


@admin_bp.route('/users/<int:id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(id):
    user = User.query.get_or_404(id)
    data = request.get_json(silent=True) or request.form
    new_password = (data.get('new_password') or '').strip()

    if not new_password or len(new_password) < 8:
        return jsonify({'error': 'New password must be at least 8 characters.'}), 400

    user.set_password(new_password)
    db.session.commit()
    return jsonify({'message': f"Password reset for user {user.email}."}), 200


@admin_bp.route('/users/<int:id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot deactivate your own account.'}), 400
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    return jsonify({'message': f'User {status}.', 'is_active': user.is_active}), 200


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
@admin_bp.route('/permissions')
@login_required
@admin_required
def permissions():
    roles = Role.query.all()
    all_permissions = Permission.query.all()
    return render_template('admin/permissions.html', roles=roles, permissions=all_permissions)


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------
@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    user_filter = request.args.get('user_id', type=int)
    action_filter = request.args.get('action', '').strip()
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = AuditLog.query

    if user_filter:
        query = query.filter(AuditLog.user_id == user_filter)
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f'%{action_filter}%'))
    if date_from:
        query = query.filter(AuditLog.timestamp >= datetime.datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(AuditLog.timestamp <= datetime.datetime.fromisoformat(date_to))

    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=50)
    return render_template('admin/audit-logs.html', pagination=pagination, logs=pagination.items)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    return render_template('admin/settings.html')


# ---------------------------------------------------------------------------
# Class Sections
# ---------------------------------------------------------------------------
@admin_bp.route('/class-sections')
@login_required
@admin_required
def class_sections():
    sections = ClassSection.query.order_by(ClassSection.name).all()
    departments = Department.query.order_by(Department.name).all()
    return render_template('admin/class-sections.html', class_sections=sections, departments=departments)


@admin_bp.route('/class-sections/add', methods=['POST'])
@login_required
@admin_required
def add_class_section():
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    department_id = int(data.get('department_id', 0))
    semester_id = data.get('semester_id')
    academic_year_id = data.get('academic_year_id')
    max_students = int(data.get('max_students', 60))

    if not name or not department_id:
        return jsonify({'error': 'name and department_id are required.'}), 400

    section = ClassSection(
        name=name,
        department_id=department_id,
        semester_id=int(semester_id) if semester_id else None,
        academic_year_id=int(academic_year_id) if academic_year_id else None,
        max_students=max_students,
    )
    db.session.add(section)
    db.session.commit()
    return jsonify({'message': 'Class section added.', 'class_section_id': section.id}), 201


# ---------------------------------------------------------------------------
# Faculty Assignments
# ---------------------------------------------------------------------------
@admin_bp.route('/faculty-assignments/add', methods=['POST'])
@login_required
@admin_required
def add_faculty_assignment():
    data = request.get_json(silent=True) or request.form
    faculty_id = int(data.get('faculty_id', 0))
    subject_id = int(data.get('subject_id', 0))
    class_section_id = int(data.get('class_section_id', 0))
    academic_year_id = data.get('academic_year_id')
    semester_id = data.get('semester_id')

    if not all([faculty_id, subject_id, class_section_id]):
        return jsonify({'error': 'faculty_id, subject_id, and class_section_id are required.'}), 400

    exists = FacultyAssignment.query.filter_by(
        faculty_id=faculty_id,
        subject_id=subject_id,
        class_section_id=class_section_id,
    ).first()
    if exists:
        return jsonify({'error': 'Assignment already exists.'}), 409

    assignment = FacultyAssignment(
        faculty_id=faculty_id,
        subject_id=subject_id,
        class_section_id=class_section_id,
        academic_year_id=int(academic_year_id) if academic_year_id else None,
        semester_id=int(semester_id) if semester_id else None,
    )
    db.session.add(assignment)
    db.session.commit()
    return jsonify({'message': 'Faculty assignment created.', 'assignment_id': assignment.id}), 201


# ---------------------------------------------------------------------------
# API – Students in a class section
# ---------------------------------------------------------------------------
@admin_bp.route('/api/students-in-class/<int:class_section_id>')
@login_required
@admin_required
def api_students_in_class(class_section_id):
    ClassSection.query.get_or_404(class_section_id)
    students = (
        Student.query
        .join(User)
        .filter(Student.class_section_id == class_section_id, Student.academic_status == 'active')
        .all()
    )
    return jsonify([
        {
            'id': s.id,
            'enrollment_number': s.enrollment_number,
            'name': f'{s.user.first_name} {s.user.last_name}',
            'email': s.user.email,
        }
        for s in students
    ]), 200
