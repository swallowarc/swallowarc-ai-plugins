# ported from: internal/infrastructure/quality/checker_code.go:104-115 (codeCheckPass/codeCheckFail),
#              internal/infrastructure/quality/checker_code.go:117-134 (checkCodeLanguageTag),
#              internal/infrastructure/quality/checker_code.go:139-197 (kindLabelNormalizer/
#              validKindLabels/isValidKindLabel/previousNonBlankLine/checkCodeKindLabel),
#              internal/infrastructure/quality/checker_code.go:201-262 (nextNonBlankLine/
#              checkMermaidContext)
#              @ autopostd 20c740b
"""コード・図チェック 3 関数（code_language_tag / code_kind_label / mermaid_context）。

- check_code_language_tag: 全 fenced code block の開始フェンスに言語タグがある
  ことを検査する（checkCodeLanguageTag の移植。ported from checker_code.go:117）。
  全記事タイプ対象。閉じフェンスに言語タグは不要。detail の行番号は body
  （frontmatter 除去後）の先頭からの 1 始まり。コードブロックが無い場合は
  skip=pass。

- check_code_kind_label: impl 記事タイプの各コードブロック（mermaid は除外）に
  ついて、開始フェンス直前の非空行がコード種別ラベル（「（コード種別: 実行可能）」
  「（コード種別: 疑似コード）」「（コード種別: 概念例）」のいずれか。全角/半角の
  括弧・コロン・半角/全角空白・タブの表記ゆれは吸収する）であることを検査する
  （checkCodeKindLabel の移植。ported from checker_code.go:169）。impl 以外の記事
  タイプ、および対象（mermaid 以外）のコードブロックが無い場合は skip=pass。

- check_mermaid_context: 各 mermaid ブロックの直前・直後に「本文テキスト」
  （見出し・フェンスコードブロック以外の非空行）が存在することを検査する
  （checkMermaidContext の移植。ported from checker_code.go:213）。全記事タイプ
  対象。mermaid ブロックが無い場合は skip=pass。

3 関数とも severity="error"（codeCheckPass/codeCheckFail が常に
domain.CheckSeverityError を使うため）。

parseFencedCodeBlocks 系（codeBlock 構造体・parseFenceOpening・isFenceClosing・
firstInfoToken）は Task 3 で wlq/fences.py に CodeBlock / parse_fenced_code_blocks
として移植済みのためここでは扱わない。checkCodeLineLength（checker_code.go:270）
は Task 6 で wlq/checks_ai_style.py に check_code_line_length として移植済みの
ため対象外。
"""
from .fences import parse_fenced_code_blocks
from .mdscan import ANY_HEADING_RE
from .model import Finding, check_fail, check_pass

_NAME_CODE_LANGUAGE_TAG = "code_language_tag"
_NAME_CODE_KIND_LABEL = "code_kind_label"
_NAME_MERMAID_CONTEXT = "mermaid_context"
_SEVERITY_ERROR = "error"


def check_code_language_tag(body: str) -> Finding:
    """checkCodeLanguageTag（checker_code.go:117）の移植。"""
    blocks = parse_fenced_code_blocks(body.split("\n"))
    if not blocks:
        return check_pass(_NAME_CODE_LANGUAGE_TAG, "skip: no code blocks", _SEVERITY_ERROR)

    missing = [f"line {b.start_line + 1}" for b in blocks if not b.lang]
    if missing:
        return check_fail(
            _NAME_CODE_LANGUAGE_TAG,
            f"code blocks without language tag: {', '.join(missing)}",
            "全てのコードブロックの開始フェンスに言語タグを付けてください"
            "（例: ```go、```mermaid。プレーンテキストは ```text）",
            _SEVERITY_ERROR,
        )
    return check_pass(
        _NAME_CODE_LANGUAGE_TAG, "all code blocks have language tags", _SEVERITY_ERROR
    )


# kindLabelNormalizer（checker_code.go:139）の移植。コード種別ラベルの表記ゆれ
# （全角/半角の括弧・コロン、半角/全角空白・タブ）を単一パスで吸収する正規化。
# strings.NewReplacer は各文字位置に対して非重複・単一パスで置換を適用するため、
# 単一文字 -> 単一文字/削除のみからなるこのテーブルは str.translate で等価に表現できる。
_KIND_LABEL_NORMALIZE_TABLE = str.maketrans(
    {"（": "(", "）": ")", "：": ":", "　": None, " ": None, "\t": None}
)

