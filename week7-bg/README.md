# Week 7 (bg): Job System

A background job system, built up in stages starting from a plain API.

## Stack
FastAPI (Python), `uvicorn`.

## Stage 0: Hello, server
A minimal server with one endpoint, `GET /health` -> `{"status": "ok"}`, the
same starting point as A1.

- [`main.py`](main.py) — the FastAPI app and the `/health` route.
- [`requirements.txt`](requirements.txt) — `fastapi`, `uvicorn[standard]`.

### Run it
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8000
```

### Checkpoint
```bash
curl -i http://localhost:8000/health
```
```
HTTP/1.1 200 OK
content-type: application/json

{"status":"ok"}
```
Confirmed working locally on 2026-08-26.
