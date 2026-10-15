# idees-voyages-backend

Async REST API (FastAPI + SQLAlchemy 2.0) behind the *Idées Voyages* app: users share trip ideas pinned on a map, browse the ones around them and rate other people's trips.

## Main concepts

- **Trips**: a title, description, coordinates, dates and addresses, owned by a user. Trips are listed by **bounding box** (`min/max_latitude`, `min/max_longitude`), so a client map can fetch only what is visible. A trip can be **private**: it is then invisible (404) to everyone but its owner.
- **Ratings**: a 1–5 score and a comment, one per user and per trip. You cannot rate your own trip. Each trip response carries its `mean_rating` and `rating_people_number`.
- **Users / auth**: handled by [fastapi-users](https://fastapi-users.github.io/fastapi-users/) with a JWT bearer token (1 hour). Deleting your account (`DELETE /users/me`) removes your trips and anonymizes your user row, so ratings you left on other trips are kept.

Interactive API docs are available at http://localhost:8000/docs once the server is running.

## Project structure

```
├── src/
│   ├── main.py          # FastAPI app: CORS, router registration, auth routes
│   ├── config.py        # Settings read from env vars / .env (pydantic-settings)
│   ├── auth.py          # fastapi-users setup: JWT backend, current_user dependencies
│   ├── database/
│   │   ├── database.py  # Async engine, session factory, get_db dependency
│   │   └── models.py    # SQLAlchemy models: Trip, Rating, User
│   ├── schemas/         # Pydantic request/response models (one file per resource)
│   ├── routers/         # HTTP endpoints: thin layer, access checks, calls services
│   └── services/        # *_crud.py: database queries and business rules
├── alembic/             # Database migrations (versions/ holds the migration files)
├── scripts/
│   └── seed_trips.py    # Fills the database with demo users, trips and ratings
└── tests/
    ├── conftest.py      # Test DB (SQLite test.db), HTTP clients, auth override
    ├── factories.py     # factory-boy factories for Trip, Rating, User
    └── unit_tests/      # Tests per resource (trips, ratings, users, config…)
```

A request flows as **router → service → model**: routers declare the endpoint and its dependencies (DB session, current user), services hold the SQL and the business rules, schemas define what goes in and out.

## Quick Start

The project uses [uv](https://docs.astral.sh/uv/) and requires Python 3.14+.

```bash
uv sync                      # install dependencies
cp .env.example .env         # then set SECRET (and DATABASE_URL if needed)
uv run alembic upgrade head  # create the schema
uv run python -m scripts.seed_trips --count 100   # optional: demo data
uv run uvicorn src.main:app --reload
```

Visit http://localhost:8000/docs. The seed script creates demo accounts (`alice@example.com`, `bob@example.com`, … with password `password123`).

### Configuration

| Variable       | Default                            | Description                                 |
|----------------|------------------------------------|---------------------------------------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./sql_app.db` | Async SQLAlchemy URL (SQLite or PostgreSQL) |
| `SECRET`       | dev-only placeholder               | Signs JWTs and reset/verification tokens    |
| `CORS_ORIGINS` | `*`                                | Comma-separated allowed origins             |

### Database migrations (Alembic)

The schema is managed by Alembic, not by the app itself. Apply migrations before starting the server (against whatever `DATABASE_URL` is configured):

```bash
uv run alembic upgrade head
```

After changing a model in `src/database/models.py`, generate a new migration and review it before committing:

```bash
uv run alembic revision --autogenerate -m "describe the change"
```

## Tests and linting

```bash
uv run pytest       # runs with coverage; uses a separate SQLite test.db
uv run ruff check .
```
