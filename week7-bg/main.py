from fastapi import FastAPI

app = FastAPI(title="Job System API", version="1.0")


@app.get("/health", summary="Health check")
def health():
    return {"status": "ok"}
