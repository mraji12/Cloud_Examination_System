import pytest
from app.models import User
from app.extensions import db


def test_student_listing_and_search(client, admin_user, student_user, second_student_user, auth):
    auth.login(admin_user.email, 'AdminPass123!')

    # 1. Listing all students
    response = client.get('/admin/students')
    assert response.status_code == 200
    assert student_user.name.encode('utf-8') in response.data
    assert second_student_user.name.encode('utf-8') in response.data

    # 2. Search by student name
    response_search = client.get(f'/admin/students?q={student_user.name}')
    assert response_search.status_code == 200
    assert student_user.name.encode('utf-8') in response_search.data
    assert second_student_user.name.encode('utf-8') not in response_search.data

    # 3. Search by student email
    response_email = client.get(f'/admin/students?q={second_student_user.email}')
    assert response_email.status_code == 200
    assert second_student_user.name.encode('utf-8') in response_email.data
    assert student_user.name.encode('utf-8') not in response_email.data


def test_student_activation_deactivation_and_login_blocking(client, admin_user, student_user, auth, app):
    auth.login(admin_user.email, 'AdminPass123!')

    # Deactivate student
    response = client.post(f'/admin/students/{student_user.id}/toggle-status', follow_redirects=True)
    assert response.status_code == 200
    assert b'deactivated' in response.data

    with app.app_context():
        user = db.session.get(User, student_user.id)
        assert user.is_active is False

    # Logout admin
    auth.logout()

    # Attempt to log in as deactivated student
    login_response = auth.login(student_user.email, 'StudentPass123!')
    assert login_response.status_code == 200
    assert b'Your account has been deactivated' in login_response.data

    # Admin reactivates student
    auth.login(admin_user.email, 'AdminPass123!')
    response_reactivate = client.post(f'/admin/students/{student_user.id}/toggle-status', follow_redirects=True)
    assert response_reactivate.status_code == 200
    assert b'activated' in response_reactivate.data

    with app.app_context():
        user = db.session.get(User, student_user.id)
        assert user.is_active is True

    # Student can log in again
    auth.logout()
    login_ok = auth.login(student_user.email, 'StudentPass123!')
    assert login_ok.status_code == 200
    assert b'Student Portal' in login_ok.data or b'Hello' in login_ok.data


def test_admin_cannot_deactivate_admin_via_student_route(client, admin_user, auth, app):
    auth.login(admin_user.email, 'AdminPass123!')

    # Try toggling admin status through student toggle route
    response = client.post(f'/admin/students/{admin_user.id}/toggle-status', follow_redirects=True)
    assert response.status_code == 200
    assert b'Cannot alter administrator status here' in response.data

    with app.app_context():
        admin = db.session.get(User, admin_user.id)
        assert admin.is_active is True
