import numpy as np
from BioSync.db import get_db

def get_trends(user_id, metric_name):
    db = get_db()
    rows = db.execute(
        '''SELECT value, recorded_date FROM biometric_reading
           WHERE user_id = ? AND metric_name = ?
           ORDER BY recorded_date ASC''',
        (user_id, metric_name)
    ).fetchall()

    if not rows:
        return None

    values = [r['value'] for r in rows]
    dates  = [str(r['recorded_date']) for r in rows]

    return {
        'metric':     metric_name,
        'dates':      dates,
        'values':     values,
        'average':    round(float(np.mean(values)), 2),
        'min':        min(values),
        'max':        max(values),
        'count':      len(values),
        'trend':      'increasing' if values[-1] > values[0] else 'decreasing',
        'change_pct': round(((values[-1] - values[0]) / values[0]) * 100, 1) if values[0] != 0 else 0
    }

def get_all_metrics(user_id):
    db = get_db()
    rows = db.execute(
        '''SELECT DISTINCT metric_name FROM biometric_reading
           WHERE user_id = ?''',
        (user_id,)
    ).fetchall()
    return [r['metric_name'] for r in rows]

def compare_baseline(user_id, metric_name):
    db = get_db()
    rows = db.execute(
        '''SELECT value FROM biometric_reading
           WHERE user_id = ? AND metric_name = ?
           ORDER BY recorded_date ASC''',
        (user_id, metric_name)
    ).fetchall()

    values = [r['value'] for r in rows]
    if len(values) < 4:
        return None

    split    = len(values) // 2
    baseline = round(float(np.mean(values[:split])), 2)
    recent   = round(float(np.mean(values[split:])), 2)
    delta    = round(recent - baseline, 2)

    return {
        'baseline_avg': baseline,
        'recent_avg':   recent,
        'delta':        delta,
        'direction':    'up' if delta > 0 else 'down'
    }