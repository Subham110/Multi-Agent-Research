# Operations Guide

## Service ownership

- `frontend`: static dashboard
- `api`: authentication, research APIs, event replay, WebSockets
- `worker`: LangGraph and Gemini execution
- `postgres`: durable source of truth, vectors, checkpoints
- `redis`: Celery broker/backend, sequence keys, tickets, pub/sub
- `migrate`: one-time Alembic release step

## Health checks

```text
GET /health
```

Process health only.

```text
GET /ready
```

Checks PostgreSQL and Redis.

## Logs

```bash
docker compose logs -f api worker
```

The backend configures JSON structured logs. Add request IDs and trace IDs at the ingress/APM layer.

## Recommended metrics

### API

- Request count/latency/error rate
- Authentication failures
- Research create rate and HTTP 429 count
- Active WebSockets
- Ticket creation/consumption failures

### Worker

- Queue depth and oldest-task age
- Running tasks
- Job duration by depth
- Failure/retry/cancellation count
- Node duration by agent
- Reflection and revision counts
- Gemini/tool latency and error rate

### Product/quality

- Completed reports
- Average quality score
- Invalid citation rejection count
- Source count/diversity
- Critic pass/revise rate
- User ratings

### Cost

- Tokens by agent
- Search calls by job
- Code-execution usage
- Embedding calls/chunks
- Estimated cost per report and tenant

## Alert examples

- Readiness failure for 5 minutes
- Queue oldest age above 10 minutes
- Worker failure rate above 5%
- Gemini 429/5xx surge
- Job p95 above expected depth-specific SLO
- PostgreSQL disk/connection pressure
- Redis memory pressure or eviction
- Backup failure

## Backup

Back up PostgreSQL because it contains:

- Users and tenants
- Jobs and events
- Reports and sources
- Vector memory
- LangGraph checkpoints

Redis is reconstructible transport state, but an outage can interrupt active streams/tasks. Configure persistence according to the chosen reliability target.

## Deployment sequence

1. Build immutable backend/frontend images.
2. Scan dependencies and images.
3. Run backend tests and frontend build.
4. Back up the database before risky migrations.
5. Run `alembic upgrade head` as a release job.
6. Deploy API.
7. Deploy workers.
8. Deploy frontend.
9. Run readiness and smoke tests.
10. Observe error, queue, and cost dashboards.

## Scaling notes

- Scale API on requests and WebSockets.
- Scale workers on queue depth and oldest task age.
- Keep worker prefetch at one for expensive jobs.
- Use separate queues for quick/deep research when volume increases.
- Apply tenant quotas before external launch.
- Partition or archive old events when volume requires it.
- Tune HNSW and memory retrieval after measuring recall and latency.
