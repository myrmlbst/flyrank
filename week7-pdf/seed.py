import datetime
import random
import sqlite3

PRODUCTS = ["Widget", "Gadget", "Gizmo", "Doohickey", "Thingamajig", "Contraption"]
FIRST_NAMES = ["Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Jamie"]
LAST_NAMES = ["Lee", "Patel", "Garcia", "Chen", "Smith", "Nguyen", "Brown", "Khan"]

NUM_ORDERS = 200
DAYS_BACK = 90

conn = sqlite3.connect("report.db")
conn.execute("DELETE FROM orders")
today = datetime.date.today()

rows = []
for _ in range(NUM_ORDERS):
    customer = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    product = random.choice(PRODUCTS)
    amount = round(random.uniform(5, 200), 2)
    created_at = today - datetime.timedelta(days=random.randint(0, DAYS_BACK))
    rows.append((customer, product, amount, created_at.isoformat()))

conn.executemany(
    "INSERT INTO orders (customer, product, amount, created_at) VALUES (?, ?, ?, ?)",
    rows,
)
conn.commit()
conn.close()

print(f"Inserted {NUM_ORDERS} orders into report.db")
