import os

from playwright.sync_api import sync_playwright

from build_html import build_html_report
from report import get_all_orders, get_report_data

OUTPUT_PATH = "reports/test.pdf"


def render_pdf(output_path: str = OUTPUT_PATH, fix_page_breaks: bool = True) -> None:
    report_data = get_report_data()
    orders = get_all_orders()
    html = build_html_report(report_data, orders, fix_page_breaks=fix_page_breaks)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.pdf(path=output_path, format="A4", print_background=True)
        browser.close()

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    render_pdf()
