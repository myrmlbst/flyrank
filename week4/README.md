# Task API with Supabase Auth
The A2 CRUD API (FastAPI), backed by Postgres, with a Supabase-backed authentication layer (BE-03: Auth - Login & protect) added on top: sign up, log in, log out, and JWT-protected routes.

## What changed from A2
- **New:** [`repository.py`](repository.py) is a Postgres-backed implementation of the exact same function set the in-memory repository exposed (`list_tasks`, `get_task`, `create_task`, `update_task`, `delete_task`, `stats`, `reset_tasks`). [`db.py`](db.py) owns the connection (`psycopg2`, reading `DATABASE_URL` from the environment) and `init_db()` (creates the `tasks` table if missing, seeds it once).

## Auth (BE-03)
[`auth.py`](auth.py) holds the Supabase client (`create_client(SUPABASE_URL, SUPABASE_KEY)`) and `get_current_user`, a FastAPI dependency that:

1. Reads the `Authorization: Bearer <token>` header via `HTTPBearer(auto_error=False)`.
2. Returns `401 {"error": "Access token required"}` if the header is missing, malformed, or has no token.
3. Calls `supabase.auth.get_user(token)` to verify the token against Supabase; returns `401 {"error": "Invalid or expired token"}` if it's invalid/expired.
4. Otherwise returns the verified Supabase `user` object.

Because it's a plain FastAPI dependency, it's reused across every protected route with `Depends(auth.get_current_user)` (the "middleware" from the assignment). Using `HTTPBearer` as part of the dependency chain is also what makes the padlock icon and "Authorize" button show up automatically in Swagger UI at `/docs`, no extra OpenAPI config needed.

### Setup

1. Create a free project at [supabase.com](https://supabase.com).
2. Project Settings -> API -> copy the **Project URL** and **anon public key**.
3. Put them in `.env` (see `.env.example`):
   ```
   SUPABASE_URL=your_project_url
   SUPABASE_KEY=your_anon_key
   ```
4. `docker compose up --build` (or run locally, see below): startup logs "Server running and connected to Supabase" once `init_db()` finishes and the Supabase client has been created without throwing.

By default a new Supabase project requires email confirmation, so a fresh signup can't log in until the confirmation link is clicked. For local testing, turn that off under Authentication -> Providers -> Email -> "Confirm email".

### Checkpoints

```bash
# Sign up (201)
curl -i -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com", "password":"password123"}'

# Log in (200, returns access_token)
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com", "password":"password123"}'

# Public route, no auth needed (200)
curl -i http://localhost:8000/public/info

# Protected route, no token (401)
curl -i http://localhost:8000/protected/profile

# Protected route, with token (200)
curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer <PASTE_ACCESS_TOKEN_HERE>"

# Logout (204)
curl -i -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer <PASTE_ACCESS_TOKEN_HERE>"
```

In Swagger UI (`/docs`), click the padlock, paste the access token (no `Bearer ` prefix needed there), then "Try it out" on `/protected/profile` or `/protected/dashboard`.

**Note on logout:** the assignment's pseudocode calls `signOut(token)`; the Supabase Python SDK's `sign_out()` only clears whatever session is set on the `Client` instance, and the shared `supabase` client here never has one (`get_current_user` verifies tokens via `get_user(token)`, not `set_session()`). So `POST /auth/logout` verifies the caller via `get_current_user` (proving it's a protected route) and then calls `auth.revoke_token`, which hits GoTrue's `/auth/v1/logout` endpoint directly with the caller's own token — that's what actually revokes that specific session server-side.

### Swagger UI
Authorized (padlock closed) and tested from `/docs`, tokens redacted:

![Swagger UI - GET /protected/profile, authorized, 200 response](imgs/CB6AF386-30DA-4CED-A41B-FDA797BD4910.jpeg)

![Swagger UI - GET /protected/dashboard, authorized, 200 response](imgs/A087AC7B-1708-4575-A907-6B68166C6B7E.jpeg)


## Stack
- `app`: FastAPI, built from [`Dockerfile`](Dockerfile)
- `db`: `postgres:16-alpine`, with a named volume (`pgdata`) so data survives container restarts/recreation
- `redis`: `redis:7-alpine`, with a named volume (`redisdata`); not used for anything yet, added now (stretch goal) so it's ready for W4. [`cache.py`](cache.py) holds the client and a `ping()` used by `/health`.
- Table created via [`sql/init.sql`](sql/init.sql), mounted into Postgres's `docker-entrypoint-initdb.d` (and also created idempotently by `init_db()` on app startup, in case the volume already existed before this file was added)

## Configuration

Connection info lives in `.env` (gitignored, see [`.env.example`](.env.example) for the committed template):
```
POSTGRES_USER=taskuser
POSTGRES_PASSWORD=taskpass
POSTGRES_DB=tasks
DATABASE_URL=postgresql://taskuser:taskpass@db:5432/tasks
REDIS_URL=redis://redis:6379/0
```

`db` and `redis` in these URLs are Compose service names, resolved over Docker's internal network, not `localhost`.

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

| Method | Path | Auth required | Description | Success | Errors |
|---|---|---|---|---|---|
| GET | `/` | No | API info | 200 | — |
| GET | `/health` | No | Health check; also pings Redis (`{"status":"ok","redis":"ok"}`) | 200 | — |
| POST | `/auth/signup` | No | Create a Supabase user (`{"email","password"}`) | 201 | 400 missing fields, 400 Supabase error |
| POST | `/auth/login` | No | Log in, returns `access_token` + `refresh_token` | 200 | 400 missing fields, 401 invalid credentials |
| POST | `/auth/logout` | Yes | End the session | 204 | 401 missing/invalid token |
| GET | `/public/info` | No | Unauthenticated info | 200 | — |
| GET | `/protected/profile` | Yes | Verified caller's Supabase user (id, email, created_at) | 200 | 401 missing/invalid/expired token |
| GET | `/protected/dashboard` | Yes | Second protected route, same dependency | 200 | 401 missing/invalid/expired token |
| GET | `/tasks` | No | List all tasks (optional `?done=` and `?search=` filters) | 200 | — |
| GET | `/tasks/{id}` | No | Get one task | 200 | 404 if not found |
| POST | `/tasks` | No | Create a task (`{"title": "..."}`) | 201 | 400 if title missing/empty |
| PUT | `/tasks/{id}` | No | Update a task's title and/or done | 200 | 400 invalid body, 404 unknown id |
| DELETE | `/tasks/{id}` | No | Delete a task | 204 | 404 if not found |
| GET | `/stats` | No | Task counts (`total`, `done`, `open`) | 200 | — |
| POST | `/reset` | No | Reset tasks to the 3 seed tasks | 200 | — |

## Persistence (how it was checked)
1. `docker compose up --build`: API came up seeded with the 3 default tasks (`GET /tasks`).
2. Created a 4th row: `curl -X POST http://localhost:8000/tasks -d '{"title":"Persistence proof row"}'` → `{"id":4,"title":"Persistence proof row","done":false}`.
3. `docker compose down`: this stops **and removes** both containers and the network (a harder test than a plain restart).
4. `docker compose up -d`: fresh containers, same named volume (`pgdata`) reattached.
5. `GET /tasks`: all 4 rows still present, including id 4.

The data survives because `pgdata` is a Docker-managed volume outside the container's writable layer; removing/recreating the `db` container doesn't touch it. Only `docker compose down -v` would delete it.

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
