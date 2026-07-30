# API Guide

Base URL:

```text
http://localhost:8000/api/v1
```

## Authentication

### Login

```http
POST /auth/login
Content-Type: application/json
```

```json
{
  "email": "admin@example.com",
  "password": "your-password",
  "tenant_slug": "default"
}
```

Use the returned JWT:

```http
Authorization: Bearer <access_token>
```

### Current user

```http
GET /auth/me
```

### One-time WebSocket ticket

```http
POST /auth/ws-ticket
Authorization: Bearer <access_token>
```

Response:

```json
{"ticket":"...","expires_in":60}
```

The ticket is single-use.

## Research

### Create

```http
POST /research
```

```json
{
  "topic": "How will small language models change enterprise AI costs?",
  "objective": "Compare cost, privacy, accuracy, and deployment tradeoffs.",
  "depth": "standard",
  "max_reflections": 2,
  "max_revisions": 2,
  "focus_urls": []
}
```

Returns `202 Accepted` and a queued job.

### List

```http
GET /research?limit=30&offset=0
```

### Workspace statistics

```http
GET /research/stats
```

### Get job

```http
GET /research/{job_id}
```

### Get persisted events

```http
GET /research/{job_id}/events
```

### Cancel

```http
POST /research/{job_id}/cancel
```

Queued tasks are revoked. Running tasks stop at the next agent-node boundary.

## WebSocket

```text
ws://localhost:8000/api/v1/ws/research/{job_id}?ticket={one_time_ticket}
```

Event example:

```json
{
  "id": "uuid",
  "sequence": 12,
  "event_type": "reflection",
  "agent": "Analyst",
  "message": "Analyst self-review score: 87",
  "payload": {
    "quality_score": 87,
    "sufficient": true
  },
  "created_at": "2026-07-30T15:00:00Z"
}
```

Event types include:

- `job_started`
- `memory_retrieved`
- `papers_loaded`
- `paper_search_warning`
- `agent_started`
- `tool_activity`
- `agent_completed`
- `reflection`
- `revision_requested`
- `job_completed`
- `job_failed`
- `cancellation_requested`
- `job_cancelled`
- `heartbeat`

## Health

```http
GET /health
GET /ready
```
