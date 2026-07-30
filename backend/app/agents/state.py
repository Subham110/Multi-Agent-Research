from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class ResearchState(TypedDict, total=False):
    job_id: str
    tenant_id: str
    topic: str
    objective: str
    depth: str
    focus_urls: list[str]
    max_reflections: int
    max_revisions: int
    research_iteration: int
    analysis_iteration: int
    writer_iteration: int
    critic_iteration: int
    revision_iteration: int
    prior_memory: list[dict[str, Any]]
    papers: list[dict[str, Any]]
    researcher_output: dict[str, Any]
    grounding_sources: list[dict[str, Any]]
    researcher_reflection: dict[str, Any]
    analyst_output: dict[str, Any]
    analyst_reflection: dict[str, Any]
    writer_output: dict[str, Any]
    writer_reflection: dict[str, Any]
    critic_output: dict[str, Any]
    critic_reflection: dict[str, Any]
    source_registry: list[dict[str, Any]]
    final_report: dict[str, Any]
    messages: Annotated[list, add_messages]
