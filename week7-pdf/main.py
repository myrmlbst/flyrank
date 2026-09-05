from fastapi import FastAPI

app = FastAPI(title="PDF Print Service", version="1.0")


@app.get("/health", summary="Health check")
def health():
    return {"status": "ok"}
