"""references/*.md の見出し規約・移植ヘッダ・プレースホルダを検証する。"""
from pathlib import Path

import pytest
import regex

from wlq.checks_structure import NEWS_LABELS

REFS_DIR = Path(__file__).resolve().parents[2] / "references"
FILES = [
    "style-guide.md", "required-sections.md", "reference-requirements.md",
    "diagram-code-rules.md", "readability-guide.md", "news-fact-opinion.md",
]
HEADER_RE = regex.compile(r"\A<!-- ported from: \S+ @ autopostd [0-9a-f]{7,} -->\n")


@pytest.mark.parametrize("name", FILES)
def test_reference_has_ported_header(name):
    assert HEADER_RE.match((REFS_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name,headings",
    [
        ("style-guide.md", ["## common", "## intro", "## news", "## impl", "## opinion", "## general"]),
        ("diagram-code-rules.md", ["## common", "## impl"]),
        ("required-sections.md", ["## common", "## intro-integration", "## news"]),
    ],
)
def test_reference_headings(name, headings):
    text = (REFS_DIR / name).read_text(encoding="utf-8")
    for h in headings:
        assert f"\n{h}\n" in f"\n{text}", f"{name} に {h} がない"


def test_required_sections_placeholder_and_news_labels():
    text = (REFS_DIR / "required-sections.md").read_text(encoding="utf-8")
    assert "{sections}" in text
    for label in NEWS_LABELS:
        assert label in text, f"news ラベル {label} がチェッカー定数と一致しない"
