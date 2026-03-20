DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS post;
DROP TABLE IF EXISTS medical_document;
DROP TABLE IF EXISTS biometric_reading;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
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
