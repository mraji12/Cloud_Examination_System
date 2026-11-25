from datetime import datetime
from app.models import ExamAttempt, StudentAnswer, Result
from app.services.evaluation import EvaluationService
from app.extensions import db


def test_automatic_evaluation_perfect_score(app, sample_exam, student_user):
    with app.app_context():
        attempt = ExamAttempt(
            student_id=student_user.id,
            exam_id=sample_exam.id,
            start_time=datetime.utcnow(),
            status='in_progress'
        )
        db.session.add(attempt)
        db.session.flush()

        # Both answers correct: Q1 correct is B, Q2 correct is A
        q1 = sample_exam.questions[0]
        q2 = sample_exam.questions[1]

        db.session.add(StudentAnswer(attempt_id=attempt.id, question_id=q1.id, selected_answer='B'))
        db.session.add(StudentAnswer(attempt_id=attempt.id, question_id=q2.id, selected_answer='A'))
        db.session.commit()

        result = EvaluationService.evaluate_attempt(attempt.id)

        assert result.obtained_marks == 2.0
        assert result.total_marks == 2.0
        assert result.percentage == 100.0
        assert result.result_status == 'PASS'
        assert attempt.status == 'submitted'


def test_automatic_evaluation_mixed_and_unanswered(app, sample_exam, student_user):
    with app.app_context():
        attempt = ExamAttempt(
            student_id=student_user.id,
            exam_id=sample_exam.id,
            start_time=datetime.utcnow(),
            status='in_progress'
        )
        db.session.add(attempt)
        db.session.flush()

        # Q1: Wrong answer ('C'), Q2: Unanswered (None)
        q1 = sample_exam.questions[0]
        db.session.add(StudentAnswer(attempt_id=attempt.id, question_id=q1.id, selected_answer='C'))
        db.session.commit()

        result = EvaluationService.evaluate_attempt(attempt.id)

        assert result.obtained_marks == 0.0
        assert result.percentage == 0.0
        assert result.result_status == 'FAIL'


def test_duplicate_evaluation_prevention(app, sample_exam, student_user):
    with app.app_context():
        attempt = ExamAttempt(
            student_id=student_user.id,
            exam_id=sample_exam.id,
            start_time=datetime.utcnow(),
            status='in_progress'
        )
        db.session.add(attempt)
        db.session.commit()

        result1 = EvaluationService.evaluate_attempt(attempt.id)
        result2 = EvaluationService.evaluate_attempt(attempt.id)

        assert result1.id == result2.id
        assert Result.query.filter_by(attempt_id=attempt.id).count() == 1
