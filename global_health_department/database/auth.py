import sqlite3
from pathlib import Path

DB_PATH = Path("database/users.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        poe TEXT,
        active INTEGER DEFAULT 1
    )
    """)

    conn.commit()
    conn.close()