"""wlq/runner.py（run_checks）の統合テスト。

Go 側対応（`~/workspace/autopostd/internal/infrastructure/quality/*_test.go` @ 20c740b）:

test_article_mode_findings_follow_production_order
    -> 対応する単一の Go テストは無く、checker.go:264-326 の Check() 登録順そのものを
       仕様として固定する（global-constraints.md: findings 配列の順序を比較対象とする）。
test_malformed_frontmatter_skips_dependent_checks_but_runs_the_rest
    -> TestRuleBasedChecker_Frontmatter_MalformedYAMLFails（Task 2 申し送り）
test_inline_triple_dash_is_not_a_delimiter
test_frontmatter_must_start_at_first_line
test_horizontal_rule_after_closing_delimiter_does_not_break_parsing
test_unclosed_frontmatter_fails
    -> TestParseFrontmatter_LineAnchored の 4 t.Run サブケース（Task 2 申し送り。
       checker_test.go:463-527。run_checks 経由で本文中の horizontal rule がパースを
       壊さないことまで検証する）
test_readability_checks_are_wired_after_frontmatter_split
    -> TestRuleBasedChecker_ReadabilityChecksRegistered（Task 5 申し送り。
       checker_readability_test.go:259）
test_rhetorical_contrast_freq_excludes_code_fence
    -> TestRuleBasedChecker_RhetoricalContrastFreq_ExcludesCodeFence（Task 6 申し送り。
       checker_ai_style_test.go:293）
test_negation_first_freq_excludes_code_fence
    -> TestRuleBasedChecker_NegationFirstFreq_ExcludesCodeFence（Task 6 申し送り。
       checker_ai_style_test.go:462）
test_title_length_is_wired_to_frontmatter_title
    -> TestRuleBasedChecker_TitleLengthRegistered（Task 9 申し送り。checker_title_test.go:99）
test_body_length_is_wired_to_plan_constraints
    -> TestRuleBasedChecker_BodyLengthRegistered（Task 9 申し送り。checker_length_test.go:74）
test_check_includes_reference_checks
    -> TestCheck_IncludesReferenceChecks（Task 11 申し送り。checker_references_test.go:356。
       Go は refPlan(t, "intro", "research") で generation_profile="research" を使うが、
       genko に profile 概念が無いため research_content を渡すことで代替する
       設計判断は Task 11 の check_references と統一。詳細は
       wlq/checks_references.py のモジュール docstring 参照）

document モード（spec 由来の縮退セット。対応する Go の Check 経路は無い）:
test_document_mode_excludes_blog_only_checks
test_document_mode_includes_readability_and_ai_style_checks_in_production_order
test_document_mode_references_only_with_research_content
test_document_mode_frontmatter_is_optional_and_stripped_when_present
test_document_mode_survives_malformed_frontmatter_by_falling_back_to_full_content

facts（spec 由来。has_fenced_block は domain/judge_aspects_diagram_code.go の
containsFencedBlock、contains_triple_backtick は domain/judge_aspects_readability.go の
strings.Contains 判定の移植。prose_runes は Go に対応の無い本移植独自の fact。
詳細は wlq/runner.py のモジュール docstring 参照）:
test_facts_has_fenced_block_true_for_backtick_fence
test_facts_has_fenced_block_true_for_tilde_fence_without_triple_backtick
test_facts_has_fenced_block_false_without_any_fence
test_facts_prose_runes_matches_manual_extraction
test_facts_prose_runes_falls_back_to_full_content_when_frontmatter_parse_fails
test_facts_article_type_echoes_resolved_value

引数バリデーション（run_checks 独自の入力検証。Go に対応なし）:
test_unknown_mode_raises_value_error

除外: TestRuleBasedChecker_DisabledChecks_SkipsNamedCheck
    -> QUALITY_DISABLED_CHECKS 機構は本移植のスコープ外
       （global-constraints.md: 「環境変数による上書き機構は作らない」）のため対象外。
"""
import pytest

from wlq.frontmatter import parse_frontmatter
from wlq.prose import count_prose_runes, extract_prose
from wlq.runner import run_checks

# checker.go:264-326 の Check() 登録順 + genko 独自追加の progress_narration_freq
# （reason_template_freq の直後。Go に対応なし。wlq/checks_narration.py 参照）。
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
    "progress_narration_freq",
    "required_sections",
    "references_section",
    "reference_entries",
    "verification_date",
    "research_reference_match",
    "series_navigation",
]

# ARTICLE_ORDER のうち「frontmatter パース成功時のみ」登録される名前
# （checker.go の `if fmErr == nil` ブロック相当。集合なので重複は気にしない）。
FRONTMATTER_DEPENDENT_NAMES = {
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
    "progress_narration_freq",
}

# document モードの相対順（article モードの「frontmatter パース成功時」ブロックのうち
# 可読性・AI 文体系のみを抜き出した順序。references は --research 時のみ末尾に追加）。
DOCUMENT_ORDER = [
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
    "progress_narration_freq",
]

REFERENCE_NAMES = [
    "references_section",
    "reference_entries",
    "verification_date",
    "research_reference_match",
]


def _names(findings):
    return [f.name for f in findings]


def _find(findings, name):
    return next(f for f in findings if f.name == name)


# ---------------------------------------------------------------------------
# 1a. 配線の統合テスト: article モードの登録順
# ---------------------------------------------------------------------------


def test_article_mode_findings_follow_production_order():
    draft = (
        "---\n"
        "title: サンプル記事のタイトル\n"
        "date: 2026-01-01\n"
        "tags:\n"
        "  - go\n"
        "  - test\n"
        "draft: false\n"
        "description: これはテスト用に十分な長さを持つ説明文です。\n"
        "---\n"
        "## 結論・要点\n"
        "\n"
        "これはテスト用の本文です。\n"
    )
    findings, _ = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    assert _names(findings) == ARTICLE_ORDER


# ---------------------------------------------------------------------------
# 1b. frontmatter パース失敗時: MalformedYAMLFails 相当
# ---------------------------------------------------------------------------


def test_malformed_frontmatter_skips_dependent_checks_but_runs_the_rest():
    # Go: checker_test.go:130 TestRuleBasedChecker_Frontmatter_MalformedYAMLFails の入力。
    draft = '---\ntitle: "unterminated\n---\nbody'
    findings, _ = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    names = _names(findings)

    fm_yaml = _find(findings, "frontmatter_yaml")
    assert fm_yaml.passed is False

    assert set(names).isdisjoint(FRONTMATTER_DEPENDENT_NAMES)

    assert "forbidden_words" in names
    assert "required_sections" in names
    assert set(REFERENCE_NAMES) <= set(names)
    assert "series_navigation" in names


# ---------------------------------------------------------------------------
# 1c. TestParseFrontmatter_LineAnchored 相当（checker_test.go:463-527）
# ---------------------------------------------------------------------------


def test_inline_triple_dash_is_not_a_delimiter():
    draft = "本文A---B---C のように行中に --- を含むだけの記事"
    findings, _ = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    assert _find(findings, "frontmatter_yaml").passed is False


def test_frontmatter_must_start_at_first_line():
    draft = "intro text\n---\ntitle: X\n---\nbody"
    findings, _ = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    assert _find(findings, "frontmatter_yaml").passed is False


def test_horizontal_rule_after_closing_delimiter_does_not_break_parsing():
    draft = "---\ntitle: X\n---\n## 見出し\n本文\n\n---\n\n続き"
    findings, _ = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    assert _find(findings, "frontmatter_yaml").passed is True


def test_unclosed_frontmatter_fails():
    draft = "---\ntitle: X\nbody without closing delimiter"
    findings, _ = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    assert _find(findings, "frontmatter_yaml").passed is False


# ---------------------------------------------------------------------------
# 1d. 可読性チェックの配線（Task 5 申し送り）
# ---------------------------------------------------------------------------


def test_readability_checks_are_wired_after_frontmatter_split():
    # Go: checker_readability_test.go:259 TestRuleBasedChecker_ReadabilityChecksRegistered。
    draft = "---\ntitle: X\n---\n## 概要\nこれは正しいかもしれない！\n"
    findings, _ = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    names = _names(findings)
    for name in ("sentence_length", "sentence_commas", "kanji_run", "weak_expressions"):
        assert name in names

    weak = _find(findings, "weak_expressions")
    assert weak.passed is False
    assert weak.severity == "warning"

    # weak_expressions の警告 fail が、他の（合否に関わる）チェックと同じ findings
    # 配列に混ざって出力されること（Task 5 申し送りの意図）。
    assert "forbidden_words" in names
    assert "bold_colon_list" in names


# ---------------------------------------------------------------------------
# 1e. AI 文体チェックの配線: ExcludesCodeFence 相当（Task 6 申し送り）
# ---------------------------------------------------------------------------


def test_rhetorical_contrast_freq_excludes_code_fence():
    # Go: checker_ai_style_test.go:293 の入力そのまま。
    draft = (
        "---\ntitle: X\n---\n## 概要\n"
        "```text\nAではなくBではなくCではなくDではなく\n```\n本文。\n"
    )
    findings, _ = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    c = _find(findings, "rhetorical_contrast_freq")
    assert c.passed is True, c.detail


def test_negation_first_freq_excludes_code_fence():
    # Go: checker_ai_style_test.go:462 の入力そのまま。
    draft = (
        "---\ntitle: X\n---\n## 概要\n"
        "```text\nAではありませんBではありませんCではありませんDではありませんEではありません\n```\n本文。\n"
    )
    findings, _ = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    c = _find(findings, "negation_first_freq")
    assert c.passed is True, c.detail


# ---------------------------------------------------------------------------
# 1f. code / title / body_length / references の配線（Task 9/10/11 申し送り）
# ---------------------------------------------------------------------------


def test_title_length_is_wired_to_frontmatter_title():
    # Go: checker_title_test.go:99 TestRuleBasedChecker_TitleLengthRegistered。
    # 19 rune は既定の下限(20)未満。
    draft = '---\ntitle: "' + "あ" * 19 + '"\n---\n## 概要\n本文\n'
    findings, _ = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    c = _find(findings, "title_length")
    assert c.passed is False
    assert c.severity == "warning"


def test_body_length_is_wired_to_plan_constraints():
    # Go: checker_length_test.go:74 TestRuleBasedChecker_BodyLengthRegistered。
    # 6000 rune はレンジ(3000-5000)を超過。
    prose = "あ。" * 3000
    draft = "---\ntitle: X\n---\n" + prose
    findings, _ = run_checks(
        draft,
        mode="article",
        article_type="general",
        constraints=["3000〜5000字"],
        research_content=None,
    )
    c = _find(findings, "body_length")
    assert c.passed is False
    assert c.severity == "error"


def test_check_includes_reference_checks():
    # Go: checker_references_test.go:356 TestCheck_IncludesReferenceChecks。
    # Go は refPlan(t, "intro", "research")（generation_profile="research"）を使うが、
    # genko には profile 概念が無いため research_content の有無で代替する
    # （Task 11 の設計判断と統一。wlq/checks_references.py 参照）。
    draft = (
        "---\ntitle: X\n---\n"
        "本文です。\n\n"
        "## 参考情報\n\n"
        "- [Go 1.24 Release Notes](https://go.dev/doc/go1.24)（一次情報）\n"
        "- [解説記事](https://example.com/blog/go124)\n\n"
        "情報確認日: 2026-07-03\n"
    )
    findings, _ = run_checks(
        draft,
        mode="article",
        article_type="intro",
        constraints=[],
        research_content="https://go.dev/doc/go1.24 を参照した。",
    )
    names = _names(findings)
    for name in REFERENCE_NAMES:
        assert name in names


# ---------------------------------------------------------------------------
# 2. document モードのチェックセット
# ---------------------------------------------------------------------------


def test_document_mode_excludes_blog_only_checks():
    draft = "普通の文章です。とても普通です。"
    findings, _ = run_checks(
        draft, mode="document", article_type="general", constraints=[], research_content=None
    )
    blog_only_names = set(ARTICLE_ORDER) - set(DOCUMENT_ORDER) - set(REFERENCE_NAMES)
    assert set(_names(findings)).isdisjoint(blog_only_names)


def test_document_mode_includes_readability_and_ai_style_checks_in_production_order():
    draft = "普通の文章です。とても普通です。これは正しいかもしれない！"
    findings, _ = run_checks(
        draft, mode="document", article_type="general", constraints=[], research_content=None
    )
    assert _names(findings) == DOCUMENT_ORDER


def test_document_mode_references_only_with_research_content():
    draft = "普通の文章です。"
    without_research, _ = run_checks(
        draft, mode="document", article_type="general", constraints=[], research_content=None
    )
    assert _names(without_research) == DOCUMENT_ORDER

    with_research, _ = run_checks(
        draft,
        mode="document",
        article_type="general",
        constraints=[],
        research_content="https://example.com/",
    )
    assert _names(with_research) == DOCUMENT_ORDER + REFERENCE_NAMES


def test_document_mode_frontmatter_is_optional_and_stripped_when_present():
    draft = "---\ntitle: X\n---\nこれは本文です。"
    findings, _ = run_checks(
        draft, mode="document", article_type="general", constraints=[], research_content=None
    )
    # frontmatter_yaml の finding は出さない（document モードの仕様）。
    assert "frontmatter_yaml" not in _names(findings)


def test_document_mode_survives_malformed_frontmatter_by_falling_back_to_full_content():
    draft = '---\ntitle: "unterminated\n---\n弱い表現かもしれない。'
    findings, _ = run_checks(
        draft, mode="document", article_type="general", constraints=[], research_content=None
    )
    assert "frontmatter_yaml" not in _names(findings)
    weak = _find(findings, "weak_expressions")
    assert weak.passed is False


# ---------------------------------------------------------------------------
# 3. facts の値
# ---------------------------------------------------------------------------


def test_facts_has_fenced_block_true_for_backtick_fence():
    draft = "text\n```\ncode\n```\n"
    _, facts = run_checks(
        draft, mode="document", article_type="general", constraints=[], research_content=None
    )
    assert facts["has_fenced_block"] is True
    assert facts["contains_triple_backtick"] is True


def test_facts_has_fenced_block_true_for_tilde_fence_without_triple_backtick():
    draft = "text\n~~~\ncode\n~~~\n"
    _, facts = run_checks(
        draft, mode="document", article_type="general", constraints=[], research_content=None
    )
    assert facts["has_fenced_block"] is True
    assert facts["contains_triple_backtick"] is False


def test_facts_has_fenced_block_false_without_any_fence():
    draft = "ただの文章です。"
    _, facts = run_checks(
        draft, mode="document", article_type="general", constraints=[], research_content=None
    )
    assert facts["has_fenced_block"] is False
    assert facts["contains_triple_backtick"] is False


def test_facts_prose_runes_matches_manual_extraction():
    draft = "---\ntitle: X\n---\nこれは本文です。"
    _, facts = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    _, body = parse_frontmatter(draft)
    assert facts["prose_runes"] == count_prose_runes(extract_prose(body))


def test_facts_prose_runes_falls_back_to_full_content_when_frontmatter_parse_fails():
    """設計判断のテスト（wlq/runner.py モジュール docstring 参照）: article モードで
    frontmatter パースが失敗した場合、prose_runes は content 全体（フォールバック）
    から計算される。
    """
    draft = '---\ntitle: "unterminated\n---\nこれは本文です。'
    _, facts = run_checks(
        draft, mode="article", article_type="general", constraints=[], research_content=None
    )
    assert facts["prose_runes"] == count_prose_runes(extract_prose(draft))


def test_facts_article_type_echoes_resolved_value():
    draft = "本文"
    _, facts = run_checks(
        draft, mode="document", article_type="impl", constraints=[], research_content=None
    )
    assert facts["article_type"] == "impl"


def test_unknown_mode_raises_value_error():
    with pytest.raises(ValueError):
        run_checks(
            "text", mode="blog", article_type="general", constraints=[], research_content=None
        )
