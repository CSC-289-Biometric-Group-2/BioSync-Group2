from app import app
import sqlite3
import os

with app.app_context():
    db_path = os.path.join(app.instance_path, 'biosync.db')
    print(f"Creating database at: {db_path}")
    conn = sqlite3.connect(db_path)
    with open('schema.sql') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print('All tables created successfully!')