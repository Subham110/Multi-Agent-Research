from typing import Literal

from pydantic import BaseModel, Field


class SourceCandidate(BaseModel):
    title: str
    url: str
    source_type: Literal["web", "paper", "official", "dataset", "other"] = "web"
    authors: list[str] = Field(default_factory=list)
    published_at: str | None = None
    key_points: list[str] = Field(default_factory=list)
    credibility_score: float = Field(default=0.6, ge=0, le=1)
    credibility_reason: str = ""


class ResearcherOutput(BaseModel):
    research_summary: str
    key_questions: list[str]
    evidence_map: list[str]
    sources: list[SourceCandidate]
    unresolved_questions: list[str] = Field(default_factory=list)


class ReflectionOutput(BaseModel):
    quality_score: int = Field(ge=0, le=100)
    strengths: list[str]
    gaps: list[str]
    contradictions: list[str]
    improvement_instructions: list[str]
    sufficient: bool


class AnalystOutput(BaseModel):
    findings: list[str]
    comparisons: list[str]
    quantitative_results: list[str]
    assumptions: list[str]
    limitations: list[str]
    confidence: float = Field(ge=0, le=1)
    code_execution_summary: str = ""


class WriterOutput(BaseModel):
    title: str
    executive_summary: str
    report_markdown: str
    citation_keys_used: list[str]


class CriticOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    verdict: Literal["pass", "revise"]
    factual_issues: list[str]
    citation_issues: list[str]
    reasoning_issues: list[str]
    clarity_issues: list[str]
    revision_instructions: list[str]


class FinalReport(BaseModel):
    title: str
    executive_summary: str
    markdown: str
    quality_score: int
    citation_keys: list[str]
