from pathlib import Path
import sqlite3


DB_PATH = f"{Path(__file__).parent.resolve()}/books.db"
CREATE_DB = """
CREATE TABLE IF NOT EXISTS books(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    author TEXT,
    status TEXT,
    date_started TEXT,
    date_completed TEXT
)
"""

if not Path(DB_PATH).is_file():
    CONN = sqlite3.connect(DB_PATH)
    CONN.execute(CREATE_DB)
    CONN.close()

CONN = sqlite3.connect(DB_PATH)
