import pytest
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import User, Exam, Question, ExamAttempt, StudentAnswer, Result


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app):
    admin = User(
        name='Test Admin',
        email='admin@example.com',
        role='admin',
        is_active=True
    )
    admin.set_password('AdminPass123!')
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def student_user(app):
    student = User(
        name='Student One',
        email='student1@example.com',
        role='student',
        is_active=True
    )
    student.set_password('StudentPass123!')
    db.session.add(student)
    db.session.commit()
    return student


@pytest.fixture
def second_student_user(app):
    student = User(
        name='Student Two',
        email='student2@example.com',
        role='student',
        is_active=True
    )
    student.set_password('StudentPass123!')
    db.session.add(student)
    db.session.commit()
    return student


@pytest.fixture
def sample_exam(app):
    now = datetime.utcnow()
    exam = Exam(
        title='Sample Test Exam',
        subject='Computer Science',
        description='A test examination for automated test suite verification.',
        duration=30,
        total_marks=2.0,
        passing_percentage=50.0,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=5),
        status='published',
        allow_retake=False
    )
    db.session.add(exam)
    db.session.flush()

    q1 = Question(
        exam_id=exam.id,
        question_text='What is 2 + 2?',
        option_a='3',
        option_b='4',
        option_c='5',
        option_d='6',
        correct_answer='B',
        marks=1.0
    )
    q2 = Question(
        exam_id=exam.id,
        question_text='Which language is used for Flask backend?',
        option_a='Python',
        option_b='Java',
        option_c='C++',
        option_d='PHP',
        correct_answer='A',
        marks=1.0
    )
    db.session.add_all([q1, q2])
    db.session.commit()
    return exam


class AuthHelper:
    def __init__(self, client):
        self.client = client

    def login(self, email, password):
        return self.client.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)


@pytest.fixture
def auth(client):
    return AuthHelper(client)
