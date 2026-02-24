"""
database.py
-----------
SQLite connection helper using raw sqlite3.
Creates and initializes all tables on startup.
"""

import sqlite3
import os

# Database file path — sits at backend root level
DB_PATH = os.path.join(os.path.dirname(__file__), "ticket_system.db")


def get_connection() -> sqlite3.Connection:
    """
    Returns a sqlite3 connection with row_factory set so that
    rows behave like dictionaries (column-accessible by name).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # allows dict-like access: row["column"]
    conn.execute("PRAGMA journal_mode=WAL;")  # better concurrency
    return conn


def init_db():
    """
    Creates all required tables if they do not already exist.
    Call once at application startup.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # ------------------------------------------------------------------
    # USERS table
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            department  TEXT,
            password    TEXT    NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP   
        )
    """)

    # ------------------------------------------------------------------
    # ADMINS table
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            department  TEXT,
            password    TEXT    NOT NULL
        )
    """)

    # ------------------------------------------------------------------
    # TICKETS table
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            description      TEXT    NOT NULL,
            category         TEXT,
            priority         TEXT,
            status           TEXT    DEFAULT 'Open',
            similarity_score REAL,
            feedback         INTEGER,           -- NULL / 1 (helpful) / 0 (not helpful)
            escalation_flag  INTEGER DEFAULT 0,
            created_at       DATETIME DEFAULT CURRENT_TIMESTAMP   ,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ------------------------------------------------------------------
    # RESOLUTIONS table
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resolutions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id        INTEGER NOT NULL,
            resolution_text  TEXT    NOT NULL,
            helpful_count    INTEGER DEFAULT 0,
            not_helpful_count INTEGER DEFAULT 0,
            resolved_date    DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id)
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")