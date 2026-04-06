"""Initialize the mortgage rates database. Safe to run multiple times."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from backend.database import db

print(f"Database initialized at: {db.db_path}")
print("Tables:")
tables = db.query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for t in tables:
    count = db.query(f"SELECT COUNT(*) as c FROM [{t['name']}]")[0]['c']
    print(f"  - {t['name']} ({count} rows)")
