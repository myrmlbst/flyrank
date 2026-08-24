from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

import ai
import auth
import cache
import repository
from db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Server running and connected to Supabase")
    yield


app = FastAPI(title="Task API", version="1.0", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    field = first["loc"][-1]
    return JSONResponse(status_code=400, content={"error": f"Invalid value for '{field}': {first['msg']}"})


class Task(BaseModel):
    id: int
    title: str
    done: bool = False


class TaskCreate(BaseModel):
    title: str
    done: Optional[bool] = False


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


@app.get("/", summary="API info")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks", "/auth", "/public", "/protected"]}


@app.get("/health", summary="Health check")
def health():
    try:
        redis_ok = cache.ping()
    except Exception:
        redis_ok = False
    return {"status": "ok", "redis": "ok" if redis_ok else "unreachable"}


@app.post("/auth/signup", status_code=201, summary="Sign up a new user")
def signup(payload: auth.Credentials):
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        response = auth.supabase.auth.sign_up({"email": payload.email, "password": payload.password})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"user": response.user}


@app.post("/auth/login", summary="Log in and receive a JWT")
def login(payload: auth.Credentials):
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        response = auth.supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")

    if response.session is None:
        raise HTTPException(status_code=401, detail="Invalid login credentials")

    return {
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
        "user": response.user,
    }


@app.post("/auth/logout", status_code=204, summary="Log out the current session")
def logout(current_user=Depends(auth.get_current_user)):
    auth.supabase.auth.sign_out()


@app.get("/public/info", summary="Public, unauthenticated info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile", summary="Get the authenticated user's profile")
def get_profile(current_user=Depends(auth.get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at,
    }


@app.get("/protected/dashboard", summary="Second protected route (proves the dependency is reusable)")
def get_dashboard(current_user=Depends(auth.get_current_user)):
    return {"message": f"Welcome back, {current_user.email}!"}


@app.get("/tasks", summary="List all tasks")
def list_tasks(done: Optional[bool] = None, search: Optional[str] = None):
    return repository.list_tasks(done=done, search=search)


@app.get("/tasks/{task_id}", summary="Get a single task")
def get_task(task_id: int):
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks", status_code=201, summary="Create a task")
def create_task(payload: TaskCreate):
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title is required and cannot be empty")

    title = payload.title.strip()
    done = bool(payload.done)

    return repository.create_task(title, done)


@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, payload: TaskUpdate):
    if payload.title is None and payload.done is None:
        raise HTTPException(status_code=400, detail="Request body must include 'title' and/or 'done'")
    if payload.title is not None and not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    title = payload.title.strip() if payload.title is not None else None
    task = repository.update_task(task_id, title, payload.done)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    deleted = repository.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.get("/stats", summary="Task stats")
def stats():
    result = repository.stats()
    total, done = result["total"], result["done"]
    return {"total": total, "done": done, "open": total - done}


@app.post("/reset", summary="Reset tasks to seed data")
def reset():
    tasks = repository.reset_tasks()
    return {"status": "reset", "tasks": tasks}


@app.post("/tasks/{task_id}/priority", summary="Ask Claude to judge a task's priority")
def judge_task_priority(task_id: int):
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        judgement = ai.classify_priority(task["title"])
    except ai.AIDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ai.AITimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except ai.AIValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ai.AIJudgementError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "task_id": task["id"],
        "title": task["title"],
        "priority": judgement.priority,
        "reasoning": judgement.reasoning,
    }
