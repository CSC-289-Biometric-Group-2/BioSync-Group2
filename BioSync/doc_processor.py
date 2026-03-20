import pdfplumber
import re
from docx import Document as DocxDocument

def extract_text(filepath):
    ext = filepath.rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    elif ext == 'docx':
        doc = DocxDocument(filepath)
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        with open(filepath, 'r') as f:
            return f.read()

# Add or extend these patterns to match your actual documents
PATTERNS = {
    'heart_rate':         r'(?:heart rate|pulse)[:\s]+(\d+)\s*bpm',
    'blood_pressure_sys': r'(\d{2,3})\s*/\s*\d{2,3}\s*mmhg',
    'blood_pressure_dia': r'\d{2,3}\s*/\s*(\d{2,3})\s*mmhg',
    'spo2':               r'(?:spo2|oxygen)[:\s]+(\d+)\s*%',
    'temperature':        r'(?:temp(?:erature)?)[:\s]+([\d.]+)\s*[°]?[fc]',
    'glucose':            r'(?:glucose|blood sugar)[:\s]+([\d.]+)\s*mg/dl',
    'weight':             r'(?:weight)[:\s]+([\d.]+)\s*(?:kg|lbs)',
    'bmi':                r'(?:bmi)[:\s]+([\d.]+)',
    'hrv':                r'(?:hrv|heart rate variability)[:\s]+([\d.]+)',
}

def parse_biometrics(text):
    results = []
    lower = text.lower()
    for metric, pattern in PATTERNS.items():
        for match in re.finditer(pattern, lower):
            try:
                results.append({
                    'metric_name': metric,
                    'value': float(match.group(1))
                })
            except ValueError:
                pass
    return results

def process_document(filepath):
    text = extract_text(filepath)
    return parse_biometrics(text)
