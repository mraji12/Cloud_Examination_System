from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.exams import exams_bp
from app.auth.decorators import student_required
from app.models import Exam, ExamAttempt, Question, StudentAnswer, Result
from app.services.evaluation import EvaluationService


@exams_bp.route('')
@login_required
@student_required
def list_exams():
    exams = Exam.query.filter_by(status='published').order_by(Exam.start_time.asc()).all()
    exam_items = []
    student_id = current_user.id

    for exam in exams:
        status_label = exam.get_status_for_student(student_id)
        existing_attempt = ExamAttempt.query.filter_by(student_id=student_id, exam_id=exam.id).order_by(ExamAttempt.id.desc()).first()
        existing_result = Result.query.filter_by(student_id=student_id, exam_id=exam.id).order_by(Result.id.desc()).first()

        exam_items.append({
            'exam': exam,
            'status_label': status_label,
            'attempt': existing_attempt,
            'result': existing_result
        })

    return render_template('exams/list.html', exam_items=exam_items)


@exams_bp.route('/<int:exam_id>/instructions')
@login_required
@student_required
def instructions(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    student_id = current_user.id
    status_label = exam.get_status_for_student(student_id)

    # Check if student is allowed to start
    if status_label == 'Completed' and not exam.allow_retake:
        flash('You have already completed this examination and retakes are not permitted.', 'warning')
        return redirect(url_for('exams.list_exams'))

    if status_label in ['Upcoming', 'Closed']:
        flash(f'This examination is {status_label.lower()} and cannot be started at this time.', 'warning')
        return redirect(url_for('exams.list_exams'))

    return render_template('exams/instructions.html', exam=exam, status_label=status_label)


@exams_bp.route('/<int:exam_id>/start', methods=['POST'])
@login_required
@student_required
def start_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    student_id = current_user.id
    now = datetime.utcnow()

    # Verify accessibility
    if not exam.is_accessible_now():
        flash('This examination is currently not open for attempts.', 'danger')
        return redirect(url_for('exams.list_exams'))

    # Check for active existing attempt
    active_attempt = ExamAttempt.query.filter_by(
        student_id=student_id,
        exam_id=exam.id,
        status='in_progress'
    ).first()

    if active_attempt:
        if active_attempt.is_expired():
            result = EvaluationService.evaluate_attempt(active_attempt.id)
            flash('Your previous attempt expired and has been submitted automatically.', 'info')
            return redirect(url_for('results.view_result', result_id=result.id))
        return redirect(url_for('exams.take_exam', attempt_id=active_attempt.id))

    # Check if previously completed
    previous_completed = ExamAttempt.query.filter_by(
        student_id=student_id,
        exam_id=exam.id,
        status='submitted'
    ).first()

    if previous_completed and not exam.allow_retake:
        flash('You have already taken this examination. Retakes are not enabled.', 'warning')
        return redirect(url_for('exams.list_exams'))

    # Create new attempt
    attempt = ExamAttempt(
        student_id=student_id,
        exam_id=exam.id,
        start_time=now,
        status='in_progress'
    )
    db.session.add(attempt)
    db.session.commit()

    return redirect(url_for('exams.take_exam', attempt_id=attempt.id))


@exams_bp.route('/take/<int:attempt_id>')
@login_required
@student_required
def take_exam(attempt_id):
    attempt = db.get_or_404(ExamAttempt, attempt_id)
    if attempt.student_id != current_user.id:
        abort(403)

    # Check if already submitted or timed out
    if attempt.status != 'in_progress':
        result = Result.query.filter_by(attempt_id=attempt.id).first()
        if result:
            return redirect(url_for('results.view_result', result_id=result.id))
        flash('This attempt is no longer in progress.', 'info')
        return redirect(url_for('exams.list_exams'))

    # Server authoritative timer expiration check
    if attempt.is_expired():
        result = EvaluationService.evaluate_attempt(attempt.id)
        flash('Time has expired! Your examination has been automatically submitted.', 'warning')
        return redirect(url_for('results.view_result', result_id=result.id))

    exam = attempt.exam
    questions = exam.questions

    # Current saved answers
    answers = {a.question_id: a.selected_answer for a in attempt.answers}

    return render_template(
        'exams/take_exam.html',
        exam=exam,
        attempt=attempt,
        questions=questions,
        answers=answers,
        remaining_seconds=attempt.remaining_seconds
    )


# -------------------------------------------------------------
# JSON APIs FOR SAVING ANSWERS & TIMER SYNC
# -------------------------------------------------------------
@exams_bp.route('/attempt/<int:attempt_id>/sync', methods=['GET'])
@login_required
@student_required
def attempt_sync(attempt_id):
    attempt = db.get_or_404(ExamAttempt, attempt_id)
    if attempt.student_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if attempt.status != 'in_progress' or attempt.is_expired():
        result = EvaluationService.evaluate_attempt(attempt.id)
        return jsonify({
            'expired': True,
            'redirect_url': url_for('results.view_result', result_id=result.id)
        })

    return jsonify({
        'expired': False,
        'remaining_seconds': attempt.remaining_seconds
    })


@exams_bp.route('/attempt/<int:attempt_id>/save-answer', methods=['POST'])
@login_required
@student_required
def save_answer(attempt_id):
    attempt = db.get_or_404(ExamAttempt, attempt_id)
    if attempt.student_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if attempt.status != 'in_progress' or attempt.is_expired():
        result = EvaluationService.evaluate_attempt(attempt.id)
        return jsonify({
            'success': False,
            'expired': True,
            'message': 'Time has expired. Examination submitted automatically.',
            'redirect_url': url_for('results.view_result', result_id=result.id)
        })

    data = request.get_json() or {}
    question_id = data.get('question_id')
    selected_option = data.get('selected_answer')

    if not question_id:
        return jsonify({'error': 'question_id is required'}), 400

    question = Question.query.filter_by(id=question_id, exam_id=attempt.exam_id).first()
    if not question:
        return jsonify({'error': 'Invalid question for this exam'}), 404

    # Validate option (must be A, B, C, D or None/empty to unselect)
    clean_option = None
    if selected_option and selected_option.strip().upper() in ['A', 'B', 'C', 'D']:
        clean_option = selected_option.strip().upper()

    student_answer = StudentAnswer.query.filter_by(attempt_id=attempt.id, question_id=question.id).first()
    if not student_answer:
        student_answer = StudentAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_answer=clean_option
        )
        db.session.add(student_answer)
    else:
        student_answer.selected_answer = clean_option

    db.session.commit()

    # Recalculate answered vs unanswered
    all_answers = StudentAnswer.query.filter_by(attempt_id=attempt.id).all()
    answered_count = sum(1 for a in all_answers if a.selected_answer and a.selected_answer.strip())
    total_questions = len(attempt.exam.questions)
    unanswered_count = total_questions - answered_count

    return jsonify({
        'success': True,
        'question_id': question_id,
        'selected_answer': clean_option,
        'answered_count': answered_count,
        'unanswered_count': unanswered_count,
        'remaining_seconds': attempt.remaining_seconds
    })


@exams_bp.route('/attempt/<int:attempt_id>/submit', methods=['POST'])
@login_required
@student_required
def submit_exam(attempt_id):
    attempt = db.get_or_404(ExamAttempt, attempt_id)
    if attempt.student_id != current_user.id:
        abort(403)

    if attempt.status == 'submitted':
        result = Result.query.filter_by(attempt_id=attempt.id).first()
        if result:
            return redirect(url_for('results.view_result', result_id=result.id))

    result = EvaluationService.evaluate_attempt(attempt.id)
    flash('Examination submitted successfully! Your results have been evaluated.', 'success')
    return redirect(url_for('results.view_result', result_id=result.id))
