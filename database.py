"""
database.py
-----------
Handles SQLite database connection and schema initialisation.
Called once when the Flask app starts up.
"""

import sqlite3
import os

# ---------------------------------------------------------------------------
# Stage 3 schema additions:
#   food_name    - the name of the specific food item (e.g. "Vegetable Biryani")
#   servings     - estimated number of people the donation can feed
#   storage_info - handling/temperature/allergy notes from the donor
#
# These are added with ALTER TABLE so existing rows and data are never touched.
# SQLite ignores the error if the column already exists (we catch it below).
# ---------------------------------------------------------------------------
STAGE3_COLUMNS = [
    ("food_name",    "TEXT",    "''"),
    ("servings",     "INTEGER", "0"),
    ("storage_info", "TEXT",    "''"),
]

# Path to the SQLite database file (created automatically if it doesn't exist)
DB_PATH = os.environ.get(
    "SHAREPLATE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "shareplate.db")
)


def get_connection():
    """
    Open and return a connection to the SQLite database.
    row_factory makes each row behave like a dictionary,
    so we can access columns by name (e.g. row["food_type"]).
    """
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_db():
    """
    Create the database tables if they don't already exist.
    Safe to call every time the app starts — it will never
    overwrite existing data.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ----------------------------------------------------------------
    # donations table
    # Stores every food donation submitted by a donor.
    # ----------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_name  TEXT    NOT NULL,          -- Name of the donor (person or organisation)
            food_type   TEXT    NOT NULL,          -- Category: cooked / raw / packaged / beverages
            quantity    INTEGER NOT NULL,          -- Approximate number of servings
            location    TEXT    NOT NULL,          -- Pickup address or area
            available_from  TEXT NOT NULL,         -- ISO datetime string: when food is ready
            available_until TEXT NOT NULL,         -- ISO datetime string: last pickup time
            notes       TEXT    DEFAULT '',        -- Any extra info from the donor
            status      TEXT    DEFAULT 'available', -- available / matched / collected / expired
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ----------------------------------------------------------------
    # ngos table
    # Stores registered NGOs and their preferences for matching.
    # ----------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ngos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            contact_name    TEXT    NOT NULL,
            phone           TEXT    NOT NULL,
            email           TEXT    DEFAULT '',
            service_area    TEXT    NOT NULL,      -- Area(s) the NGO can reach
            food_preference TEXT    DEFAULT 'any', -- cooked / raw / packaged / any
            min_quantity    INTEGER DEFAULT 1,     -- Minimum servings they can handle
            created_at      TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ----------------------------------------------------------------
    # matches table
    # Records which donation has been matched to which NGO.
    # ----------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            donation_id INTEGER NOT NULL REFERENCES donations(id),
            ngo_id      INTEGER NOT NULL REFERENCES ngos(id),
            matched_at  TEXT    DEFAULT (datetime('now')),
            collected_at TEXT   DEFAULT NULL       -- Filled in when NGO confirms pickup
        )
    """)

    # ----------------------------------------------------------------
    # Stage 3 additions — add new columns to donations if not present.
    # ALTER TABLE ... ADD COLUMN is safe: it never removes existing data.
    # ----------------------------------------------------------------
    for col_name, col_type, col_default in STAGE3_COLUMNS:
        try:
            cursor.execute(
                f"ALTER TABLE donations ADD COLUMN {col_name} {col_type} DEFAULT {col_default}"
            )
        except sqlite3.OperationalError:
            # Column already exists — that is fine, skip silently.
            pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_donations_status_deadline ON donations(status, available_until)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_donations_category ON donations(food_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_donation ON matches(donation_id)")
    conn.commit()
    conn.close()
    print("[OK] Database initialised at:", DB_PATH)
