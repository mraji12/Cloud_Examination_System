from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User


class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message="Full name is required."),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email address is required."),
        Email(check_deliverability=False, message="Please enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords do not match.")
    ])
    submit = SubmitField('Register as Student')

    def validate_email(self, field):
        normalized_email = field.data.strip().lower()
        if User.query.filter_by(email=normalized_email).first():
            raise ValidationError('An account with this email address already exists.')


class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email address is required."),
        Email(check_deliverability=False, message="Please enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required.")
    ])
    submit = SubmitField('Log In')
