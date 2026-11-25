import json
from datetime import datetime
from app.models import ExamAttempt, StudentAnswer
from app.services.evaluation import EvaluationService
from app.extensions import db


def test_admin_and_student_analytics(client, sample_exam, student_user, second_student_user, admin_user, auth, app):
    with app.app_context():
        # Attempt 1: Student 1 scores 100% (2/2) -> PASS
        att1 = ExamAttempt(student_id=student_user.id, exam_id=sample_exam.id, start_time=datetime.utcnow(), status='in_progress')
        db.session.add(att1)
        db.session.flush()
        db.session.add(StudentAnswer(attempt_id=att1.id, question_id=sample_exam.questions[0].id, selected_answer='B'))
        db.session.add(StudentAnswer(attempt_id=att1.id, question_id=sample_exam.questions[1].id, selected_answer='A'))
        db.session.commit()
        EvaluationService.evaluate_attempt(att1.id)

        # Attempt 2: Student 2 scores 0% (0/2) -> FAIL
        att2 = ExamAttempt(student_id=second_student_user.id, exam_id=sample_exam.id, start_time=datetime.utcnow(), status='in_progress')
        db.session.add(att2)
        db.session.flush()
        db.session.add(StudentAnswer(attempt_id=att2.id, question_id=sample_exam.questions[0].id, selected_answer='D'))
        db.session.commit()
        EvaluationService.evaluate_attempt(att2.id)

    # 1. Test Admin Analytics Data Endpoint
    auth.login(admin_user.email, 'AdminPass123!')
    resp = client.get('/admin/analytics/data')
    assert resp.status_code == 200
    data = json.loads(resp.data)

    # Pass vs Fail: 1 Pass, 1 Fail
    assert data['pass_fail']['data'] == [1, 1]
    # Exam average: (100 + 0) / 2 = 50.0%
    assert 50.0 in data['exam_averages']['data']

    # 2. Test Student Analytics Data Endpoint
    auth.logout()
    auth.login(student_user.email, 'StudentPass123!')
    s_resp = client.get('/student/performance/data')
    assert s_resp.status_code == 200
    s_data = json.loads(s_resp.data)
    assert 100.0 in s_data['timeline']['data']
