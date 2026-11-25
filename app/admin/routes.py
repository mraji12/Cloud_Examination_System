from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, Response, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.admin import admin_bp
from app.auth.decorators import admin_required
from app.models import User, Exam, Question, ExamAttempt, StudentAnswer, Result
from app.admin.forms import ExamForm, QuestionForm
from app.services.report_generator import ReportService


# -------------------------------------------------------------
# 9. ADMIN DASHBOARD
# -------------------------------------------------------------
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_students = User.query.filter_by(role='student').count()
    total_exams = Exam.query.count()
    published_exams = Exam.query.filter_by(status='published').count()
    draft_exams = Exam.query.filter_by(status='draft').count()
    closed_exams = Exam.query.filter_by(status='closed').count()
    total_questions = Question.query.count()
    completed_attempts = ExamAttempt.query.filter_by(status='submitted').count()

    recent_results = Result.query.order_by(Result.created_at.desc()).limit(7).all()
    recent_attempts = ExamAttempt.query.order_by(ExamAttempt.start_time.desc()).limit(7).all()

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_exams=total_exams,
        published_exams=published_exams,
        draft_exams=draft_exams,
        closed_exams=closed_exams,
        total_questions=total_questions,
        completed_attempts=completed_attempts,
        recent_results=recent_results,
        recent_attempts=recent_attempts
    )


# -------------------------------------------------------------
# STUDENT MANAGEMENT
# -------------------------------------------------------------
@admin_bp.route('/students')
@login_required
@admin_required
def students():
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'all')

    query = User.query.filter_by(role='student')

    if search_query:
        query = query.filter((User.name.ilike(f"%{search_query}%")) | (User.email.ilike(f"%{search_query}%")))

    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)

    students_list = query.order_by(User.created_at.desc()).all()
    return render_template('admin/students.html', students=students_list, search_query=search_query, status_filter=status_filter)


@admin_bp.route('/students/<int:student_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_student_status(student_id):
    student = db.get_or_404(User, student_id)
    if student.role != 'student':
        flash('Cannot alter administrator status here.', 'warning')
        return redirect(url_for('admin.students'))

    student.is_active = not student.is_active
    db.session.commit()
    state = "activated" if student.is_active else "deactivated"
    flash(f"Student '{student.name}' account has been {state}.", 'success')
    return redirect(url_for('admin.students'))


# -------------------------------------------------------------
# 11 & 12. ADMIN EXAMINATION MANAGEMENT
# -------------------------------------------------------------
@admin_bp.route('/exams')
@login_required
@admin_required
def exams():
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'all')

    query = Exam.query

    if search_query:
        query = query.filter((Exam.title.ilike(f"%{search_query}%")) | (Exam.subject.ilike(f"%{search_query}%")))

    if status_filter in ['draft', 'published', 'closed']:
        query = query.filter_by(status=status_filter)

    exams_list = query.order_by(Exam.created_at.desc()).all()
    return render_template('admin/exams.html', exams=exams_list, search_query=search_query, status_filter=status_filter)


