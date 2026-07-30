import json
import re
from typing import Literal

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.prompts import (
    ANALYST_PROMPT,
    CRITIC_PROMPT,
    REFLECTION_PROMPT,
    RESEARCHER_PROMPT,
    SYSTEM_BOUNDARY,
    WRITER_PROMPT,
)
from app.agents.schemas import (
    AnalystOutput,
    CriticOutput,
    FinalReport,
    ReflectionOutput,
    ResearcherOutput,
    WriterOutput,
)
from app.agents.state import ResearchState
from app.core.config import settings
from app.db.models import JobStatus, ResearchJob
from app.services.arxiv import ArxivService
from app.services.event_bus import EventPublisher
from app.services.gemini import GeminiService
from app.services.memory import MemoryService


class ResearchCancelled(RuntimeError):
    pass


class ResearchWorkflow:
    def __init__(self, db: Session, job: ResearchJob) -> None:
        self.db = db
        self.job = job
        self.gemini = GeminiService()
        self.memory = MemoryService(db, self.gemini)
        self.arxiv = ArxivService()
        self.events = EventPublisher(db, job.id, job.tenant_id)

    def run(self) -> ResearchState:
        builder = self._build_graph()
        checkpointer_url = settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
        with PostgresSaver.from_conn_string(checkpointer_url) as checkpointer:
            checkpointer.setup()
            graph = builder.compile(checkpointer=checkpointer)
            initial: ResearchState = {
                "job_id": str(self.job.id),
                "tenant_id": str(self.job.tenant_id),
                "topic": self.job.topic,
                "objective": self.job.objective,
                "depth": self.job.depth.value,
                "focus_urls": list(self.job.config.get("focus_urls", [])),
                "max_reflections": self.job.max_reflections,
                "max_revisions": self.job.max_revisions,
                "research_iteration": 0,
                "analysis_iteration": 0,
                "writer_iteration": 0,
                "critic_iteration": 0,
                "revision_iteration": 0,
                "messages": [],
            }
            config = {"configurable": {"thread_id": str(self.job.id)}}
            snapshot = graph.get_state(config)
            if snapshot.values and not snapshot.next:
                return snapshot.values
            graph_input = None if snapshot.values else initial
            return graph.invoke(graph_input, config=config)

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(ResearchState)
        graph.add_node("initialize", self.initialize)
        graph.add_node("researcher", self.researcher)
        graph.add_node("researcher_reflect", self.researcher_reflect)
        graph.add_node("analyst", self.analyst)
        graph.add_node("analyst_reflect", self.analyst_reflect)
        graph.add_node("writer", self.writer)
        graph.add_node("writer_reflect", self.writer_reflect)
        graph.add_node("critic", self.critic)
        graph.add_node("critic_reflect", self.critic_reflect)
        graph.add_node("prepare_revision", self.prepare_revision)
        graph.add_node("finalize", self.finalize)

        graph.add_edge(START, "initialize")
        graph.add_edge("initialize", "researcher")
        graph.add_edge("researcher", "researcher_reflect")
        graph.add_conditional_edges(
            "researcher_reflect",
            self.route_researcher,
            {"researcher": "researcher", "analyst": "analyst"},
        )
        graph.add_edge("analyst", "analyst_reflect")
        graph.add_conditional_edges(
            "analyst_reflect",
            self.route_analyst,
            {"analyst": "analyst", "writer": "writer"},
        )
        graph.add_edge("writer", "writer_reflect")
        graph.add_conditional_edges(
            "writer_reflect",
            self.route_writer,
            {"writer": "writer", "critic": "critic"},
        )
        graph.add_edge("critic", "critic_reflect")
        graph.add_conditional_edges(
            "critic_reflect",
            self.route_critic,
            {"critic": "critic", "prepare_revision": "prepare_revision", "finalize": "finalize"},
        )
        graph.add_edge("prepare_revision", "writer")
        graph.add_edge("finalize", END)
        return graph

    def initialize(self, state: ResearchState) -> dict:
        self._set_progress("Researcher", 5)
        self.events.publish("job_started", "Research workflow started", agent="Orchestrator")
        prior_memory = self.memory.retrieve(self.job.tenant_id, f"{state['topic']}\n{state['objective']}")
        self.events.publish(
            "memory_retrieved",
            f"Retrieved {len(prior_memory)} relevant memories",
            agent="Orchestrator",
            payload={"count": len(prior_memory)},
        )
        try:
            papers = self.arxiv.search_and_read(state["topic"], self._paper_limit(state["depth"]))
            self.events.publish(
                "papers_loaded",
                f"Loaded {len(papers)} verified arXiv papers",
                agent="Researcher",
                payload={"papers": [{"title": p["title"], "url": p["url"]} for p in papers]},
            )
        except Exception as exc:
            papers = []
            self.events.publish(
                "paper_search_warning",
                "arXiv was unavailable; continuing with grounded web evidence",
                agent="Researcher",
                payload={"error": str(exc)[:500]},
            )
        return {"prior_memory": prior_memory, "papers": papers}

    def researcher(self, state: ResearchState) -> dict:
        iteration = state.get("research_iteration", 0) + 1
        self._set_progress("Researcher", min(12 + iteration * 6, 28))
        self.events.publish(
            "agent_started",
            f"Researcher gathering evidence (iteration {iteration})",
            agent="Researcher",
        )
        prompt = RESEARCHER_PROMPT.format(
            boundary=SYSTEM_BOUNDARY,
            topic=state["topic"],
            objective=state["objective"],
            depth=state["depth"],
            focus_urls=json.dumps(state.get("focus_urls", [])),
            prior_memory=self._compact(state.get("prior_memory", [])),
            papers=self._compact(state.get("papers", [])),
            previous_output=self._compact(state.get("researcher_output", {})),
            reflection=self._compact(state.get("researcher_reflection", {})),
        )
        output, tools = self.gemini.structured_interaction(
            prompt=prompt,
            schema=ResearcherOutput,
            tools=[{"type": "google_search"}, {"type": "url_context"}],
        )
        self._publish_tools("Researcher", tools)
        self.events.publish(
            "agent_completed",
            f"Researcher collected {len(output.sources)} source candidates",
            agent="Researcher",
            payload={"source_count": len(output.sources), "unresolved": len(output.unresolved_questions)},
        )
        grounding_sources = [
            *state.get("grounding_sources", []),
            *(item for item in tools if item.get("type") == "grounding_citation"),
        ]
        unique_grounding: list[dict] = []
        seen_urls: set[str] = set()
        for source in grounding_sources:
            normalized = self._normalize_url(source.get("url", ""))
            if normalized and normalized not in seen_urls:
                seen_urls.add(normalized)
                unique_grounding.append({**source, "url": normalized})
        return {
            "research_iteration": iteration,
            "researcher_output": output.model_dump(),
            "grounding_sources": unique_grounding,
        }

    def researcher_reflect(self, state: ResearchState) -> dict:
        reflection = self._reflect("Researcher", state["topic"], state["researcher_output"])
        self.events.publish(
            "reflection",
            f"Researcher self-review score: {reflection.quality_score}",
            agent="Researcher",
            payload=reflection.model_dump(),
        )
        return {"researcher_reflection": reflection.model_dump()}

    def analyst(self, state: ResearchState) -> dict:
        iteration = state.get("analysis_iteration", 0) + 1
        self._set_progress("Analyst", min(35 + iteration * 7, 52))
        self.events.publish(
            "agent_started",
            f"Analyst synthesizing evidence (iteration {iteration})",
            agent="Analyst",
        )
        prompt = ANALYST_PROMPT.format(
            boundary=SYSTEM_BOUNDARY,
            topic=state["topic"],
            objective=state["objective"],
            research=self._compact(state["researcher_output"]),
            papers=self._compact(state.get("papers", [])),
            prior_memory=self._compact(state.get("prior_memory", [])),
            previous_output=self._compact(state.get("analyst_output", {})),
            reflection=self._compact(state.get("analyst_reflection", {})),
        )
        output, tools = self.gemini.structured_interaction(
            prompt=prompt,
            schema=AnalystOutput,
            tools=[{"type": "code_execution"}],
        )
        self._publish_tools("Analyst", tools)
        self.events.publish(
            "agent_completed",
            f"Analyst produced {len(output.findings)} findings",
            agent="Analyst",
            payload={"confidence": output.confidence, "finding_count": len(output.findings)},
        )
        return {"analysis_iteration": iteration, "analyst_output": output.model_dump()}

    def analyst_reflect(self, state: ResearchState) -> dict:
        reflection = self._reflect("Analyst", state["topic"], state["analyst_output"])
        self.events.publish(
            "reflection",
            f"Analyst self-review score: {reflection.quality_score}",
            agent="Analyst",
            payload=reflection.model_dump(),
        )
        return {"analyst_reflection": reflection.model_dump()}

    def writer(self, state: ResearchState) -> dict:
        iteration = state.get("writer_iteration", 0) + 1
        revision_iteration = state.get("revision_iteration", 0)
        self._set_progress("Writer", min(58 + iteration * 6, 74))
        registry = self._build_source_registry(state)
        if not registry:
            raise ValueError("No grounded sources were returned; retry the research job")
        self.events.publish(
            "agent_started",
            f"Writer drafting report (iteration {iteration})",
            agent="Writer",
        )
        prompt = WRITER_PROMPT.format(
            boundary=SYSTEM_BOUNDARY,
            topic=state["topic"],
            objective=state["objective"],
            research=self._compact(state["researcher_output"]),
            analysis=self._compact(state["analyst_output"]),
            source_registry=self._compact(registry),
            previous_draft=self._compact(state.get("writer_output", {})),
            revision_instructions=self._compact(state.get("critic_output", {}).get("revision_instructions", [])),
        )
        output, _ = self.gemini.structured_interaction(prompt=prompt, schema=WriterOutput)
        output.report_markdown = self._append_references(output.report_markdown, registry)
        self.events.publish(
            "agent_completed",
            "Writer completed a cited report draft",
            agent="Writer",
            payload={"word_count": len(output.report_markdown.split()), "citations": len(output.citation_keys_used)},
        )
        return {
            "writer_iteration": iteration,
            "revision_iteration": revision_iteration,
            "writer_output": output.model_dump(),
            "source_registry": registry,
        }

    def writer_reflect(self, state: ResearchState) -> dict:
        reflection = self._reflect("Writer", state["topic"], state["writer_output"])
        self.events.publish(
            "reflection",
            f"Writer self-review score: {reflection.quality_score}",
            agent="Writer",
            payload=reflection.model_dump(),
        )
        return {"writer_reflection": reflection.model_dump()}

    def critic(self, state: ResearchState) -> dict:
        iteration = state.get("critic_iteration", 0) + 1
        self._set_progress("Critic", min(80 + iteration * 4, 90))
        self.events.publish(
            "agent_started",
            f"Critic auditing report (iteration {iteration})",
            agent="Critic",
        )
        prompt = CRITIC_PROMPT.format(
            boundary=SYSTEM_BOUNDARY,
            topic=state["topic"],
            objective=state["objective"],
            draft=self._compact(state["writer_output"]),
            source_registry=self._compact(state["source_registry"]),
            research=self._compact(state["researcher_output"]),
            analysis=self._compact(state["analyst_output"]),
        )
        output, _ = self.gemini.structured_interaction(prompt=prompt, schema=CriticOutput)
        self.events.publish(
            "agent_completed",
            f"Critic verdict: {output.verdict} ({output.score}/100)",
            agent="Critic",
            payload=output.model_dump(),
        )
        return {"critic_iteration": iteration, "critic_output": output.model_dump()}

    def critic_reflect(self, state: ResearchState) -> dict:
        reflection = self._reflect("Critic", state["topic"], state["critic_output"])
        self.events.publish(
            "reflection",
            f"Critic self-review score: {reflection.quality_score}",
            agent="Critic",
            payload=reflection.model_dump(),
        )
        return {"critic_reflection": reflection.model_dump()}

    def prepare_revision(self, state: ResearchState) -> dict:
        revision_iteration = state.get("revision_iteration", 0) + 1
        self.events.publish(
            "revision_requested",
            f"Critic requested report revision {revision_iteration}",
            agent="Orchestrator",
            payload={"revision_iteration": revision_iteration},
        )
        return {"revision_iteration": revision_iteration, "writer_reflection": {}}

    def finalize(self, state: ResearchState) -> dict:
        writer = WriterOutput.model_validate(state["writer_output"])
        critic = CriticOutput.model_validate(state["critic_output"])
        valid_keys = {item["key"] for item in state["source_registry"]}
        report_body = re.split(
            r"\n## References",
            writer.report_markdown,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        used_keys = sorted(set(re.findall(r"\[(S\d+)\]", report_body)))
        if not used_keys:
            raise ValueError("Report body contains no grounded citations")
        invalid_keys = set(used_keys) - valid_keys
        if invalid_keys:
            raise ValueError(f"Report contains invalid citation keys: {sorted(invalid_keys)}")
        cited_sources = len(set(used_keys))
        coverage = cited_sources / max(1, len(valid_keys))
        deterministic_score = min(100, round(55 + coverage * 30 + min(len(used_keys), 15)))
        quality_score = min(critic.score, deterministic_score)
        final = FinalReport(
            title=writer.title,
            executive_summary=writer.executive_summary,
            markdown=writer.report_markdown,
            quality_score=quality_score,
            citation_keys=used_keys,
        )
        self._set_progress("Complete", 100)
        self.events.publish(
            "quality_gate_passed",
            f"Critic and citation quality gates passed with score {quality_score}",
            agent="Orchestrator",
            payload={"quality_score": quality_score, "citation_count": len(used_keys)},
        )
        return {"final_report": final.model_dump()}

    def route_researcher(self, state: ResearchState) -> Literal["researcher", "analyst"]:
        reflection = ReflectionOutput.model_validate(state["researcher_reflection"])
        if not reflection.sufficient and state["research_iteration"] < state["max_reflections"] + 1:
            return "researcher"
        return "analyst"

    def route_analyst(self, state: ResearchState) -> Literal["analyst", "writer"]:
        reflection = ReflectionOutput.model_validate(state["analyst_reflection"])
        if not reflection.sufficient and state["analysis_iteration"] < state["max_reflections"] + 1:
            return "analyst"
        return "writer"

    def route_writer(self, state: ResearchState) -> Literal["writer", "critic"]:
        reflection = ReflectionOutput.model_validate(state["writer_reflection"])
        if not reflection.sufficient and state["writer_iteration"] < state["max_reflections"] + 1:
            return "writer"
        return "critic"

    def route_critic(self, state: ResearchState) -> Literal["critic", "prepare_revision", "finalize"]:
        reflection = ReflectionOutput.model_validate(state["critic_reflection"])
        critic = CriticOutput.model_validate(state["critic_output"])
        if not reflection.sufficient and state["critic_iteration"] < state["max_reflections"] + 1:
            return "critic"
        needs_revision = critic.verdict == "revise" or critic.score < 85
        if needs_revision and state["revision_iteration"] < state["max_revisions"]:
            return "prepare_revision"
        return "finalize"

    def _reflect(self, agent_name: str, topic: str, output: dict) -> ReflectionOutput:
        prompt = REFLECTION_PROMPT.format(
            boundary=SYSTEM_BOUNDARY,
            agent_name=agent_name,
            topic=topic,
            output=self._compact(output),
        )
        reflection, _ = self.gemini.structured_interaction(prompt=prompt, schema=ReflectionOutput)
        return reflection

    def _build_source_registry(self, state: ResearchState) -> list[dict]:
        grounded = state.get("grounding_sources", [])
        trusted_urls = {self._normalize_url(item.get("url", "")) for item in grounded}
        trusted_urls.update(self._normalize_url(url) for url in state.get("focus_urls", []))
        trusted_urls.update(self._normalize_url(paper.get("url", "")) for paper in state.get("papers", []))
        trusted_urls.discard("")

        candidates: list[dict] = []
        for source in state["researcher_output"].get("sources", []):
            if self._normalize_url(source.get("url", "")) in trusted_urls:
                candidates.append(source)
        for citation in grounded:
            candidates.append(
                {
                    "title": citation.get("title", "Grounded web source"),
                    "url": citation.get("url", ""),
                    "source_type": "web",
                    "authors": [],
                    "key_points": [],
                    "credibility_score": 0.7,
                }
            )
        for focus_url in state.get("focus_urls", []):
            candidates.append(
                {
                    "title": "User-provided focus source",
                    "url": focus_url,
                    "source_type": "other",
                    "authors": [],
                    "key_points": [],
                    "credibility_score": 0.5,
                }
            )
        for paper in state.get("papers", []):
            candidates.append(
                {
                    "title": paper["title"],
                    "url": paper["url"],
                    "source_type": "paper",
                    "authors": paper.get("authors", []),
                    "published_at": paper.get("published_at"),
                    "key_points": [paper.get("abstract", "")[:500]],
                    "credibility_score": 0.9,
                }
            )

        seen: set[str] = set()
        registry: list[dict] = []
        for candidate in candidates:
            normalized = self._normalize_url(candidate.get("url", ""))
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            registry.append({"key": f"S{len(registry)+1}", **candidate, "url": normalized})
            if len(registry) >= settings.MAX_RESEARCH_SOURCES:
                break
        return registry

    @staticmethod
    def _normalize_url(url: object) -> str:
        value = str(url).strip()
        if not value.startswith(("https://", "http://")) or any(char.isspace() for char in value):
            return ""
        return value.rstrip("/").split("#", 1)[0]

    @staticmethod
    def _append_references(markdown: str, registry: list[dict]) -> str:
        cleaned = re.sub(r"\n## References.*$", "", markdown, flags=re.DOTALL | re.IGNORECASE).rstrip()
        lines = ["", "## References"]
        for source in registry:
            authors = ", ".join(source.get("authors", [])[:5])
            author_part = f" — {authors}" if authors else ""
            title = (
                str(source.get("title", "Source"))
                .replace("\n", " ")
                .replace("\r", " ")
                .replace("[", "\\[")
                .replace("]", "\\]")
            )[:500]
            url = str(source["url"]).replace("(", "%28").replace(")", "%29").replace(" ", "%20")
            lines.append(f"- [{source['key']}] [{title}]({url}){author_part}")
        return cleaned + "\n" + "\n".join(lines) + "\n"

    def _publish_tools(self, agent: str, tools: list[dict]) -> None:
        for tool in tools:
            tool_type = tool.get("type", "tool")
            self.events.publish(
                "tool_activity",
                f"{agent} used {tool_type.replace('_', ' ')}",
                agent=agent,
                payload={"tool_type": tool_type, "details": tool},
            )

    def _set_progress(self, agent: str, progress: int) -> None:
        self.db.refresh(self.job)
        if self.job.status == JobStatus.cancelled:
            raise ResearchCancelled("Research job was cancelled")
        self.job.current_agent = agent
        self.job.progress = progress
        self.db.add(self.job)
        self.db.commit()

    @staticmethod
    def _compact(value: object, limit: int = 28_000) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)[:limit]

    @staticmethod
    def _paper_limit(depth: str) -> int:
        return {"quick": min(2, settings.MAX_PAPERS), "standard": min(4, settings.MAX_PAPERS), "deep": settings.MAX_PAPERS}[depth]
