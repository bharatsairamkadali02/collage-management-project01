"""
Faculty routes for the College Management System.
All routes require authentication + faculty role.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app, abort
from flask_login import login_required, current_user, login_user, logout_user
from extensions import db
from models import (
    User, Student, Faculty, Subject, ClassSection, FacultyAssignment,
    Attendance, AttendanceSession, Exam, ExamQuestion, ExamOption,
    ExamAttempt, Result, StudyMaterial, Assignment, Notification,
    Semester, AcademicYear
)
from security.decorators import admin_required, faculty_required, student_required, permission_required
from security.permissions import MARK_ATTENDANCE, MANAGE_EXAMS, UPLOAD_MATERIALS
import datetime
import boto3
from botocore.exceptions import ClientError

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')


def _get_current_faculty():
    """Return the Faculty record for the currently logged-in user, or 404."""
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    if faculty is None:
        abort(404)
    return faculty


def _s3_client():
    """Return a boto3 S3 client using app config credentials."""
    return boto3.client(
        's3',
        aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
        region_name=current_app.config.get('AWS_REGION', 'us-east-1'),
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@faculty_bp.route('/dashboard')
@login_required
@faculty_required
def dashboard():
    faculty = _get_current_faculty()

    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty.id).all()
    class_ids = list({a.class_section_id for a in assignments})
    subject_ids = list({a.subject_id for a in assignments})

    assigned_students = (
        Student.query
        .filter(Student.class_section_id.in_(class_ids), Student.academic_status == 'active')
        .count()
    ) if class_ids else 0

    today = datetime.date.today()
    today_sessions = (
        AttendanceSession.query
        .filter(
            AttendanceSession.faculty_id == faculty.id,
            AttendanceSession.date == today,
        )
        .count()
    )

    upcoming_exams = (
        Exam.query
        .filter(
            Exam.created_by_id == faculty.user_id,
            Exam.exam_date >= today,
            Exam.status == 'published',
        )
        .order_by(Exam.exam_date.asc())
        .limit(5)
        .all()
    )

    return render_template(
        'faculty/dashboard.html',
        faculty=faculty,
        assigned_students=assigned_students,
        assigned_subjects=len(subject_ids),
        today_attendance_sessions=today_sessions,
        upcoming_exams=upcoming_exams,
    )


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
@faculty_bp.route('/students')
@login_required
@faculty_required
def students():
    faculty = _get_current_faculty()
    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty.id).all()
    class_ids = list({a.class_section_id for a in assignments})

    search = request.args.get('search', '').strip()
    query = (
        Student.query
        .join(User)
        .filter(
            Student.class_section_id.in_(class_ids),
            Student.academic_status == 'active',
        )
    )
    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                Student.enrollment_number.ilike(like),
            )
        )

    students_list = query.order_by(User.last_name).all()
    return render_template('faculty/students.html', students=students_list, faculty=faculty)


@faculty_bp.route('/students/<int:student_id>')
@login_required
@faculty_required
def student_details(student_id):
    faculty = _get_current_faculty()
    student = Student.query.get_or_404(student_id)

    # Ensure faculty teaches at least one class the student belongs to.
    assignments = FacultyAssignment.query.filter_by(
        faculty_id=faculty.id,
        class_section_id=student.class_section_id,
    ).first()
    if not assignments:
        abort(403)

    results = Result.query.filter_by(student_id=student_id).all()
    attendance_records = Attendance.query.filter_by(student_id=student_id).all()

    return render_template(
        'faculty/student-details.html',
        student=student,
        results=results,
        attendance_records=attendance_records,
    )


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------
@faculty_bp.route('/attendance')
@login_required
@faculty_required
def attendance():
    faculty = _get_current_faculty()
    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty.id).all()
    return render_template('faculty/attendance.html', faculty=faculty, assignments=assignments)


@faculty_bp.route('/api/attendance-session')
@login_required
@faculty_required
def api_attendance_session():
    """
    GET /faculty/api/attendance-session?subject_id=&class_section_id=&date=YYYY-MM-DD

    Returns an existing or newly created attendance session.
    """
    faculty = _get_current_faculty()
    subject_id = request.args.get('subject_id', type=int)
    class_section_id = request.args.get('class_section_id', type=int)
    date_str = request.args.get('date', datetime.date.today().isoformat())

    if not subject_id or not class_section_id:
        return jsonify({'error': 'subject_id and class_section_id are required.'}), 400

    # Validate faculty assignment.
    assignment = FacultyAssignment.query.filter_by(
        faculty_id=faculty.id,
        subject_id=subject_id,
        class_section_id=class_section_id,
    ).first()
    if not assignment:
        return jsonify({'error': 'You are not assigned to this subject/class combination.'}), 403

    session_date = datetime.date.fromisoformat(date_str)
    att_session = AttendanceSession.query.filter_by(
        faculty_id=faculty.id,
        subject_id=subject_id,
        class_section_id=class_section_id,
        date=session_date,
    ).first()

    if not att_session:
        att_session = AttendanceSession(
            faculty_id=faculty.id,
            subject_id=subject_id,
            class_section_id=class_section_id,
            date=session_date,
        )
        db.session.add(att_session)
        db.session.commit()

    # Return session + list of students pre-populated with current status.
    students = (
        Student.query
        .join(User)
        .filter(
            Student.class_section_id == class_section_id,
            Student.academic_status == 'active',
        )
        .all()
    )

    records_map = {
        r.student_id: r.status
        for r in Attendance.query.filter_by(session_id=att_session.id).all()
    }

    return jsonify({
        'session_id': att_session.id,
        'date': session_date.isoformat(),
        'subject_id': subject_id,
        'class_section_id': class_section_id,
        'students': [
            {
                'student_id': s.id,
                'name': f'{s.user.first_name} {s.user.last_name}',
                'enrollment_number': s.enrollment_number,
                'status': records_map.get(s.id, 'absent'),
            }
            for s in students
        ],
    }), 200


@faculty_bp.route('/api/attendance/mark', methods=['POST'])
@login_required
@faculty_required
def api_mark_attendance():
    """
    POST /faculty/api/attendance/mark
    Body: { "session_id": int, "records": [{"student_id": int, "status": "present|absent|late"}] }
    """
    faculty = _get_current_faculty()
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    records = data.get('records', [])

    if not session_id or not isinstance(records, list):
        return jsonify({'error': 'session_id and records[] are required.'}), 400

    att_session = AttendanceSession.query.get_or_404(session_id)
    if att_session.faculty_id != faculty.id:
        abort(403)

    updated = 0
    for rec in records:
        student_id = rec.get('student_id')
        status = rec.get('status', 'absent')
        if not student_id:
            continue

        existing = Attendance.query.filter_by(
            session_id=session_id,
            student_id=student_id,
        ).first()

        if existing:
            existing.status = status
        else:
            attendance_record = Attendance(
                session_id=session_id,
                student_id=student_id,
                subject_id=att_session.subject_id,
                class_section_id=att_session.class_section_id,
                faculty_id=faculty.id,
                date=att_session.date,
                status=status,
            )
            db.session.add(attendance_record)
        updated += 1

    db.session.commit()
    return jsonify({'message': f'Attendance marked for {updated} student(s).'}), 200


@faculty_bp.route('/api/attendance-report')
@login_required
@faculty_required
def api_attendance_report():
    """
    GET /faculty/api/attendance-report?subject_id=&class_section_id=

    Returns per-student attendance percentages.
    """
    faculty = _get_current_faculty()
    subject_id = request.args.get('subject_id', type=int)
    class_section_id = request.args.get('class_section_id', type=int)

    if not subject_id or not class_section_id:
        return jsonify({'error': 'subject_id and class_section_id are required.'}), 400

    total_sessions = AttendanceSession.query.filter_by(
        faculty_id=faculty.id,
        subject_id=subject_id,
        class_section_id=class_section_id,
    ).count()

    students = (
        Student.query
        .join(User)
        .filter(
            Student.class_section_id == class_section_id,
            Student.academic_status == 'active',
        )
        .all()
    )

    report = []
    for s in students:
        present_count = Attendance.query.filter_by(
            student_id=s.id,
            subject_id=subject_id,
            status='present',
        ).count()
        percentage = round((present_count / total_sessions * 100), 2) if total_sessions else 0
        report.append({
            'student_id': s.id,
            'name': f'{s.user.first_name} {s.user.last_name}',
            'enrollment_number': s.enrollment_number,
            'present_classes': present_count,
            'total_classes': total_sessions,
            'attendance_percentage': percentage,
        })

    return jsonify({'report': report, 'total_sessions': total_sessions}), 200


# ---------------------------------------------------------------------------
# Examinations
# ---------------------------------------------------------------------------
@faculty_bp.route('/examinations')
@login_required
@faculty_required
def examinations():
    faculty = _get_current_faculty()
    exams = (
        Exam.query
        .filter_by(created_by_id=faculty.user_id)
        .order_by(Exam.exam_date.desc())
        .all()
    )
    return render_template('faculty/examinations.html', exams=exams)


@faculty_bp.route('/examinations/create', methods=['GET', 'POST'])
@login_required
@faculty_required
def create_exam():
    faculty = _get_current_faculty()
    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty.id).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        subject_id = request.form.get('subject_id', type=int)
        class_section_id = request.form.get('class_section_id', type=int)
        semester_id = request.form.get('semester_id', type=int)
        academic_year_id = request.form.get('academic_year_id', type=int)
        exam_date = request.form.get('exam_date')
        duration_minutes = request.form.get('duration_minutes', 60, type=int)
        total_marks = request.form.get('total_marks', 100, type=int)
        passing_marks = request.form.get('passing_marks', 40, type=int)
        exam_type = request.form.get('exam_type', 'mcq').strip()
        instructions = request.form.get('instructions', '').strip()

        if not all([title, subject_id, class_section_id, exam_date]):
            flash('Title, subject, class, and date are required.', 'danger')
            return render_template('faculty/create-exam.html', assignments=assignments)

        exam = Exam(
            title=title,
            subject_id=subject_id,
            class_section_id=class_section_id,
            semester_id=semester_id,
            academic_year_id=academic_year_id,
            created_by_id=faculty.user_id,
            exam_date=datetime.date.fromisoformat(exam_date),
            duration_minutes=duration_minutes,
            total_marks=total_marks,
            passing_marks=passing_marks,
            exam_type=exam_type,
            instructions=instructions,
            status='draft',
        )
        db.session.add(exam)
        db.session.commit()
        flash('Exam created successfully. Add questions now.', 'success')
        return redirect(url_for('faculty_bp.exam_questions', id=exam.id))

    return render_template('faculty/create-exam.html', assignments=assignments)


@faculty_bp.route('/examinations/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@faculty_required
def edit_exam(id):
    faculty = _get_current_faculty()
    exam = Exam.query.get_or_404(id)
    if exam.created_by_id != faculty.user_id:
        abort(403)

    data = request.get_json(silent=True) or request.form
    exam.title = (data.get('title') or exam.title).strip()
    if data.get('exam_date'):
        exam.exam_date = datetime.date.fromisoformat(data.get('exam_date'))
    exam.duration_minutes = int(data.get('duration_minutes', exam.duration_minutes))
    exam.total_marks = int(data.get('total_marks', exam.total_marks))
    exam.passing_marks = int(data.get('passing_marks', exam.passing_marks))
    exam.instructions = (data.get('instructions') or exam.instructions or '').strip()

    db.session.commit()
    return jsonify({'message': 'Exam updated.', 'exam_id': exam.id}), 200


@faculty_bp.route('/examinations/<int:id>/publish', methods=['POST'])
@login_required
@faculty_required
def publish_exam(id):
    faculty = _get_current_faculty()
    exam = Exam.query.get_or_404(id)
    if exam.created_by_id != faculty.user_id:
        abort(403)

    question_count = ExamQuestion.query.filter_by(exam_id=id).count()
    if question_count == 0:
        return jsonify({'error': 'Cannot publish an exam with no questions.'}), 400

    exam.status = 'published'
    db.session.commit()
    return jsonify({'message': 'Exam published.'}), 200


@faculty_bp.route('/examinations/<int:id>/close', methods=['POST'])
@login_required
@faculty_required
def close_exam(id):
    faculty = _get_current_faculty()
    exam = Exam.query.get_or_404(id)
    if exam.created_by_id != faculty.user_id:
        abort(403)
    exam.status = 'closed'
    db.session.commit()
    return jsonify({'message': 'Exam closed.'}), 200


@faculty_bp.route('/examinations/<int:id>/questions')
@login_required
@faculty_required
def exam_questions(id):
    faculty = _get_current_faculty()
    exam = Exam.query.get_or_404(id)
    if exam.created_by_id != faculty.user_id:
        abort(403)
    questions = ExamQuestion.query.filter_by(exam_id=id).order_by(ExamQuestion.order).all()
    return render_template('faculty/questions.html', exam=exam, questions=questions)


@faculty_bp.route('/examinations/<int:id>/questions/add', methods=['POST'])
@login_required
@faculty_required
def add_question(id):
    faculty = _get_current_faculty()
    exam = Exam.query.get_or_404(id)
    if exam.created_by_id != faculty.user_id:
        abort(403)

    data = request.get_json(silent=True) or {}
    question_text = (data.get('question_text') or '').strip()
    marks = float(data.get('marks', 1))
    options = data.get('options', [])

    if not question_text:
        return jsonify({'error': 'question_text is required.'}), 400

    order = ExamQuestion.query.filter_by(exam_id=id).count() + 1
    question = ExamQuestion(
        exam_id=id,
        question_text=question_text,
        marks=marks,
        order=order,
    )
    db.session.add(question)
    db.session.flush()

    for opt in options:
        option = ExamOption(
            question_id=question.id,
            text=opt.get('text', '').strip(),
            is_correct=bool(opt.get('is_correct', False)),
        )
        db.session.add(option)

    db.session.commit()
    return jsonify({'message': 'Question added.', 'question_id': question.id}), 201


@faculty_bp.route('/questions/<int:id>/edit', methods=['POST'])
@login_required
@faculty_required
def edit_question(id):
    faculty = _get_current_faculty()
    question = ExamQuestion.query.get_or_404(id)
    if question.exam.created_by_id != faculty.user_id:
        abort(403)

    data = request.get_json(silent=True) or {}
    question.question_text = (data.get('question_text') or question.question_text).strip()
    question.marks = float(data.get('marks', question.marks))

    db.session.commit()
    return jsonify({'message': 'Question updated.'}), 200


@faculty_bp.route('/questions/<int:id>/delete', methods=['POST'])
@login_required
@faculty_required
def delete_question(id):
    faculty = _get_current_faculty()
    question = ExamQuestion.query.get_or_404(id)
    if question.exam.created_by_id != faculty.user_id:
        abort(403)
    db.session.delete(question)
    db.session.commit()
    return jsonify({'message': 'Question deleted.'}), 200


@faculty_bp.route('/examinations/<int:id>/attempts')
@login_required
@faculty_required
def exam_attempts(id):
    faculty = _get_current_faculty()
    exam = Exam.query.get_or_404(id)
    if exam.created_by_id != faculty.user_id:
        abort(403)

    attempts = ExamAttempt.query.filter_by(exam_id=id).all()

    if request.headers.get('Accept') == 'application/json':
        return jsonify([
            {
                'attempt_id': a.id,
                'student_id': a.student_id,
                'score': a.score,
                'total': a.total_marks,
                'percentage': a.percentage,
                'submitted_at': a.submitted_at.isoformat() if a.submitted_at else None,
                'status': a.status,
            }
            for a in attempts
        ]), 200

    return render_template('faculty/exam-attempts.html', exam=exam, attempts=attempts)


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------
@faculty_bp.route('/marks')
@login_required
@faculty_required
def marks():
    faculty = _get_current_faculty()
    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty.id).all()
    semesters = Semester.query.order_by(Semester.name).all()
    return render_template('faculty/marks.html', faculty=faculty, assignments=assignments, semesters=semesters)


@faculty_bp.route('/marks/add', methods=['POST'])
@login_required
@faculty_required
def add_marks():
    """
    Body: {student_id, subject_id, semester_id, academic_year_id,
           internal_marks, external_marks, practical_marks}
    """
    faculty = _get_current_faculty()
    data = request.get_json(silent=True) or request.form

    student_id = int(data.get('student_id', 0))
    subject_id = int(data.get('subject_id', 0))
    semester_id = int(data.get('semester_id', 0))
    academic_year_id = int(data.get('academic_year_id', 0))
    internal_marks = float(data.get('internal_marks', 0))
    external_marks = float(data.get('external_marks', 0))
    practical_marks = float(data.get('practical_marks', 0))

    if not all([student_id, subject_id, semester_id, academic_year_id]):
        return jsonify({'error': 'student_id, subject_id, semester_id, and academic_year_id are required.'}), 400

    result = Result.query.filter_by(
        student_id=student_id,
        subject_id=subject_id,
        semester_id=semester_id,
        academic_year_id=academic_year_id,
    ).first()

    if result:
        result.internal_marks = internal_marks
        result.external_marks = external_marks
        result.practical_marks = practical_marks
        result.total_marks = internal_marks + external_marks + practical_marks
        result.marked_by_id = faculty.user_id
        result.updated_at = datetime.datetime.utcnow()
    else:
        result = Result(
            student_id=student_id,
            subject_id=subject_id,
            semester_id=semester_id,
            academic_year_id=academic_year_id,
            internal_marks=internal_marks,
            external_marks=external_marks,
            practical_marks=practical_marks,
            total_marks=internal_marks + external_marks + practical_marks,
            marked_by_id=faculty.user_id,
            is_published=False,
        )
        db.session.add(result)

    db.session.commit()
    return jsonify({'message': 'Marks saved.', 'result_id': result.id}), 200


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@faculty_bp.route('/results')
@login_required
@faculty_required
def results():
    faculty = _get_current_faculty()
    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty.id).all()
    semesters = Semester.query.order_by(Semester.name).all()
    return render_template('faculty/results.html', faculty=faculty, assignments=assignments, semesters=semesters)


@faculty_bp.route('/results/publish', methods=['POST'])
@login_required
@faculty_required
def publish_results():
    """Body: {subject_id, semester_id, academic_year_id}"""
    faculty = _get_current_faculty()
    data = request.get_json(silent=True) or {}
    subject_id = int(data.get('subject_id', 0))
    semester_id = int(data.get('semester_id', 0))
    academic_year_id = int(data.get('academic_year_id', 0))

    if not all([subject_id, semester_id, academic_year_id]):
        return jsonify({'error': 'subject_id, semester_id, and academic_year_id are required.'}), 400

    updated = (
        Result.query
        .filter_by(
            subject_id=subject_id,
            semester_id=semester_id,
            academic_year_id=academic_year_id,
            marked_by_id=faculty.user_id,
        )
        .update({'is_published': True, 'published_at': datetime.datetime.utcnow()})
    )
    db.session.commit()
    return jsonify({'message': f'{updated} result(s) published.'}), 200


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------
@faculty_bp.route('/assignments')
@login_required
@faculty_required
def assignments():
    faculty = _get_current_faculty()
    all_assignments = (
        Assignment.query
        .filter_by(created_by_id=faculty.user_id)
        .order_by(Assignment.due_date.asc())
        .all()
    )
    return render_template('faculty/assignments.html', assignments=all_assignments)


@faculty_bp.route('/assignments/create', methods=['POST'])
@login_required
@faculty_required
def create_assignment():
    faculty = _get_current_faculty()
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    subject_id = request.form.get('subject_id', type=int)
    class_section_id = request.form.get('class_section_id', type=int)
    due_date = request.form.get('due_date')
    max_marks = request.form.get('max_marks', 100, type=int)

    if not all([title, subject_id, class_section_id, due_date]):
        flash('Title, subject, class, and due date are required.', 'danger')
        return redirect(url_for('faculty_bp.assignments'))

    file_url = None
    file = request.files.get('file')
    if file and file.filename:
        s3 = _s3_client()
        bucket = current_app.config['S3_BUCKET']
        key = f'assignments/{faculty.id}/{datetime.datetime.utcnow().timestamp()}_{file.filename}'
        try:
            s3.upload_fileobj(file, bucket, key, ExtraArgs={'ContentType': file.content_type})
            file_url = f"https://{bucket}.s3.amazonaws.com/{key}"
        except ClientError as e:
            current_app.logger.error('S3 upload failed: %s', e)
            flash('File upload failed. Please try again.', 'danger')
            return redirect(url_for('faculty_bp.assignments'))

    assignment = Assignment(
        title=title,
        description=description,
        subject_id=subject_id,
        class_section_id=class_section_id,
        created_by_id=faculty.user_id,
        due_date=datetime.date.fromisoformat(due_date),
        max_marks=max_marks,
        file_url=file_url,
    )
    db.session.add(assignment)
    db.session.commit()
    flash('Assignment created successfully.', 'success')
    return redirect(url_for('faculty_bp.assignments'))


# ---------------------------------------------------------------------------
# Study Materials
# ---------------------------------------------------------------------------
@faculty_bp.route('/materials')
@login_required
@faculty_required
def materials():
    faculty = _get_current_faculty()
    all_materials = (
        StudyMaterial.query
        .filter_by(uploaded_by_id=faculty.user_id)
        .order_by(StudyMaterial.uploaded_at.desc())
        .all()
    )
    return render_template('faculty/materials.html', materials=all_materials)


@faculty_bp.route('/materials/upload', methods=['POST'])
@login_required
@faculty_required
def upload_material():
    faculty = _get_current_faculty()
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    subject_id = request.form.get('subject_id', type=int)
    class_section_id = request.form.get('class_section_id', type=int)
    file = request.files.get('file')

    if not title or not subject_id or not file or not file.filename:
        return jsonify({'error': 'title, subject_id, and file are required.'}), 400

    s3 = _s3_client()
    bucket = current_app.config['S3_BUCKET']
    key = f'materials/{faculty.id}/{datetime.datetime.utcnow().timestamp()}_{file.filename}'
    try:
        s3.upload_fileobj(file, bucket, key, ExtraArgs={'ContentType': file.content_type})
        file_url = f"https://{bucket}.s3.amazonaws.com/{key}"
    except ClientError as e:
        current_app.logger.error('S3 upload failed: %s', e)
        return jsonify({'error': 'File upload failed.'}), 500

    material = StudyMaterial(
        title=title,
        description=description,
        subject_id=subject_id,
        class_section_id=class_section_id,
        uploaded_by_id=faculty.user_id,
        file_url=file_url,
        file_name=file.filename,
        s3_key=key,
    )
    db.session.add(material)
    db.session.commit()
    return jsonify({'message': 'Material uploaded.', 'material_id': material.id, 'url': file_url}), 201


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
@faculty_bp.route('/notifications')
@login_required
@faculty_required
def notifications():
    page = request.args.get('page', 1, type=int)
    faculty = _get_current_faculty()
    all_notifications = (
        Notification.query
        .filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .paginate(page=page, per_page=25)
    )
    return render_template('faculty/notifications.html', notifications=all_notifications)


@faculty_bp.route('/notifications/send', methods=['POST'])
@login_required
@faculty_required
def send_notification():
    faculty = _get_current_faculty()
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    message = (data.get('message') or '').strip()
    class_section_id = data.get('class_section_id', type=int) if hasattr(data, 'get') else data.get('class_section_id')

    if not title or not message:
        return jsonify({'error': 'title and message are required.'}), 400

    students = Student.query.filter_by(
        class_section_id=int(class_section_id) if class_section_id else None,
        academic_status='active',
    ).all() if class_section_id else []

    count = 0
    for student in students:
        notif = Notification(
            user_id=student.user_id,
            title=title,
            message=message,
            sent_by_id=current_user.id,
            is_read=False,
        )
        db.session.add(notif)
        count += 1

    db.session.commit()
    return jsonify({'message': f'Notification sent to {count} student(s).'}), 201


# ---------------------------------------------------------------------------
# API – Faculty's classes and subjects
# ---------------------------------------------------------------------------
@faculty_bp.route('/api/my-classes')
@login_required
@faculty_required
def api_my_classes():
    faculty = _get_current_faculty()
    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty.id).all()
    class_ids = list({a.class_section_id for a in assignments})
    sections = ClassSection.query.filter(ClassSection.id.in_(class_ids)).all()
    return jsonify([
        {'id': s.id, 'name': s.name, 'department': s.department.name if s.department else None}
        for s in sections
    ]), 200


@faculty_bp.route('/api/my-subjects')
@login_required
@faculty_required
def api_my_subjects():
    faculty = _get_current_faculty()
    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty.id).all()
    subject_ids = list({a.subject_id for a in assignments})
    subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
    return jsonify([
        {'id': s.id, 'name': s.name, 'code': s.code, 'credits': s.credits}
        for s in subjects
    ]), 200
