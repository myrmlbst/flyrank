import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tasks.db"

SEED_TASKS = [
    ("Buy milk", False),
    ("Walk the dog", False),
    ("Learn FastAPI", True),
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()

        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)", SEED_TASKS
            )
            conn.commit()
    finally:
        conn.close()
