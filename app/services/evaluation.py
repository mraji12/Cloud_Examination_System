from datetime import datetime
from app.extensions import db
from app.models import ExamAttempt, StudentAnswer, Result, Question


class EvaluationService:
    @staticmethod
    def evaluate_attempt(attempt_id):
        """
        Evaluates an exam attempt atomically within a database transaction.
        Calculates:
          - correct answers count
          - incorrect answers count
          - unanswered count
          - obtained marks
          - total marks
          - percentage
          - pass/fail status
        Updates attempt status and creates or updates the Result record.
        """
        attempt = db.session.get(ExamAttempt, attempt_id)
        if not attempt:
            raise ValueError(f"Attempt {attempt_id} not found.")

        # Check for existing result to prevent duplicate evaluation
        existing_result = Result.query.filter_by(attempt_id=attempt_id).first()
        if existing_result:
            return existing_result

        exam = attempt.exam
        questions = exam.questions
        total_questions = len(questions)

        # Map questions by ID
        question_map = {q.id: q for q in questions}

        # Map student answers by question_id
        student_answers = StudentAnswer.query.filter_by(attempt_id=attempt_id).all()
        answers_map = {sa.question_id: sa for sa in student_answers}

        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0
        obtained_marks = 0.0
        total_marks = 0.0

        for q in questions:
            total_marks += float(q.marks)
            sa = answers_map.get(q.id)

            if not sa or not sa.selected_answer or sa.selected_answer.strip() == '':
                unanswered_count += 1
                if sa:
                    sa.is_correct = False
                    sa.marks_obtained = 0.0
            else:
                selected = sa.selected_answer.strip().upper()
                if selected == q.correct_answer.strip().upper():
                    correct_count += 1
                    sa.is_correct = True
                    sa.marks_obtained = float(q.marks)
                    obtained_marks += float(q.marks)
                else:
                    incorrect_count += 1
                    sa.is_correct = False
                    sa.marks_obtained = 0.0

        # Edge case: if total_marks is 0, fall back to configured exam total_marks
        if total_marks == 0.0:
            total_marks = float(exam.total_marks) or 1.0

        percentage = round((obtained_marks / total_marks) * 100.0, 2)
        result_status = 'PASS' if percentage >= float(exam.passing_percentage) else 'FAIL'

        # Update attempt details
        attempt.status = 'submitted'
        if not attempt.submission_time:
            attempt.submission_time = datetime.utcnow()
        attempt.score = obtained_marks

        result = Result(
            student_id=attempt.student_id,
            exam_id=attempt.exam_id,
            attempt_id=attempt.id,
            total_marks=total_marks,
            obtained_marks=obtained_marks,
            percentage=percentage,
            result_status=result_status,
            created_at=datetime.utcnow()
        )

        db.session.add(result)
        db.session.commit()

        return result
