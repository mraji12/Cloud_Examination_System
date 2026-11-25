from datetime import datetime, timedelta
from app.models import Exam, Question
from app.extensions import db


def test_create_examination(client, admin_user, auth, app):
    auth.login(admin_user.email, 'AdminPass123!')
    now = datetime.utcnow()
    start = (now + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
    end = (now + timedelta(hours=4)).strftime('%Y-%m-%dT%H:%M')

    response = client.post('/admin/exams/create', data={
        'title': 'Operating Systems Fundamentals',
        'subject': 'Computer Science',
        'description': 'Processes, threads, and virtual memory.',
        'duration': 45,
        'total_marks': 5.0,
        'passing_percentage': 50.0,
        'start_time': start,
        'end_time': end,
        'status': 'draft'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'created successfully' in response.data

    with app.app_context():
        exam = Exam.query.filter_by(title='Operating Systems Fundamentals').first()
        assert exam is not None
        assert exam.duration == 45
        assert exam.status == 'draft'


def test_edit_examination(client, admin_user, sample_exam, auth, app):
    auth.login(admin_user.email, 'AdminPass123!')
    start = sample_exam.start_time.strftime('%Y-%m-%dT%H:%M')
    end = sample_exam.end_time.strftime('%Y-%m-%dT%H:%M')

    response = client.post(f'/admin/exams/{sample_exam.id}/edit', data={
        'title': 'Sample Test Exam Updated',
        'subject': 'Software Engineering',
        'description': 'Updated overview.',
        'duration': 40,
        'total_marks': 2.0,
        'passing_percentage': 50.0,
        'start_time': start,
        'end_time': end,
        'status': 'published'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'updated successfully' in response.data

    with app.app_context():
        updated = db.session.get(Exam, sample_exam.id)
        assert updated.title == 'Sample Test Exam Updated'
        assert updated.duration == 40


def test_publish_validation(client, admin_user, auth, app):
    auth.login(admin_user.email, 'AdminPass123!')
    now = datetime.utcnow()
    
    with app.app_context():
        # Create an exam with total_marks=10.0 and no questions
        empty_exam = Exam(
            title='Empty Exam',
            subject='CS',
            duration=30,
            total_marks=10.0,
            passing_percentage=50.0,
            start_time=now,
            end_time=now + timedelta(days=1),
            status='draft'
        )
        db.session.add(empty_exam)
        db.session.commit()
        exam_id = empty_exam.id

    # Attempt to publish empty exam
    response = client.post(f'/admin/exams/{exam_id}/publish', follow_redirects=True)
    assert b'Cannot publish: Examination has no questions' in response.data

    # Add a question with 5 marks (configured total is 10)
    with app.app_context():
        q = Question(
            exam_id=exam_id,
            question_text='Sample Q?',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A',
            marks=5.0
        )
        db.session.add(q)
        db.session.commit()

    # Attempt to publish when sum of question marks (5.0) != total_marks (10.0)
    response = client.post(f'/admin/exams/{exam_id}/publish', follow_redirects=True)
    assert b'does not equal configured examination total marks' in response.data

    # Fix marks to 10.0 and publish
    with app.app_context():
        q_obj = Question.query.filter_by(exam_id=exam_id).first()
        q_obj.marks = 10.0
        db.session.commit()

    response = client.post(f'/admin/exams/{exam_id}/publish', follow_redirects=True)
    assert b'is now published' in response.data


def test_question_crud(client, admin_user, sample_exam, auth, app):
    auth.login(admin_user.email, 'AdminPass123!')

    # Add Question
    response = client.post(f'/admin/exams/{sample_exam.id}/questions/add', data={
        'question_text': 'What does HTTP stand for?',
        'option_a': 'HyperText Transfer Protocol',
        'option_b': 'HyperText Testing Protocol',
        'option_c': 'High Transfer Text Protocol',
        'option_d': 'Home Tool Transfer Protocol',
        'correct_answer': 'A',
        'marks': 1.0
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Question added successfully' in response.data

    with app.app_context():
        q = Question.query.filter_by(question_text='What does HTTP stand for?').first()
        assert q is not None
        assert q.correct_answer == 'A'
        q_id = q.id

    # Edit Question
    response = client.post(f'/admin/questions/{q_id}/edit', data={
        'question_text': 'What does HTTP stand for? (Updated)',
        'option_a': 'HyperText Transfer Protocol',
        'option_b': 'HyperText Testing Protocol',
        'option_c': 'High Transfer Text Protocol',
        'option_d': 'Home Tool Transfer Protocol',
        'correct_answer': 'A',
        'marks': 2.0
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Question updated successfully' in response.data

    # Delete Question
    response = client.post(f'/admin/questions/{q_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Question deleted successfully' in response.data


def test_delete_examination(client, admin_user, sample_exam, auth, app):
    auth.login(admin_user.email, 'AdminPass123!')
    exam_id = sample_exam.id

    response = client.post(f'/admin/exams/{exam_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'have been deleted' in response.data

    with app.app_context():
        assert db.session.get(Exam, exam_id) is None
        assert Question.query.filter_by(exam_id=exam_id).count() == 0


def test_unpublish_and_close_examination(client, admin_user, sample_exam, auth, app):
    auth.login(admin_user.email, 'AdminPass123!')
    exam_id = sample_exam.id

    # Unpublish
    response_unpub = client.post(f'/admin/exams/{exam_id}/unpublish', follow_redirects=True)
    assert response_unpub.status_code == 200
    assert b'status changed to Draft' in response_unpub.data
    with app.app_context():
        exam = db.session.get(Exam, exam_id)
        assert exam.status == 'draft'

    # Close
    response_close = client.post(f'/admin/exams/{exam_id}/close', follow_redirects=True)
    assert response_close.status_code == 200
    assert b'has been closed' in response_close.data
    with app.app_context():
        exam = db.session.get(Exam, exam_id)
        assert exam.status == 'closed'


def test_invalid_examination_date_validation(client, admin_user, auth):
    auth.login(admin_user.email, 'AdminPass123!')
    now = datetime.utcnow()
    start = (now + timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M')
    end = (now + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')  # end is before start!

    response = client.post('/admin/exams/create', data={
        'title': 'Bad Schedule Exam',
        'subject': 'Physics',
        'description': 'Testing invalid dates',
        'duration': 30,
        'total_marks': 5.0,
        'passing_percentage': 40.0,
        'start_time': start,
        'end_time': end,
        'status': 'draft'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'End date &amp; time must be strictly after the start date &amp; time' in response.data or b'End date' in response.data


def test_question_search_and_invalid_data(client, admin_user, sample_exam, auth):
    auth.login(admin_user.email, 'AdminPass123!')

    # Question search
    response_search = client.get(f'/admin/exams/{sample_exam.id}/questions?q=Flask')
    assert response_search.status_code == 200
    assert b'Which language is used for Flask backend?' in response_search.data
    assert b'What is 2 + 2?' not in response_search.data

    # Add question missing required option
    response_invalid = client.post(f'/admin/exams/{sample_exam.id}/questions/add', data={
        'question_text': 'Incomplete Question?',
        'option_a': 'Option 1',
        'option_b': '',  # missing option B
        'option_c': 'Option 3',
        'option_d': 'Option 4',
        'correct_answer': 'A',
        'marks': 1.0
    }, follow_redirects=True)

    assert response_invalid.status_code == 200
    assert b'Option B is required' in response_invalid.data
