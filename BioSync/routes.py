import os
from flask import (
    Blueprint, flash, g, redirect, render_template,
    request, jsonify, url_for, current_app
)
from werkzeug.utils import secure_filename
from BioSync.auth import login_required
from BioSync.db import get_db
from BioSync.doc_processor import process_document
from BioSync.pattern_engine import get_trends, get_all_metrics, compare_baseline
from BioSync.caretaker.utils import generate_patient_code

bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    documents = db.execute(
        'SELECT * FROM medical_document WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 5',
        (g.user['id'],)
    ).fetchall()
    latest = db.execute(
        '''SELECT DISTINCT metric_name, value, unit, recorded_date
           FROM biometric_reading WHERE user_id = ?
           GROUP BY metric_name ORDER BY recorded_date DESC LIMIT 4''',
        (g.user['id'],)
    ).fetchall()
    caregivers = db.execute(
        '''SELECT u.username, cl.caregiver_type
           FROM caretaker_link cl
           JOIN user u ON u.id = cl.caregiver_id
           WHERE cl.patient_id = ?''',
        (g.user['id'],)
    ).fetchall()
    return render_template('dashboard.html',
                           documents=documents,
                           latest=latest,
                           caregivers=caregivers,
                           notes=None)

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files.get('document')
        if not file or not allowed_file(file.filename):
            flash('Please upload a PDF, DOCX, TXT, or CSV file.')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        user_folder = os.path.join(current_app.instance_path, 'uploads', str(g.user['id']))
        os.makedirs(user_folder, exist_ok=True)
        filepath = os.path.join(user_folder, filename)
        file.save(filepath)

        db = get_db()
        db.execute(
            'INSERT INTO medical_document (user_id, filename, file_path) VALUES (?, ?, ?)',
            (g.user['id'], filename, filepath)
        )
        db.commit()

        doc_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

        readings = process_document(filepath)
        for r in readings:
            db.execute(
                '''INSERT INTO biometric_reading (user_id, document_id, metric_name, value)
                   VALUES (?, ?, ?, ?)''',
                (g.user['id'], doc_id, r['metric_name'], r['value'])
            )

        db.execute('UPDATE medical_document SET processed = 1 WHERE id = ?', (doc_id,))
        db.commit()

        flash(f'Document uploaded. Found {len(readings)} biometric readings.')
        return redirect(url_for('main.dashboard'))

    return render_template('upload.html')

@bp.route('/individual-profile')
@login_required
def individual_profile():
    db = get_db()
    docs = db.execute(
        'SELECT * FROM medical_document WHERE user_id = ? ORDER BY uploaded_at DESC',
        (g.user['id'],)
    ).fetchall()
    metrics = get_all_metrics(g.user['id'])
    latest = db.execute(
        '''SELECT DISTINCT metric_name, value, unit, recorded_date
           FROM biometric_reading WHERE user_id = ?
           GROUP BY metric_name ORDER BY recorded_date DESC''',
        (g.user['id'],)
    ).fetchall()
    patient_code = db.execute(
        'SELECT code FROM patient_code WHERE user_id = ?',
        (g.user['id'],)
    ).fetchone()
    return render_template('auth/individual_profile.html',
                           docs=docs,
                           metrics=metrics,
                           latest=latest,
                           patient_code=patient_code['code'] if patient_code else None)

@bp.route('/generate-code', methods=['POST'])
@login_required
def generate_code():
    generate_patient_code(g.user['id'])
    return redirect(url_for('main.individual_profile'))

@bp.route('/trends/<metric_name>')
@login_required
def trends(metric_name):
    trend_data = get_trends(g.user['id'], metric_name)
    comparison = compare_baseline(g.user['id'], metric_name)
    return render_template('trends.html',
                           metric=metric_name,
                           trend=trend_data,
                           comparison=comparison)

@bp.route('/api/trends/<metric_name>')
@login_required
def api_trends(metric_name):
    return jsonify(get_trends(g.user['id'], metric_name))