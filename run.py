import os
import sys
import click
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import User, Exam, Question, ExamAttempt, StudentAnswer, Result
from app.services.evaluation import EvaluationService

app = create_app()


@app.cli.command('create-admin')
@click.option('--email', prompt=True, help='Administrator email address')
@click.option('--name', prompt=True, default='CloudExam Admin', help='Administrator name')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Administrator password')
def create_admin(email, name, password):
    """Create a secure administrator account."""
    email = email.strip().lower()
    if len(password) < 8:
        click.echo(click.style("Error: Password must be at least 8 characters long.", fg='red'))
        return

    existing = User.query.filter_by(email=email).first()
    if existing:
        if existing.role == 'admin':
            click.echo(click.style(f"Administrator with email {email} already exists.", fg='yellow'))
            return
        existing.role = 'admin'
        existing.set_password(password)
        db.session.commit()
        click.echo(click.style(f"User {email} has been promoted to Administrator.", fg='green'))
        return

    admin = User(
        name=name.strip(),
        email=email,
        role='admin',
        is_active=True
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(click.style(f"Administrator account '{name}' ({email}) created successfully!", fg='green'))


@app.cli.command('seed-data')
def seed_data():
    """Populate database with sample examinations, questions, students and sample attempts."""
    click.echo("Seeding sample data...")

    # 1. Ensure Admin exists
    admin_email = 'admin@cloudexam.edu'
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(
            name='System Administrator',
            email=admin_email,
            role='admin',
            is_active=True
        )
        admin.set_password('AdminSecure2026!')
        db.session.add(admin)
        click.echo(f"Created default admin: {admin_email} / AdminSecure2026!")

    # 2. Ensure Sample Students exist
    student_creds = [
        ('Aarav Sharma', 'aarav@cloudexam.edu', 'StudentPass123!'),
        ('Priya Patel', 'priya@cloudexam.edu', 'StudentPass123!'),
        ('Rohan Verma', 'rohan@cloudexam.edu', 'StudentPass123!'),
    ]
    created_students = []
    for name, email, pwd in student_creds:
        student = User.query.filter_by(email=email).first()
        if not student:
            student = User(
                name=name,
                email=email,
                role='student',
                is_active=True
            )
            student.set_password(pwd)
            db.session.add(student)
            click.echo(f"Created sample student: {email} / {pwd}")
        created_students.append(student)

    db.session.commit()

    # 3. Create Sample Exams
    now = datetime.utcnow()

    # Exam 1: Available Now (Python Programming Assessment)
    exam1 = Exam.query.filter_by(title='Python Core & Advanced Concepts').first()
    if not exam1:
        exam1 = Exam(
            title='Python Core & Advanced Concepts',
            subject='Computer Science',
            description='Comprehensive evaluation of Python data types, OOP, list comprehensions, decorators, and memory management.',
            duration=30,  # 30 minutes
            total_marks=5.0,
            passing_percentage=40.0,
            start_time=now - timedelta(hours=2),
            end_time=now + timedelta(days=7),
            status='published',
            allow_retake=False
        )
        db.session.add(exam1)
        db.session.flush()

        questions_exam1 = [
            ("What is the output of print(type([]) is list)?", "True", "False", "TypeError", "None", "A", 1.0),
            ("Which built-in Python module is used for regular expressions?", "regex", "re", "pyregex", "match", "B", 1.0),
            ("How is memory managed in Python?", "Manual allocation only", "Garbage collection and reference counting", "Static stack only", "Direct pointer manipulation", "B", 1.0),
            ("Which keyword is used to create an anonymous function in Python?", "def", "func", "lambda", "inline", "C", 1.0),
            ("What does the *args parameter in a Python function definition allow?", "Keyword arguments as a dict", "Variable number of non-keyword arguments as a tuple", "Default parameters", "Global scope access", "B", 1.0),
        ]
        for q_text, a, b, c, d, correct, marks in questions_exam1:
            q = Question(
                exam_id=exam1.id,
                question_text=q_text,
                option_a=a,
                option_b=b,
                option_c=c,
                option_d=d,
                correct_answer=correct,
                marks=marks
            )
            db.session.add(q)
        click.echo("Created Exam 1: Python Core & Advanced Concepts with 5 questions.")

    # Exam 2: Cloud Computing & Systems (Published)
    exam2 = Exam.query.filter_by(title='Cloud Architecture & Web Fundamentals').first()
    if not exam2:
        exam2 = Exam(
            title='Cloud Architecture & Web Fundamentals',
            subject='Cloud Computing',
            description='Test your understanding of HTTP protocols, RESTful APIs, scalability, load balancing, and cloud storage principles.',
            duration=20,
            total_marks=4.0,
            passing_percentage=50.0,
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(days=5),
            status='published',
            allow_retake=True
        )
        db.session.add(exam2)
        db.session.flush()

        questions_exam2 = [
            ("Which HTTP status code represents 'Internal Server Error'?", "400", "404", "500", "502", "C", 1.0),
            ("What is the primary benefit of horizontal scaling compared to vertical scaling?", "Upgrading CPU on a single machine", "Adding more servers to distribute traffic", "Using in-memory caching", "Reducing bandwidth", "B", 1.0),
            ("Which HTTP method is typically idempotent in REST API design?", "POST", "GET", "PATCH", "CONNECT", "B", 1.0),
            ("What does SaaS stand for in cloud service models?", "Software as a Service", "Storage as a System", "Security as a Standard", "Server as a Service", "A", 1.0),
        ]
        for q_text, a, b, c, d, correct, marks in questions_exam2:
            q = Question(
                exam_id=exam2.id,
                question_text=q_text,
                option_a=a,
                option_b=b,
                option_c=c,
                option_d=d,
                correct_answer=correct,
                marks=marks
            )
            db.session.add(q)
        click.echo("Created Exam 2: Cloud Architecture & Web Fundamentals with 4 questions.")

    # Exam 3: Upcoming Exam
    exam3 = Exam.query.filter_by(title='Database Engineering & SQL Mastery').first()
    if not exam3:
        exam3 = Exam(
            title='Database Engineering & SQL Mastery',
            subject='Database Systems',
            description='Relational database design, normalization, ACID properties, indexing, and complex queries.',
            duration=45,
            total_marks=3.0,
            passing_percentage=60.0,
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=9),
            status='published',
            allow_retake=False
        )
        db.session.add(exam3)
        db.session.flush()

        questions_exam3 = [
            ("Which normal form eliminates partial dependency on a composite key?", "1NF", "2NF", "3NF", "BCNF", "B", 1.0),
            ("What does the 'I' represent in ACID transaction properties?", "Integrity", "Isolation", "Index", "Idempotence", "B", 1.0),
            ("Which SQL clause is used to filter groups created by GROUP BY?", "WHERE", "ORDER BY", "HAVING", "LIMIT", "C", 1.0),
        ]
        for q_text, a, b, c, d, correct, marks in questions_exam3:
            q = Question(
                exam_id=exam3.id,
                question_text=q_text,
                option_a=a,
                option_b=b,
                option_c=c,
                option_d=d,
                correct_answer=correct,
                marks=marks
            )
            db.session.add(q)
        click.echo("Created Exam 3: Upcoming Database Engineering exam.")

    # Exam 4: Draft Exam
    exam4 = Exam.query.filter_by(title='Data Structures & Algorithm Analysis').first()
    if not exam4:
        exam4 = Exam(
            title='Data Structures & Algorithm Analysis',
            subject='Algorithms',
            description='Draft exam for algorithmic complexity, trees, graphs, and sorting algorithms.',
            duration=60,
            total_marks=10.0,
            passing_percentage=50.0,
            start_time=now + timedelta(days=7),
            end_time=now + timedelta(days=14),
            status='draft',
            allow_retake=False
        )
        db.session.add(exam4)
        click.echo("Created Exam 4: Draft Algorithms exam.")

    db.session.commit()

    # 4. Create sample attempt and result for the first student on Exam 2 for immediate dashboard metrics
    s1 = created_students[0]
    existing_attempt = ExamAttempt.query.filter_by(student_id=s1.id, exam_id=exam2.id).first()
    if not existing_attempt:
        attempt = ExamAttempt(
            student_id=s1.id,
            exam_id=exam2.id,
            start_time=now - timedelta(minutes=18),
            submission_time=now - timedelta(minutes=3),
            status='submitted'
        )
        db.session.add(attempt)
        db.session.flush()

        # Add answers (3 correct, 1 incorrect)
        q_list = exam2.questions
        # Q1: C (correct)
        db.session.add(StudentAnswer(attempt_id=attempt.id, question_id=q_list[0].id, selected_answer='C'))
        # Q2: B (correct)
        db.session.add(StudentAnswer(attempt_id=attempt.id, question_id=q_list[1].id, selected_answer='B'))
        # Q3: B (correct)
        db.session.add(StudentAnswer(attempt_id=attempt.id, question_id=q_list[2].id, selected_answer='B'))
        # Q4: B (incorrect, correct is A)
        db.session.add(StudentAnswer(attempt_id=attempt.id, question_id=q_list[3].id, selected_answer='B'))

        db.session.commit()
        EvaluationService.evaluate_attempt(attempt.id)
        click.echo("Seeded completed attempt and result for Aarav Sharma on Exam 2.")

    # Also seed a sample attempt for Priya on Exam 2
    s2 = created_students[1]
    existing_attempt2 = ExamAttempt.query.filter_by(student_id=s2.id, exam_id=exam2.id).first()
    if not existing_attempt2:
        attempt2 = ExamAttempt(
            student_id=s2.id,
            exam_id=exam2.id,
            start_time=now - timedelta(minutes=25),
            submission_time=now - timedelta(minutes=10),
            status='submitted'
        )
        db.session.add(attempt2)
        db.session.flush()

        q_list = exam2.questions
        # 4 correct
        for q in q_list:
            db.session.add(StudentAnswer(attempt_id=attempt2.id, question_id=q.id, selected_answer=q.correct_answer))

        db.session.commit()
        EvaluationService.evaluate_attempt(attempt2.id)
        click.echo("Seeded completed attempt and result for Priya Patel on Exam 2.")

    click.echo(click.style("Data seeding completed successfully!", fg='green'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    if len(sys.argv) > 1 and sys.argv[1] != 'run':
        app.cli()
    else:
        app.run(host='127.0.0.1', port=5000, debug=True)
