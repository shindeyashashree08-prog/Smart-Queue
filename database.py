
import sqlite3
import hashlib
import os

DB_NAME = "smartqueue.db"

def hash_password(password: str) -> str:
    """Helper function to hash passwords using SHA-256 for secure storage."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_db_connection():
    """
    Creates and returns a connection to the SQLite database.
    row_factory = sqlite3.Row allows column access by name (like a Python dictionary).
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the database schema by creating all required tables:
    1. users: Stores registered user details
    2. admins: Stores admin credentials for queue management
    3. services: Stores queue categories (Hospital, Bank, College, etc.)
    4. tokens: Stores generated queue tokens and their current status
    5. queue_history: Tracks life-cycle actions (Generated, Serving, Completed, etc.)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Admins Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'Administrator',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Services Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        prefix TEXT NOT NULL UNIQUE,
        avg_time_mins INTEGER NOT NULL,
        description TEXT,
        is_active INTEGER DEFAULT 1
    );
    """)

    # 4. Tokens Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_number TEXT NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        service_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Waiting', -- Waiting, called, Serving, Completed, Cancelled, Skipped
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        called_at TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (service_id) REFERENCES services (id) ON DELETE CASCADE
    );
    """)

    # 5. Queue History Table (Audit Trail)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS queue_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_id INTEGER NOT NULL,
        action TEXT NOT NULL, -- Created, Called, Completed, Cancelled, Skipped
        notes TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (token_id) REFERENCES tokens (id) ON DELETE CASCADE
    );
    """)

    # Seed Default Administrator (username: admin, password: admin123)
    cursor.execute("SELECT * FROM admins WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        default_admin_pass = hash_password("admin123")
        cursor.execute(
            "INSERT INTO admins (username, password, role) VALUES (?, ?, ?)",
            ("admin", default_admin_pass, "Super Admin")
        )
        print("[DB Setup] Default admin created -> Username: admin | Password: admin123")

    # Seed Default Services
    default_services = [
        ("Hospital & Clinic OPD", "HOSP", 10, "Doctor consultation, general physician, and patient health checkup."),
        ("Bank Cash & Accounts", "BANK", 8, "Cash deposits, withdrawals, new account openings, and cheque clearance."),
        ("College Student Section", "CLG", 12, "Admission verification, fee payments, bonafide certificates, and transcripts."),
        ("RTO & Government Services", "GOV", 15, "Driving license tests, document verification, and official permits."),
        ("Salon & Grooming Lounge", "SAL", 20, "Hair styling, grooming, and personal care appointments.")
    ]

    for name, prefix, avg_time, desc in default_services:
        cursor.execute("SELECT * FROM services WHERE prefix = ?", (prefix,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO services (name, prefix, avg_time_mins, description) VALUES (?, ?, ?, ?)",
                (name, prefix, avg_time, desc)
            )
            print(f"[DB Setup] Service added: {name} (Prefix: {prefix})")

    conn.commit()
    conn.close()
    print("[DB Setup] Database 'smartqueue.db' initialized successfully!")

if __name__ == "__main__":
    init_db()