@admin_bp.route('/exams/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_exam():
    form = ExamForm()
    if form.validate_on_submit():
        # Notice: When creating, cannot publish immediately if no questions exist
        if form.status.data == 'published':
            flash('A new examination must first be created with draft status and have questions added before publishing.', 'warning')
            form.status.data = 'draft'

        exam = Exam(
            title=form.title.data.strip(),
            subject=form.subject.data.strip(),
            description=form.description.data.strip() if form.description.data else '',
            duration=form.duration.data,
            total_marks=form.total_marks.data,
            passing_percentage=form.passing_percentage.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            status=form.status.data,
            allow_retake=form.allow_retake.data
        )
        db.session.add(exam)
        db.session.commit()
        flash(f"Examination '{exam.title}' created successfully! Now add questions to it.", 'success')
        return redirect(url_for('admin.exam_questions', exam_id=exam.id))

    return render_template('admin/exam_form.html', form=form, title='Create Examination', is_edit=False)


@admin_bp.route('/exams/<int:exam_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    form = ExamForm(obj=exam)

    if form.validate_on_submit():
        desired_status = form.status.data
        if desired_status == 'published':
            if len(exam.questions) == 0:
                flash('Cannot publish: Examination must have at least one question before publishing.', 'danger')
                return render_template('admin/exam_form.html', form=form, title=f"Edit {exam.title}", is_edit=True, exam=exam)
            if round(exam.calculated_total_marks, 2) != round(form.total_marks.data, 2):
                flash(f"Cannot publish: Total question marks ({exam.calculated_total_marks:.1f}) must equal configured examination total marks ({form.total_marks.data:.1f}).", 'danger')
                return render_template('admin/exam_form.html', form=form, title=f"Edit {exam.title}", is_edit=True, exam=exam)

        exam.title = form.title.data.strip()
        exam.subject = form.subject.data.strip()
        exam.description = form.description.data.strip() if form.description.data else ''
        exam.duration = form.duration.data
        exam.total_marks = form.total_marks.data
        exam.passing_percentage = form.passing_percentage.data
        exam.start_time = form.start_time.data
        exam.end_time = form.end_time.data
        exam.status = form.status.data
        exam.allow_retake = form.allow_retake.data

        db.session.commit()
        flash(f"Examination '{exam.title}' updated successfully.", 'success')
        return redirect(url_for('admin.exams'))

    return render_template('admin/exam_form.html', form=form, title=f"Edit {exam.title}", is_edit=True, exam=exam)


@admin_bp.route('/exams/<int:exam_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)

    # Validations before publishing
    if len(exam.questions) == 0:
        flash('Cannot publish: Examination has no questions. Please add questions first.', 'danger')
        return redirect(url_for('admin.exam_questions', exam_id=exam.id))

    if round(exam.calculated_total_marks, 2) != round(exam.total_marks, 2):
        flash(f"Cannot publish: Sum of question marks ({exam.calculated_total_marks:.1f}) does not equal configured examination total marks ({exam.total_marks:.1f}).", 'danger')
        return redirect(url_for('admin.exam_questions', exam_id=exam.id))

    exam.status = 'published'
    db.session.commit()
    flash(f"Examination '{exam.title}' is now published and accessible according to its schedule.", 'success')
    return redirect(url_for('admin.exams'))


@admin_bp.route('/exams/<int:exam_id>/unpublish', methods=['POST'])
@login_required
@admin_required
def unpublish_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    exam.status = 'draft'
    db.session.commit()
    flash(f"Examination '{exam.title}' status changed to Draft.", 'info')
    return redirect(url_for('admin.exams'))


@admin_bp.route('/exams/<int:exam_id>/close', methods=['POST'])
@login_required
@admin_required
def close_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    exam.status = 'closed'
    db.session.commit()
    flash(f"Examination '{exam.title}' has been closed.", 'warning')
    return redirect(url_for('admin.exams'))


@admin_bp.route('/exams/<int:exam_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    title = exam.title
    db.session.delete(exam)
    db.session.commit()
    flash(f"Examination '{title}' and all associated questions and attempts have been deleted.", 'info')
    return redirect(url_for('admin.exams'))


# -------------------------------------------------------------
# 13. QUESTION MANAGEMENT
# -------------------------------------------------------------
@admin_bp.route('/exams/<int:exam_id>/questions')
@login_required
@admin_required
def exam_questions(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    search_query = request.args.get('q', '').strip()

    questions = exam.questions
    if search_query:
        questions = [q for q in questions if search_query.lower() in q.question_text.lower()]

    calculated_total = exam.calculated_total_marks
    marks_difference = exam.total_marks - calculated_total

    return render_template(
        'admin/questions.html',
        exam=exam,
        questions=questions,
        calculated_total=calculated_total,
        marks_difference=marks_difference,
        search_query=search_query
    )


@admin_bp.route('/exams/<int:exam_id>/questions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_question(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    form = QuestionForm()

    if form.validate_on_submit():
        question = Question(
            exam_id=exam.id,
            question_text=form.question_text.data.strip(),
            option_a=form.option_a.data.strip(),
            option_b=form.option_b.data.strip(),
            option_c=form.option_c.data.strip(),
            option_d=form.option_d.data.strip(),
            correct_answer=form.correct_answer.data.strip().upper(),
            marks=form.marks.data
        )
        db.session.add(question)
        db.session.commit()
        flash('Question added successfully.', 'success')
        return redirect(url_for('admin.exam_questions', exam_id=exam.id))

    return render_template('admin/question_form.html', form=form, exam=exam, title='Add Question', is_edit=False)


@admin_bp.route('/questions/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_question(question_id):
    question = db.get_or_404(Question, question_id)
    exam = question.exam
    form = QuestionForm(obj=question)

    if form.validate_on_submit():
        question.question_text = form.question_text.data.strip()
        question.option_a = form.option_a.data.strip()
        question.option_b = form.option_b.data.strip()
        question.option_c = form.option_c.data.strip()
        question.option_d = form.option_d.data.strip()
        question.correct_answer = form.correct_answer.data.strip().upper()
        question.marks = form.marks.data

        db.session.commit()
        flash('Question updated successfully.', 'success')
        return redirect(url_for('admin.exam_questions', exam_id=exam.id))

    return render_template('admin/question_form.html', form=form, exam=exam, title='Edit Question', is_edit=True, question=question)


@admin_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_question(question_id):
    question = db.get_or_404(Question, question_id)
    exam_id = question.exam_id
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully.', 'info')
    return redirect(url_for('admin.exam_questions', exam_id=exam_id))


# -------------------------------------------------------------
# 22. ADMIN RESULT MANAGEMENT
# -------------------------------------------------------------
@admin_bp.route('/results')
@login_required
@admin_required
def results():
    student_query = request.args.get('student', '').strip()
    exam_query = request.args.get('exam', '').strip()
    subject_filter = request.args.get('subject', 'all')
    status_filter = request.args.get('status', 'all')

    query = Result.query.join(User, Result.student_id == User.id).join(Exam, Result.exam_id == Exam.id)

    if student_query:
        query = query.filter((User.name.ilike(f"%{student_query}%")) | (User.email.ilike(f"%{student_query}%")))

    if exam_query:
        query = query.filter(Exam.title.ilike(f"%{exam_query}%"))

    if subject_filter != 'all' and subject_filter:
        query = query.filter(Exam.subject == subject_filter)

    if status_filter in ['PASS', 'FAIL']:
        query = query.filter(Result.result_status == status_filter)

    results_list = query.order_by(Result.created_at.desc()).all()

    # Get distinct subjects for dropdown
    subjects = [s[0] for s in db.session.query(Exam.subject).distinct().all()]

    return render_template(
        'admin/results.html',
        results=results_list,
        subjects=subjects,
        student_query=student_query,
        exam_query=exam_query,
        subject_filter=subject_filter,
        status_filter=status_filter
    )


@admin_bp.route('/results/<int:result_id>')
@login_required
@admin_required
def result_detail(result_id):
    result = db.get_or_404(Result, result_id)
    exam = result.exam
    student = result.student
    attempt = result.attempt

    questions_with_answers = []
    answers_map = {a.question_id: a for a in attempt.answers} if attempt else {}

    for q in exam.questions:
        sa = answers_map.get(q.id)
        questions_with_answers.append({
            'question': q,
            'student_answer': sa.selected_answer if sa else None,
            'is_correct': sa.is_correct if sa else False,
            'marks_obtained': sa.marks_obtained if sa else 0.0
        })

    return render_template(
        'admin/result_detail.html',
        result=result,
        student=student,
        exam=exam,
        attempt=attempt,
        questions_with_answers=questions_with_answers
    )


@admin_bp.route('/results/export/csv')
@login_required
@admin_required
def export_csv():
    results_list = Result.query.order_by(Result.created_at.desc()).all()
    csv_data = ReportService.export_results_csv(results_list)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=cloudexam_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
    )


@admin_bp.route('/results/<int:result_id>/pdf')
@login_required
@admin_required
def download_result_pdf(result_id):
    result = db.get_or_404(Result, result_id)
    pdf_buffer = ReportService.generate_result_pdf(result)
    return Response(
        pdf_buffer,
        mimetype='application/pdf',
        headers={"Content-Disposition": f"attachment;filename=Result_{result.student.name.replace(' ', '_')}_Exam_{result.exam.id}.pdf"}
    )


# -------------------------------------------------------------
# 23. PERFORMANCE ANALYTICS (ADMIN)
# -------------------------------------------------------------
@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    total_exams = Exam.query.count()
    total_students = User.query.filter_by(role='student').count()
    total_attempts = ExamAttempt.query.filter_by(status='submitted').count()

    results = Result.query.all()
    if results:
        scores = [r.percentage for r in results]
        avg_marks = round(sum(scores) / len(scores), 2)
        highest_score = round(max(scores), 2)
        lowest_score = round(min(scores), 2)
        pass_count = sum(1 for r in results if r.result_status == 'PASS')
        fail_count = len(results) - pass_count
        pass_pct = round((pass_count / len(results)) * 100.0, 2)
    else:
        avg_marks = 0.0
        highest_score = 0.0
        lowest_score = 0.0
        pass_count = 0
        fail_count = 0
        pass_pct = 0.0

    return render_template(
        'admin/analytics.html',
        total_exams=total_exams,
        total_students=total_students,
        total_attempts=total_attempts,
        avg_marks=avg_marks,
        highest_score=highest_score,
        lowest_score=lowest_score,
        pass_count=pass_count,
        fail_count=fail_count,
        pass_pct=pass_pct
    )


@admin_bp.route('/analytics/data')
@login_required
@admin_required
def analytics_data():
    """Returns Chart.js data structures for admin analytics."""
    results = Result.query.all()

    # 1. Pass vs Fail Pie Chart
    pass_count = sum(1 for r in results if r.result_status == 'PASS')
    fail_count = sum(1 for r in results if r.result_status == 'FAIL')

    # 2. Examination-wise average marks
    exam_stats = db.session.query(
        Exam.title,
        func.avg(Result.percentage),
        func.count(Result.id)
    ).join(Result, Exam.id == Result.exam_id).group_by(Exam.id).all()

    exam_labels = [e[0] for e in exam_stats]
    exam_averages = [round(float(e[1]), 2) for e in exam_stats]
    exam_attempts = [int(e[2]) for e in exam_stats]

    # 3. Subject-wise performance
    subject_stats = db.session.query(
        Exam.subject,
        func.avg(Result.percentage)
    ).join(Result, Exam.id == Result.exam_id).group_by(Exam.subject).all()

    subject_labels = [s[0] for s in subject_stats]
    subject_averages = [round(float(s[1]), 2) for s in subject_stats]

    # 4. Student-wise performance (top/recent 10 students)
    student_stats = db.session.query(
        User.name,
        func.avg(Result.percentage)
    ).join(Result, User.id == Result.student_id).group_by(User.id).limit(10).all()

    student_labels = [s[0] for s in student_stats]
    student_averages = [round(float(s[1]), 2) for s in student_stats]

    return jsonify({
        'pass_fail': {
            'labels': ['Pass', 'Fail'],
            'data': [pass_count, fail_count]
        },
        'exam_averages': {
            'labels': exam_labels,
            'data': exam_averages
        },
        'exam_participation': {
            'labels': exam_labels,
            'data': exam_attempts
        },
        'subject_performance': {
            'labels': subject_labels,
            'data': subject_averages
        },
        'student_performance': {
            'labels': student_labels,
            'data': student_averages
        }
    })
