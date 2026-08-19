# Applied “Memory of All Documentation”

The project was reviewed against the user's established production-documentation preferences after the code was written.

## Applied architecture preferences

- FastAPI backend with typed Pydantic request/response models
- React and TypeScript frontend
- Redux Toolkit state management
- PostgreSQL as durable source of truth
- pgvector for real long-term research memory
- Redis and Celery for expensive asynchronous work
- LangGraph for explicit, stateful, bounded orchestration
- Separate API and worker containers
- Thin API routes and service/agent modules
- Alembic database migrations
- Docker Compose local stack
- GitHub Actions backend, frontend, and image checks

## Applied production behavior

- Research request returns after queueing
- Worker performs Gemini, web, paper, code, and reflection work
- Redis is transport, not permanent business storage
- Jobs, sources, events, reports, and memory are persisted
- LangGraph checkpoints are stored in PostgreSQL
- Retry-safe derived-source/report persistence
- Checkpoint-aware worker-crash resumption
- Worker timeout, late acknowledgement, and prefetch controls
- Health and readiness endpoints
- Bounded loops rather than open-ended autonomous execution

## Applied memory/RAG requirements

- Completed reports are chunked
- Chunks are embedded with Gemini Embedding 2
- 768-dimensional embeddings are stored in pgvector
- HNSW cosine search retrieves prior team knowledge
- Retrieval is tenant-filtered
- Memory is explicitly treated as untrusted context, not fact

## Applied security preferences

- Argon2 password hashing
- JWT-protected dashboard APIs
- Tenant-scoped object authorization
- Registration disabled by default
- Strong production secret validation
- Strict production CORS validation
- Environment-based secrets
- One-time WebSocket tickets
- Prompt-injection boundaries
- No chain-of-thought storage or exposure
- Server-controlled final source registry
- Gemini grounding-annotation source allowlist
- Invalid citation-key rejection
- No local execution of model-generated code
- PDF size/page controls
- Per-user active-job limit

## Applied testing and documentation preferences

- pytest tests
- Ruff lint configuration
- Frontend ESLint/build scripts
- GitHub Actions CI
- PRD
- Architecture document
- Setup guide
- Security guide
- Testing and evaluation guide
- Operations guide
- API guide
- Validation report
- Evaluation harness for measured single-agent comparison

## Important implementation clarification

The original product description says users can see each agent's “thinking.” The production-safe implementation shows observable activity, tool use, summaries, evidence, reflection scores, and decisions. It intentionally does not expose private hidden reasoning.

The original description also says the system is “significantly more accurate.” The code implements mechanisms intended to improve accuracy, but the repository does not claim statistical improvement without running the included benchmark process.
