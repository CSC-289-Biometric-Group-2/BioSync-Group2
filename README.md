# BioSync
> A Biometric Wellness Ecosystem

**CSC 289-0B01 · Programming Capstone · Spring 2026**  
**Group 2:** Joshua · Toni · Myra · Sarah

---

## What is BioSync?

BioSync is a biometric wellness web application built with Python and Flask. 
Users can create a personal health profile, upload medical documents, and track 
long-term biometric patterns — including heart rate, blood pressure, SpO2, 
glucose, sleep, and more. The platform unifies fragmented health data into one 
personalized dashboard.

---

## Features

- Secure user registration and login
- Medical document upload (PDF, DOCX, TXT, CSV)
- Automatic extraction of biometric readings from documents
- Long-term trend tracking and pattern comparison
- Personal health profile dashboard
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

## Getting Started

See [SETUP.md](SETUP.md) for full instructions on running the project locally.

---

## License

This project was created for educational purposes as part of the CSC 289 
Programming Capstone at Wake Tech Community College.
