from flask import Blueprint

bp = Blueprint('caretaker', __name__, url_prefix='/caretaker')

from BioSync.caretaker import routes