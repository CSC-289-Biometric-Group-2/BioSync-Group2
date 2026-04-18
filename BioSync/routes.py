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
LAB_EXTENSIONS = {'pdf', 'csv', 'txt'}
IMAGING_EXTENSIONS = {'dcm', 'dicom', 'jpg', 'jpeg', 'png'}
PRESCRIPTION_EXTENSIONS = {'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_category(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in IMAGING_EXTENSIONS:
        return 'imaging'
    elif ext in PRESCRIPTION_EXTENSIONS:
        return 'prescription'
    else:
        return 'lab'

def get_member_since(db, user_id):
    user_info = db.execute('SELECT created_at FROM user WHERE id = ?', (user_id,)).fetchone()
    if user_info and user_info['created_at']:
        from datetime import datetime
        val = user_info['created_at']
        if isinstance(val, str):
            try:
                val = datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        if isinstance(val, datetime):
            return val.strftime('%B %Y')
        return str(val)
    return None

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    db = get_db()

    # Recent documents
    documents = db.execute(
        'SELECT * FROM medical_document WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 5',
        (g.user['id'],)
    ).fetchall()

    # Latest reading per metric for biometrics table
    latest = db.execute(
        '''SELECT metric_name, value, unit, recorded_date
           FROM biometric_reading WHERE user_id = ?
           GROUP BY metric_name
           HAVING recorded_date = MAX(recorded_date)
           ORDER BY recorded_date DESC''',
        (g.user['id'],)
    ).fetchall()

    # Summary card values
    def get_metric(metric_name):
        row = db.execute(
            '''SELECT value FROM biometric_reading
               WHERE user_id = ? AND metric_name = ?
               ORDER BY recorded_date DESC LIMIT 1''',
            (g.user['id'], metric_name)
        ).fetchone()
        return int(row['value']) if row else None

    heart_rate = get_metric('heart_rate')
    bp_sys = get_metric('blood_pressure_sys')
    bp_dia = get_metric('blood_pressure_dia')
    spo2 = get_metric('spo2')
    weight = get_metric('weight')

    # Quick stats
    total_docs = db.execute(
        'SELECT COUNT(*) as cnt FROM medical_document WHERE user_id = ?',
        (g.user['id'],)
    ).fetchone()['cnt']

    total_readings = db.execute(
        'SELECT COUNT(*) as cnt FROM biometric_reading WHERE user_id = ?',
        (g.user['id'],)
    ).fetchone()['cnt']

    # Patient code
    patient_code_row = db.execute(
        'SELECT code FROM patient_code WHERE user_id = ?',
        (g.user['id'],)
    ).fetchone()
    patient_code = patient_code_row['code'] if patient_code_row else None

    member_since = get_member_since(db, g.user['id'])

    return render_template('dashboard.html',
                           documents=documents,
                           latest=latest,
                           heart_rate=heart_rate,
                           bp_sys=bp_sys,
                           bp_dia=bp_dia,
                           spo2=spo2,
                           weight=weight,
                           total_docs=total_docs,
                           total_readings=total_readings,
                           patient_code=patient_code,
                           member_since=member_since)

@bp.route('/doc-hub', methods=['GET', 'POST'])
@login_required
def doc_hub():
    db = get_db()

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
        return redirect(url_for('main.doc_hub'))

    all_docs = db.execute(
        'SELECT * FROM medical_document WHERE user_id = ? ORDER BY uploaded_at DESC',
        (g.user['id'],)
    ).fetchall()

    lab_count = imaging_count = prescription_count = 0
    for doc in all_docs:
        cat = get_file_category(doc['filename'])
        if cat == 'lab': lab_count += 1
        elif cat == 'imaging': imaging_count += 1
        elif cat == 'prescription': prescription_count += 1

    recent_docs = all_docs[:5]

    queue_docs = db.execute(
        '''SELECT * FROM medical_document WHERE user_id = ? AND processed = 0
           ORDER BY uploaded_at DESC LIMIT 4''',
        (g.user['id'],)
    ).fetchall()

    verified_docs = db.execute(
        '''SELECT * FROM medical_document WHERE user_id = ? AND processed = 1
           ORDER BY uploaded_at DESC LIMIT 2''',
        (g.user['id'],)
    ).fetchall()

    return render_template('doc_hub.html',
                           all_docs=all_docs,
                           recent_docs=recent_docs,
                           lab_count=lab_count,
                           imaging_count=imaging_count,
                           prescription_count=prescription_count,
                           queue_docs=queue_docs,
                           verified_docs=verified_docs)

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
        '''SELECT metric_name, value, unit, recorded_date
           FROM biometric_reading WHERE user_id = ?
           GROUP BY metric_name
           HAVING recorded_date = MAX(recorded_date)
           ORDER BY recorded_date DESC''',
        (g.user['id'],)
    ).fetchall()

    caregivers = db.execute(
        '''SELECT u.username, cl.caregiver_type
           FROM caretaker_link cl
           JOIN user u ON u.id = cl.caregiver_id
           WHERE cl.patient_id = ?''',
        (g.user['id'],)
    ).fetchall()

    patient_code = db.execute(
        'SELECT code FROM patient_code WHERE user_id = ?',
        (g.user['id'],)
    ).fetchone()

    def get_metric(metric_name):
        row = db.execute(
            '''SELECT value FROM biometric_reading
               WHERE user_id = ? AND metric_name = ?
               ORDER BY recorded_date DESC LIMIT 1''',
            (g.user['id'], metric_name)
        ).fetchone()
        return int(row['value']) if row else None

    bp_sys = get_metric('blood_pressure_sys')
    bp_dia = get_metric('blood_pressure_dia')
    heart_rate = get_metric('heart_rate')

    if bp_sys is None:
        sys_label = '—'; sys_pct = 0
    elif bp_sys < 120:
        sys_label = 'Normal'; sys_pct = int((bp_sys / 180) * 100)
    elif bp_sys < 130:
        sys_label = 'Elevated'; sys_pct = int((bp_sys / 180) * 100)
    else:
        sys_label = 'High'; sys_pct = min(int((bp_sys / 180) * 100), 100)

    if bp_dia is None:
        dia_label = '—'; dia_pct = 0
    elif bp_dia < 80:
        dia_label = 'Normal'; dia_pct = int((bp_dia / 120) * 100)
    else:
        dia_label = 'High'; dia_pct = min(int((bp_dia / 120) * 100), 100)

    bp_history = db.execute(
        '''SELECT value, recorded_date FROM biometric_reading
           WHERE user_id = ? AND metric_name = 'blood_pressure_sys'
           ORDER BY recorded_date ASC''',
        (g.user['id'],)
    ).fetchall()

    bp_chart_labels = []
    bp_chart_values = []
    for row in bp_history:
        val = row['recorded_date']
        label = val.strftime('%b %d') if hasattr(val, 'strftime') else str(val)[:10]
        bp_chart_labels.append(label)
        bp_chart_values.append(row['value'])

    member_since = get_member_since(db, g.user['id'])

    return render_template('auth/individual_profile.html',
                           docs=docs,
                           metrics=metrics,
                           latest=latest,
                           caregivers=caregivers,
                           patient_code=patient_code['code'] if patient_code else None,
                           notes=None,
                           member_since=member_since,
                           bp_sys=bp_sys,
                           bp_dia=bp_dia,
                           sys_label=sys_label,
                           sys_pct=sys_pct,
                           dia_label=dia_label,
                           dia_pct=dia_pct,
                           heart_rate=heart_rate,
                           bp_chart_labels=bp_chart_labels,
                           bp_chart_values=bp_chart_values)

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