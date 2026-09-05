import sqlite3

conn = sqlite3.connect("report.db")
conn.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        customer TEXT NOT NULL,
        product TEXT NOT NULL,
        amount REAL NOT NULL,
        created_at DATE NOT NULL
    )
""")
conn.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY,
        path TEXT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()
conn.close()
