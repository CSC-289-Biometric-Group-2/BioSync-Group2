# System Architecture

## 6a. Tech Stack

| Technology | Category | Reason Used |
|-----------|----------|-------------|
| Python 3.11+ | Language | Course requirement; well-suited for Flask web development |
| Flask 3.1.3 | Web framework | Lightweight, blueprint-based structure allows modular organization |
| Jinja2 3.1.6 | Templating | Bundled with Flask; enables server-side HTML rendering with template inheritance |
| Werkzeug 3.1.6 | Security / WSGI | Provides password hashing and WSGI utilities bundled with Flask |
| SQLite 3 | Database | Zero-configuration file-based database; appropriate for a single-server development build |
| pdfplumber | Document parsing | Extracts text from uploaded PDF medical records |
| python-docx | Document parsing | Extracts text from DOCX medical record uploads |
| NumPy | Data analysis | Statistical calculations (mean, trend direction) for the pattern engine |
| Tailwind CSS (CDN) | Frontend styling | Utility-first CSS framework for rapid UI development without a build step |
| Chart.js (CDN) | Data visualization | Client-side charting library used to render biometric trend line charts |
| Material Symbols | Icons | Google icon font for consistent UI iconography |

---

## 6b. Application Structure

BioSync follows a **Flask Blueprint** architecture, separating concerns into three distinct modules.

```
BioSync/
├── __init__.py          # App factory — creates Flask app, registers blueprints, inits DB
├── auth.py              # Auth blueprint — registration, login, logout, alert engine
├── routes.py            # Main blueprint — all patient-facing routes
├── db.py                # Database helpers — get_db(), init_db(), teardown
├── doc_processor.py     # Document pipeline — text extraction + regex biometric parsing
├── pattern_engine.py    # Trend engine — statistics, baseline comparison (NumPy)
├── schema.sql           # SQLite schema — all CREATE TABLE statements
├── requirements.txt
├── static/
│   ├── BioSync.png      # Application logo
│   └── style.css        # Custom CSS
├── templates/
│   ├── base.html        # Base layout (navbar, notification badge, footer)
│   ├── index.html       # Landing page
│   ├── dashboard.html   # Patient overview (biometric cards, recent docs)
│   ├── trends.html      # Trend visualization (Chart.js, time-range filter)
│   ├── manual_readings.html  # Biometric entry form
│   ├── doc_hub.html     # Document upload center
│   ├── notifications.html    # Alert center
│   ├── auth/            # Login, register, individual profile templates
│   └── caretaker/       # Caregiver dashboard, patient view, link patient templates
└── caretaker/
    ├── __init__.py
    ├── routes.py        # Caregiver blueprint — caregiver dashboard and patient management
    └── utils.py         # Patient code generation utility
```

### Request Flow

```
Browser Request
      │
      ▼
  Flask App (__init__.py)
      │
      ├─── Auth Blueprint (auth.py)
      │         └── /auth/*  →  session management, registration
      │
      ├─── Main Blueprint (routes.py)
      │         └── /*, /dashboard, /add-reading, /doc-hub, /trends-overview, /api/*
      │                  │
      │                  ├── db.py → SQLite (instance/flaskr.sqlite)
      │                  ├── doc_processor.py → pdfplumber / python-docx
      │                  └── pattern_engine.py → NumPy statistics
      │
      └─── Caretaker Blueprint (caretaker/routes.py)
                └── /caretaker/*  →  caregiver dashboard, patient linking
```

Business logic lives primarily in `routes.py` and `caretaker/routes.py`. Shared logic (alert thresholds, password handling) lives in `auth.py`. Document parsing and trend calculations are isolated in `doc_processor.py` and `pattern_engine.py` respectively.

---

## 6c. Route Map

### Authentication Routes

| Route | Method | Description | Auth Required? |
|-------|--------|-------------|----------------|
| `/auth/register` | GET, POST | Individual user registration | No |
| `/auth/caregiver/register` | GET, POST | Caregiver account registration | No |
| `/auth/login` | GET, POST | Login; routes caregivers to caregiver dashboard, patients to main dashboard | No |
| `/auth/logout` | GET | Clears session and redirects to login | No |

### Patient Routes

| Route | Method | Description | Auth Required? |
|-------|--------|-------------|----------------|
| `/` | GET | Public landing / marketing page | No |
| `/dashboard` | GET | Patient overview — latest readings, recent documents, quick stats | Yes |
| `/add-reading` | GET, POST | Manual biometric entry form (heart rate, BP, SpO2, glucose, temperature, weight, BMI, HRV) | Yes |
| `/doc-hub` | GET, POST | Document upload center; triggers document parsing pipeline on upload | Yes |
| `/upload` | GET, POST | Legacy upload route (kept for backward compatibility) | Yes |
| `/trends-overview` | GET | Biometric trend visualization with time-range filter (7/30/90 days or all) | Yes |
| `/individual-profile` | GET | Patient profile — bio details, BP chart, care team, clinical notes, documents | Yes |
| `/generate-code` | POST | Generates a unique patient code for caregiver linking | Yes |
| `/trends/<metric_name>` | GET | Legacy per-metric trends endpoint | Yes |
| `/notifications` | GET | Notification center; auto-marks all as read on visit | Yes |
| `/notifications/clear` | POST | Deletes all notifications for the current user | Yes |
| `/api/notifications/unread-count` | GET | JSON — returns count of unread notifications (used for navbar badge) | Yes |
| `/api/export/readings` | GET | CSV download for a single metric (query param: `metric=heart_rate`) | Yes |
| `/api/export/all-readings` | GET | CSV download for all readings (past 30 days) | Yes |
| `/api/trends/<metric_name>` | GET | JSON trend data for a given metric | Yes |

### Caregiver Routes

| Route | Method | Description | Auth Required? |
|-------|--------|-------------|----------------|
| `/caretaker/dashboard` | GET | Patient hub — grid of linked patients with latest readings and alert badges | Yes (caregiver) |
| `/caretaker/link-patient` | GET, POST | Enter patient code to establish caregiver–patient link | Yes (caregiver) |
| `/caretaker/patient/<patient_id>` | GET | Detailed view of a linked patient's biometrics, alerts, and documents | Yes (caregiver) |
| `/caretaker/unlink-patient/<patient_id>` | POST | Removes the caregiver–patient relationship | Yes (caregiver) |
| `/caretaker/notifications` | GET | Aggregated alerts across all linked patients | Yes (caregiver) |
| `/caretaker/profile` | GET | Caregiver's own profile — linked patients, total docs, total alerts | Yes (caregiver) |
| `/caretaker/upload` | GET, POST | Upload a document on behalf of a selected patient | Yes (caregiver) |
