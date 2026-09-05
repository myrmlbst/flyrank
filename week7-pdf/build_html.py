import datetime
import html


def build_html_report(report_data: dict, orders: list[dict], fix_page_breaks: bool = True) -> str:
    today = datetime.date.today().isoformat()

    top_products_rows = "\n".join(
        f"<tr><td>{html.escape(p['product'])}</td><td>${p['revenue']:.2f}</td></tr>"
        for p in report_data["top_products"]
    )

    orders_rows = "\n".join(
        f"<tr><td>{o['id']}</td><td>{html.escape(o['customer'])}</td>"
        f"<td>{html.escape(o['product'])}</td><td>${o['amount']:.2f}</td>"
        f"<td>{o['created_at']}</td></tr>"
        for o in orders
    )

    if fix_page_breaks:
        # tr break-inside avoids splitting a row across a page break; a real
        # <thead> makes the browser repeat the header row on every page.
        print_css = "tr { break-inside: avoid; }"
        orders_header = f"<thead><tr><th>ID</th><th>Customer</th><th>Product</th><th>Amount</th><th>Date</th></tr></thead>\n<tbody>\n{orders_rows}\n</tbody>"
    else:
        print_css = ""
        orders_header = f"<tbody>\n<tr><th>ID</th><th>Customer</th><th>Product</th><th>Amount</th><th>Date</th></tr>\n{orders_rows}\n</tbody>"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Sales Report</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; color: #222; }}
  h1 {{ margin-bottom: 0; }}
  .subtitle {{ color: #666; margin-top: 4px; }}
  .totals {{ display: flex; gap: 40px; margin: 24px 0; }}
  .totals div {{ font-size: 14px; color: #666; }}
  .totals strong {{ display: block; font-size: 24px; color: #111; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 32px; }}
  th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #ddd; font-size: 13px; }}
  th {{ background: #f5f5f5; }}
  {print_css}
</style>
</head>
<body>
  <h1>Sales Report</h1>
  <p class="subtitle">Generated {today}</p>

  <div class="totals">
    <div>Total Orders<strong>{report_data['total_orders']}</strong></div>
    <div>Total Revenue<strong>${report_data['total_revenue']:.2f}</strong></div>
  </div>

  <h2>Top 5 Products by Revenue</h2>
  <table>
    <thead><tr><th>Product</th><th>Revenue</th></tr></thead>
    <tbody>
      {top_products_rows}
    </tbody>
  </table>

  <h2>All Orders ({len(orders)})</h2>
  <table>
    {orders_header}
  </table>
</body>
</html>"""
