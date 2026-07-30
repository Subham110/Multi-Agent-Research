import re
from dataclasses import asdict, dataclass
from urllib.parse import urlencode

import feedparser
import fitz
import httpx

from app.core.config import settings

ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_PDF = "https://arxiv.org/pdf/{paper_id}"


@dataclass
class Paper:
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    published_at: str
    url: str
    pdf_url: str
    excerpt: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ArxivService:
    def search_and_read(self, query: str, max_results: int | None = None) -> list[dict]:
        limit = max_results if max_results is not None else settings.MAX_PAPERS
        if limit <= 0:
            return []
        params = {"search_query": f"all:{query}", "start": 0, "max_results": limit, "sortBy": "relevance"}
        with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "ResearchMesh/1.0"}) as client:
            response = client.get(f"{ARXIV_API}?{urlencode(params)}")
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            papers: list[Paper] = []
            for entry in feed.entries[:limit]:
                paper_id = entry.id.rsplit("/", 1)[-1]
                paper_id = re.sub(r"v\d+$", "", paper_id)
                paper = Paper(
                    paper_id=paper_id,
                    title=" ".join(entry.title.split()),
                    authors=[author.name for author in entry.get("authors", [])],
                    abstract=" ".join(entry.summary.split()),
                    published_at=entry.get("published", ""),
                    url=f"https://arxiv.org/abs/{paper_id}",
                    pdf_url=ARXIV_PDF.format(paper_id=paper_id),
                )
                try:
                    paper.excerpt = self._read_pdf_excerpt(client, paper.pdf_url)
                except Exception:
                    paper.excerpt = paper.abstract
                papers.append(paper)
        return [paper.to_dict() for paper in papers]

    @staticmethod
    def _read_pdf_excerpt(client: httpx.Client, pdf_url: str) -> str:
        with client.stream("GET", pdf_url) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > settings.MAX_PDF_BYTES:
                    raise ValueError("PDF exceeds configured size limit")
        document = fitz.open(stream=bytes(content), filetype="pdf")
        text_parts: list[str] = []
        for page in document[:8]:
            text_parts.append(page.get_text("text"))
            if sum(map(len, text_parts)) > 18_000:
                break
        return "\n".join(text_parts)[:18_000]
