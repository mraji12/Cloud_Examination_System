from app.models import User


def test_student_registration(client, app):
    response = client.post('/register', data={
        'name': 'New Student',
        'email': 'newstudent@example.com',
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Registration successful' in response.data

    with app.app_context():
        user = User.query.filter_by(email='newstudent@example.com').first()
        assert user is not None
        assert user.name == 'New Student'
        assert user.role == 'student'
        assert user.is_active is True
        assert user.check_password('SecurePassword123!')


def test_duplicate_email_prevention(client, student_user):
    response = client.post('/register', data={
        'name': 'Imposter',
        'email': student_user.email,
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'An account with this email address already exists' in response.data


def test_student_login(client, student_user, auth):
    response = auth.login(student_user.email, 'StudentPass123!')
    assert response.status_code == 200
    assert b'Student Portal' in response.data or b'Hello, Student One' in response.data


def test_admin_login(client, admin_user, auth):
    response = auth.login(admin_user.email, 'AdminPass123!')
    assert response.status_code == 200
    assert b'Administrator Dashboard' in response.data


def test_invalid_login(client, student_user, auth):
    response = auth.login(student_user.email, 'WrongPassword!')
    assert response.status_code == 200
    assert b'Invalid email address or password' in response.data


def test_password_hashing(student_user):
    assert student_user.password_hash != 'StudentPass123!'
    assert student_user.password_hash.startswith('scrypt:') or student_user.password_hash.startswith('pbkdf2:')


def test_logout(client, student_user, auth):
    auth.login(student_user.email, 'StudentPass123!')
    response = auth.logout()
    assert response.status_code == 200
    assert b'logged out' in response.data or b'Sign In' in response.data or b'Welcome Back' in response.data


def test_role_based_access(client, student_user, admin_user, auth):
    # Student attempts to access admin dashboard -> redirected
    auth.login(student_user.email, 'StudentPass123!')
    response = client.get('/admin/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'Access denied. Administrator privileges required' in response.data

    # Admin accesses admin dashboard -> OK
    auth.logout()
    auth.login(admin_user.email, 'AdminPass123!')
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'Administrator Dashboard' in response.data
