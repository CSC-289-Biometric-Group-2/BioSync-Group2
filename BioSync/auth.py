# User Authentication
# This is where the user will register, if they do not have an account, 
# Or Login if they do have one.

import functools
from datetime import datetime

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from BioSync.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')


def calculate_age(dob_str):
    """Calculate age from date of birth string (YYYY-MM-DD)."""
    if not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        today = datetime.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except ValueError:
        return None


def get_hr_range(age, sex):
    """Return (hr_min, hr_max) resting BPM range for a given age and sex."""
    if age is None or not sex:
        return None, None
    sex = sex.lower()
    if sex == 'male':
        if age >= 65:   return 62, 73
        elif age >= 56: return 61, 74
        elif age >= 46: return 63, 76
        elif age >= 36: return 63, 75
        elif age >= 26: return 62, 74
        elif age >= 18: return 62, 73
    elif sex == 'female':
        if age >= 65:   return 63, 76
        elif age >= 56: return 64, 77
        elif age >= 46: return 65, 77
        elif age >= 36: return 65, 77
        elif age >= 26: return 64, 76
        elif age >= 18: return 63, 76
    return None, None


def create_notification(db, user_id, metric, value, status, message):
    """Insert a notification for the user."""
    db.execute(
        '''INSERT INTO notification (user_id, metric, value, status, message)
           VALUES (?, ?, ?, ?, ?)''',
        (user_id, metric, str(value), status, message)
    )


def check_and_notify(db, user_id, metric_name, value):
    """Check a biometric value and create a notification if it's outside safe range."""
    value = float(value)
    notif = None

    if metric_name == 'heart_rate':
        if value < 40:
            notif = ('warning', '⚠ Very Low Heart Rate — Seek medical attention')
        elif value > 150:
            notif = ('danger', '⚠ High Heart Rate (>150 BPM) — Seek medical attention. Emergency care if accompanied by chest pain, dizziness, or fainting.')
        elif value > 100:
            notif = ('caution', '⚠ Tachycardia detected (>100 BPM) — Consult your doctor')
        else:
            user_row = db.execute('SELECT dob, sex FROM user WHERE id = ?', (user_id,)).fetchone()
            age = calculate_age(user_row['dob']) if user_row else None
            sex = user_row['sex'] if user_row else None
            hr_min, hr_max = get_hr_range(age, sex)

            if hr_min is not None and value > hr_max:
                notif = ('warning', f'High Heart Rate: {int(value)} BPM exceeds normal range ({hr_min}–{hr_max} BPM) for your age and sex')
            elif hr_min is not None and value < hr_min:
                notif = ('warning', f'Low Heart Rate: {int(value)} BPM is below normal range ({hr_min}–{hr_max} BPM) for your age and sex')

    elif metric_name == 'blood_pressure_sys':
        dia_row = db.execute(
            '''SELECT value FROM biometric_reading WHERE user_id = ? AND metric_name = 'blood_pressure_dia'
               ORDER BY recorded_date DESC LIMIT 1''', (user_id,)
        ).fetchone()
        dia = float(dia_row['value']) if dia_row else 0
        if value > 180 or dia > 120:
            notif = ('danger', f'⚠ Hypertensive Crisis ({int(value)}/{int(dia)} mmHg) — Call 911 immediately')
        elif value >= 140 or dia >= 90:
            notif = ('warning', f'⚠ Hypertension Stage 2 ({int(value)}/{int(dia)} mmHg) — Seek medical attention')
        elif value >= 130 or dia >= 80:
            notif = ('caution', f'⚠ Hypertension Stage 1 ({int(value)}/{int(dia)} mmHg) — Consult your doctor')
        elif value >= 120:
            notif = ('info', f'Blood Pressure Elevated ({int(value)}/{int(dia)} mmHg) — Monitor regularly')

    elif metric_name == 'spo2':
        if value < 80:
            notif = ('danger', f'⚠ Cyanosis ({value}% SpO2) — Seek emergency care now')
        elif value < 90:
            notif = ('danger', f'⚠ Critically Low SpO2 ({value}%) — Seek medical attention immediately')
        elif value < 91:
            notif = ('warning', f'⚠ Low SpO2 ({value}%) — Monitor closely')
        elif value < 95:
            notif = ('caution', f'⚠ Concerning SpO2 ({value}%) — Consult your doctor')

    elif metric_name == 'glucose':
        if value < 50:
            notif = ('danger', f'⚠ Danger Low Glucose ({value} mg/dL) — Seek medical attention now')
        elif value < 70:
            notif = ('warning', f'⚠ Low Glucose ({value} mg/dL) — Consult your doctor')
        elif value > 315:
            notif = ('danger', f'⚠ Danger High Glucose ({value} mg/dL) — Seek medical attention now')
        elif value > 180:
            notif = ('warning', f'⚠ High Glucose ({value} mg/dL) — Consult your doctor')
        elif value > 108:
            notif = ('caution', f'Borderline Glucose ({value} mg/dL) — Monitor closely')

    elif metric_name == 'temperature':
        if value < 95:
            notif = ('danger', f'⚠ Hypothermia ({value}°F) — Seek medical attention immediately')
        elif value > 102.2:
            notif = ('danger', f'⚠ High Fever ({value}°F) — Seek medical attention')
        elif value > 100.4:
            notif = ('warning', f'⚠ Fever ({value}°F) — Consult your doctor')
        elif value > 99.1:
            notif = ('caution', f'Slight Fever ({value}°F) — Monitor closely')

    elif metric_name == 'bmi':
        if value < 18.5:
            notif = ('caution', f'BMI indicates Underweight ({value}) — Consult your doctor')
        elif value >= 30:
            notif = ('warning', f'BMI indicates Obese ({value}) — Consult your doctor')
        elif value >= 25:
            notif = ('caution', f'BMI indicates Overweight ({value}) — Monitor your health')

    elif metric_name == 'hrv':
        if value < 40:
            notif = ('warning', f'⚠ Low HRV ({value} ms) — Consult your doctor')

    if notif:
        create_notification(db, user_id, metric_name, value, notif[0], notif[1])
        db.commit()


