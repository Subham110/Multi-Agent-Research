# Complete Setup Guide

This guide covers Windows 11, macOS, and Linux. Docker Compose is the recommended setup because it starts PostgreSQL, pgvector, Redis, the API, the worker, and the React dashboard together.

## 1. Prerequisites

Install:

- Git
- Docker Desktop with Docker Compose
- Python 3.12+ for the environment helper
- A Gemini API key

Confirm:

```bash
docker --version
docker compose version
python --version
```

## 2. Extract and open the project

### Windows PowerShell

```powershell
Expand-Archive .\multi-agent-research-system.zip
cd .\multi-agent-research-system
code .
```

### macOS or Linux

```bash
unzip multi-agent-research-system.zip
cd multi-agent-research-system
code .
```

## 3. Create a Gemini API key

1. Open Google AI Studio.
2. Create or select a Google Cloud project.
3. Create a Gemini API key.
4. Keep the key private. Do not commit it to Git.

The application defaults to:

```env
GEMINI_MODEL=gemini-3.6-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_DIMENSION=768
```

`gemini-3.6-flash` supports search grounding, URL context, code execution, structured outputs, and agentic workflows. Model names remain configurable because availability and pricing can change. The checked-in vector migration uses 768 dimensions; changing `EMBEDDING_DIMENSION` requires a new database migration.

## 4. Generate `.env`

```bash
python scripts/init_env.py
```

The script copies `.env.example` and creates a strong random `SECRET_KEY`.

Edit `.env`:

```env
GEMINI_API_KEY=replace-with-your-key
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=replace-with-a-long-unique-password
BOOTSTRAP_TENANT_SLUG=default
BOOTSTRAP_TENANT_NAME=Default Research Team
```

Keep registration disabled for a private workspace:

```env
ALLOW_REGISTRATION=false
```

## 5. Start Docker Desktop

On Windows, open Docker Desktop and wait until it reports that the engine is running.

## 6. Build and start

```bash
docker compose up --build -d
```

Check status:

```bash
docker compose ps
```

Expected services:

```text
postgres
redis
api
worker
frontend
```

The one-time `migrate` container should show `Exited (0)`.

## 7. Create or update the administrator

```bash
docker compose run --rm api python scripts/bootstrap_admin.py
```

This command is idempotent. Running it again updates the configured administrator password and role.

## 8. Open the dashboard

Open:

```text
http://localhost:8080
```

Log in with:

```text
Email: value of BOOTSTRAP_ADMIN_EMAIL
Password: value of BOOTSTRAP_ADMIN_PASSWORD
Team slug: value of BOOTSTRAP_TENANT_SLUG
```

API documentation:

```text
http://localhost:8000/docs
```

## 9. Launch the first research job

Enter a topic and objective, choose Quick, Standard, or Deep, and optionally add focus URLs.

The job is accepted with HTTP `202`, placed on Celery, and processed outside the API process. The dashboard reconnects to live events automatically.

## 10. Watch logs

```bash
docker compose logs -f api worker
```

Database and Redis logs:

```bash
docker compose logs -f postgres redis
```

## 11. Run validation

```bash
python scripts/validate_project.py
```

Docker-based backend checks:

```bash
docker compose run --rm api ruff check app tests
docker compose run --rm api pytest --cov=app --cov-report=term-missing
```

Frontend checks:

```bash
cd frontend
npm install
npm run lint
npm run build
```

## 12. Run without Docker for development

Start PostgreSQL with pgvector and Redis yourself, then set localhost URLs:

```env
DATABASE_URL=postgresql+psycopg://research:research@localhost:5432/research
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:5173
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/api/v1/ws
```

### Backend

```bash
cd backend
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
python scripts/bootstrap_admin.py
uvicorn app.main:app --reload
```

Second terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A app.worker.celery_app worker --loglevel=INFO --pool=solo
```

Use `--pool=solo` for a simple Windows development worker. Linux production workers can use the default prefork pool.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## 13. Production configuration

Set:

```env
ENVIRONMENT=production
ALLOW_REGISTRATION=false
SECRET_KEY=<at-least-32-random-characters>
CORS_ORIGINS=https://research.example.com
DATABASE_URL=<managed-postgresql-with-pgvector>
REDIS_URL=<managed-redis-with-tls-when-supported>
GEMINI_API_KEY=<secret-manager-reference-at-deploy-time>
```

Also:

- Terminate TLS at the ingress or load balancer.
- Use `https://` and `wss://` frontend URLs.
- Run migrations as a release job before application rollout.
- Use separate API and worker autoscaling policies.
- Restrict database and Redis network access.
- Back up PostgreSQL and test restoration.
- Add central logs, metrics, traces, and alerts.
- Review Gemini quotas and per-tool search billing.

## 14. Common problems

### `GEMINI_API_KEY is not configured`

Edit `.env`, then restart:

```bash
docker compose up -d --force-recreate api worker
```

### Login fails

Run:

```bash
docker compose run --rm api python scripts/bootstrap_admin.py
```

Confirm the email, password, and tenant slug exactly match `.env`.

### Job stays queued

```bash
docker compose ps worker redis
docker compose logs worker redis
```

### Database migration fails

```bash
docker compose logs migrate postgres
docker compose run --rm api alembic current
docker compose run --rm api alembic upgrade head
```

### WebSocket says reconnecting

Confirm:

- API is reachable at port 8000.
- `VITE_WS_URL` uses `ws://` locally and `wss://` in production.
- Redis is healthy.
- Reverse proxy supports WebSocket upgrades.

### Too many active jobs

The default limit is three queued/running jobs per user:

```env
MAX_ACTIVE_JOBS_PER_USER=3
```

Wait for a job to finish or cancel an active job before launching another.
