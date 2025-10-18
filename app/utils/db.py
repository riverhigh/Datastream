# app/utils/db.py
import sqlite3
import os
import json
from typing import Optional, List

DB_PATH = "storage/datastream.db"
os.makedirs("storage", exist_ok=True)

def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _get_conn()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Analyses table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

# ============================
# User Functions
# ============================
def create_user(username: str, password: str, api_key: str):
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password, api_key) VALUES (?, ?, ?)",
        (username, password, api_key)
    )
    conn.commit()
    conn.close()

def get_user(api_key: str) -> Optional[dict]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE api_key = ?", (api_key,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_credentials(username: str, password: str) -> Optional[dict]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

# ============================
# Analysis Functions
# ============================
def save_analysis_db(analysis_id: str, result: dict, user_id: int):
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO analyses (id, user_id, result) VALUES (?, ?, ?)",
        (analysis_id, user_id, json.dumps(result))
    )
    conn.commit()
    conn.close()

def get_analysis_db(analysis_id: str, user_id: int) -> Optional[dict]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, result, created_at FROM analyses WHERE id = ? AND user_id = ?",
        (analysis_id, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def list_all_analyses(user_id: int) -> List[dict]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, result, created_at FROM analyses WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_analysis_db(analysis_id: str, user_id: int) -> bool:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM analyses WHERE id = ? AND user_id = ?",
        (analysis_id, user_id)
    )
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted
