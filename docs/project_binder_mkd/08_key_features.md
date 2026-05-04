# Key Features & Implementation Notes

---

## Feature 1: Intelligent Biometric Alert Engine

### What It Does

When a user submits a biometric reading — whether manually entered or extracted from an uploaded document — the application automatically evaluates that reading against medically established thresholds. If the value falls outside a normal range, a notification is generated and stored in the user's notification center. Notifications are color-coded by severity: **info**, **caution**, **warning**, and **danger**. Caregivers can also see alerts for their linked patients.

### How It Works

The `check_and_notify()` function in `auth.py` is called every time a new reading is saved. It evaluates eight metrics against multi-tier thresholds:

- **Heart rate** — thresholds are age- and sex-specific. The user's date of birth and sex are used to select the appropriate normal range (e.g., males 65+: 62–73 BPM vs. adult females: 60–80 BPM). Readings outside the range trigger tachycardia or bradycardia alerts.
- **Blood pressure** — staged as normal, elevated, Stage 1 hypertension, Stage 2 hypertension, or hypertensive crisis (≥180/≥120 mmHg), with the crisis level generating a "Call 911 immediately" message.
- **SpO2** — levels below 90% are flagged as critical; 90–94% as low; 95–96% as worth monitoring.
- **Glucose** — separate danger, warning, and borderline thresholds for both hypoglycemia and hyperglycemia.
- **Temperature** — stages cover hypothermia, low-grade fever, moderate fever, and high fever.
- **BMI** — categories follow standard WHO classifications (underweight, overweight, obese).
- **HRV** — a low-HRV warning is generated below a configurable threshold.

Notifications are written to the `notification` table and an unread count is exposed via `/api/notifications/unread-count` for the navbar badge.

### Challenges Encountered

Getting heart rate thresholds right required research into age- and sex-adjusted normal ranges. An early version used a single flat range for all users, which produced false alerts for elderly patients whose resting heart rates naturally trend lower. The fix involved calculating the user's current age at query time from their stored date of birth and selecting from a lookup of ranges.

---

## Feature 2: Medical Document Parsing Pipeline

### What It Does

Users can upload PDF, DOCX, or plain-text medical records (lab reports, discharge summaries, clinic notes) through the Document Hub. The application extracts text from the file and attempts to identify biometric values using pattern matching. Any values found are automatically added as biometric readings linked to that document. This removes the need for manual re-entry of data that already exists in a document.

### How It Works

`doc_processor.py` drives the pipeline in two stages:

1. **Text extraction** — `extract_text(filepath)` routes to the appropriate parser based on file extension: `pdfplumber` for PDFs, `python-docx` for DOCX, and standard file I/O for TXT and CSV.

2. **Biometric parsing** — `parse_biometrics(text)` applies a set of compiled regular expressions against the full extracted text. Each regex is designed to be format-tolerant; for example, the heart rate pattern matches `Heart Rate: 72 BPM`, `Pulse: 72`, and `HR: 72 bpm`. Matched values are deduplicated within a single document before being stored, so a document that mentions the same value multiple times only creates one reading.

The route handler in `routes.py` calls both functions on upload, stores the returned readings in `biometric_reading` with `source='document'` and the `document_id` reference, and marks the document as `processed=1`.

### Challenges Encountered

Medical documents have no standard format, so the regex patterns had to be written broadly enough to handle varied phrasing while avoiding false positives. Numeric values that appear in non-metric contexts (page numbers, patient IDs) initially caused spurious readings. Adding unit-awareness to the patterns — requiring a recognizable unit string near the numeric value — reduced false matches significantly.

---

## Feature 3: Dual-Account System with Caregiver Linking

### What It Does

BioSync supports two account types: **individual patient** and **caregiver**. At registration, the user selects which type they are, and the application routes them to the appropriate dashboard and feature set. Caregivers can be linked to one or more patients; patients can be linked to one or more caregivers. Caregivers can view patient readings, upload documents on a patient's behalf, and see aggregated alerts for all of their linked patients.

### How It Works

Account type is stored in `user.account_type` (`'individual'` or `'caregiver'`). On login, `auth.py` checks this field and redirects accordingly. A `caregiver_required` decorator in `caretaker/routes.py` blocks non-caregivers from accessing caregiver routes.

Linking is done via a **patient code** system:

1. The patient navigates to their profile and generates a unique 8-character code (stored in the `patient_code` table).
2. The patient shares this code with their caregiver out of band (verbally, by text, etc.).
3. The caregiver enters the code at `/caretaker/link-patient`. The app looks up the corresponding patient and inserts a row in `caretaker_link`.

This design avoids exposing patient search or patient IDs directly in the caregiver UI — a caregiver can only link to patients who actively share their code.

### Challenges Encountered

Ensuring that caregivers could not access data for patients they are not linked to required careful filtering on every caregiver route. Each query in `caretaker/routes.py` joins against `caretaker_link` to verify the relationship before returning any patient data.

---

## Feature 4: Historical Trend Analysis with Baseline Comparison

### What It Does

The Trends page lets users select any biometric metric they have recorded and view a line chart of readings over time. A time-range selector (7 days, 30 days, 90 days, or all-time) filters the data. A baseline comparison section shows whether the user's recent average is higher, lower, or about the same as their historical average for that metric.

### How It Works

`pattern_engine.py` provides two key functions:

- `get_trends(metric_name, user_id, days)` — queries all readings for the selected metric and time range, then calculates mean, min, max, and trend direction. Trend direction is determined by splitting the readings into two chronological halves and comparing their averages.
- `compare_baseline(metric_name, user_id)` — performs the same split but over the full history, returning the older half's average as the baseline and the newer half's average as the current value.

NumPy is used for the statistical calculations. The route handler in `routes.py` serializes the data as JSON, which Chart.js in the template uses to render an interactive line chart. Blood pressure renders as a dual-line chart (systolic and diastolic).

The CSV export endpoints (`/api/export/readings` and `/api/export/all-readings`) allow users to download their raw data for use in external tools.

### Challenges Encountered

The time-range filter initially queried the database for all readings and then sliced them in Python, which was inefficient for users with long histories. The filter was moved into the SQL `WHERE` clause to let the database handle the date arithmetic. Blood pressure required special handling because two related metrics (`blood_pressure_sys` and `blood_pressure_dia`) need to be plotted together on the same chart, while all other metrics are single-value.

---

## Feature 5: Real-Time Notification Center

### What It Does

The notification center collects all health alerts in one place. Each alert shows the metric name, the out-of-range value, and a plain-language description of what the reading means and what action to consider. Unread notifications are counted and displayed as a badge on the navbar bell icon so that users notice new alerts without having to visit the page.

### How It Works

Notifications are generated by `check_and_notify()` (see Feature 1) and stored in the `notification` table with a `status` field (`info`, `caution`, `warning`, `danger`) and an `is_read` flag.

The `/api/notifications/unread-count` endpoint returns a JSON count used by a small JavaScript snippet in `base.html` to update the badge on every page load. Visiting `/notifications` marks all current notifications as read. Caregivers have a parallel `/caretaker/notifications` route that aggregates alerts across all linked patients, prefixing each message with the patient's name for clarity.

### Challenges Encountered

Avoiding duplicate notifications was a key concern — if a user submits ten identical readings in a row, only one alert per reading should be generated. The current implementation generates a notification on every reading insert rather than deduplicating, which means repeated out-of-range entries do produce repeated alerts. A future improvement would be to suppress alerts when the same metric was already flagged within a short window.
