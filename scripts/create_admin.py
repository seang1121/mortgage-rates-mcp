"""Create admin user and print API key. Run once during initial setup."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from backend.auth import create_user, generate_api_key
from backend.database import db

email = input("Admin email: ").strip()
password = input("Admin password: ").strip()

if not email or not password:
    print("Email and password required.")
    sys.exit(1)

if len(password) < 8:
    print("Password must be at least 8 characters.")
    sys.exit(1)

# Check if admin already exists
existing = db.query("SELECT id FROM users WHERE email = ?", (email,))
if existing:
    print(f"User {email} already exists.")
    sys.exit(1)

user = create_user(email, password, role='admin')
api_key = generate_api_key(user['id'])

# Mark key tier as admin
db.execute("UPDATE api_keys SET tier = 'admin' WHERE user_id = ?", (user['id'],))

print(f"\nAdmin user created successfully:")
print(f"  Email:   {email}")
print(f"  User ID: {user['id']}")
print(f"  API Key: {api_key}")
print(f"\n  SAVE THIS KEY — it cannot be retrieved later.")
