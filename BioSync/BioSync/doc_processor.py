import re
from datetime import datetime

# ─────────────────────────────────────────────
# TEXT EXTRACTION
# Supports: PDF, DOCX, TXT, CSV
# ─────────────────────────────────────────────
def extract_text(filepath):
    ext = filepath.rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        except Exception:
            return ""
    elif ext == 'docx':
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(filepath)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception:
            return ""
    else:
        # TXT, CSV
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            with open(filepath, 'r', encoding='latin-1') as f:
                return f.read()


# ─────────────────────────────────────────────
# DATE EXTRACTION
# Tries to pull the report date from the document
# text. Handles formats like:
#   "Date: April 19, 2026"
#   "Date: 04/19/2026"
#   "Date: 2026-04-19"
#   "Report Date: December 14, 2025"
# Falls back to None if no date found —
# routes.py will then use today's date.
# ─────────────────────────────────────────────
DATE_PATTERNS = [
    # "Date: April 19, 2026"  or  "Report Date: December 14, 2025"
    (r'(?:report\s*)?date[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
     ['%B %d, %Y', '%B %d %Y']),

    # "Date: 04/19/2026"  or  "Date: 04-19-2026"
    (r'(?:report\s*)?date[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
     ['%m/%d/%Y', '%m-%d-%Y']),

    # "Date: 2026-04-19"  (ISO format)
    (r'(?:report\s*)?date[:\s]+(\d{4}[\/\-]\d{2}[\/\-]\d{2})',
     ['%Y-%m-%d', '%Y/%m/%d']),

    # "| Date: April 19, 2026" (pipe-separated like our PDFs)
    (r'\|\s*date[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
     ['%B %d, %Y', '%B %d %Y']),
]

def extract_date(text):
    """
    Try to extract a report date from document text.
    Returns a datetime object or None.
    """
    lower = text.lower()

    for pattern, formats in DATE_PATTERNS:
        match = re.search(pattern, lower)
        if match:
            raw = match.group(1).strip()
            # Normalize — remove extra spaces, fix comma
            raw = re.sub(r'\s+', ' ', raw)
            for fmt in formats:
                try:
                    return datetime.strptime(raw, fmt)
                except ValueError:
                    continue

    return None


# ─────────────────────────────────────────────
# BIOMETRIC PATTERNS
# Each pattern uses flexible matching to handle
# variations like:
#   "Heart Rate: 72 BPM"
#   "Heart Rate (Resting): 72 BPM"
#   "Pulse: 72"
# ─────────────────────────────────────────────
PATTERNS = {

    # HEART RATE
    # Matches: "Heart Rate: 72 BPM", "Pulse: 72", "HR: 72 bpm"
    'heart_rate': r'(?:heart\s*rate|pulse|resting\s*hr|hr)[^:\d]{0,30}[:\s]+([\d]+)\s*bpm',

    # BLOOD PRESSURE SYSTOLIC
    # Matches: "118/76 mmHg", "Blood Pressure: 118/76"
    # Requires 2-3 digit systolic / 2-3 digit diastolic
    'blood_pressure_sys': r'(?<!\d)(\d{2,3})\s*/\s*\d{2,3}\s*mmhg',

    # BLOOD PRESSURE DIASTOLIC
    'blood_pressure_dia': r'(?<!\d)\d{2,3}\s*/\s*(\d{2,3})\s*mmhg',

    # SPO2
    # Matches: "SpO2: 97%", "SpO2 (Oxygen Saturation): 97%",
    #          "Oxygen Saturation: 97%", "O2 Sat: 97%"
    'spo2': r'(?:spo2|oxygen\s*saturation|o2\s*sat(?:uration)?)[^:\d]{0,40}[:\s]+([\d]+)\s*%',

    # TEMPERATURE
    # Matches: "Temperature: 98.6°F", "Temp: 98.4 F", "Body Temp: 37.0°C"
    'temperature': r'(?:temp(?:erature)?|body\s*temp)[^:\d]{0,30}[:\s]+([\d.]+)\s*[°]?\s*[fc]',

    # GLUCOSE
    # Matches: "Glucose: 95 mg/dL", "Glucose (Fasting): 95 mg/dL",
    #          "Blood Sugar: 95 mg/dL", "Blood Glucose: 95"
    'glucose': r'(?:glucose|blood\s*sugar|blood\s*glucose)[^:\d]{0,30}[:\s]+([\d.]+)\s*(?:mg/dl|mg/dL)?',

    # WEIGHT
    # Matches: "Weight: 265 lbs", "Weight: 120 kg"
    'weight': r'(?:weight)[^:\d]{0,20}[:\s]+([\d.]+)\s*(?:lbs|kg)',

    # BMI
    # Matches: "BMI: 42.8", "Body Mass Index: 22.5"
    'bmi': r'(?:bmi|body\s*mass\s*index)[^:\d]{0,30}[:\s]+([\d.]+)',

    # HRV
    # Matches: "HRV: 55", "Heart Rate Variability: 45 ms",
    #          "HRV (Heart Rate Variability): 38"
    'hrv': r'(?:hrv|heart\s*rate\s*variability)[^:\d]{0,40}[:\s]+([\d.]+)',
}


# ─────────────────────────────────────────────
# PARSE BIOMETRICS FROM TEXT
# Runs all patterns against lowercased text
# Returns list of {metric_name, value} dicts
# ─────────────────────────────────────────────
def parse_biometrics(text):
    results = []
    lower = text.lower()
    seen = set()  # avoid duplicate readings per metric per document

    for metric, pattern in PATTERNS.items():
        for match in re.finditer(pattern, lower):
            try:
                value = float(match.group(1))
                # Skip duplicate metric values in same doc
                key = (metric, value)
                if key not in seen:
                    seen.add(key)
                    results.append({
                        'metric_name': metric,
                        'value': value
                    })
            except (ValueError, IndexError):
                pass

    return results


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# Called by routes.py for each uploaded file.
# Now returns a dict with:
#   'readings' — list of {metric_name, value}
#   'recorded_date' — datetime from the doc, or None
# routes.py uses recorded_date if present,
# otherwise falls back to datetime.now()
# ─────────────────────────────────────────────
def process_document(filepath):
    text = extract_text(filepath)
    return {
        'readings': parse_biometrics(text),
        'recorded_date': extract_date(text),
    }