import secrets
from db import get_db

def generate_patient_code(user_id):
    """Generate a unique patient code for linking."""
    db = get_db()
    existing = db.execute(
        'SELECT code FROM patient_code WHERE user_id = ?',
        (user_id,)
    ).fetchone()

    if existing:
        return existing['code']

    code = secrets.token_urlsafe(8).upper()
    db.execute(
        'INSERT INTO patient_code (user_id, code) VALUES (?, ?)',
        (user_id, code)
    )
    db.commit()
    return code