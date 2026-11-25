from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, FloatField, SelectField, BooleanField, DateTimeLocalField, SubmitField, RadioField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
try:
    from wtforms.fields.choices import SelectChoice
    STATUS_CHOICES = [
        SelectChoice('draft', 'Draft (Work in progress)'),
        SelectChoice('published', 'Published (Live per schedule)'),
        SelectChoice('closed', 'Closed (Archived/No attempts allowed)')
    ]
    ANSWER_CHOICES = [
        SelectChoice('A', 'Option A'),
        SelectChoice('B', 'Option B'),
        SelectChoice('C', 'Option C'),
        SelectChoice('D', 'Option D')
    ]
except ImportError:
    STATUS_CHOICES = [
        ('draft', 'Draft (Work in progress)'),
        ('published', 'Published (Live per schedule)'),
        ('closed', 'Closed (Archived/No attempts allowed)')
    ]
    ANSWER_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D')
    ]


class ExamForm(FlaskForm):
    title = StringField('Examination Title', validators=[
        DataRequired(message="Title is required."),
        Length(min=3, max=150, message="Title must be between 3 and 150 characters.")
    ])
    subject = StringField('Subject Name', validators=[
        DataRequired(message="Subject is required."),
        Length(min=2, max=100, message="Subject must be between 2 and 100 characters.")
    ])
    description = TextAreaField('Description / Overview', validators=[
        Length(max=1000, message="Description must not exceed 1000 characters.")
    ])
    duration = IntegerField('Duration (Minutes)', validators=[
        DataRequired(message="Duration is required."),
        NumberRange(min=1, max=1440, message="Duration must be between 1 and 1440 minutes.")
    ])
    total_marks = FloatField('Configured Total Marks', validators=[
        DataRequired(message="Total marks is required."),
        NumberRange(min=0.5, max=10000, message="Total marks must be positive.")
    ])
    passing_percentage = FloatField('Passing Percentage (%)', validators=[
        DataRequired(message="Passing percentage is required."),
        NumberRange(min=1.0, max=100.0, message="Passing percentage must be between 1 and 100.")
    ], default=40.0)
    start_time = DateTimeLocalField('Start Date & Time (UTC)', format='%Y-%m-%dT%H:%M', validators=[
        DataRequired(message="Start time is required.")
    ])
    end_time = DateTimeLocalField('End Date & Time (UTC)', format='%Y-%m-%dT%H:%M', validators=[
        DataRequired(message="End time is required.")
    ])
    status = SelectField('Status', choices=STATUS_CHOICES, default='draft')
    allow_retake = BooleanField('Allow Retakes (Students can attempt again if completed)')
    submit = SubmitField('Save Examination')

    def validate_end_time(self, field):
        if self.start_time.data and field.data:
            if field.data <= self.start_time.data:
                raise ValidationError("End date & time must be strictly after the start date & time.")


class QuestionForm(FlaskForm):
    question_text = TextAreaField('Question Text', validators=[
        DataRequired(message="Question text is required."),
        Length(min=5, message="Question text must be at least 5 characters.")
    ])
    option_a = StringField('Option A', validators=[
        DataRequired(message="Option A is required.")
    ])
    option_b = StringField('Option B', validators=[
        DataRequired(message="Option B is required.")
    ])
    option_c = StringField('Option C', validators=[
        DataRequired(message="Option C is required.")
    ])
    option_d = StringField('Option D', validators=[
        DataRequired(message="Option D is required.")
    ])
    correct_answer = RadioField('Correct Answer Option', choices=ANSWER_CHOICES, validators=[DataRequired(message="Please specify the correct option.")])
    marks = FloatField('Marks for this Question', validators=[
        DataRequired(message="Marks are required."),
        NumberRange(min=0.5, max=500, message="Marks must be between 0.5 and 500.")
    ], default=1.0)
    submit = SubmitField('Save Question')
