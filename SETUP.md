# BioSync — Setup Guide
> How to get the VitalWatch project working on your local machine

---

## Prerequisites

Make sure you have the following installed before starting:

- [Python 3.11 or newer](https://www.python.org/downloads/)
- [Git](https://git-scm.com) or Git Desktop
- [VS Code](https://code.visualstudio.com) (recommended)

---

## Step 1 — Clone the Repository

**In the terminal:**
```bash
git clone https://github.com/your-group/BioSync.git
cd BioSync
```

**In Git Desktop:**
File → Clone Repository → paste the repo URL

---

## Step 2 — Create a Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\activate
```

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal prompt.

---

## Step 3 — Install Dependencies
```powershell
pip install -r requirements.txt
pip install pdfplumber python-docx pandas numpy
```

---

## Step 4 — Initialize the Database

**Windows:**
```powershell
$env:FLASK_APP = "__init__"
flask init-db
```

**Mac / Linux:**
```bash
export FLASK_APP=__init__
flask init-db
```

You should see: `Initialized the database.`

---

## Step 5 — Run the App

**Windows:**
```powershell
$env:FLASK_APP = "__init__"
flask run
```

**Mac / Linux:**
```bash
export FLASK_APP=__init__
flask run
```

Then open your browser and go to:
```
http://127.0.0.1:5000
```

---

## Step 6 — Create an Account

Go to `http://127.0.0.1:5000/auth/register` and create your account.  
Then log in at `http://127.0.0.1:5000/auth/login`.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Could not import BioSync.BioSync` | Run flask from inside the BioSync folder with `FLASK_APP=__init__` |
| `TemplateNotFound: auth/register.html` | Make sure `templates/auth/` folder exists with `login.html` and `register.html` inside |
| `No such file: requirements.txt` | You are in the wrong folder — `cd BioSync` first |
| `Initialized the database` shows error | Delete `instance/flaskr.sqlite` and run `flask init-db` again |
| `pip not recognized` | Make sure Python is installed and added to PATH |
