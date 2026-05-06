DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS post;
DROP TABLE IF EXISTS medical_document;
DROP TABLE IF EXISTS biometric_reading;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  -- Personal details
  first_name TEXT,
  last_name TEXT,
  dob TEXT,
  sex TEXT,
  -- Physical stats
  height_ft INTEGER,
  height_in INTEGER,
  weight REAL,
  weight_unit TEXT DEFAULT 'lbs',
  blood_type TEXT,
  -- Health goals & lifestyle
  health_goal TEXT,
  medications TEXT,
  surgeries TEXT,
  smoking TEXT,
  quit_date TEXT,
  years_smoked INTEGER,
  alcohol TEXT,
  exercise TEXT,
  sleep TEXT,
  stress TEXT,
  allergies TEXT,
  -- Emergency & doctor info
  emergency_name TEXT,
  emergency_phone TEXT,
  doctor_name TEXT,
  insurance TEXT,
  -- Account type
  account_type TEXT DEFAULT 'individual',
  -- Caregiver specific fields
  email TEXT,
  clinical_id TEXT,
  caregiver_type TEXT,
  duration TEXT,
  end_date TEXT,
  organization TEXT
);

-- Stores uploaded medical documents linked to a user
CREATE TABLE medical_document (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  processed INTEGER DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES user (id)
);

-- Stores individual biometric readings extracted from documents
CREATE TABLE biometric_reading (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  document_id INTEGER,
  metric_name TEXT NOT NULL,
  value REAL NOT NULL,
  unit TEXT,
  recorded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  source TEXT,
  FOREIGN KEY (user_id) REFERENCES user (id),
  FOREIGN KEY (document_id) REFERENCES medical_document (id)
);

-- Stores the link between a caregiver and a patient
CREATE TABLE IF NOT EXISTS caretaker_link (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  caregiver_id INTEGER NOT NULL,
  patient_id INTEGER NOT NULL,
  caregiver_type TEXT NOT NULL,
  duration TEXT NOT NULL,
  end_date TEXT,
  linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (caregiver_id) REFERENCES user (id),
  FOREIGN KEY (patient_id) REFERENCES user (id)
);

-- Stores unique patient codes for linking
CREATE TABLE IF NOT EXISTS patient_code (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  code TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user (id)
);

-- Stores clinical notes written or uploaded by the user
CREATE TABLE IF NOT EXISTS clinical_note (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user (id)
);

-- Stores notifications for the user
CREATE TABLE IF NOT EXISTS notification (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  metric TEXT NOT NULL,
  value TEXT NOT NULL,
  status TEXT NOT NULL,
  message TEXT NOT NULL,
  is_read INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user (id)
);