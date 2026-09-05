import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from render_report import DB_PATH, generate_report

app = FastAPI(title="PDF Print Service", version="1.0")


@app.get("/health", summary="Health check")
def health():
    return {"status": "ok"}


@app.post("/reports", status_code=201, summary="Generate a report")
def create_report():
    report_id = generate_report()
    return {"id": report_id, "file": f"/reports/{report_id}/file"}


def _get_report_row(report_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return dict(row)


@app.get("/reports/{report_id}", summary="Get a report's bookkeeping row")
def get_report(report_id: int):
    row = _get_report_row(report_id)
    return {**row, "file": f"/reports/{report_id}/file"}


@app.get("/reports/{report_id}/file", summary="Download a report's PDF")
def get_report_file(report_id: int):
    row = _get_report_row(report_id)
    return FileResponse(row["path"], media_type="application/pdf", filename=f"report-{report_id}.pdf")
