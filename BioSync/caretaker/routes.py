import os
import functools
from datetime import datetime
from flask import (
    Blueprint, flash, g, redirect, render_template,
    request, url_for, current_app
)
from werkzeug.utils import secure_filename
from BioSync.auth import login_required
from BioSync.db import get_db
from BioSync.doc_processor import process_document

bp = Blueprint('caretaker', __name__, url_prefix='/caretaker')


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get_member_since(db, user_id):
    user_info = db.execute('SELECT created_at FROM user WHERE id = ?', (user_id,)).fetchone()
    if user_info and user_info['created_at']:
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


def calculate_age(dob_str):
    if not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        today = datetime.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except ValueError:
        return None


def caregiver_required(view):
    """Redirect non-caregivers to patient dashboard."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        if g.user['account_type'] != 'caregiver':
            return redirect(url_for('main.dashboard'))
        return view(**kwargs)
    return wrapped_view


# ─────────────────────────────────────────────
# ROUTE: /caretaker/dashboard
# TEMPLATE: templates/caretaker/caregiver_dashboard.html
# PURPOSE: Patient hub — grid of all linked patients
#          with latest biometrics and alert badges
# ─────────────────────────────────────────────
@bp.route('/dashboard')
@login_required
@caregiver_required
def dashboard():
    db = get_db()

    linked_patients = db.execute(
        '''SELECT u.id, u.username, u.first_name, u.last_name,
                  u.dob, cl.linked_at
           FROM caretaker_link cl
           JOIN user u ON u.id = cl.patient_id
           WHERE cl.caregiver_id = ?
           ORDER BY cl.linked_at DESC''',
        (g.user['id'],)
    ).fetchall()

    patients_data = []
    for patient in linked_patients:
        pid = patient['id']

        def get_metric(uid, metric):
            row = db.execute(
                '''SELECT value FROM biometric_reading
                   WHERE user_id = ? AND metric_name = ?
                   ORDER BY recorded_date DESC LIMIT 1''',
                (uid, metric)
            ).fetchone()
            return row['value'] if row else None

        unread_alerts = db.execute(
            '''SELECT COUNT(*) as cnt FROM notification
               WHERE user_id = ? AND is_read = 0
               AND status IN ('danger', 'warning')''',
            (pid,)
        ).fetchone()['cnt']

        patients_data.append({
            'id': pid,
            'username': patient['username'],
            'first_name': patient['first_name'],
            'last_name': patient['last_name'],
            'dob': patient['dob'],
            'age': calculate_age(patient['dob']),
            'linked_at': patient['linked_at'],
            'heart_rate': get_metric(pid, 'heart_rate'),
            'bp_sys': get_metric(pid, 'blood_pressure_sys'),
            'bp_dia': get_metric(pid, 'blood_pressure_dia'),
            'spo2': get_metric(pid, 'spo2'),
            'glucose': get_metric(pid, 'glucose'),
            'unread_alerts': unread_alerts,
        })

    return render_template('caretaker/caregiver_dashboard.html',
                           patients=patients_data,
                           member_since=get_member_since(db, g.user['id']))


# ─────────────────────────────────────────────
# ROUTE: /caretaker/link-patient  (GET + POST)
# TEMPLATE: templates/caretaker/link_patient.html
# PURPOSE: Enter a patient code to link a patient
# ─────────────────────────────────────────────
@bp.route('/link-patient', methods=['GET', 'POST'])
@login_required
@caregiver_required
def link_patient():
    db = get_db()

    if request.method == 'POST':
        patient_code = request.form.get('patient_code', '').strip()

        if not patient_code:
            flash('Please enter a patient code.')
            return redirect(request.url)

        code_row = db.execute(
            'SELECT * FROM patient_code WHERE code = ?', (patient_code,)
        ).fetchone()

        if not code_row:
            flash('Invalid patient code. Please check with your patient.')
            return redirect(request.url)

        patient_id = code_row['user_id']

        existing = db.execute(
            'SELECT * FROM caretaker_link WHERE caregiver_id = ? AND patient_id = ?',
            (g.user['id'], patient_id)
        ).fetchone()

        if existing:
            flash('You are already linked to this patient.')
            return redirect(url_for('caretaker.dashboard'))

        db.execute(
            '''INSERT INTO caretaker_link (caregiver_id, patient_id, caregiver_type, duration)
               VALUES (?, ?, ?, ?)''',
            (g.user['id'], patient_id,
             g.user['caregiver_type'] or 'informal',
             g.user['duration'] or 'long_term')
        )
        db.commit()

        patient = db.execute('SELECT * FROM user WHERE id = ?', (patient_id,)).fetchone()
        name = patient['first_name'] if patient['first_name'] else patient['username']
        flash(f'Successfully linked to patient {name}!')
        return redirect(url_for('caretaker.dashboard'))

    return render_template('caretaker/link_patient.html')


# ─────────────────────────────────────────────
# ROUTE: /caretaker/patient/<patient_id>
# TEMPLATE: templates/caretaker/patient_view.html
# PURPOSE: Detailed view of one patient's biometrics,
#          alerts, and documents
# ─────────────────────────────────────────────
@bp.route('/patient/<int:patient_id>')
@login_required
@caregiver_required
def patient_detail(patient_id):
    db = get_db()

    link = db.execute(
        'SELECT * FROM caretaker_link WHERE caregiver_id = ? AND patient_id = ?',
        (g.user['id'], patient_id)
    ).fetchone()
    if not link:
        flash('You are not linked to this patient.')
        return redirect(url_for('caretaker.dashboard'))

    patient = db.execute('SELECT * FROM user WHERE id = ?', (patient_id,)).fetchone()

    def get_metric(metric):
        row = db.execute(
            '''SELECT value FROM biometric_reading
               WHERE user_id = ? AND metric_name = ?
               ORDER BY recorded_date DESC LIMIT 1''',
            (patient_id, metric)
        ).fetchone()
        return row['value'] if row else None

    latest = db.execute(
        '''SELECT metric_name, value, unit, recorded_date
           FROM biometric_reading WHERE user_id = ?
           GROUP BY metric_name
           HAVING recorded_date = MAX(recorded_date)
           ORDER BY recorded_date DESC''',
        (patient_id,)
    ).fetchall()

    bp_history = db.execute(
        '''SELECT value, recorded_date FROM biometric_reading
           WHERE user_id = ? AND metric_name = 'blood_pressure_sys'
           ORDER BY recorded_date ASC''',
        (patient_id,)
    ).fetchall()

    bp_chart_labels = []
    bp_chart_values = []
    for row in bp_history:
        val = row['recorded_date']
        bp_chart_labels.append(val.strftime('%b %d') if hasattr(val, 'strftime') else str(val)[:10])
        bp_chart_values.append(row['value'])

    return render_template('caretaker/patient_view.html',
                           patient=patient,
                           age=calculate_age(patient['dob']),
                           latest=latest,
                           notifications=db.execute(
                               'SELECT * FROM notification WHERE user_id = ? ORDER BY created_at DESC LIMIT 20',
                               (patient_id,)
                           ).fetchall(),
                           documents=db.execute(
                               'SELECT * FROM medical_document WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 5',
                               (patient_id,)
                           ).fetchall(),
                           bp_sys=get_metric('blood_pressure_sys'),
                           bp_dia=get_metric('blood_pressure_dia'),
                           bp_chart_labels=bp_chart_labels,
                           bp_chart_values=bp_chart_values)


# ─────────────────────────────────────────────
# ROUTE: /caretaker/unlink-patient/<patient_id>
# PURPOSE: Remove caregiver-patient link
# ─────────────────────────────────────────────
@bp.route('/unlink-patient/<int:patient_id>', methods=['POST'])
@login_required
@caregiver_required
def unlink_patient(patient_id):
    db = get_db()
    db.execute(
        'DELETE FROM caretaker_link WHERE caregiver_id = ? AND patient_id = ?',
        (g.user['id'], patient_id)
    )
    db.commit()
    flash('Patient unlinked successfully.')
    return redirect(url_for('caretaker.dashboard'))


# ─────────────────────────────────────────────
# ROUTE: /caretaker/notifications
# TEMPLATE: templates/caretaker/caregiver_notifications.html
# PURPOSE: All alerts across all linked patients
# ─────────────────────────────────────────────
@bp.route('/notifications')
@login_required
@caregiver_required
def notifications():
    db = get_db()

    linked = db.execute(
        'SELECT patient_id FROM caretaker_link WHERE caregiver_id = ?',
        (g.user['id'],)
    ).fetchall()

    all_notifications = []
    for row in linked:
        pid = row['patient_id']
        patient = db.execute(
            'SELECT id, first_name, last_name, username FROM user WHERE id = ?', (pid,)
        ).fetchone()
        notifs = db.execute(
            'SELECT * FROM notification WHERE user_id = ? ORDER BY created_at DESC',
            (pid,)
        ).fetchall()
        for n in notifs:
            name = f"{patient['first_name']} {patient['last_name']}" if patient['first_name'] else patient['username']
            all_notifications.append({
                'id': n['id'],
                'patient_name': name,
                'patient_id': pid,
                'metric': n['metric'],
                'value': n['value'],
                'status': n['status'],
                'message': n['message'],
                'is_read': n['is_read'],
                'created_at': n['created_at'],
            })

    all_notifications.sort(key=lambda x: str(x['created_at']), reverse=True)

    for row in linked:
        db.execute('UPDATE notification SET is_read = 1 WHERE user_id = ?', (row['patient_id'],))
    db.commit()

    return render_template('caretaker/caregiver_notifications.html',
                           notifications=all_notifications)


# ─────────────────────────────────────────────
# ROUTE: /caretaker/profile
# TEMPLATE: templates/caretaker/caregiver_profile.html
# PURPOSE: Caregiver's own profile page
# ─────────────────────────────────────────────
@bp.route('/profile')
@login_required
@caregiver_required
def profile():
    db = get_db()

    linked_patients = db.execute(
        '''SELECT u.id, u.username, u.first_name, u.last_name, cl.linked_at
           FROM caretaker_link cl
           JOIN user u ON u.id = cl.patient_id
           WHERE cl.caregiver_id = ?
           ORDER BY cl.linked_at DESC''',
        (g.user['id'],)
    ).fetchall()

    total_docs = db.execute(
        '''SELECT COUNT(*) as cnt FROM medical_document
           WHERE user_id IN (
               SELECT patient_id FROM caretaker_link WHERE caregiver_id = ?
           )''', (g.user['id'],)
    ).fetchone()['cnt']

    total_alerts = db.execute(
        '''SELECT COUNT(*) as cnt FROM notification
           WHERE user_id IN (
               SELECT patient_id FROM caretaker_link WHERE caregiver_id = ?
           )''', (g.user['id'],)
    ).fetchone()['cnt']

    return render_template('caretaker/caregiver_profile.html',
                           linked_patients=linked_patients,
                           total_docs=total_docs,
                           total_alerts=total_alerts,
                           member_since=get_member_since(db, g.user['id']))


# ─────────────────────────────────────────────
# ROUTE: /caretaker/upload  (GET + POST)
# TEMPLATE: templates/caretaker/caregiver_upload.html
# PURPOSE: Upload a document on behalf of a patient
# ─────────────────────────────────────────────
@bp.route('/upload', methods=['GET', 'POST'])
@login_required
@caregiver_required
def upload_document():
    db = get_db()

    linked_patients = db.execute(
        '''SELECT u.id, u.username, u.first_name, u.last_name
           FROM caretaker_link cl
           JOIN user u ON u.id = cl.patient_id
           WHERE cl.caregiver_id = ?''',
        (g.user['id'],)
    ).fetchall()

    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        files = request.files.getlist('documents')

        if not patient_id:
            flash('Please select a patient.')
            return redirect(request.url)

        if not files or all(f.filename == '' for f in files):
            flash('Please select at least one PDF file.')
            return redirect(request.url)

        link = db.execute(
            'SELECT * FROM caretaker_link WHERE caregiver_id = ? AND patient_id = ?',
            (g.user['id'], patient_id)
        ).fetchone()
        if not link:
            flash('You are not linked to this patient.')
            return redirect(request.url)

        total_readings = 0
        uploaded_count = 0

        for file in files:
            if not file or not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() == 'pdf'):
                continue

            filename = secure_filename(file.filename)
            user_folder = os.path.join(current_app.instance_path, 'uploads', str(patient_id))
            os.makedirs(user_folder, exist_ok=True)
            filepath = os.path.join(user_folder, filename)
            file.save(filepath)

            db.execute(
                'INSERT INTO medical_document (user_id, filename, file_path) VALUES (?, ?, ?)',
                (patient_id, filename, filepath)
            )
            db.commit()
            doc_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

            readings = process_document(filepath)
            for r in readings:
                db.execute(
                    '''INSERT INTO biometric_reading (user_id, document_id, metric_name, value, source)
                       VALUES (?, ?, ?, ?, ?)''',
                    (patient_id, doc_id, r['metric_name'], r['value'], 'document')
                )

            db.execute('UPDATE medical_document SET processed = 1 WHERE id = ?', (doc_id,))
            db.commit()
            total_readings += len(readings)
            uploaded_count += 1

        flash(f'{uploaded_count} file{"s" if uploaded_count != 1 else ""} uploaded. Found {total_readings} biometric readings.')
        return redirect(url_for('caretaker.upload_document'))

    return render_template('caretaker/caregiver_upload.html',
                           linked_patients=linked_patients)