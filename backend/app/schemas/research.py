from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class ResearchCreate(BaseModel):
    topic: str = Field(min_length=5, max_length=500)
    objective: str = Field(default="", max_length=4000)
    depth: Literal["quick", "standard", "deep"] = "standard"
    max_reflections: int = Field(default=2, ge=0, le=4)
    max_revisions: int = Field(default=2, ge=0, le=4)
    focus_urls: list[HttpUrl] = Field(default_factory=list, max_length=10)


class ResearchEventResponse(BaseModel):
    id: str
    sequence: int
    event_type: str
    agent: str | None
    message: str
    payload: dict
    created_at: datetime


class SourceResponse(BaseModel):
    id: str
    title: str
    url: str
    source_type: str
    authors: list
    published_at: str | None
    abstract: str
    excerpt: str
    credibility_score: float


class ReportResponse(BaseModel):
    id: str
    title: str
    executive_summary: str
    markdown: str
    quality_score: int
    citation_count: int
    metadata: dict
    version: int
    created_at: datetime


class ResearchJobResponse(BaseModel):
    id: str
    topic: str
    objective: str
    depth: str
    status: str
    current_agent: str | None
    progress: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    report: ReportResponse | None = None
    sources: list[SourceResponse] = Field(default_factory=list)


class DashboardStats(BaseModel):
    total_jobs: int
    completed_jobs: int
    running_jobs: int
    failed_jobs: int
    average_quality_score: float
    total_sources: int
