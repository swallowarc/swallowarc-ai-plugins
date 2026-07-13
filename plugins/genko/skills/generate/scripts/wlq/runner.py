# ported from: internal/infrastructure/quality/checker.go:264-326 (RuleBasedChecker.Check)
#              @ autopostd 20c740b
#              internal/domain/judge_aspects_diagram_code.go:10-18 (containsFencedBlock)
#              @ autopostd 20c740b
#              internal/domain/judge_aspects_readability.go:27
#              (strings.Contains(content, "```") -> facts.contains_triple_backtick)
#              @ autopostd 20c740b
"""Task 1〜11 の全チェック関数を本番 `RuleBasedChecker.Check`（checker.go:264-326）と
同一順序で束ねる runner。

`run_checks(draft_text, *, mode, article_type, constraints, research_content)` が
唯一の公開エントリで、(findings, facts) を返す。

## article モード

Go の `Check` をそのまま踏襲する:

1. `check_forbidden_words(content)`
2. `parse_frontmatter(content)` を一度だけ実行し、`FrontmatterError` を捕捉する。
3. `check_frontmatter_yaml(err)`
4. パース成功時のみ（Go の `if fmErr == nil` ブロック）: frontmatter 系・構造系・
   code/mermaid・body_length・可読性 4 件・AI 文体系 9 件・AI 文体構造系 4 件を
   Go の登録順のまま実行する。この区間の末尾に genko 独自の
   `check_progress_narration_freq`（Go に対応なし。checks_narration.py 参照）を
   1 件追加する。`check_series_consistency()` はこのブロック内
   （series==nil 分岐の定数のみ。Go の `checkSeriesConsistency(series, fm)` が
   同じ `if` 内にあることに対応）。
5. `check_required_sections(article_type, content)`（if ブロックの外。パース失敗時も実行）
6. `check_references(article_type, research_content, content)`（同上）
7. `check_series_navigation()`（同上。series==nil 分岐の定数）

## document モード（spec 由来の縮退セット。Go に対応する Check 経路は無い）

frontmatter は任意。content が "---" で始まる場合のみ `parse_frontmatter` を試み、
成功したら本文を分離する。失敗時・"---" で始まらない場合は content 全体を本文として
扱う（frontmatter_yaml の finding は出さない）。可読性・AI 文体系チェックのみを
article モードと同じ相対順序で実行し、`--research` 指定時（research_content is not
None）のみ `check_references` を追加する。blog 都合のチェック（frontmatter/title/
heading/code/body_length/required_sections/series）は一切実行しない。

## facts

`has_fenced_block` / `contains_triple_backtick` は draft の content 全体
（frontmatter 込み）に対して判定する（本番 `JudgeAspectsFor` が content を
そのまま受け取るのと同じ）。`prose_runes` は各モードの本文分離ロジックが
決定した「本文」（body）に対して `count_prose_runes(extract_prose(body))` を
計算する。

設計判断（Go に対応が無い箇所）: article モードで frontmatter のパースが失敗した
場合、Go の `parseFrontmatter` はエラー時に body として "" を返すが、これは
Check() 内で使われないため実質未定義である。`prose_runes` は Go に存在しない
本移植独自の fact であるため、document モードの「パース失敗時は content 全体を
本文として扱う」というフォールバックと挙動を統一し、article モードでも同様に
`content` をフォールバック値として採用する（空文字列より情報量が多く、
モード間で一貫した規則になるため）。
"""
from .checks_ai_style import (
    check_bold_colon_list,
    check_cliche_phrases,
    check_code_line_length,
    check_emoji_markers,
    check_hype_expressions,
    check_negation_first_freq,
    check_rhetorical_contrast_freq,
    check_sentence_ending_run,
    check_sentence_ending_variety,
)
from .checks_ai_style_structure import (
    check_first_person_freq,
    check_hard_line_breaks,
    check_paragraph_uniformity,
    check_reason_template_freq,
)
from .checks_code import check_code_kind_label, check_code_language_tag, check_mermaid_context
from .checks_narration import check_progress_narration_freq
from .checks_frontmatter import (
    check_description_quality,
    check_forbidden_words,
    check_frontmatter_values,
    check_frontmatter_yaml,
    check_tags_format,
)
from .checks_length import check_body_length
from .checks_readability import (
    check_kanji_run,
    check_sentence_commas,
    check_sentence_length,
    check_weak_expressions,
)
from .checks_references import check_references
from .checks_series import check_series_consistency, check_series_navigation
from .checks_structure import check_heading_structure, check_required_sections
from .checks_title import check_title_length
from .frontmatter import FrontmatterError, parse_frontmatter
from .model import Finding
from .prose import count_prose_runes, extract_prose

