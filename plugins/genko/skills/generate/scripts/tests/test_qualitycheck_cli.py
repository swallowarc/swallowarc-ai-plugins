"""qualitycheck.py（CLI エントリ）のテスト。subprocess で sys.executable 実行する。

task-12.md 記載の必須テスト:
- test_cli_outputs_json_to_stdout / test_cli_missing_draft_exits_nonzero
  （task-12.md のコードブロックをそのまま転記）
- --plan からの article_type/constraints 解決 -> test_cli_resolves_article_type_and_constraints_from_plan
- --type が --plan より優先 -> test_cli_type_flag_overrides_plan
- --out ファイル書き出し -> test_cli_writes_output_file
- article モードの JSON が本番順の findings を持つこと
  -> test_cli_article_mode_json_has_production_order_findings

対応する単一の Go テストは無い（CLI は本移植独自の成果物のため）。
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent

# checker.go:264-326 の Check() 登録順そのもの（tests/test_runner.py の
# ARTICLE_ORDER と同一。CLI 経由の配線を独立に検証するため、テストファイルの
# 自己完結性を優先してここでも定義する）。
ARTICLE_ORDER = [
    "forbidden_words",
    "frontmatter_yaml",
    "frontmatter_values",
    "description_quality",
    "title_length",
    "heading_structure",
    "tags_format",
    "series_consistency",
    "code_language_tag",
    "code_kind_label",
    "mermaid_context",
    "body_length",
    "sentence_length",
    "sentence_length",
    "sentence_commas",
    "kanji_run",
    "weak_expressions",
    "bold_colon_list",
    "emoji_markers",
    "hype_expressions",
    "code_line_length",
    "sentence_ending_run",
    "sentence_ending_variety",
    "rhetorical_contrast_freq",
    "negation_first_freq",
    "cliche_phrases",
    "paragraph_uniformity",
    "hard_line_breaks",
    "first_person_freq",
    "reason_template_freq",
    "required_sections",
    "references_section",
    "reference_entries",
    "verification_date",
    "research_reference_match",
    "series_navigation",
]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "qualitycheck.py"), *args],
        capture_output=True,
        text=True,
    )


def test_cli_outputs_json_to_stdout(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("自由なメモ。", encoding="utf-8")
    r = run_cli("--draft", str(draft), "--mode", "document", "--out", "-")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["schema_version"] == 1
    assert isinstance(data["findings"], list)


def test_cli_missing_draft_exits_nonzero(tmp_path):
    r = run_cli("--draft", str(tmp_path / "nai.md"), "--mode", "article", "--out", "-")
    assert r.returncode != 0


def test_cli_missing_plan_exits_nonzero(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("自由なメモ。", encoding="utf-8")
    r = run_cli(
        "--draft", str(draft), "--mode", "article",
        "--plan", str(tmp_path / "nai-plan.md"), "--out", "-",
    )
    assert r.returncode != 0
    assert r.stderr != ""


def test_cli_missing_research_exits_nonzero(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("自由なメモ。", encoding="utf-8")
    r = run_cli(
        "--draft", str(draft), "--mode", "document",
        "--research", str(tmp_path / "nai-research.md"), "--out", "-",
    )
    assert r.returncode != 0
    assert r.stderr != ""


def test_cli_invalid_mode_exits_nonzero(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("自由なメモ。", encoding="utf-8")
    r = run_cli("--draft", str(draft), "--mode", "blog", "--out", "-")
    assert r.returncode != 0


def test_cli_non_utf8_draft_exits_nonzero(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_bytes(b"\xff\xfe\x00invalid utf-8 \x80\x81")
    r = run_cli("--draft", str(draft), "--mode", "document", "--out", "-")
    assert r.returncode != 0
    assert r.stderr.startswith("error:")


def test_cli_malformed_plan_frontmatter_exits_nonzero(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("自由なメモ。", encoding="utf-8")
    plan = tmp_path / "plan.md"
    plan.write_text('---\narticle_type: "unterminated\n---\n計画本文\n', encoding="utf-8")
    r = run_cli(
        "--draft", str(draft), "--mode", "article", "--plan", str(plan), "--out", "-",
    )
    assert r.returncode != 0
    assert r.stderr.startswith("error:")


def test_cli_resolves_article_type_and_constraints_from_plan(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text(
        "---\ntitle: X\n---\n" + "あ。" * 2000,  # 4000 rune な本文（3000-5000 内）
        encoding="utf-8",
    )
    plan = tmp_path / "plan.md"
    plan.write_text(
        '---\narticle_type: impl\nconstraints:\n  - "3000〜5000字"\n---\n計画本文\n',
        encoding="utf-8",
    )
    r = run_cli(
        "--draft", str(draft), "--mode", "article", "--plan", str(plan), "--out", "-",
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["facts"]["article_type"] == "impl"

    body_length = next(f for f in data["findings"] if f["name"] == "body_length")
    # constraints が実際に渡っていることを、body_length の detail が
    # 「制約なし」ではなく実際のレンジ判定であることで確認する。
    assert "no length constraint" not in body_length["detail"]
    assert "3000" in body_length["detail"] and "5000" in body_length["detail"]


def test_cli_type_flag_overrides_plan(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("---\ntitle: X\n---\n本文\n", encoding="utf-8")
    plan = tmp_path / "plan.md"
    plan.write_text("---\narticle_type: impl\n---\n計画本文\n", encoding="utf-8")
    r = run_cli(
        "--draft", str(draft), "--mode", "article",
        "--plan", str(plan), "--type", "general", "--out", "-",
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["facts"]["article_type"] == "general"


def test_cli_defaults_article_type_to_general_without_plan_or_type(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("---\ntitle: X\n---\n本文\n", encoding="utf-8")
    r = run_cli("--draft", str(draft), "--mode", "article", "--out", "-")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["facts"]["article_type"] == "general"


def test_cli_writes_output_file(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("自由なメモ。", encoding="utf-8")
    out = tmp_path / "out" / "rules.json"
    out.parent.mkdir()
    r = run_cli("--draft", str(draft), "--mode", "document", "--out", str(out))
    assert r.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["mode"] == "document"


def test_cli_article_mode_json_has_production_order_findings(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text(
        "---\n"
        "title: サンプル記事のタイトル\n"
        "date: 2026-01-01\n"
        "tags:\n"
        "  - go\n"
        "  - test\n"
        "draft: false\n"
        "description: これはテスト用に十分な長さを持つ説明文です。\n"
        "---\n"
        "## 結論・要点\n\nこれはテスト用の本文です。\n",
        encoding="utf-8",
    )
    r = run_cli("--draft", str(draft), "--mode", "article", "--out", "-")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert [f["name"] for f in data["findings"]] == ARTICLE_ORDER


def test_cli_document_mode_references_only_with_research(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("普通の文章です。", encoding="utf-8")

    r_without = run_cli("--draft", str(draft), "--mode", "document", "--out", "-")
    assert r_without.returncode == 0
    names_without = [f["name"] for f in json.loads(r_without.stdout)["findings"]]
    assert "references_section" not in names_without

    research = tmp_path / "research.md"
    research.write_text("https://example.com/ を参照。", encoding="utf-8")
    r_with = run_cli(
        "--draft", str(draft), "--mode", "document",
        "--research", str(research), "--out", "-",
    )
    assert r_with.returncode == 0
    names_with = [f["name"] for f in json.loads(r_with.stdout)["findings"]]
    assert "references_section" in names_with


def test_cli_exit_code_is_zero_even_when_findings_fail(tmp_path):
    # forbidden_words に確実に fail する draft（error severity）でも exit 0 のまま。
    draft = tmp_path / "d.md"
    draft.write_text("---\ntitle: X\n---\nこれは絶対に正しいTODOです。", encoding="utf-8")
    r = run_cli("--draft", str(draft), "--mode", "article", "--out", "-")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    forbidden = next(f for f in data["findings"] if f["name"] == "forbidden_words")
    assert forbidden["passed"] is False
