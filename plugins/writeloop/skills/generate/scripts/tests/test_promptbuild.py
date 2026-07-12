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


def test_load_plan_rejects_scalar_list_field(tmp_path):
    broken = ARTICLE_PLAN.replace(
        'topics_in_scope: ["Workflow の再実行モデル"]', "topics_in_scope: 記事の主題"
    )
    with pytest.raises(ValueError, match="topics_in_scope"):
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


from datetime import datetime
from wlq.promptbuild import _JST, build_writer_prompt

FIXED_NOW = datetime(2026, 7, 12, 9, 0, 0, tzinfo=_JST)


def _headers(prompt: str) -> list[str]:
    import regex
    return regex.findall(r"^\[[^\]]+\]$", prompt, regex.MULTILINE)


def test_writer_article_research_block_order(tmp_path):
    plan = load_plan(_write_plan(tmp_path))  # impl / research
    prompt = build_writer_prompt(plan, "リサーチ本文", REFS_DIR, FIXED_NOW)
    assert _headers(prompt) == [
        "[文体ガイド（記事タイプ: impl）]", "[投稿計画]", "[必須セクション]",
        "[参考情報要件]", "[図とコード例のルール]", "[リサーチ結果]",
        "[品質ルール]", "[読まれやすさ]", "[出力形式]",
    ]
    assert "date: 2026-07-12T09:00:00+09:00" in prompt
    assert 'tags: ["go", "temporal"]' in prompt


def test_writer_article_basic_intro_omits_conditionals(tmp_path):
    text = ARTICLE_PLAN.replace("article_type: impl", "article_type: intro").replace(
        "profile: research", "profile: basic")
    prompt = build_writer_prompt(load_plan(_write_plan(tmp_path, text)), None, REFS_DIR, FIXED_NOW)
    hs = _headers(prompt)
    assert "[参考情報要件]" not in hs and "[リサーチ結果]" not in hs and "[事実と見解の分離]" not in hs


def test_writer_news_adds_fact_opinion(tmp_path):
    text = ARTICLE_PLAN.replace("article_type: impl", "article_type: news").replace(
        "profile: research", "profile: basic")
    hs = _headers(build_writer_prompt(load_plan(_write_plan(tmp_path, text)), None, REFS_DIR, FIXED_NOW))
    assert "[参考情報要件]" in hs and "[事実と見解の分離]" in hs  # news は basic でも参考情報要件が入る


DOCUMENT_PLAN = """---
mode: document
profile: research
created: 2026-07-12
title_draft: "MCP サーバーの認可モデル調査"
slug: mcp-auth
questions: ["OAuth 対応の現状", "ローカル実行時の権限境界"]
depth: "一次情報まで当たる"
---
"""


def test_writer_document_reduced_blocks(tmp_path):
    prompt = build_writer_prompt(load_plan(_write_plan(tmp_path, DOCUMENT_PLAN)), "調査", REFS_DIR, FIXED_NOW)
    assert _headers(prompt) == [
        "[投稿計画]", "[参考情報要件]", "[リサーチ結果]", "[品質ルール]", "[読まれやすさ]", "[出力形式]",
    ]
    assert "必須 Frontmatter キー" not in prompt


def test_writer_golden_article_impl_research(tmp_path):
    prompt = build_writer_prompt(load_plan(_write_plan(tmp_path)), "リサーチ本文", REFS_DIR, FIXED_NOW)
    golden = (Path(__file__).parent / "golden" / "writer-article-impl-research.md").read_text(encoding="utf-8")
    assert prompt == golden


def test_writer_document_basic_fully_reduced(tmp_path):
    text = DOCUMENT_PLAN.replace("profile: research", "profile: basic")
    prompt = build_writer_prompt(load_plan(_write_plan(tmp_path, text)), None, REFS_DIR, FIXED_NOW)
    assert _headers(prompt) == ["[投稿計画]", "[品質ルール]", "[読まれやすさ]", "[出力形式]"]


def test_writer_document_output_format_title_only(tmp_path):
    prompt = build_writer_prompt(load_plan(_write_plan(tmp_path, DOCUMENT_PLAN)), "調査", REFS_DIR, FIXED_NOW)
    tail = prompt.split("[出力形式]\n", 1)[1]
    assert 'title: "MCP サーバーの認可モデル調査"' in tail
    for absent in ("description:", "date:", "tags:", "draft:", "H2"):
        assert absent not in tail


from wlq.promptbuild import build_judge_prompt

ASPECTS = [
    {"key": "concrete_examples", "allow_error": True, "instruction": "具体例を評価する"},
    {"key": "failure_cases", "allow_error": False, "instruction": "失敗例を評価する"},
]


def test_judge_prompt_structure(tmp_path):
    plan = load_plan(_write_plan(tmp_path))
    prompt = build_judge_prompt(plan, "# 本文\n", ASPECTS, None)
    assert _headers(prompt) == ["[severity 制約]", "[記事情報]", "[評価観点]", "[記事本文]"]
    assert "  - failure_cases" in prompt          # allow_error=false のみ列挙
    assert "  - concrete_examples" not in prompt.split("[記事情報]")[0]
    assert "- concrete_examples: 具体例を評価する" in prompt


def test_judge_prompt_omits_severity_block_when_all_allow_error(tmp_path):
    plan = load_plan(_write_plan(tmp_path))
    prompt = build_judge_prompt(plan, "x", [ASPECTS[0]], None)
    assert "[severity 制約]" not in prompt


def test_judge_prompt_document_article_info(tmp_path):
    plan = load_plan(_write_plan(tmp_path, DOCUMENT_PLAN))
    prompt = build_judge_prompt(plan, "# 本文\n", ASPECTS, None)
    info = prompt.split("[評価観点]", 1)[0]
    assert '- タイトル: MCP サーバーの認可モデル調査' in info
    assert "- 知りたいこと:" in info
    for absent in ("- 記事タイプ:", "- 想定読者:", "- ゴール:"):
        assert absent not in info


def test_judge_prompt_research_requires_source_fidelity(tmp_path):
    plan = load_plan(_write_plan(tmp_path))
    without = build_judge_prompt(plan, "x", ASPECTS, "リサーチ")
    assert "[リサーチ結果]" not in without       # source_fidelity 非選定なら research があっても入れない
    aspects = ASPECTS + [{"key": "source_fidelity", "allow_error": True, "instruction": "照合する"}]
    with_research = build_judge_prompt(plan, "x", aspects, "リサーチ")
    assert "[リサーチ結果]" in with_research
    assert with_research.index("[リサーチ結果]") < with_research.index("[記事本文]")
