# VitalWatch
> A Biometric Wellness Ecosystem

**CSC 289-0B01 · Programming Capstone · Spring 2026**  
**Group 2:** Joshua · Toni · Myra · Sarah

---

## What is VitalWatch?

VitalWatch is a biometric wellness web application built with Python and Flask.
Users can create a personal health profile, upload medical documents, and track
long-term biometric patterns — including heart rate, blood pressure, SpO2,
glucose, sleep, and more. The platform unifies fragmented health data into one
personalized dashboard.

VitalWatch supports two account types — Individual patients and Caregivers —
allowing trusted family members, formal caregivers, and healthcare professionals
to securely view and manage a patient's biometric information.

---

## Features

- Secure user registration and login for Individual and Caregiver accounts
- Medical document upload (PDF, DOCX, TXT, CSV)
- Automatic extraction of biometric readings from documents
- Long-term trend tracking and pattern comparison
- Personal health profile dashboard
- Caregiver linking via unique patient code
- Role-based access for different caregiver types
- REST API for biometric data

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, Flask 3.1 |
| Database | SQLite |
| Auth | Werkzeug password hashing, Flask sessions |
| Doc Parsing | pdfplumber, python-docx |
| Data Analysis | pandas, numpy |
| Frontend | Jinja2, HTML, CSS |

---

## Caregiver Types

| Type | Access Level |
|------|-------------|
| Informal (family, friends) | View, add and delete readings |
| Formal (agency or facility) | View and add readings |
| Agency (CNA, multiple clients) | View only |
| Senior Living | View and add readings |

---

## Getting Started

See [SETUP.md](SETUP.md) for full instructions on running the project locally.

---

## License

This project was created for educational purposes as part of the CSC 289
Programming Capstone at Fayetteville Technical Community College.