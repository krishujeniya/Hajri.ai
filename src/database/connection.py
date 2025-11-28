"""
Database connection and initialization
Handles all database setup and connection management
"""

import sqlite3
from typing import Optional
from contextlib import contextmanager
from src.config.settings import Config


def get_connection() -> sqlite3.Connection:
    """
    Get a database connection with foreign keys enabled.
    
    Returns:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(str(Config.DB_FILE))
    if Config.DB_FOREIGN_KEYS:
        conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db():
    """
    Context manager for database connections.
    Automatically handles connection closing.
    
    Usage:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize database with all required tables"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student'))
        );
        """)
        
        # Subjects table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL UNIQUE
        );
        """)
        
        # Teacher-Subject mapping
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_subjects (
            user_id INTEGER,
            subject_id INTEGER,
            PRIMARY KEY (user_id, subject_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE
        );
        """)
        
        # Student-Subject mapping
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_subjects (
            user_id INTEGER,
            subject_id INTEGER,
            PRIMARY KEY (user_id, subject_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE
        );
        """)
        
        # Lectures table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS lectures (
            lecture_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            lecture_name TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects (subject_id) ON DELETE CASCADE,
            UNIQUE(subject_id, lecture_name)
        );
        """)
        
        # Attendance table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lecture_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('P', 'A')),
            FOREIGN KEY (lecture_id) REFERENCES lectures (lecture_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
            UNIQUE(lecture_id, user_id)
        );
        """)
        
        conn.commit()
        print("✅ Database initialized successfully")
