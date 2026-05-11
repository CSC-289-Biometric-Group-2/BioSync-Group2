# BioSync
> A biometric health Ecosystem that bridges the gap between patients, caregivers, and providers.

**CSC 289 · Programming Capstone · Spring 2026**
**Fayetteville Technical Community College · Group 2**

---

BioSync consolidates health data collection, storage, and analysis into a single accessible platform. Patients upload medical documents and log readings — heart rate, blood pressure, blood oxygen, glucose, and more — and the app extracts biometric data automatically, tracks trends over time, and alerts when values fall outside safe ranges.

Caregivers connect to patients through a secure, patient-initiated linking system using a unique code — no shared passwords, no HIPAA violations. They get a role-scoped view of the patients they support: readings, alerts, and documents, without access to anything beyond what their role requires.

The project was inspired by a real problem: team lead Sarah Ayres is an active caregiver whose mother is a veteran. Managing care across VA and local hospital systems — where medication changes take days to communicate and no tool adequately supports the caregiver role — directly shaped every feature in BioSync.

## Screenshots

<!-- Take a screenshot of your dashboard and save it as docs/screenshot.png -->
[BioSync Landing](docs/screenshot.png)

## Quick Start (GitHub Codespace)

1. Click **Code** → **Codespaces** → **Create codespace on main**
2. Run `bash setup.sh`
3. Run `bash run.sh`
4. Open the forwarded port URL — BioSync loads in your browser
5. Register at `/auth/register`, then log in at `/auth/login`

## Features

- **PDF Lab Report Parsing** — upload a report and biometric readings are extracted and stored automatically
- **Health Trend Charts** — visualize heart rate, blood pressure, SpO₂, glucose, and more over time
- **Smart Health Alerts** — age- and sex-adjusted notifications flag readings outside safe ranges
- **Caregiver Portal** — caregivers link to patients via a unique code, no shared credentials needed
- **Document Hub** — all uploaded medical documents organized and accessible in one place
- **Baseline Comparison** — detects meaningful shifts by comparing recent readings to your historical average
- **CSV Export** — download biometric history per metric or as a full all-readings report to share with providers

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, Flask 3.1 |
| Database | SQLite |
| Auth | Werkzeug (PBKDF2-SHA256), Flask sessions |
| Doc Parsing | pdfplumber |
| Data Analysis | NumPy, pandas |
| Report Generation | ReportLab |
| Frontend | Jinja2, HTML, CSS, JavaScript |
| Dev Environment | GitHub Codespaces |

## Team

| Name | Role | Contribution | GitHub |
|------|------|-------------|--------|
| Sarah Ayres | Scrum Master | Led full-stack development across all major features — dashboard, caregiver portal, PDF extraction, notification system, clinical thresholds, and UI design | [@Sayres-dev](https://github.com/Sayres-dev) |
| Joshua Eckman | Developer | Built the initial Flask application structure and SQLite database schema. Implemented age/sex-based heart rate thresholds using CDC resting BPM ranges | [@Eckmanj8966](https://github.com/Eckmanj8966) |
| Myra Williams | Developer | Built the live biometric readings feature allowing users to log real-time vitals directly from connected devices (companion Python app — not included in this repository) | [@mwill2214](https://github.com/mwill2214) |
| Toni Wilson | Developer | Prepped initial pitch and user stories | [@toniwilson](https://github.com/toniwilson) |

## Future Implications

- **Native iOS & Android Apps** — dedicated mobile applications for both platforms connecting directly to wearable devices via Bluetooth
- **Device Integration** — direct Bluetooth connectivity to home monitors; readings flow into BioSync automatically
- **Medication List Automation** — automatically extract medication changes from uploaded discharge summaries and visit records
- **PDF Summary Output** — one-tap generation of a provider-ready PDF health summary for any appointment
- **Sleep Data Tracking** — sync sleep metrics from wearables and health apps for a complete wellness picture
- **Cycle Tracking** — integrated menstrual cycle tracking to provide context for biometric fluctuations
- **Cloud Deployment** — production deployment to Render with PostgreSQL for scalability and persistent storage
- **Health App Integration** — sync with Apple Health, Google Health Connect, and Samsung Health

## Project Documents

- [Project Binder](docs/BioSync_ProjectBinder.pdf)
- [Pitch Deck](docs/BioSync_Presentation__2__6556985.pptx)
- [Project Showcase](https://CSC-289-Biometric-Group-2.github.io/BioSync-Group2)

## License

This project was created for educational purposes as part of the CSC 289 Programming Capstone at Wake Technical Community College.
