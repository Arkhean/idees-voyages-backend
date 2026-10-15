# idees-voyages-backend

A project created with FastAPI CLI.

## Quick Start

### Start the development server

```bash
uvicorn src.main:app --reload
```

Visit http://localhost:8000

### Database migrations (Alembic)

The schema is managed by Alembic, not by the app itself. Apply migrations before starting the server (against whatever `DATABASE_URL` is configured):

```bash
uv run alembic upgrade head
```

After changing a model in `src/database/models.py`, generate a new migration and review it before committing:

```bash
uv run alembic revision --autogenerate -m "describe the change"
```
