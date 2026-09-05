import os
import sqlite3

from playwright.sync_api import sync_playwright

from build_html import build_html_report
from report import get_all_orders, get_report_data

OUTPUT_PATH = "reports/test.pdf"
DB_PATH = "report.db"


def _write_pdf(html: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=output_path, format="A4", print_background=True)
        browser.close()


def render_pdf(output_path: str = OUTPUT_PATH, fix_page_breaks: bool = True) -> None:
    report_data = get_report_data()
    orders = get_all_orders()
    html = build_html_report(report_data, orders, fix_page_breaks=fix_page_breaks)

    _write_pdf(html, output_path)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO reports (path) VALUES (?)", (output_path,))
    conn.commit()
    conn.close()

    print(f"Wrote {output_path}")


def find_todays_report() -> int | None:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id FROM reports WHERE date(created_at) = date('now') ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row[0] if row else None


def generate_report() -> int:
    """Runs the full pipeline: query -> render -> bookkeeping row. Returns the report id."""
    conn = sqlite3.connect(DB_PATH)
    report_id = conn.execute("INSERT INTO reports (path) VALUES ('')").lastrowid
    conn.commit()

    output_path = f"reports/{report_id}.pdf"
    report_data = get_report_data()
    orders = get_all_orders()
    html = build_html_report(report_data, orders)

    _write_pdf(html, output_path)

    conn.execute("UPDATE reports SET path = ? WHERE id = ?", (output_path, report_id))
    conn.commit()
    conn.close()

    return report_id


if __name__ == "__main__":
    render_pdf()
