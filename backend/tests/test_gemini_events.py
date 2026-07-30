from dataclasses import dataclass, field

from app.services.gemini import GeminiService


@dataclass
class Annotation:
    type: str
    title: str
    url: str


@dataclass
class Block:
    annotations: list[Annotation] = field(default_factory=list)


@dataclass
class ModelOutputStep:
    type: str = "model_output"
    content: list[Block] = field(default_factory=list)


class ToolStep:
    type = "code_execution_call"

    @staticmethod
    def model_dump(**_: object) -> dict:
        return {
            "type": "code_execution_call",
            "arguments": {"code": "print(2 + 2)"},
            "thought": "private material must not be copied",
        }


def test_public_events_include_grounded_citations_without_thoughts() -> None:
    events = GeminiService._extract_tool_events(
        [
            ModelOutputStep(
                content=[
                    Block(
                        annotations=[
                            Annotation("url_citation", "Official source", "https://example.com/source")
                        ]
                    )
                ]
            ),
            ToolStep(),
        ]
    )
    assert any(event["type"] == "grounding_citation" for event in events)
    serialized = str(events).lower()
    assert "private material" not in serialized
    assert "print(2 + 2)" in serialized
