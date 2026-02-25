"""
database.py
-----------
Database connection helper.

Supports two modes:
  - SQLite (default / local dev): used when DATABASE_URL is not set.
  - PostgreSQL (cloud): used when DATABASE_URL env var is set.
    e.g. DATABASE_URL=postgresql://user:password@host:5432/dbname

Tables are created on startup in both modes.
"""

import os
import sqlite3

# ---------------------------------------------------------------------------
# Detect which database to use
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Heroku/Render sometimes give "postgres://" which psycopg2 needs as "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USE_POSTGRES = bool(DATABASE_URL)

# SQLite fallback path — sits at backend root level
DB_PATH = os.path.join(os.path.dirname(__file__), "ticket_system.db")


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_connection():
    """
    Returns a database connection.
    - PostgreSQL when DATABASE_URL is set (cloud)
    - SQLite otherwise (local dev)

    psycopg2 is only imported when PostgreSQL is actually needed,
    so the app runs fine locally even without psycopg2 installed.
    """
    if USE_POSTGRES:
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            raise RuntimeError(
                "psycopg2-binary is required when DATABASE_URL is set. "
                "Install it with: pip install psycopg2-binary"
            )
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row   # allows dict-like access: row["column"]
        conn.execute("PRAGMA journal_mode=WAL;")  # better concurrency
        return conn


# ---------------------------------------------------------------------------
# Schema helpers (SQL that works for both SQLite and PostgreSQL)
# ---------------------------------------------------------------------------

def _sqlite_create_tables(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            department  TEXT,
            password    TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            department  TEXT,
            password    TEXT    NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            description      TEXT    NOT NULL,
            category         TEXT,
            priority         TEXT,
            status           TEXT    DEFAULT 'Open',
            similarity_score REAL,
            feedback         INTEGER,
            escalation_flag  INTEGER DEFAULT 0,
            created_at       TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resolutions (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id         INTEGER NOT NULL,
            resolution_text   TEXT    NOT NULL,
            helpful_count     INTEGER DEFAULT 0,
            not_helpful_count INTEGER DEFAULT 0,
            resolved_date     TEXT,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id)
        )
    """)
    conn.commit()


def _postgres_create_tables(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          SERIAL PRIMARY KEY,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            department  TEXT,
            password    TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id          SERIAL PRIMARY KEY,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            department  TEXT,
            password    TEXT    NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id               SERIAL  PRIMARY KEY,
            user_id          INTEGER NOT NULL,
            description      TEXT    NOT NULL,
            category         TEXT,
            priority         TEXT,
            status           TEXT    DEFAULT 'Open',
            similarity_score REAL,
            feedback         INTEGER,
            escalation_flag  INTEGER DEFAULT 0,
            created_at       TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resolutions (
            id                SERIAL  PRIMARY KEY,
            ticket_id         INTEGER NOT NULL,
            resolution_text   TEXT    NOT NULL,
            helpful_count     INTEGER DEFAULT 0,
            not_helpful_count INTEGER DEFAULT 0,
            resolved_date     TEXT,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id)
        )
    """)
    conn.commit()
    cursor.close()


# ---------------------------------------------------------------------------
# Public init function
# ---------------------------------------------------------------------------

def init_db():
    """
    Creates all required tables if they do not already exist.
    Call once at application startup.
    """
    conn = get_connection()
    try:
        if USE_POSTGRES:
            _postgres_create_tables(conn)
            print("[DB] PostgreSQL database initialized successfully.")
        else:
            _sqlite_create_tables(conn)
            print("[DB] SQLite database initialized successfully.")
    finally:
        conn.close()