from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'admin' or 'student'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    attempts = db.relationship('ExamAttempt', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    results = db.relationship('Result', backref='student', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_student(self):
        return self.role == 'student'

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Exam(db.Model):
    __tablename__ = 'exams'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration in minutes
    total_marks = db.Column(db.Float, nullable=False, default=0.0)
    passing_percentage = db.Column(db.Float, nullable=False, default=40.0)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='draft')  # 'draft', 'published', 'closed'
    allow_retake = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    questions = db.relationship('Question', backref='exam', lazy='joined', cascade='all, delete-orphan', order_by='Question.id')
    attempts = db.relationship('ExamAttempt', backref='exam', lazy='dynamic', cascade='all, delete-orphan')
    results = db.relationship('Result', backref='exam', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def calculated_total_marks(self):
        return sum(q.marks for q in self.questions)

    @property
    def question_count(self):
        return len(self.questions)

    def get_status_for_student(self, student_id):
        now = datetime.utcnow()
        # Check attempts
        attempt = ExamAttempt.query.filter_by(student_id=student_id, exam_id=self.id).order_by(ExamAttempt.id.desc()).first()
        if attempt:
            if attempt.status in ['submitted', 'timed_out']:
                if not self.allow_retake:
                    return 'Completed'
            elif attempt.status == 'in_progress':
                # Check if attempt time expired
                total_seconds = self.duration * 60
                elapsed = (now - attempt.start_time).total_seconds()
                if elapsed > total_seconds or now > self.end_time:
                    return 'Expired'
                return 'In Progress'

        if self.status != 'published':
            return 'Closed' if self.status == 'closed' else 'Draft'

        if now < self.start_time:
            return 'Upcoming'
        elif now > self.end_time:
            return 'Closed'
        else:
            return 'Available'

    def is_accessible_now(self):
        now = datetime.utcnow()
        return self.status == 'published' and self.start_time <= now <= self.end_time

    def __repr__(self):
        return f"<Exam {self.id}: {self.title}>"


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    option_d = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', 'D'
    marks = db.Column(db.Float, nullable=False, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to answers
    student_answers = db.relationship('StudentAnswer', backref='question', lazy='dynamic', cascade='all, delete-orphan')

    def to_student_dict(self):
        """Sanitized question payload for student exam interface. Never exposes correct_answer!"""
        return {
            'id': self.id,
            'exam_id': self.exam_id,
            'question_text': self.question_text,
            'option_a': self.option_a,
            'option_b': self.option_b,
            'option_c': self.option_c,
            'option_d': self.option_d,
            'marks': self.marks
        }

    def __repr__(self):
        return f"<Question {self.id} for Exam {self.exam_id}>"


class ExamAttempt(db.Model):
    __tablename__ = 'exam_attempts'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False, index=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    submission_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='in_progress', nullable=False)  # 'in_progress', 'submitted', 'timed_out'
    score = db.Column(db.Float, default=0.0, nullable=False)

    # Relationships
    answers = db.relationship('StudentAnswer', backref='attempt', lazy='joined', cascade='all, delete-orphan')
    result = db.relationship('Result', backref='attempt', uselist=False, cascade='all, delete-orphan')

    @property
    def remaining_seconds(self):
        """Server-authoritative remaining time calculation."""
        if self.status != 'in_progress':
            return 0
        now = datetime.utcnow()
        exam_limit = self.exam.duration * 60
        elapsed = (now - self.start_time).total_seconds()
        remaining_by_duration = max(0, exam_limit - elapsed)
        
        # Also bounded by exam end_time
        remaining_by_window = max(0, (self.exam.end_time - now).total_seconds())
        remaining = min(remaining_by_duration, remaining_by_window)
        return int(remaining)

    def is_expired(self):
        return self.remaining_seconds <= 0

    def __repr__(self):
        return f"<ExamAttempt {self.id} (Student {self.student_id}, Exam {self.exam_id}, {self.status})>"


class StudentAnswer(db.Model):
    __tablename__ = 'student_answers'
    __table_args__ = (
        db.UniqueConstraint('attempt_id', 'question_id', name='uq_attempt_question'),
    )

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    selected_answer = db.Column(db.String(1), nullable=True)  # 'A', 'B', 'C', 'D' or None
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    marks_obtained = db.Column(db.Float, default=0.0, nullable=False)

    def __repr__(self):
        return f"<StudentAnswer Attempt {self.attempt_id} Q{self.question_id}: {self.selected_answer}>"


class Result(db.Model):
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False, index=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), nullable=False, unique=True)
    total_marks = db.Column(db.Float, nullable=False)
    obtained_marks = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    result_status = db.Column(db.String(10), nullable=False)  # 'PASS', 'FAIL'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Result {self.id}: Student {self.student_id} Exam {self.exam_id} Score {self.obtained_marks}/{self.total_marks} ({self.result_status})>"
