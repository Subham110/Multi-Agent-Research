import json
from collections.abc import Iterable
from typing import TypeVar

from google import genai
from google.genai import errors
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_random_exponential

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


def _retryable_gemini_error(exc: BaseException) -> bool:
    if isinstance(exc, ConnectionError | TimeoutError):
        return True
    return isinstance(exc, errors.APIError) and getattr(exc, "code", 0) in {408, 429, 500, 502, 503, 504}


class GeminiService:
    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    @retry(
        retry=retry_if_exception(_retryable_gemini_error),
        wait=wait_random_exponential(multiplier=1, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def structured_interaction(
        self,
        *,
        prompt: str,
        schema: type[T],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> tuple[T, list[dict]]:
        interaction = self.client.interactions.create(
            model=model or settings.GEMINI_MODEL,
            input=prompt,
            tools=tools or [],
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": schema.model_json_schema(),
            },
        )
        parsed = schema.model_validate_json(interaction.output_text)
        return parsed, self._extract_tool_events(interaction.steps or [])

    @retry(
        retry=retry_if_exception(_retryable_gemini_error),
        wait=wait_random_exponential(multiplier=1, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def embed(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=text[:30_000],
            config={"output_dimensionality": settings.EMBEDDING_DIMENSION},
        )
        if not response.embeddings:
            raise RuntimeError("Gemini returned no embedding")
        return list(response.embeddings[0].values)

    @staticmethod
    def _extract_tool_events(steps: Iterable[object]) -> list[dict]:
        """Return bounded public tool activity and grounded source metadata only."""
        allowed_types = {
            "google_search_call",
            "google_search_result",
            "url_context_call",
            "url_context_result",
            "code_execution_call",
            "code_execution_result",
        }
        safe_fields = {
            "type",
            "id",
            "status",
            "query",
            "queries",
            "url",
            "language",
            "outcome",
            "arguments",
            "result",
            "output",
        }
        events: list[dict] = []
        for step in steps:
            step_type = getattr(step, "type", "unknown")
            if step_type == "model_output":
                for block in getattr(step, "content", []) or []:
                    for annotation in getattr(block, "annotations", []) or []:
                        if getattr(annotation, "type", "") != "url_citation":
                            continue
                        url = str(getattr(annotation, "url", ""))[:2_000]
                        if url.startswith(("https://", "http://")):
                            events.append(
                                {
                                    "type": "grounding_citation",
                                    "title": str(getattr(annotation, "title", "Web source"))[:500],
                                    "url": url,
                                }
                            )
                continue
            if step_type not in allowed_types:
                continue
            raw = step.model_dump(mode="json", exclude_none=True) if hasattr(step, "model_dump") else {}
            compact: dict[str, object] = {"type": step_type}
            for key in safe_fields:
                if key in raw and key != "type":
                    compact[key] = GeminiService._sanitize_public_value(raw[key])
            events.append(compact)

        deduplicated: list[dict] = []
        seen: set[str] = set()
        for event in events:
            fingerprint = json.dumps(event, sort_keys=True, default=str)
            if fingerprint not in seen:
                seen.add(fingerprint)
                deduplicated.append(event)
        return deduplicated[:50]

    @staticmethod
    def _sanitize_public_value(value: object, depth: int = 0) -> object:
        if depth >= 3:
            return "[truncated]"
        if isinstance(value, str):
            return value[:2_000]
        if isinstance(value, int | float | bool) or value is None:
            return value
        if isinstance(value, list):
            return [GeminiService._sanitize_public_value(item, depth + 1) for item in value[:10]]
        if isinstance(value, dict):
            return {
                str(key)[:100]: GeminiService._sanitize_public_value(item, depth + 1)
                for key, item in list(value.items())[:20]
                if str(key).lower() not in {"thought", "thinking", "reasoning", "summary"}
            }
        return str(value)[:2_000]
