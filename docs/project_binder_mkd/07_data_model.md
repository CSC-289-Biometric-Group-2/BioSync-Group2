# Data Model

## 7a. Entity Relationship Diagram

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────────────┐
│    user     │──1:N──│ medical_document │──1:N──│  biometric_reading  │
│─────────────│       │──────────────────│       │─────────────────────│
│ id (PK)     │       │ id (PK)          │       │ id (PK)             │
│ username    │       │ user_id (FK)     │       │ user_id (FK)        │
│ password    │       │ filename         │       │ document_id (FK)    │
│ account_type│       │ file_path        │       │ metric_name         │
│ ...         │       │ uploaded_at      │       │ value               │
└──────┬──────┘       │ processed        │       │ unit                │
       │              └──────────────────┘       │ recorded_date       │
       │                                         │ source              │
       │──1:N──┐                                 └─────────────────────┘
       │       │
       │  ┌────┴───────────┐       ┌───────────────────┐
       │  │  notification  │       │   patient_code    │
       │  │────────────────│       │───────────────────│
       │  │ id (PK)        │       │ id (PK)           │
       │  │ user_id (FK)   │       │ user_id (FK, UQ)  │
       │  │ metric         │       │ code (UQ)         │
       │  │ value          │       │ created_at        │
       │  │ status         │       └───────────────────┘
       │  │ message        │
       │  │ is_read        │
       │  └────────────────┘
       │
       └─────────────────────────────────────┐
                                             │
