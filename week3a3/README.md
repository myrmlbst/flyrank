# Task API Containerized
The A2 CRUD API (FastAPI), now backed by Postgres instead of an in-memory/SQLite store, with the whole stack (app + database) started by one command: `docker compose up`.

## What changed from A2
- **New:** [`repository.py`](repository.py) is a Postgres-backed implementation of the exact same function set the in-memory repository exposed (`list_tasks`, `get_task`, `create_task`, `update_task`, `delete_task`, `stats`, `reset_tasks`). [`db.py`](db.py) owns the connection (`psycopg2`, reading `DATABASE_URL` from the environment) and `init_db()` (creates the `tasks` table if missing, seeds it once).


## Stack

- `app`: FastAPI, built from [`Dockerfile`](Dockerfile)
- `db`: `postgres:16-alpine`, with a named volume (`pgdata`) so data survives container restarts/recreation
- `redis`: `redis:7-alpine`, with a named volume (`redisdata`); not used for anything yet, added now (stretch goal) so it's ready for W4. [`cache.py`](cache.py) holds the client and a `ping()` used by `/health`.
- Table created via [`sql/init.sql`](sql/init.sql), mounted into Postgres's `docker-entrypoint-initdb.d` (and also created idempotently by `init_db()` on app startup, in case the volume already existed before this file was added)

## Configuration
Connection info lives in `.env` (gitignored). See [`.env.example`](.env.example) for the committed template:

```
POSTGRES_USER=taskuser
POSTGRES_PASSWORD=taskpass
POSTGRES_DB=tasks
DATABASE_URL=postgresql://taskuser:taskpass@db:5432/tasks
REDIS_URL=redis://redis:6379/0
```

`db` and `redis` in these URLs are Compose service names, resolved over Docker's internal network — not `localhost`.

Before first run: `cp .env.example .env`.

## Run the whole stack
```bash
docker compose up --build
```

This builds the app image, starts Postgres, waits for it to report healthy (`pg_isready`), then starts the app. API is at http://localhost:8000, docs at http://localhost:8000/docs.

```bash
docker compose down        # stop, keep the volume (data kept)
docker compose down -v     # stop and delete the volume (data wiped)
```

## Endpoints

| Method | Path | Description | Success | Errors |
|---|---|---|---|---|
| GET | `/` | API info | 200 | — |
| GET | `/health` | Health check; also pings Redis (`{"status":"ok","redis":"ok"}`) | 200 | — |
| GET | `/tasks` | List all tasks (optional `?done=` and `?search=` filters) | 200 | — |
| GET | `/tasks/{id}` | Get one task | 200 | 404 if not found |
| POST | `/tasks` | Create a task (`{"title": "..."}`) | 201 | 400 if title missing/empty |
| PUT | `/tasks/{id}` | Update a task's title and/or done | 200 | 400 invalid body, 404 unknown id |
| DELETE | `/tasks/{id}` | Delete a task | 204 | 404 if not found |
| GET | `/stats` | Task counts (`total`, `done`, `open`) | 200 | — |
| POST | `/reset` | Reset tasks to the 3 seed tasks | 200 | — |

## Persistence (how it was checked)
1. `docker compose up --build`: API came up seeded with the 3 default tasks (`GET /tasks`).
2. Created a 4th row: `curl -X POST http://localhost:8000/tasks -d '{"title":"Persistence proof row"}'` → `{"id":4,"title":"Persistence proof row","done":false}`.
3. `docker compose down`: stops **and removes** both containers and the network (a harder test than a plain restart).
4. `docker compose up -d`: fresh containers, same named volume (`pgdata`) reattached.
5. `GET /tasks` → all 4 rows still present, including id 4.

The data survives because `pgdata` is a Docker-managed volume outside the container's writable layer; removing/recreating the `db` container doesn't touch it. Only `docker compose down -v` would delete it.

## Stretch: Redis
Added a `redis` service to `docker-compose.yml` (not used for caching yet... just wired up ahead of W4). `GET /health` pings it via [`cache.py`](cache.py):

```bash
curl http://localhost:8000/health
# {"status":"ok","redis":"ok"}
```

`app` waits on `redis`'s healthcheck (`redis-cli ping`) the same way it waits on Postgres's, via `depends_on: condition: service_healthy`.

## Local (non-Docker) dev
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Point `DATABASE_URL` and `REDIS_URL` in `.env` at reachable instances (e.g. `postgresql://taskuser:taskpass@localhost:5432/tasks` and `redis://localhost:6379/0` if you expose the `db`/`redis` services' ports), then:

```bash
uvicorn main:app --reload --port 8000
```