_MODES = ("article", "document")


def _contains_fenced_block(content: str) -> bool:
    """containsFencedBlock（domain/judge_aspects_diagram_code.go:10）の移植。

    trim 後に ``` または ~~~ で始まる行が 1 行でもあれば True（開始/閉じの
    厳密な区別はしない軽量判定）。
    """
    for line in content.split("\n"):
        trimmed = line.strip()
        if trimmed.startswith("```") or trimmed.startswith("~~~"):
            return True
    return False


def _run_prose_checks(prose: str, body: str) -> list[Finding]:
    """可読性・AI 文体系チェック（check_sentence_length 〜 check_reason_template_freq）を
    Go の Check() 登録順のまま実行する（article / document 両モード共通の区間）。

    prose 系チェックは extract_prose 済みの prose を、行単位・コードブロック系
    チェック（bold_colon_list / emoji_markers / code_line_length）は body を受け取る
    （checker.go:287-313 の引数対応と同一）。
    """
    findings: list[Finding] = []

    findings.extend(check_sentence_length(prose))
    findings.append(check_sentence_commas(prose))
    findings.append(check_kanji_run(prose))
    findings.append(check_weak_expressions(prose))

    findings.append(check_bold_colon_list(body))
    findings.append(check_emoji_markers(body))
    findings.append(check_hype_expressions(prose))
    findings.append(check_code_line_length(body))

    findings.append(check_sentence_ending_run(prose))
    findings.append(check_sentence_ending_variety(prose))
    findings.append(check_rhetorical_contrast_freq(prose))
    findings.append(check_negation_first_freq(prose))
    findings.append(check_cliche_phrases(prose))

    findings.append(check_paragraph_uniformity(prose))
    findings.append(check_hard_line_breaks(prose))
    findings.append(check_first_person_freq(prose))
    findings.append(check_reason_template_freq(prose))

    # genko 独自追加（Go の Check() に対応なし）: 進行実況の頻度チェック。
    # 詳細は wlq/checks_narration.py のモジュール docstring 参照。
    findings.append(check_progress_narration_freq(prose))

    return findings


def _run_article_checks(
    content: str,
    article_type: str,
    constraints: list[str],
    research_content: str | None,
) -> tuple[list[Finding], str]:
    findings: list[Finding] = []

    findings.append(check_forbidden_words(content))

    try:
        fm, body = parse_frontmatter(content)
        err: FrontmatterError | None = None
    except FrontmatterError as e:
        fm, body, err = None, content, e

    findings.append(check_frontmatter_yaml(err))

    if err is None:
        findings.append(check_frontmatter_values(fm))
        findings.append(check_description_quality(fm))
        findings.append(check_title_length(fm))
        findings.append(check_heading_structure(body))
        findings.append(check_tags_format(fm))
        findings.append(check_series_consistency())
        findings.append(check_code_language_tag(body))
        findings.append(check_code_kind_label(article_type, body))
        findings.append(check_mermaid_context(body))
        findings.append(check_body_length(constraints, body))

        prose = extract_prose(body)
        findings.extend(_run_prose_checks(prose, body))

    findings.append(check_required_sections(article_type, content))
    findings.extend(check_references(article_type, research_content, content))
    findings.append(check_series_navigation())

    return findings, body


def _run_document_checks(
    content: str,
    article_type: str,
    research_content: str | None,
) -> tuple[list[Finding], str]:
    findings: list[Finding] = []

    if content.startswith("---"):
        try:
            _, body = parse_frontmatter(content)
        except FrontmatterError:
            body = content
    else:
        body = content

    prose = extract_prose(body)
    findings.extend(_run_prose_checks(prose, body))

    if research_content is not None:
        findings.extend(check_references(article_type, research_content, content))

    return findings, body


def run_checks(
    draft_text: str,
    *,
    mode: str,
    article_type: str,
    constraints: list[str],
    research_content: str | None,
) -> tuple[list[Finding], dict]:
    """全チェックを本番 `Check` と同一順序で実行し、(findings, facts) を返す。

    mode は "article" | "document" のいずれか。それ以外は ValueError。
    """
    if mode == "article":
        findings, body = _run_article_checks(
            draft_text, article_type, constraints, research_content
        )
    elif mode == "document":
        findings, body = _run_document_checks(draft_text, article_type, research_content)
    else:
        raise ValueError(f"unknown mode: {mode!r} (must be one of {_MODES})")

    facts = {
        "article_type": article_type,
        "has_fenced_block": _contains_fenced_block(draft_text),
        "contains_triple_backtick": "```" in draft_text,
        "prose_runes": count_prose_runes(extract_prose(body)),
    }
    return findings, facts
