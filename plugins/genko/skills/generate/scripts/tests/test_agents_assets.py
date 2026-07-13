"""agents/*.md の frontmatter 規約（tools 最小権限・model 非指定・専用明記）を検証する。"""
from pathlib import Path

import pytest

from wlq.frontmatter import parse_frontmatter

AGENTS_DIR = Path(__file__).resolve().parents[4] / "agents"
EXPECTED_TOOLS = {
    "researcher": "WebSearch, WebFetch, Read, Write",
    "writer": "Read, Write",
    "judge": "Read, Write",
    "fixer": "Read, Write",
}


@pytest.mark.parametrize("name,tools", sorted(EXPECTED_TOOLS.items()))
def test_agent_frontmatter(name, tools):
    meta, body = parse_frontmatter((AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8"))
    assert meta["name"] == name
    assert meta["tools"] == tools
    assert "model" not in meta, "model はセッション継承（spec）— 指定しない"
    assert "genko:generate" in meta["description"]
    assert body.strip(), "本文（system prompt 相当）が空"