# validKindLabels（checker_code.go:145）の移植。正規化後の有効なコード種別ラベル。
_VALID_KIND_LABELS = frozenset(
    {"(コード種別:実行可能)", "(コード種別:疑似コード)", "(コード種別:概念例)"}
)


def _is_valid_kind_label(line: str) -> bool:
    """isValidKindLabel（checker_code.go:151）の移植。"""
    return line.translate(_KIND_LABEL_NORMALIZE_TABLE) in _VALID_KIND_LABELS


def _previous_non_blank_line(lines: list[str], idx: int) -> int:
    """previousNonBlankLine（checker_code.go:157）の移植。idx より前で最も近い
    非空行の index を返す（無ければ -1）。
    """
    for i in range(idx - 1, -1, -1):
        if lines[i].strip() != "":
            return i
    return -1


def _go_quote(s: str) -> str:
    """Go の fmt "%q" による文字列の二重引用符付与を再現する（バックスラッシュと
    ダブルクォートのみエスケープ）。article_type は通常英数字の識別子であり、
    この範囲では checker_code.go の出力と一致する。
    """
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def check_code_kind_label(article_type: str, body: str) -> Finding:
    """checkCodeKindLabel（checker_code.go:169）の移植。"""
    if article_type != "impl":
        return check_pass(
            _NAME_CODE_KIND_LABEL,
            f"skip: article type {_go_quote(article_type)} does not require code kind labels",
            _SEVERITY_ERROR,
        )

    lines = body.split("\n")
    targets = [b for b in parse_fenced_code_blocks(lines) if b.lang.lower() != "mermaid"]
    if not targets:
        return check_pass(
            _NAME_CODE_KIND_LABEL, "skip: no non-mermaid code blocks", _SEVERITY_ERROR
        )

    missing = []
    for b in targets:
        idx = _previous_non_blank_line(lines, b.start_line)
        if idx < 0 or not _is_valid_kind_label(lines[idx]):
            missing.append(f"line {b.start_line + 1}")
    if missing:
        return check_fail(
            _NAME_CODE_KIND_LABEL,
            f"code blocks without kind label: {', '.join(missing)}",
            "impl 記事では Mermaid 以外の各コードブロックの直前の行に"
            "「（コード種別: 実行可能）」「（コード種別: 疑似コード）」"
            "「（コード種別: 概念例）」のいずれかのラベルを置いてください",
            _SEVERITY_ERROR,
        )
    return check_pass(_NAME_CODE_KIND_LABEL, "all code blocks have kind labels", _SEVERITY_ERROR)


def _next_non_blank_line(lines: list[str], idx: int) -> int:
    """nextNonBlankLine（checker_code.go:201）の移植。idx より後で最も近い非空行の
    index を返す（無ければ -1）。
    """
    for i in range(idx + 1, len(lines)):
        if lines[i].strip() != "":
            return i
    return -1


def check_mermaid_context(body: str) -> Finding:
    """checkMermaidContext（checker_code.go:213）の移植。"""
    lines = body.split("\n")
    blocks = parse_fenced_code_blocks(lines)

    mermaids = [b for b in blocks if b.lang.lower() == "mermaid"]
    if not mermaids:
        return check_pass(_NAME_MERMAID_CONTEXT, "skip: no mermaid blocks", _SEVERITY_ERROR)

    # フェンス行およびコードブロック内部の行は「本文テキスト」ではない
    non_text: set[int] = set()
    for b in blocks:
        for i in range(b.start_line, min(b.end_line, len(lines) - 1) + 1):
            non_text.add(i)

    def is_body_text(idx: int) -> bool:
        if idx < 0 or idx >= len(lines):
            return False
        if idx in non_text:
            return False
        trimmed = lines[idx].strip()
        if trimmed == "":
            return False
        return not ANY_HEADING_RE.match(trimmed)

    problems = []
    for m in mermaids:
        if not is_body_text(_previous_non_blank_line(lines, m.start_line)):
            problems.append(
                f"mermaid block at line {m.start_line + 1} lacks preceding body text"
            )
        if not is_body_text(_next_non_blank_line(lines, m.end_line)):
            problems.append(
                f"mermaid block at line {m.start_line + 1} lacks following body text"
            )

    if problems:
        return check_fail(
            _NAME_MERMAID_CONTEXT,
            "; ".join(problems),
            "各 Mermaid 図の直前に図の目的を、直後に図から読み取るべきポイントを"
            "本文の文章で書いてください（見出しやコードブロックは本文テキストとみなしません）",
            _SEVERITY_ERROR,
        )
    return check_pass(
        _NAME_MERMAID_CONTEXT, "all mermaid blocks have surrounding body text", _SEVERITY_ERROR
    )
