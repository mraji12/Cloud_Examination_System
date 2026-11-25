from datetime import datetime
from app.models import ExamAttempt, Result
from app.services.evaluation import EvaluationService
from app.extensions import db


def test_results_access_control(client, sample_exam, student_user, second_student_user, admin_user, auth, app):
    with app.app_context():
        attempt = ExamAttempt(
            student_id=student_user.id,
            exam_id=sample_exam.id,
            start_time=datetime.utcnow(),
            status='in_progress'
        )
        db.session.add(attempt)
        db.session.commit()
        result = EvaluationService.evaluate_attempt(attempt.id)
        result_id = result.id

    # 1. Student One can view their own result
    auth.login(student_user.email, 'StudentPass123!')
    resp1 = client.get(f'/results/{result_id}')
    assert resp1.status_code == 200
    assert student_user.name.encode() in resp1.data

    # 2. Student Two attempts to view Student One's result -> 403 Forbidden
    auth.logout()
    auth.login(second_student_user.email, 'StudentPass123!')
    resp2 = client.get(f'/results/{result_id}')
    assert resp2.status_code == 403

    # 3. Admin can view Student One's result
    auth.logout()
    auth.login(admin_user.email, 'AdminPass123!')
    resp3 = client.get(f'/results/{result_id}')
    assert resp3.status_code == 200
    assert student_user.name.encode() in resp3.data


def test_pdf_generation(client, sample_exam, student_user, auth, app):
    with app.app_context():
        attempt = ExamAttempt(
            student_id=student_user.id,
            exam_id=sample_exam.id,
            start_time=datetime.utcnow(),
            status='in_progress'
        )
        db.session.add(attempt)
        db.session.commit()
        result = EvaluationService.evaluate_attempt(attempt.id)
        result_id = result.id

    auth.login(student_user.email, 'StudentPass123!')
    resp = client.get(f'/results/{result_id}/pdf')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/pdf'
    assert resp.data.startswith(b'%PDF')


def test_csv_export(client, sample_exam, student_user, admin_user, auth, app):
    with app.app_context():
        attempt = ExamAttempt(
            student_id=student_user.id,
            exam_id=sample_exam.id,
            start_time=datetime.utcnow(),
            status='in_progress'
        )
        db.session.add(attempt)
        db.session.commit()
        EvaluationService.evaluate_attempt(attempt.id)

    auth.login(admin_user.email, 'AdminPass123!')
    resp = client.get('/admin/results/export/csv')
    assert resp.status_code == 200
    assert resp.mimetype == 'text/csv'
    assert b'Result ID,Student ID,Student Name' in resp.data
    assert student_user.name.encode() in resp.data
