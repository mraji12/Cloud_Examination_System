from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('student.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.is_admin:
            flash('Administrators do not have a student portal. Redirecting to Admin Dashboard.', 'info')
            return redirect(url_for('admin.dashboard'))
        if not current_user.is_active:
            flash('Your account has been deactivated. Please contact the administrator.', 'danger')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorated_function
