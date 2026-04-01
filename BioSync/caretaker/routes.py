import secrets
from flask import (
    Blueprint, flash, g, redirect, render_template,
    request, url_for
)
from BioSync.auth import login_required
from BioSync.db import get_db
from BioSync.caretaker import bp

@bp.route('/link', methods=['GET', 'POST'])
@login_required
def link_patient():
    if request.method == 'POST':
        patient_code = request.form['patient_code']
        db = get_db()
        error = None

        # Find the patient by their code
        patient = db.execute(
            'SELECT * FROM patient_code WHERE code = ?',
            (patient_code,)
        ).fetchone()

        if patient is None:
            error = 'Invalid patient code.'

        if error is None:
            # Check if already linked
            existing = db.execute(
                '''SELECT * FROM caretaker_link 
                   WHERE caregiver_id = ? AND patient_id = ?''',
                (g.user['id'], patient['user_id'])
            ).fetchone()

            if existing:
                error = 'You are already linked to this patient.'

        if error is None:
            db.execute(
                '''INSERT INTO caretaker_link 
                   (caregiver_id, patient_id, caregiver_type, duration)
                   VALUES (?, ?, ?, ?)''',
                (g.user['id'], patient['user_id'],
                 g.user['username'], 'long_term')
            )
            db.commit()
            flash('Successfully linked to patient!')