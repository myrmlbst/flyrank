# PDF Report Generator

## What This Is
A FastAPI app that turns rows in a SQLite database into a downloadable PDF report: query the data, render it to HTML, print that HTML to a PDF with headless Chromium (Playwright), and hand back a link. Built in stages: a health check, a seeded `orders` table, aggregate SQL queries, an HTML/PDF renderer, and endpoints to generate, look up, and download a report.

## Running Locally
```bash
source venv/bin/activate
uvicorn main:app --port 8000
```

## Data
```bash
python init_db.py   # creates report.db (orders, reports tables)
python seed.py       # inserts 200 random orders (safe to re-run)
```

## Endpoints
| Method | Path                  | Body | Success | Errors |
|--------|-----------------------|------|---------|--------|
| GET    | `/health`             | —    | `200` `{"status":"ok"}` | — |
| POST   | `/reports`            | —    | `201` `{"id","file"}` after a synchronous render | — |
| GET    | `/reports/{id}`       | —    | `200` the bookkeeping row + file link | `404` unknown id |
| GET    | `/reports/{id}/file`  | —    | `200` the PDF file | `404` unknown id |

## Proof: Generate and Download
```
$ time curl -i -X POST http://localhost:8000/reports
HTTP/1.1 201 Created
content-type: application/json

{"id":5,"file":"/reports/5/file"}
curl -i -X POST http://localhost:8000/reports  0.01s user 0.01s system 1% cpu 1.014 total

$ curl -o my-report.pdf http://localhost:8000/reports/5/file
$ file my-report.pdf
my-report.pdf: PDF document, version 1.4, 6 pages
```

## Report Contents
`getReportData()` aggregates the `orders` table into: total order count,
total revenue, top 5 products by revenue, and orders per day for the last 7 days. That data plus a full order dump gets rendered into an HTML template and printed to PDF. The long orders table uses `tr { break-inside: avoid; }` and a real `<thead>` so rows don't get sliced across a page break and the header repeats on every page.

## On Background Jobs
I'd move report generation out of the request and into a background job (accept-now/work-later, as in `week7-bg`) once a single render regularly exceeds ~1-2s or the endpoint needs to serve more than one concurrent user, since a multi-second synchronous request ties up a worker thread and leaves every caller behind it waiting.
