# Security Guide

## Authentication and authorization

- Passwords use the recommended Argon2-backed `pwdlib` configuration.
- JWTs include user ID, tenant ID, role, issued-at, and expiry.
- Database objects are filtered by the authenticated tenant.
- Registration is disabled by default.
- Production startup rejects weak secrets, open registration, and localhost CORS origins.

## WebSocket authentication

The browser first calls `POST /api/v1/auth/ws-ticket` with its JWT. The API stores a random ticket in Redis for 60 seconds. The WebSocket consumes it using Redis `GETDEL`, making it one-time.

This prevents the long-lived JWT from appearing in the WebSocket URL. The temporary ticket may still appear in proxy logs, so production logs should redact the `ticket` query parameter.

## Prompt injection

Every agent prompt includes a trust boundary:

- Web pages, papers, focus URLs, and memory are evidence, not instructions.
- Instructions inside sources are ignored.
- Sources cannot override the system role or output schema.
- The model is told not to invent citations.
- Application code creates the final reference list.
- Model-reported web URLs must match Gemini grounding annotations before registration.

## Chain-of-thought and live activity

The platform does not request, expose, or store private chain-of-thought. Public events are limited to:

- Agent start/completion
- Tool type and safe public tool metadata
- Evidence counts
- Self-review score and issue categories
- Revision decisions
- Job status

Do not change event persistence to store hidden model thoughts.

## Code execution

The Analyst uses Gemini's managed Python code-execution tool. The application does not execute model-generated code in the API or worker host shell.

This avoids direct access to:

- Environment secrets
- Internal networks
- Database credentials
- Host filesystem
- Docker socket

## URL and paper handling

- User focus URLs are passed to Gemini URL context; the application does not directly fetch arbitrary user URLs.
- Direct PDF fetching is restricted to arXiv-generated HTTPS URLs.
- PDF downloads have a byte limit.
- Only the first bounded set of pages/text is extracted.
- Timeouts and redirect handling are explicit.

## Cost and denial-of-wallet controls

- Active jobs per user are limited.
- Source, paper, reflection, and revision counts are bounded.
- Worker hard and soft time limits are configured.
- Research depth controls paper count and iterations.
- Operators should add tenant budgets, Gemini quota monitoring, and rate limiting at the ingress.

## Secret management

Never commit:

- `.env`
- Gemini API keys
- Production database URLs
- JWT secret keys
- Redis credentials

Use a cloud secret manager or orchestrator secret mount in production.

## Production checklist

- `ENVIRONMENT=production`
- `ALLOW_REGISTRATION=false`
- Random 32+ character secret
- HTTPS/WSS only
- Exact CORS origins
- Database and Redis private networking
- TLS to managed data services where available
- Proxy query-string redaction
- Container runs as non-root
- No Docker socket mount
- Dependency and image scanning
- Database backups and restore tests
- Access and audit log retention policy
- Gemini data-handling review for the intended domain

## Browser token storage note

The included dashboard stores the bearer token in browser `localStorage` to keep the self-hosted starter simple. Because any successful same-origin XSS can read browser storage, an internet-facing production deployment should move authentication to `Secure`, `HttpOnly`, appropriately `SameSite` cookies and add a CSRF defense, or use a dedicated identity provider with a short-lived token flow. Maintain a restrictive Content Security Policy and keep Markdown raw HTML disabled.
