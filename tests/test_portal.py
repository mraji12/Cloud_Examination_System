import json
from datetime import datetime, timedelta
from app.models import ExamAttempt, StudentAnswer, Result
from app.extensions import db


def test_student_view_published_exams(client, student_user, sample_exam, auth):
    auth.login(student_user.email, 'StudentPass123!')
    response = client.get('/exams')
    assert response.status_code == 200
    assert sample_exam.title.encode() in response.data
    assert b'Available Now' in response.data


def test_student_start_exam_and_answer_saving(client, student_user, sample_exam, auth, app):
    auth.login(student_user.email, 'StudentPass123!')

    # Instructions page
    resp = client.get(f'/exams/{sample_exam.id}/instructions')
    assert resp.status_code == 200
    assert b'Examination Instructions' in resp.data

    # Start examination
    resp = client.post(f'/exams/{sample_exam.id}/start', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Question 1 of 2' in resp.data

    with app.app_context():
        attempt = ExamAttempt.query.filter_by(student_id=student_user.id, exam_id=sample_exam.id).first()
        assert attempt is not None
        assert attempt.status == 'in_progress'
        assert attempt.remaining_seconds > 0
        attempt_id = attempt.id
        q1_id = sample_exam.questions[0].id

    # Save answer via API
    api_resp = client.post(f'/exams/attempt/{attempt_id}/save-answer',
                           data=json.dumps({'question_id': q1_id, 'selected_answer': 'B'}),
                           content_type='application/json')
    assert api_resp.status_code == 200
    data = json.loads(api_resp.data)
    assert data['success'] is True
    assert data['answered_count'] == 1
    assert data['unanswered_count'] == 1

    with app.app_context():
        ans = StudentAnswer.query.filter_by(attempt_id=attempt_id, question_id=q1_id).first()
        assert ans is not None
        assert ans.selected_answer == 'B'


def test_duplicate_attempts_prevention(client, student_user, sample_exam, auth, app):
    auth.login(student_user.email, 'StudentPass123!')

    # Start and submit attempt
    client.post(f'/exams/{sample_exam.id}/start', follow_redirects=True)

    with app.app_context():
        attempt = ExamAttempt.query.filter_by(student_id=student_user.id, exam_id=sample_exam.id).first()
        attempt_id = attempt.id

    # Submit
    client.post(f'/exams/attempt/{attempt_id}/submit', follow_redirects=True)

    # Attempt to start again when allow_retake=False
    resp = client.post(f'/exams/{sample_exam.id}/start', follow_redirects=True)
    assert b'already taken this examination' in resp.data or b'Retakes are not enabled' in resp.data


def test_expired_attempt_handling(client, student_user, sample_exam, auth, app):
    auth.login(student_user.email, 'StudentPass123!')

    with app.app_context():
        # Create an attempt started 40 minutes ago for a 30-minute exam
        expired_start = datetime.utcnow() - timedelta(minutes=40)
        attempt = ExamAttempt(
            student_id=student_user.id,
            exam_id=sample_exam.id,
            start_time=expired_start,
            status='in_progress'
        )
        db.session.add(attempt)
        db.session.commit()
        attempt_id = attempt.id

    # Visiting take_exam on expired attempt must auto-submit and redirect to result
    resp = client.get(f'/exams/take/{attempt_id}', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Time has expired' in resp.data or b'Assessment Completed' in resp.data or b'Examination Assessment Result' in resp.data

    with app.app_context():
        updated_attempt = db.session.get(ExamAttempt, attempt_id)
        assert updated_attempt.status == 'submitted'
        res = Result.query.filter_by(attempt_id=attempt_id).first()
        assert res is not None
