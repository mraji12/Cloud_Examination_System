from datetime import datetime
from flask import render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.student import student_bp
from app.auth.decorators import student_required
from app.models import Exam, ExamAttempt, Result


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    now = datetime.utcnow()
    student_id = current_user.id

    # All published exams
    published_exams = Exam.query.filter_by(status='published').all()

    available_exams = []
    upcoming_exams = []
    completed_exams = []

    for exam in published_exams:
        status_for_student = exam.get_status_for_student(student_id)
        if status_for_student in ['Available', 'In Progress']:
            available_exams.append(exam)
        elif status_for_student == 'Upcoming':
            upcoming_exams.append(exam)
        elif status_for_student == 'Completed':
            completed_exams.append(exam)

    # Student results
    student_results = Result.query.filter_by(student_id=student_id).order_by(Result.created_at.desc()).all()

    if student_results:
        percentages = [r.percentage for r in student_results]
        avg_score = round(sum(percentages) / len(percentages), 2)
        passed_count = sum(1 for r in student_results if r.result_status == 'PASS')
        pass_rate = round((passed_count / len(student_results)) * 100.0, 1)
    else:
        avg_score = 0.0
        pass_rate = 0.0

    latest_results = student_results[:5]

    return render_template(
        'student/dashboard.html',
        available_exams=available_exams,
        upcoming_exams=upcoming_exams,
        completed_exams=completed_exams,
        latest_results=latest_results,
        avg_score=avg_score,
        pass_rate=pass_rate,
        total_completed=len(student_results)
    )


@student_bp.route('/performance')
@login_required
@student_required
def performance():
    student_id = current_user.id
    results = Result.query.filter_by(student_id=student_id).order_by(Result.created_at.asc()).all()

    if results:
        percentages = [r.percentage for r in results]
        avg_marks = round(sum(percentages) / len(percentages), 2)
        highest_marks = round(max(percentages), 2)
        lowest_marks = round(min(percentages), 2)
        pass_count = sum(1 for r in results if r.result_status == 'PASS')
        fail_count = len(results) - pass_count
    else:
        avg_marks = 0.0
        highest_marks = 0.0
        lowest_marks = 0.0
        pass_count = 0
        fail_count = 0

    return render_template(
        'student/performance.html',
        results=results,
        avg_marks=avg_marks,
        highest_marks=highest_marks,
        lowest_marks=lowest_marks,
        pass_count=pass_count,
        fail_count=fail_count
    )


@student_bp.route('/performance/data')
@login_required
@student_required
def performance_data():
    student_id = current_user.id
    results = Result.query.filter_by(student_id=student_id).order_by(Result.created_at.asc()).all()

    # Progress timeline: Exam titles and scores
    timeline_labels = [r.exam.title for r in results]
    timeline_scores = [r.percentage for r in results]

    # Subject-wise performance
    subject_stats = db.session.query(
        Exam.subject,
        func.avg(Result.percentage)
    ).join(Result, Exam.id == Result.exam_id).filter(Result.student_id == student_id).group_by(Exam.subject).all()

    subject_labels = [s[0] for s in subject_stats]
    subject_scores = [round(float(s[1]), 2) for s in subject_stats]

    return jsonify({
        'timeline': {
            'labels': timeline_labels,
            'data': timeline_scores
        },
        'subject_performance': {
            'labels': subject_labels,
            'data': subject_scores
        }
    })
