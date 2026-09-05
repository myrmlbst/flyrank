import datetime
import sqlite3


def get_report_data(db_path: str = "report.db") -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    total_orders = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]

    total_revenue = conn.execute(
        "SELECT SUM(amount) AS total FROM orders"
    ).fetchone()["total"] or 0

    top_products = [
        {"product": row["product"], "revenue": round(row["revenue"], 2)}
        for row in conn.execute("""
            SELECT product, SUM(amount) AS revenue
            FROM orders
            GROUP BY product
            ORDER BY revenue DESC
            LIMIT 5
        """)
    ]

    today = datetime.date.today()
    last_7_days = [
        (today - datetime.timedelta(days=offset)).isoformat()
        for offset in range(6, -1, -1)
    ]
    counts_by_day = dict(
        conn.execute("""
            SELECT created_at, COUNT(*) AS n
            FROM orders
            WHERE created_at >= date('now', '-6 days')
            GROUP BY created_at
        """).fetchall()
    )
    orders_per_day = [
        {"date": day, "count": counts_by_day.get(day, 0)} for day in last_7_days
    ]

    conn.close()

    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "top_products": top_products,
        "orders_per_day": orders_per_day,
    }


def get_all_orders(db_path: str = "report.db") -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in conn.execute(
            "SELECT id, customer, product, amount, created_at FROM orders ORDER BY created_at, id"
        )
    ]
    conn.close()
    return rows
