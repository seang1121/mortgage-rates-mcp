"""SQLite database singleton for the mortgage rates backend."""
import os
import sqlite3
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mortgage_rates.db")


class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.db_path = DB_PATH
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        # Auto-truncate WAL every ~1000 pages to prevent unbounded growth
        # if the app crashes mid-scrape.
        conn.execute("PRAGMA wal_autocheckpoint=1000")
        return conn

    def query(self, sql, params=None):
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params or ())
            return [dict(row) for row in cursor.fetchall()]

    def execute(self, sql, params=None):
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params or ())
            conn.commit()
            return cursor

    def init_db(self):
        with self.get_connection() as conn:
            conn.executescript("""
                -- Current scrape results (replaced each scrape cycle)
                CREATE TABLE IF NOT EXISTS rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lender TEXT NOT NULL,
                    product TEXT NOT NULL,
                    rate REAL NOT NULL,
                    apr REAL,
                    zip_code TEXT,
                    is_benchmark INTEGER DEFAULT 0,
                    stale INTEGER DEFAULT 0,
                    scraped_at TEXT NOT NULL,
                    scrape_session TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Rolling 90-day history with AM/PM granularity
                CREATE TABLE IF NOT EXISTS rate_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time_of_day TEXT NOT NULL,
                    lender TEXT NOT NULL,
                    product TEXT NOT NULL,
                    rate REAL NOT NULL,
                    apr REAL,
                    zip_code TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- User accounts
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- API keys (mort_* prefix)
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    key_prefix TEXT NOT NULL,
                    tier TEXT DEFAULT 'free',
                    requests_today INTEGER DEFAULT 0,
                    last_reset_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    revoked_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                -- User-configured rate threshold alerts
                CREATE TABLE IF NOT EXISTS rate_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    product TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    lender TEXT,
                    active INTEGER DEFAULT 1,
                    last_triggered_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                -- Notification delivery preferences per user
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                -- Per-lender scrape logs for debugging and monitoring
                CREATE TABLE IF NOT EXISTS scrape_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scrape_session TEXT NOT NULL,
                    lender TEXT NOT NULL,
                    status TEXT NOT NULL,
                    rates_found INTEGER DEFAULT 0,
                    error_message TEXT,
                    screenshot_path TEXT,
                    duration_ms INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Indexes for fast lookups
                CREATE INDEX IF NOT EXISTS idx_rates_scrape_session ON rates(scrape_session);
                CREATE INDEX IF NOT EXISTS idx_rates_lender_product ON rates(lender, product);
                CREATE INDEX IF NOT EXISTS idx_rate_history_date ON rate_history(date, product);
                CREATE INDEX IF NOT EXISTS idx_rate_history_lender ON rate_history(lender, product);
                CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
                CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
                CREATE INDEX IF NOT EXISTS idx_scrape_logs_session ON scrape_logs(scrape_session);
            """)


db = Database()
