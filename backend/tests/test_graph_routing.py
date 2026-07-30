from app.agents.graph import ResearchWorkflow


def workflow_without_services() -> ResearchWorkflow:
    return ResearchWorkflow.__new__(ResearchWorkflow)


def reflection(sufficient: bool, score: int = 80) -> dict:
    return {
        "quality_score": score,
        "strengths": [],
        "gaps": [],
        "contradictions": [],
        "improvement_instructions": [],
        "sufficient": sufficient,
    }


def critic(verdict: str, score: int = 90) -> dict:
    return {
        "score": score,
        "verdict": verdict,
        "factual_issues": [],
        "citation_issues": [],
        "reasoning_issues": [],
        "clarity_issues": [],
        "revision_instructions": [],
    }


def test_researcher_reflection_is_bounded() -> None:
    workflow = workflow_without_services()
    state = {"researcher_reflection": reflection(False), "research_iteration": 1, "max_reflections": 2}
    assert workflow.route_researcher(state) == "researcher"
    state["research_iteration"] = 3
    assert workflow.route_researcher(state) == "analyst"


def test_critic_can_send_report_back_to_writer() -> None:
    workflow = workflow_without_services()
    state = {
        "critic_reflection": reflection(True),
        "critic_output": critic("revise"),
        "critic_iteration": 1,
        "max_reflections": 2,
        "revision_iteration": 0,
        "max_revisions": 2,
    }
    assert workflow.route_critic(state) == "prepare_revision"
    state["revision_iteration"] = 2
    assert workflow.route_critic(state) == "finalize"


def test_reference_section_uses_registry_keys() -> None:
    report = ResearchWorkflow._append_references(
        "# Report\n\nEvidence [S1].",
        [{"key": "S1", "title": "Official source", "url": "https://example.com", "authors": []}],
    )
    assert "## References" in report
    assert "[S1]" in report
    assert "https://example.com" in report


def test_source_registry_rejects_model_only_urls() -> None:
    workflow = workflow_without_services()
    state = {
        "researcher_output": {
            "sources": [
                {
                    "title": "Invented source",
                    "url": "https://unverified.example/source",
                    "source_type": "web",
                    "authors": [],
                    "key_points": [],
                    "credibility_score": 0.5,
                }
            ]
        },
        "grounding_sources": [
            {"type": "grounding_citation", "title": "Verified", "url": "https://verified.example/source"}
        ],
        "focus_urls": [],
        "papers": [],
    }
    registry = workflow._build_source_registry(state)
    assert [source["url"] for source in registry] == ["https://verified.example/source"]
