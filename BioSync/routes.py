import os
from datetime import datetime, timedelta
from flask import (
    Blueprint, flash, g, redirect, render_template,
    request, jsonify, url_for, current_app
)
from werkzeug.utils import secure_filename
from BioSync.auth import login_required, check_and_notify, create_notification
from BioSync.db import get_db
from BioSync.doc_processor import process_document
from BioSync.pattern_engine import get_trends, get_all_metrics, compare_baseline
from BioSync.caretaker.utils import generate_patient_code

bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'pdf'}
LAB_EXTENSIONS = {'pdf'}
IMAGING_EXTENSIONS = {'dcm', 'dicom'}
PRESCRIPTION_EXTENSIONS = {'pdf'}

# Metric units lookup
METRIC_UNITS = {
    'heart_rate': 'BPM',
    'blood_pressure_sys': 'mmHg',
    'blood_pressure_dia': 'mmHg',
    'spo2': '%',
    'weight': 'lbs',
    'glucose': 'mg/dL',
    'temperature': '°F',
    'bmi': '',
    'hrv': 'ms',
}

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


# ─────────────────────────────────────────────
# ROUTE: /
# TEMPLATE: templates/index.html
# PURPOSE: Landing/marketing page
# ─────────────────────────────────────────────
@bp.route('/')
def index():
    return render_template('index.html')


# ─────────────────────────────────────────────
# ROUTE: /dashboard
# TEMPLATE: templates/dashboard.html
# PURPOSE: Overview page — biometric cards, recent docs,
#          quick stats, patient code, biometrics table
# VARIABLES PASSED: documents, latest, heart_rate, bp_sys,
#   bp_dia, spo2, weight, total_docs, total_readings,
#   patient_code, member_since
# ─────────────────────────────────────────────
@bp.route('/dashboard')
@login_required
def dashboard():
    db = get_db()

    documents = db.execute(
        'SELECT * FROM medical_document WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 5',
        (g.user['id'],)
    ).fetchall()

    latest = db.execute(
        '''SELECT metric_name, value, unit, recorded_date
           FROM biometric_reading WHERE user_id = ?
           GROUP BY metric_name
           HAVING recorded_date = MAX(recorded_date)
           ORDER BY recorded_date DESC''',
        (g.user['id'],)
    ).fetchall()

    def get_metric(metric_name):
        row = db.execute(
            '''SELECT value FROM biometric_reading
               WHERE user_id = ? AND metric_name = ?
               ORDER BY recorded_date DESC LIMIT 1''',
            (g.user['id'], metric_name)
        ).fetchone()
        return int(row['value']) if row else None

    heart_rate = get_metric('heart_rate')
    bp_sys     = get_metric('blood_pressure_sys')
    bp_dia     = get_metric('blood_pressure_dia')
    spo2       = get_metric('spo2')
    weight     = get_metric('weight')
    glucose    = get_metric('glucose')

    total_docs = db.execute(
        'SELECT COUNT(*) as cnt FROM medical_document WHERE user_id = ?',
        (g.user['id'],)
    ).fetchone()['cnt']

    total_readings = db.execute(
        'SELECT COUNT(*) as cnt FROM biometric_reading WHERE user_id = ?',
        (g.user['id'],)
    ).fetchone()['cnt']

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
                           glucose=glucose,
                           total_docs=total_docs,
                           total_readings=total_readings,
                           patient_code=patient_code,
                           member_since=member_since)