# Individual Register Page
@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username   = request.form.get('username', '').strip()
        password   = request.form.get('password', '').strip()
        first_name = request.form.get('first_name', '')
        last_name  = request.form.get('last_name', '')
        dob        = request.form.get('dob', '')
        sex        = request.form.get('sex', '')
        height_ft  = request.form.get('height_ft') or None
        height_in  = request.form.get('height_in') or None
        weight     = request.form.get('weight') or None
        weight_unit    = request.form.get('weight_unit', 'lbs')
        blood_type     = request.form.get('blood_type', '')
        health_goal    = request.form.get('health_goal', '')
        medications    = request.form.get('medications', '')
        surgeries      = request.form.get('surgeries', '')
        smoking        = request.form.get('smoking', '')
        quit_date      = request.form.get('quit_date', '')
        years_smoked   = request.form.get('years_smoked') or None
        alcohol        = request.form.get('alcohol', '')
        exercise       = request.form.get('exercise', '')
        sleep          = request.form.get('sleep', '')
        stress         = request.form.get('stress', '')
        allergies      = request.form.get('allergies', '')
        emergency_name  = request.form.get('emergency_name', '')
        emergency_phone = request.form.get('emergency_phone', '')
        doctor_name    = request.form.get('doctor_name', '')
        insurance      = request.form.get('insurance', '')
        account_type   = request.form.get('account_type', 'individual')

        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            try:
                db.execute(
                    '''INSERT INTO user (
                        username, password, first_name, last_name, dob, sex,
                        height_ft, height_in, weight, weight_unit, blood_type,
                        health_goal, medications, surgeries, smoking, quit_date,
                        years_smoked, alcohol, exercise, sleep, stress, allergies,
                        emergency_name, emergency_phone, doctor_name, insurance,
                        account_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        username, generate_password_hash(password),
                        first_name, last_name, dob, sex,
                        height_ft, height_in, weight, weight_unit, blood_type,
                        health_goal, medications, surgeries, smoking, quit_date,
                        years_smoked, alcohol, exercise, sleep, stress, allergies,
                        emergency_name, emergency_phone, doctor_name, insurance,
                        account_type
                    ),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')


# Caregiver Register Page
@bp.route('/caregiver/register', methods=('GET', 'POST'))
def register_caregiver():
    if request.method == 'POST':
        username       = request.form.get('username', '').strip()
        password       = request.form.get('password', '').strip()
        caregiver_type = request.form.get('caregiver_type', '')
        duration       = request.form.get('duration', '')
        end_date       = request.form.get('end_date', '')
        first_name     = request.form.get('first_name', '')
        last_name      = request.form.get('last_name', '')
        email          = request.form.get('email', '')
        clinical_id    = request.form.get('clinical_id', '')
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif not caregiver_type:
            error = 'Caregiver type is required.'

        if error is None:
            try:
                db.execute(
                    '''INSERT INTO user (
                        username, password, account_type,
                        first_name, last_name, email, clinical_id,
                        caregiver_type, duration, end_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        username, generate_password_hash(password), 'caregiver',
                        first_name, last_name, email, clinical_id,
                        caregiver_type, duration, end_date
                    ),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/caregiver/register_caregiver.html')


# Login Page
@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            # Redirect caregivers to caregiver dashboard
            if user['account_type'] == 'caregiver':
                return redirect(url_for('caretaker.dashboard'))
            return redirect(url_for('main.dashboard'))

        flash(error)

    return render_template('auth/login.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view