┌──────────────────────────────────────────────────────────┐
│                    caretaker_link                        │
│──────────────────────────────────────────────────────────│
│ id (PK)                                                  │
│ caregiver_id (FK → user.id)                              │
│ patient_id   (FK → user.id)                              │
│ caregiver_type                                           │
│ duration                                                 │
│ end_date                                                 │
│ linked_at                                                │
└──────────────────────────────────────────────────────────┘
```

> **Note:** An ERD image generated from a tool such as dbdiagram.io or drawn.io can replace this ASCII diagram when preparing the final submission.

---

## 7b. Data Dictionary

### `user`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, auto-increment | Unique identifier |
| username | TEXT | Unique, NOT NULL | Login name |
| password | TEXT | NOT NULL | Werkzeug-hashed password |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation time |
| first_name | TEXT | | First name |
| last_name | TEXT | | Last name |
| dob | TEXT | | Date of birth (YYYY-MM-DD); used to calculate age-specific HR thresholds |
| sex | TEXT | | `'male'` or `'female'`; used alongside age for heart rate range calculation |
| height_ft | INTEGER | | Height feet component |
| height_in | INTEGER | | Height inches component |
| weight | REAL | | Body weight value |
| weight_unit | TEXT | DEFAULT `'lbs'` | `'lbs'` or `'kg'` |
| blood_type | TEXT | | ABO blood type |
| health_goal | TEXT | | User-entered health goal description |
| medications | TEXT | | Current medications (free text) |
| surgeries | TEXT | | Surgical history (free text) |
| smoking | TEXT | | `'yes'`, `'no'`, or `'former'` |
| quit_date | TEXT | | Date quit smoking (YYYY-MM-DD) |
| years_smoked | INTEGER | | Number of years smoked |
| alcohol | TEXT | | Alcohol use description |
| exercise | TEXT | | Exercise habits description |
| sleep | TEXT | | Sleep habits description |
| stress | TEXT | | Stress level description |
| allergies | TEXT | | Known allergies (free text) |
| emergency_name | TEXT | | Emergency contact name |
| emergency_phone | TEXT | | Emergency contact phone |
| doctor_name | TEXT | | Primary care doctor name |
| insurance | TEXT | | Insurance information |
| account_type | TEXT | DEFAULT `'individual'` | `'individual'` or `'caregiver'`; controls dashboard routing |
| email | TEXT | | Email address (caregiver accounts) |
| clinical_id | TEXT | | Clinical/employee ID (caregiver accounts) |
| caregiver_type | TEXT | | `'nurse'`, `'family'`, `'informal'`, etc. |
| duration | TEXT | | `'short_term'` or `'long_term'` |
| end_date | TEXT | | Optional caregiving end date |
| organization | TEXT | | Employing organization (caregiver accounts) |

### `medical_document`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, auto-increment | Unique identifier |
| user_id | INTEGER | NOT NULL, FK → user.id | Owner of the document |
| filename | TEXT | NOT NULL | Original filename as uploaded |
| file_path | TEXT | NOT NULL | Absolute path to file on disk (`instance/uploads/{user_id}/{filename}`) |
| uploaded_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Upload timestamp |
| processed | INTEGER | DEFAULT `0` | Processing flag: `0` = pending, `1` = biometrics extracted |

### `biometric_reading`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, auto-increment | Unique identifier |
| user_id | INTEGER | NOT NULL, FK → user.id | Patient this reading belongs to |
| document_id | INTEGER | FK → medical_document.id, nullable | Source document if reading came from a file upload; NULL for manual entries |
| metric_name | TEXT | NOT NULL | Metric identifier: `heart_rate`, `blood_pressure_sys`, `blood_pressure_dia`, `spo2`, `glucose`, `temperature`, `weight`, `bmi`, `hrv` |
| value | REAL | NOT NULL | Numeric measurement value |
| unit | TEXT | | Unit string: `BPM`, `mmHg`, `%`, `mg/dL`, `°F`, `lbs`, `ms` |
| recorded_date | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When the reading was recorded |
| source | TEXT | | `'manual'`, `'document'`, or `'device'` |

### `caretaker_link`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, auto-increment | Unique identifier |
| caregiver_id | INTEGER | NOT NULL, FK → user.id | The caregiver user |
| patient_id | INTEGER | NOT NULL, FK → user.id | The patient user |
| caregiver_type | TEXT | NOT NULL | Type of caregiving relationship |
| duration | TEXT | NOT NULL | `'short_term'` or `'long_term'` |
| end_date | TEXT | | Optional planned end date |
| linked_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When the link was established |

### `patient_code`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, auto-increment | Unique identifier |
| user_id | INTEGER | NOT NULL, Unique, FK → user.id | The patient who owns this code; one code per patient enforced |
| code | TEXT | NOT NULL, Unique | 8-character base64-safe code shared with caregivers to establish a link |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Code generation timestamp |

### `notification`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, auto-increment | Unique identifier |
| user_id | INTEGER | NOT NULL, FK → user.id | Recipient of this notification |
| metric | TEXT | NOT NULL | Metric that triggered the alert |
| value | TEXT | NOT NULL | String representation of the out-of-range value |
| status | TEXT | NOT NULL | Severity level: `'info'`, `'caution'`, `'warning'`, `'danger'` |
| message | TEXT | NOT NULL | Human-readable alert message (e.g., "Hypertensive Crisis — Call 911 immediately") |
| is_read | INTEGER | DEFAULT `0` | `0` = unread, `1` = read |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When the alert was generated |

---

## 7c. Key Relationships

**User → Medical Document (one-to-many):** Each user can upload many medical documents. Documents are owned by a single user and stored in a per-user directory on disk.

**User → Biometric Reading (one-to-many):** Each user accumulates many biometric readings over time. Readings may be entered manually or extracted from an uploaded document; the `source` column distinguishes these cases.

**Medical Document → Biometric Reading (one-to-many):** A single uploaded document can produce multiple readings (e.g., a lab report containing heart rate, SpO2, and blood pressure). The `document_id` foreign key links each parsed reading back to its source file for traceability.

**User (caregiver) ↔ User (patient) via Caretaker Link (many-to-many):** A caregiver can be linked to multiple patients and a patient can have multiple caregivers. The `caretaker_link` join table stores metadata about each relationship (type, duration, start date). The link is established by the caregiver entering the patient's unique `patient_code`.

**User → Patient Code (one-to-one):** Each patient has exactly one shareable code. The `UNIQUE` constraint on `user_id` enforces this. Codes are regenerated on demand and the old one is replaced.

**User → Notification (one-to-many):** Every biometric reading that falls outside normal thresholds generates a notification record for that user. Caregivers receive notifications scoped to readings submitted through their uploads on behalf of a patient.
