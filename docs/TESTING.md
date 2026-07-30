# Testing and Evaluation

## Backend checks

```bash
cd backend
ruff check app tests
pytest --cov=app --cov-report=term-missing
```

Included tests cover:

- Argon2 password verification
- JWT tenant scope
- Bounded graph routing
- Critic-to-Writer revision routing
- Server-generated reference section
- Rejection of ungrounded model-only source URLs
- Public Gemini tool-event filtering without hidden reasoning
- Health endpoint
- Prompt-injection and chain-of-thought boundary text

## Frontend checks

```bash
cd frontend
npm install
npm run lint
npm run build
```

Recommended additions:

- Vitest component tests
- Redux thunk tests with mocked fetch
- Playwright login/create/live-report flow
- Accessibility checks with axe
- Visual regression for dashboard states

## Integration test plan

1. Start PostgreSQL and Redis.
2. Run migrations.
3. Bootstrap an administrator.
4. Log in and obtain a JWT.
5. Create a WebSocket ticket and verify it can be consumed once only.
6. Create a research job.
7. Verify API response is `202` while work continues.
8. Verify Researcher, Analyst, Writer, and Critic events are persisted.
9. Verify the final report only uses registered citation keys.
10. Restart the WebSocket and verify event replay without duplicates.
11. Cancel a running job and verify cancellation at a node boundary.
12. Attempt cross-tenant access and expect `404`/denial.

## Live Gemini test

Use a low-cost, narrow topic. Confirm:

- Google Search tool event
- arXiv sources where relevant
- Code execution on a quantitative prompt
- Reflection event for every agent
- Final report and source registry
- Memory chunks after completion

Live tests incur API/tool usage and should not run on every pull request.

## Accuracy evaluation

Do not infer accuracy improvement from architecture alone.

Build a benchmark with:

- Questions with known answers
- Time-sensitive questions
- Quantitative questions
- Questions with conflicting credible sources
- Paper-heavy technical questions
- Prompt-injection documents

For each question, generate:

- Single-agent baseline
- Multi-agent ResearchMesh report

Blindly evaluate:

- Factual correctness
- Citation correctness
- Citation coverage
- Source quality/diversity
- Calculation correctness
- Contradiction handling
- Calibration/uncertainty
- Completeness
- Usefulness
- Cost and latency

Store rows as JSONL and summarize:

```bash
python scripts/evaluate_reports.py results.jsonl
```

Example row:

```json
{"system":"multi","quality_score":91,"citation_count":12,"invalid_citations":0,"critic_issues":1}
```

Use enough representative samples and report confidence intervals before using words such as “significantly.”
