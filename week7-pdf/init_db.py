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
conn.commit()
conn.close()