# ─────────────────────────────────────────────
# ROUTE: /add-reading  (GET + POST)
# TEMPLATE: templates/manual_readings.html
# PURPOSE: Manual biometric entry form — user selects
#          metric, enters value, picks source/device
# VARIABLES PASSED: recent_readings
# ─────────────────────────────────────────────
@bp.route('/add-reading', methods=['GET', 'POST'])
@login_required
def add_reading():
    db = get_db()

    if request.method == 'POST':
        metric_name = request.form.get('metric_name')
        source = request.form.get('source', 'manual')

        if metric_name == 'blood_pressure':
            systolic  = request.form.get('bp_systolic')
            diastolic = request.form.get('bp_diastolic')

            if not systolic or not diastolic:
                flash('Please enter both systolic and diastolic values.')
                return redirect(request.url)

            try:
                sys_val = float(systolic)
                dia_val = float(diastolic)
            except ValueError:
                flash('Please enter valid numeric values.')
                return redirect(request.url)

            db.execute(
                '''INSERT INTO biometric_reading (user_id, metric_name, value, unit, source)
                   VALUES (?, ?, ?, ?, ?)''',
                (g.user['id'], 'blood_pressure_sys', sys_val, 'mmHg', source)
            )
            db.execute(
                '''INSERT INTO biometric_reading (user_id, metric_name, value, unit, source)
                   VALUES (?, ?, ?, ?, ?)''',
                (g.user['id'], 'blood_pressure_dia', dia_val, 'mmHg', source)
            )
            db.commit()
            check_and_notify(db, g.user['id'], 'blood_pressure_sys', sys_val)
            flash(f'Blood pressure reading ({int(sys_val)}/{int(dia_val)} mmHg) saved successfully!')

        else:
            value = request.form.get('value')
            if not value:
                flash('Please enter a value.')
                return redirect(request.url)

            try:
                float_val = float(value)
            except ValueError:
                flash('Please enter a valid number.')
                return redirect(request.url)

            # Use unit submitted by form (supports toggles for weight, temp, glucose)
            unit = request.form.get('unit') or METRIC_UNITS.get(metric_name, '')

            db.execute(
                '''INSERT INTO biometric_reading (user_id, metric_name, value, unit, source)
                   VALUES (?, ?, ?, ?, ?)''',
                (g.user['id'], metric_name, float_val, unit, source)
            )
            db.commit()
            check_and_notify(db, g.user['id'], metric_name, float_val)
            flash(f'{metric_name.replace("_", " ").title()} reading ({float_val} {unit}) saved successfully!')

        return redirect(url_for('main.add_reading'))

    recent_readings = db.execute(
        '''SELECT metric_name, value, unit, source, recorded_date
           FROM biometric_reading
           WHERE user_id = ? AND (source IS NULL OR source != 'document')
           ORDER BY recorded_date DESC LIMIT 10''',
        (g.user['id'],)
    ).fetchall()

    # ↓ TEMPLATE: templates/manual_readings.html
    return render_template('manual_readings.html', recent_readings=recent_readings)


# ─────────────────────────────────────────────
# ROUTE: /doc-hub  (GET + POST)
# TEMPLATE: templates/doc_hub.html
# PURPOSE: Document upload hub — drag/drop upload,
#          category counts, recent docs table,
#          processing queue, security notice
# VARIABLES PASSED: all_docs, recent_docs, lab_count,
#   imaging_count, prescription_count,
#   queue_docs, verified_docs
# ─────────────────────────────────────────────
@bp.route('/doc-hub', methods=['GET', 'POST'])
@login_required
def doc_hub():
    db = get_db()

    if request.method == 'POST':
        files = request.files.getlist('documents')
        if not files or all(f.filename == '' for f in files):
            flash('Please select at least one PDF file.')
            return redirect(request.url)

        total_readings = 0
        uploaded_count = 0

        for file in files:
            if not file or not allowed_file(file.filename):
                continue

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
                    '''INSERT INTO biometric_reading (user_id, document_id, metric_name, value, source)
                       VALUES (?, ?, ?, ?, ?)''',
                    (g.user['id'], doc_id, r['metric_name'], r['value'], 'document')
                )

            db.execute('UPDATE medical_document SET processed = 1 WHERE id = ?', (doc_id,))
            db.commit()
            total_readings += len(readings)
            uploaded_count += 1

        flash(f'{uploaded_count} file{"s" if uploaded_count != 1 else ""} uploaded. Found {total_readings} biometric readings.')
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


# ─────────────────────────────────────────────
# ROUTE: /upload  (GET + POST)
# TEMPLATE: templates/upload.html
# PURPOSE: Legacy upload route — kept for compatibility
# ─────────────────────────────────────────────
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
                '''INSERT INTO biometric_reading (user_id, document_id, metric_name, value, source)
                   VALUES (?, ?, ?, ?, ?)''',
                (g.user['id'], doc_id, r['metric_name'], r['value'], 'document')
            )

        db.execute('UPDATE medical_document SET processed = 1 WHERE id = ?', (doc_id,))
        db.commit()

        flash(f'Document uploaded. Found {len(readings)} biometric readings.')
        return redirect(url_for('main.dashboard'))

    return render_template('upload.html')


