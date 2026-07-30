from app.agents.prompts import SYSTEM_BOUNDARY


def test_prompt_boundary_blocks_source_instructions_and_cot_storage() -> None:
    lowered = SYSTEM_BOUNDARY.lower()
    assert "untrusted evidence" in lowered
    assert "prompt injection" in lowered
    assert "chain-of-thought" in lowered
    assert "never invent a citation" in lowered
