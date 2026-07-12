from pathlib import Path

import pytest

from wlq.promptbuild import (
    load_plan, load_reference, plan_section, quality_rules_block,
    required_sections_block, requires_references, style_guide_block,
)
from wlq import config

REFS_DIR = str(Path(__file__).resolve().parents[2] / "references")

ARTICLE_PLAN = """---
mode: article
article_type: impl
profile: research
created: 2026-07-12
title_draft: "Temporal で学ぶ Durable Execution"
slug: durable-execution
tags: [go, temporal]
target_audience: "Go で API サーバーを運用していてリトライ処理を自作している中級者。"
goal: "Durable Execution の価値を判断できるようになる"
topics_in_scope: ["Workflow の再実行モデル"]
topics_out_of_scope: []
constraints: []
---
## 壁打ちメモ
"""


def _write_plan(tmp_path, text=ARTICLE_PLAN):
    p = tmp_path / "plan.md"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_load_plan_article(tmp_path):
    plan = load_plan(_write_plan(tmp_path))
    assert plan.mode == "article" and plan.article_type == "impl"
    assert plan.tags == ("go", "temporal")
    assert requires_references(plan) is True  # profile=research


def test_load_plan_missing_required_field(tmp_path):
    broken = ARTICLE_PLAN.replace('goal: "Durable Execution の価値を判断できるようになる"\n', "")
    with pytest.raises(ValueError, match="goal"):
        load_plan(_write_plan(tmp_path, broken))


def test_load_reference_strips_header():
    text = load_reference(REFS_DIR, "readability-guide.md")
    assert "ported from" not in text


def test_style_guide_block_combines_type_and_common():
    block = style_guide_block(REFS_DIR, "impl")
    assert block.startswith("[文体ガイド（記事タイプ: impl）]\n")
    assert "一文は 60〜80 文字" in block  # common が連結されている


def test_required_sections_block_impl():
    block = required_sections_block(REFS_DIR, "impl")
    assert "- はじめに" in block and "- 結論・要点" in block and "- 次にやること" in block
    assert "{sections}" not in block
    assert "重要度" not in block  # news 指示は impl では入らない


def test_plan_section_empty_lists_render_nashi(tmp_path):
    section = plan_section(load_plan(_write_plan(tmp_path)))
    assert section.splitlines()[0] == "[投稿計画]"
    assert "- 書かないこと:\n  - なし" in section and "- 制約:\n  - なし" in section


def test_quality_rules_block_document_omits_frontmatter_keys():
    art, doc = quality_rules_block("article"), quality_rules_block("document")
    assert all(w in art for w in config.FORBIDDEN_WORDS[:1])
    assert "必須 Frontmatter キー" in art and "必須 Frontmatter キー" not in doc


def test_reference_requirements_block_substitutes_date():
    from datetime import datetime
    from wlq.promptbuild import _JST, reference_requirements_block
    block = reference_requirements_block(REFS_DIR, datetime(2026, 7, 12, 9, 0, 0, tzinfo=_JST))
    assert block.startswith("[参考情報要件]\n")
    assert "情報確認日: 2026-07-12" in block
    assert "%s" not in block
