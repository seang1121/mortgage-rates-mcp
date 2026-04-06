"""Authentication system — mort_* API keys, open registration, no rate limits (free for now)."""
import hashlib
import secrets
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from backend.database import db

KEY_PREFIX = "mort_"


def generate_api_key(user_id: str) -> str:
    """Generate a mort_* API key. Returns plaintext key (shown once, never again)."""
    raw = secrets.token_hex(32)
    full_key = f"{KEY_PREFIX}{raw}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    prefix = full_key[:12]

    db.execute(
        """INSERT INTO api_keys (user_id, key_hash, key_prefix, tier, requests_today, last_reset_date)
           VALUES (?, ?, ?, 'free', 0, ?)""",
        (user_id, key_hash, prefix, datetime.now().strftime('%Y-%m-%d'))
    )
    return full_key


def validate_api_key(raw_key: str) -> dict | None:
    """Validate an API key. Returns key record or None.

    Currently no rate limiting — all tiers get unlimited access.
    The requests_today counter still increments for analytics/future use.
    """
    if not raw_key or not raw_key.startswith(KEY_PREFIX):
        return None

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    rows = db.query(
        """SELECT ak.*, u.role, u.email
           FROM api_keys ak
           JOIN users u ON ak.user_id = u.id
           WHERE ak.key_hash = ? AND ak.revoked_at IS NULL""",
        (key_hash,)
    )
    if not rows:
        return None

    record = rows[0]
    today = datetime.now().strftime('%Y-%m-%d')

    # Reset daily counter if new day (for analytics, not enforcement)
    if record['last_reset_date'] != today:
        db.execute(
            "UPDATE api_keys SET requests_today = 1, last_reset_date = ? WHERE id = ?",
            (today, record['id'])
        )
    else:
        db.execute(
            "UPDATE api_keys SET requests_today = requests_today + 1 WHERE id = ?",
            (record['id'],)
        )

    record['rate_limited'] = False  # free for now — no limits
    return record


def create_user(email: str, password: str, role: str = 'user') -> dict | None:
    """Create a user account. Returns user dict or None if email already exists."""
    existing = db.query("SELECT id FROM users WHERE email = ?", (email,))
    if existing:
        return None

    user_id = secrets.token_hex(16)
    pw_hash = generate_password_hash(password, method='scrypt', salt_length=32)
    db.execute(
        "INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (user_id, email, pw_hash, role)
    )
    return {'id': user_id, 'email': email, 'role': role}


def register_user(email: str, password: str) -> tuple[dict, str] | tuple[None, str]:
    """Create user + generate API key. Returns (user_dict, api_key) or (None, error_msg)."""
    if not email or '@' not in email:
        return None, "Valid email required"
    if not password or len(password) < 8:
        return None, "Password must be at least 8 characters"

    user = create_user(email, password)
    if user is None:
        return None, "Email already registered"

    api_key = generate_api_key(user['id'])
    return user, api_key
