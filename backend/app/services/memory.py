import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MemoryChunk
from app.services.gemini import GeminiService


class MemoryService:
    def __init__(self, db: Session, gemini: GeminiService) -> None:
        self.db = db
        self.gemini = gemini

    def retrieve(self, tenant_id: uuid.UUID, query: str, limit: int = 5) -> list[dict]:
        has_memory = self.db.scalar(
            select(MemoryChunk.id).where(MemoryChunk.tenant_id == tenant_id).limit(1)
        )
        if has_memory is None:
            return []

        embedding = self.gemini.embed(query)
        distance = MemoryChunk.embedding.cosine_distance(embedding)
        rows = self.db.execute(
            select(MemoryChunk, distance.label("distance"))
            .where(MemoryChunk.tenant_id == tenant_id)
            .order_by(distance)
            .limit(limit)
        ).all()
        return [
            {
                "content": chunk.content,
                "kind": chunk.kind,
                "metadata": chunk.metadata_json,
                "similarity": round(1 - float(dist), 4),
            }
            for chunk, dist in rows
        ]

    def remember_report(self, tenant_id: uuid.UUID, job_id: uuid.UUID, markdown: str, metadata: dict) -> None:
        for index, chunk in enumerate(self._chunk(markdown)):
            self.db.add(
                MemoryChunk(
                    tenant_id=tenant_id,
                    job_id=job_id,
                    kind="report",
                    content=chunk,
                    embedding=self.gemini.embed(chunk),
                    metadata_json={**metadata, "chunk_index": index},
                )
            )
        self.db.commit()

    @staticmethod
    def _chunk(text: str, size: int = 2400, overlap: int = 300) -> Iterable[str]:
        cursor = 0
        while cursor < len(text):
            end = min(len(text), cursor + size)
            yield text[cursor:end]
            if end == len(text):
                break
            cursor = end - overlap
