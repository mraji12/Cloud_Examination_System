from flask import Blueprint

exams_bp = Blueprint('exams', __name__, url_prefix='/exams')

from app.exams import routes
