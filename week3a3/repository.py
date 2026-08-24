"""Postgres-backed task repository.

Every function opens its own connection and closes it when done, mirroring
the request-scoped connection lifecycle the SQLite version used. Swapping
storage again later means writing a new module with this same set of
functions and pointing main.py at it -- nothing here leaks into the routes.
"""

from typing import Optional

from db import SEED_TASKS, get_connection


def list_tasks(done: Optional[bool] = None, search: Optional[str] = None):
    query = "SELECT id, title, done FROM tasks WHERE 1=1"
    params = []
    if done is not None:
        query += " AND done = %s"
        params.append(done)
    if search:
        query += " AND LOWER(title) LIKE %s"
        params.append(f"%{search.lower()}%")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_task(task_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def create_task(title: str, done: bool):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
                (title, done),
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    return dict(row)


def update_task(task_id: int, title: Optional[str], done: Optional[bool]):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
            if row is None:
                return None

            new_title = title if title is not None else row["title"]
            new_done = done if done is not None else row["done"]

            cur.execute(
                "UPDATE tasks SET title = %s, done = %s WHERE id = %s",
                (new_title, new_done, task_id),
            )
        conn.commit()
    finally:
        conn.close()
    return {"id": task_id, "title": new_title, "done": new_done}


def delete_task(task_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            deleted = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    return deleted > 0


def stats():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS total, COALESCE(SUM(done::int), 0) AS done FROM tasks"
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return {"total": row["total"], "done": row["done"]}


def reset_tasks():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks")
            cur.executemany(
                "INSERT INTO tasks (title, done) VALUES (%s, %s)", SEED_TASKS
            )
            cur.execute("SELECT id, title, done FROM tasks ORDER BY id")
            rows = cur.fetchall()
        conn.commit()
    finally:
        conn.close()
    return [dict(r) for r in rows]
