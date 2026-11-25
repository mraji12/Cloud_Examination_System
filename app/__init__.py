import os
from flask import Flask, redirect, url_for, render_template
from flask_login import current_user
from config import config_by_name
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name])

    # Ensure instance and uploads directories exist
    os.makedirs(app.config.get('INSTANCE_PATH', os.path.join(app.root_path, '..', 'instance')), exist_ok=True)
    os.makedirs(app.config.get('REPORTS_DIR', os.path.join(app.root_path, '..', 'uploads', 'reports')), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.student import student_bp
    from app.exams import exams_bp
    from app.results import results_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(exams_bp)
    app.register_blueprint(results_bp)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('student.dashboard'))
        return redirect(url_for('auth.login'))

    # Context processors
    @app.context_processor
    def inject_global_data():
        from datetime import datetime
        return {
            'now': datetime.utcnow(),
            'app_name': 'CloudExam'
        }

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('base.html', error_code=403, error_title="Access Forbidden",
                               error_msg="You do not have permission to access this resource."), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('base.html', error_code=404, error_title="Page Not Found",
                               error_msg="The page you are looking for does not exist."), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('base.html', error_code=500, error_title="Internal Server Error",
                               error_msg="An unexpected error occurred. Please contact the administrator."), 500

    return app