# ─────────────────────────────────────────────
# ROUTE: /trends-overview
# TEMPLATE: templates/trends.html
# PURPOSE: Biometric trends page — metric selector pills,
#          Chart.js line chart, time range filter,
#          biometric snapshot, baseline comparison,
#          readings history table
# VARIABLES PASSED: available_metrics, selected_metric,
#   selected_days, trend, comparison,
#   chart_labels, chart_values
# ─────────────────────────────────────────────
@bp.route('/trends-overview')
@login_required
def trends_overview():
    db = get_db()

    # Get all distinct metrics, merging blood_pressure_sys/dia into one 'blood_pressure' entry
    rows = db.execute(
        'SELECT DISTINCT metric_name FROM biometric_reading WHERE user_id = ? ORDER BY metric_name',
        (g.user['id'],)
    ).fetchall()
    raw_metrics = [r['metric_name'] for r in rows]

    # Replace sys/dia with single 'blood_pressure' entry
    available_metrics = []
    bp_added = False
    for m in raw_metrics:
        if m in ('blood_pressure_sys', 'blood_pressure_dia'):
            if not bp_added:
                available_metrics.append('blood_pressure')
                bp_added = True
        else:
            available_metrics.append(m)

    selected_metric = request.args.get('metric', available_metrics[0] if available_metrics else 'heart_rate')
    selected_days   = request.args.get('days', '30')
    is_bp           = selected_metric == 'blood_pressure'

    def fetch_readings(metric_name):
        if selected_days != '0':
            cutoff = datetime.now() - timedelta(days=int(selected_days))
            return db.execute(
                '''SELECT value, unit, recorded_date FROM biometric_reading
                   WHERE user_id = ? AND metric_name = ? AND recorded_date >= ?
                   ORDER BY recorded_date ASC''',
                (g.user['id'], metric_name, cutoff)
            ).fetchall()
        else:
            return db.execute(
                '''SELECT value, unit, recorded_date FROM biometric_reading
                   WHERE user_id = ? AND metric_name = ?
                   ORDER BY recorded_date ASC''',
                (g.user['id'], metric_name)
            ).fetchall()

    chart_labels    = []
    chart_values    = []
    chart_values_dia = []  # only used for BP

    if is_bp:
        sys_readings = fetch_readings('blood_pressure_sys')
        dia_readings = fetch_readings('blood_pressure_dia')
        for r in sys_readings:
            val = r['recorded_date']
            chart_labels.append(val.strftime('%b %d') if hasattr(val, 'strftime') else str(val)[:10])
            chart_values.append(r['value'])
        for r in dia_readings:
            chart_values_dia.append(r['value'])
        readings = sys_readings  # use sys for stats
    else:
        readings = fetch_readings(selected_metric)
        for r in readings:
            val = r['recorded_date']
            chart_labels.append(val.strftime('%b %d') if hasattr(val, 'strftime') else str(val)[:10])
            chart_values.append(r['value'])

    trend = None
    comparison = None
    if chart_values:
        avg  = round(sum(chart_values) / len(chart_values), 1)
        unit = 'mmHg' if is_bp else (readings[0]['unit'] if readings else '')

        if len(chart_values) >= 2:
            first_half  = chart_values[:len(chart_values)//2]
            second_half = chart_values[len(chart_values)//2:]
            first_avg   = sum(first_half) / len(first_half)
            second_avg  = sum(second_half) / len(second_half)
            trend_dir   = 'increasing' if second_avg > first_avg * 1.02 else ('decreasing' if second_avg < first_avg * 0.98 else 'stable')
        else:
            trend_dir = 'stable'

        change_pct = round(((chart_values[-1] - chart_values[0]) / chart_values[0]) * 100, 1) if chart_values[0] != 0 else 0

        if is_bp:
            all_sys = db.execute(
                'SELECT value, recorded_date FROM biometric_reading WHERE user_id = ? AND metric_name = ? ORDER BY recorded_date DESC',
                (g.user['id'], 'blood_pressure_sys')
            ).fetchall()
            all_dia = db.execute(
                'SELECT value, recorded_date FROM biometric_reading WHERE user_id = ? AND metric_name = ? ORDER BY recorded_date DESC',
                (g.user['id'], 'blood_pressure_dia')
            ).fetchall()
            all_dates  = []
            all_values = []  # sys values for stats
            bp_readings = []  # (date, sys/dia string)
            for i, r in enumerate(all_sys[:20]):
                val = r['recorded_date']
                date_str = val.strftime('%b %d, %Y %I:%M %p') if hasattr(val, 'strftime') else str(val)
                sys_val = r['value']
                dia_val = all_dia[i]['value'] if i < len(all_dia) else '—'
                all_dates.append(date_str)
                all_values.append(sys_val)
                bp_readings.append((date_str, f"{int(sys_val)}/{int(dia_val)}"))
        else:
            all_readings = db.execute(
                'SELECT value, unit, recorded_date FROM biometric_reading WHERE user_id = ? AND metric_name = ? ORDER BY recorded_date DESC',
                (g.user['id'], selected_metric)
            ).fetchall()
            all_dates  = []
            all_values = []
            for r in all_readings:
                val = r['recorded_date']
                all_dates.append(val.strftime('%b %d, %Y %I:%M %p') if hasattr(val, 'strftime') else str(val))
                all_values.append(r['value'])
            bp_readings = list(zip(all_dates[:20], all_values[:20]))

        trend = {
            'average':    avg,
            'min':        min(chart_values),
            'max':        max(chart_values),
            'count':      len(all_values),
            'trend':      trend_dir,
            'change_pct': abs(change_pct),
            'unit':       unit,
            'readings':   bp_readings[:20],
            'is_bp':      is_bp,
            'avg_dia':    round(sum(chart_values_dia) / len(chart_values_dia), 1) if is_bp and chart_values_dia else None,
            'min_dia':    min(chart_values_dia) if is_bp and chart_values_dia else None,
            'max_dia':    max(chart_values_dia) if is_bp and chart_values_dia else None,
        }

        if len(all_values) >= 4:
            half         = len(all_values) // 2
            baseline_avg = round(sum(all_values[half:]) / len(all_values[half:]), 1)
            recent_avg   = round(sum(all_values[:half]) / len(all_values[:half]), 1)
            delta        = round(recent_avg - baseline_avg, 1)
            comparison   = {
                'baseline_avg': baseline_avg,
                'recent_avg':   recent_avg,
                'delta':        delta,
                'direction':    'above baseline' if delta > 0 else 'below baseline',
            }

    return render_template('trends.html',
                           available_metrics=available_metrics,
                           selected_metric=selected_metric,
                           selected_days=selected_days,
                           trend=trend,
                           comparison=comparison,
                           chart_labels=chart_labels,
                           chart_values=chart_values,
                           chart_values_dia=chart_values_dia,
                           is_bp=is_bp)


# ─────────────────────────────────────────────
# ROUTE: /individual-profile
# TEMPLATE: templates/auth/individual_profile.html
# PURPOSE: Patient profile page — biometric cards,
#          BP history chart, BP sliders, documents list,
#          clinical notes, care team
# VARIABLES PASSED: docs, metrics, latest, caregivers,
#   patient_code, notes, member_since, bp_sys, bp_dia,
#   sys_label, sys_pct, dia_label, dia_pct,
#   heart_rate, bp_chart_labels, bp_chart_values
# ─────────────────────────────────────────────
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

    bp_sys     = get_metric('blood_pressure_sys')
    bp_dia     = get_metric('blood_pressure_dia')
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


# ─────────────────────────────────────────────
# ROUTE: /generate-code  (POST)
# PURPOSE: Generates a unique patient code for linking
#          to a caregiver — redirects back to profile
# ─────────────────────────────────────────────
@bp.route('/generate-code', methods=['POST'])
@login_required
def generate_code():
    generate_patient_code(g.user['id'])
    return redirect(url_for('main.individual_profile'))


# ─────────────────────────────────────────────
# ROUTE: /trends/<metric_name>
# TEMPLATE: templates/trends.html
# PURPOSE: Legacy trends route from pattern_engine
#          (kept for compatibility with old links)
# ─────────────────────────────────────────────
@bp.route('/trends/<metric_name>')
@login_required
def trends(metric_name):
    trend_data = get_trends(g.user['id'], metric_name)
    comparison = compare_baseline(g.user['id'], metric_name)
    return render_template('trends.html',
                           metric=metric_name,
                           trend=trend_data,
                           comparison=comparison)


# ─────────────────────────────────────────────
# ROUTE: /api/trends/<metric_name>
# PURPOSE: JSON API endpoint — returns trend data
#          for a given metric (for future mobile app use)
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
# ROUTE: /notifications
# TEMPLATE: templates/notifications.html
# PURPOSE: Shows all notifications for the user
#          with read/unread status and mark as read
# ─────────────────────────────────────────────
@bp.route('/notifications')
@login_required
def notifications():
    db = get_db()
    all_notifs = db.execute(
        '''SELECT * FROM notification WHERE user_id = ?
           ORDER BY created_at DESC''',
        (g.user['id'],)
    ).fetchall()
    # Mark all as read when page is opened
    db.execute(
        'UPDATE notification SET is_read = 1 WHERE user_id = ?',
        (g.user['id'],)
    )
    db.commit()
    return render_template('notifications.html', notifications=all_notifs)


@bp.route('/notifications/clear', methods=['POST'])
@login_required
def clear_notifications():
    db = get_db()
    db.execute('DELETE FROM notification WHERE user_id = ?', (g.user['id'],))
    db.commit()
    return redirect(url_for('main.notifications'))


@bp.route('/api/notifications/unread-count')
@login_required
def unread_count():
    db = get_db()
    count = db.execute(
        'SELECT COUNT(*) as cnt FROM notification WHERE user_id = ? AND is_read = 0',
        (g.user['id'],)
    ).fetchone()['cnt']
    return jsonify({'count': count})

@bp.route('/api/trends/<metric_name>')
@login_required
def api_trends(metric_name):
    return jsonify(get_trends(g.user['id'], metric_name))