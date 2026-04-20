import re

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
# Called by routes.py for each uploaded file
# ─────────────────────────────────────────────
def process_document(filepath):
    text = extract_text(filepath)
    return parse_biometrics(text)