# Validation Report

Validation date: **2026-07-30**

## Result

The repository passed the static and dependency-independent checks available in the build workspace.

### Passed

- Python compilation for backend, Alembic, tests, and helper scripts
- Python AST parsing for all source files
- Prompt-boundary unit test
- TypeScript and TSX compiler syntax transpilation across 17 files
- `package.json` parsing
- `pyproject.toml` parsing
- Docker Compose YAML parsing
- GitHub Actions YAML parsing
- Environment-file initializer and random secret generation
- Offline evaluation CLI sample
- Heuristic unused-import scan
- No application-host execution primitives in agent and service runtime code
- No committed `.env`, Gemini API key pattern, or private-key pattern
- Gemini model configuration consistency
- README documentation-link existence

## Important runtime limitation

This workspace could not complete external dependency installation because its Python and npm package network/mirror access was unavailable or incomplete. Therefore, the following were **not claimed as executed here**:

- Full `pip install -e ".[dev]"`
- Full backend pytest suite with PostgreSQL, Redis, LangGraph, Gemini SDK, and pgvector imports
- Ruff lint execution
- Full `npm install`
- ESLint execution
- TypeScript semantic type-check through installed React dependencies
- Vite production bundle
- Docker image builds
- Live Gemini, arXiv, PostgreSQL, Redis, Celery, and WebSocket integration test

The repository includes CI and Docker commands for all of these checks. Run them in an environment with normal package and container access before deployment.

## Final local verification

```bash
docker compose up --build -d
docker compose ps
docker compose run --rm api ruff check app tests
docker compose run --rm api pytest --cov=app --cov-report=term-missing
docker compose --profile tools run --rm frontend-build
curl http://localhost:8000/ready
```

Then create a test research job and confirm:

1. The API responds with HTTP `202`.
2. The Celery worker changes the job to `running`.
3. Public agent events replay after reconnecting the browser.
4. Search citations registered in the report came from grounding annotations, focus URLs, or verified arXiv records.
5. The report body contains valid inline `[S#]` citations.
6. The final `job_completed` event occurs only after the report and sources are committed.
7. Cancelling a running job does not later overwrite it as completed.
8. A completed report is stored in pgvector memory and can inform a later job in the same tenant.

## Deployment gate

Do not promote the project to an internet-facing environment until the full CI workflow passes, secrets are moved to a secret manager, HTTPS/WSS is configured, ingress rate limits are enabled, and database backup restoration has been tested.
