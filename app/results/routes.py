from flask import render_template, redirect, url_for, flash, abort, Response
from flask_login import login_required, current_user
from app.extensions import db
from app.results import results_bp
from app.models import Result
from app.services.report_generator import ReportService


@results_bp.route('/<int:result_id>')
@login_required
def view_result(result_id):
    result = db.get_or_404(Result, result_id)

    # Security: student can only view their own results; admin can view any
    if not current_user.is_admin and result.student_id != current_user.id:
        abort(403)

    student = result.student
    exam = result.exam
    attempt = result.attempt

    # Compute breakdown counts
    answers = attempt.answers if attempt else []
    correct_count = sum(1 for a in answers if a.is_correct)
    unanswered_count = sum(1 for a in answers if not a.selected_answer or not a.selected_answer.strip())
    total_q = len(exam.questions)
    incorrect_count = max(0, total_q - correct_count - unanswered_count)

    # Duration taken
    if attempt and attempt.submission_time and attempt.start_time:
        duration_minutes = round((attempt.submission_time - attempt.start_time).total_seconds() / 60, 1)
    else:
        duration_minutes = 0.0

    return render_template(
        'results/view.html',
        result=result,
        student=student,
        exam=exam,
        attempt=attempt,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        unanswered_count=unanswered_count,
        total_questions=total_q,
        duration_minutes=duration_minutes
    )


@results_bp.route('/<int:result_id>/pdf')
@login_required
def download_pdf(result_id):
    result = db.get_or_404(Result, result_id)

    # Security check: student can only download their own PDF; admin can download any
    if not current_user.is_admin and result.student_id != current_user.id:
        abort(403)

    pdf_buffer = ReportService.generate_result_pdf(result)
    filename = f"CloudExam_Result_{result.student.name.replace(' ', '_')}_{result.exam.id}.pdf"

    return Response(
        pdf_buffer,
        mimetype='application/pdf',
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@results_bp.route('/history')
@login_required
def history():
    if current_user.is_admin:
        return redirect(url_for('admin.results'))

    results_list = Result.query.filter_by(student_id=current_user.id).order_by(Result.created_at.desc()).all()
    return render_template('results/history.html', results=results_list)
