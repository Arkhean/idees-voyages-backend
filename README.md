# idees-voyages-backend

A project created with FastAPI CLI.

## Quick Start

### Start the development server

```bash
uv run fastapi dev
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

### Deploy to FastAPI Cloud

Sign up and log in at https://fastapicloud.com, then deploy with:

```bash
uv run fastapi deploy
```

## Project Structure

- `main.py` - Your FastAPI application
- `pyproject.toml` - Project dependencies

## Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [FastAPI Cloud](https://fastapicloud.com)
