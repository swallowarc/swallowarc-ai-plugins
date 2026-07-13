# ported from: internal/infrastructure/quality/checker_ai_style_structure.go @ autopostd 20c740b
"""AI 文体スメルの構造・頻度系チェック(docs/ai-writing-smells.md phase6)。

2026-07-08 公開の 2 記事(ai-shifted-sre-toil-2026 / npm-pypi-supply-chain-attacks-2026-h1)で
観測した、既存チェック(sentence_ending_run / sentence_ending_variety 等)をすり抜ける
「静かな AI くささ」への対策:

- paragraph_uniformity(軸 d): 段落の文数が揃いすぎるスライド調
  (実測: 2 文段落が地の文段落の 85%・最長 15 連続)
- hard_line_breaks(軸 d): 1 文ごとの強制改行(行末スペース 2 個 = <br>)による詩型リズム
- first_person_freq(軸 e): 「私は〜と考えます」型の一人称意見スタンプの乱発(実測 16 回/記事)
- reason_template_freq(軸 e): 「主張。理由は〜ためです。」型の理由構文テンプレ(実測 18 回/記事)

すべて warning(合否には影響しない)。

- _prose_paragraphs: prose(extract_prose 済み)を地の文の段落単位に分割し、各段落の
  結合テキストを返す(proseParagraphs の移植)。空行・見出し・表・箇条書き・番号リスト・
  引用の行は段落の区切りとして扱い、段落には含めない。
- check_paragraph_uniformity: 地の文段落の文数の均質性を検査する。2 つの条件のどちらかで
  warning: 連続規制(同一文数の段落が run_max を超えて連続。見出しや箇条書きを挟んでも
  読者の読むリズムは連続するためリセットしない)と、総量規制(段落数が min_paragraphs 以上
  のとき、最頻の文数が全段落の max_percent% を超える)。
- check_hard_line_breaks: 段落内の行継ぎ目(同一段落内で行が次の行へ続く箇所)のうち、
  行末スペース 2 個の強制改行(markdown の <br>)が占める割合を検査する。継ぎ目が
  min_joints 未満の記事は判定をスキップする。
- check_first_person_freq / check_reason_template_freq: 一人称の意見マーカー
  (「私は」「筆者は」等)・理由提示の定型構文(「理由は」「〜ためです」等)の合計出現数が
  それぞれ max_total を超えた場合に warning とする。「長いパターン優先で消費」ロジック
  (_count_phrases_longest_first)は checks_ai_style.py(Task 6)のものを再利用する。
"""
import regex

from . import config
from .checks_ai_style import _count_phrases_longest_first, _first_runes
from .mdscan import ANY_HEADING_RE
from .model import Finding, check_fail, check_pass
from .prose import split_sentences

_NAME_PARAGRAPH_UNIFORMITY = "paragraph_uniformity"
_NAME_HARD_LINE_BREAKS = "hard_line_breaks"
_NAME_FIRST_PERSON_FREQ = "first_person_freq"
_NAME_REASON_TEMPLATE_FREQ = "reason_template_freq"

# paragraphBreakRe (checker_ai_style_structure.go:23): 段落の一部として数えない行
# (箇条書き・番号リスト・引用)を判定する。見出し(ANY_HEADING_RE)・表(|)・空行と
# 合わせて段落の区切りとして扱う。
_PARAGRAPH_BREAK_RE = regex.compile(r"^([-*+]\s|\d+\.\s|>)")


def _is_prose_paragraph_line(trimmed: str) -> bool:
    """trimmed(strip 済み)が地の文段落を構成する行かを返す
    (isProseParagraphLine の移植)。
    """
    return (
        bool(trimmed)
        and not ANY_HEADING_RE.match(trimmed)
        and not trimmed.startswith("|")
        and not _PARAGRAPH_BREAK_RE.match(trimmed)
    )


def _prose_paragraphs(prose: str) -> list[str]:
    """prose(extract_prose 済み)を地の文の段落単位に分割し、各段落の結合テキストを
    返す(proseParagraphs の移植)。空行・見出し・表・箇条書き・番号リスト・引用の行は
    段落の区切りとして扱い、段落には含めない。
    """
    paras: list[str] = []
    cur: list[str] = []

    def flush() -> None:
        nonlocal cur
        if cur:
            paras.append("".join(cur))
            cur = []

    for line in prose.split("\n"):
        t = line.strip()
        if not _is_prose_paragraph_line(t):
            flush()
            continue
        cur.append(t)
    flush()
    return paras


def check_paragraph_uniformity(
    prose: str,
    *,
    run_max: int = config.PARAGRAPH_LENGTH_RUN_MAX,
    max_percent: int = config.PARAGRAPH_UNIFORMITY_MAX_PERCENT,
    min_paragraphs: int = config.PARAGRAPH_UNIFORMITY_MIN_PARAGRAPHS,
) -> Finding:
    """地の文段落の文数の均質性を検査する(checkParagraphUniformity の移植。
    軸 d: リズム均質性の段落版)。2 つの条件のどちらかで warning:

    - 連続規制: 同一文数の段落が run_max を超えて連続する。見出しや箇条書きを
      挟んでも読者の読むリズムは連続するため、区切りではリセットしない。
    - 総量規制: 段落数が min_paragraphs 以上のとき、最頻の文数が全段落の
      max_percent% を超える。
    """
    paras = _prose_paragraphs(prose)

    counts: list[int] = []
    texts: list[str] = []
    for p in paras:
        n = len(split_sentences(p))
        if n > 0:
            counts.append(n)
            texts.append(p)

    # 連続規制
    run, prev, run_start = 0, -1, 0
    for i, n in enumerate(counts):
        if n == prev:
            run += 1
        else:
            run, prev, run_start = 1, n, i
        if run > run_max:
            pos = _first_runes(texts[run_start], 20)
            detail = f"{n}文の段落が{run}個連続（上限 {run_max}、先頭: {pos}…）"
            return check_fail(
                _NAME_PARAGRAPH_UNIFORMITY,
                detail,
                "同じ文数の段落が続きすぎています。関連する文を 1 つの段落にまとめる・"
                "長い説明は 3〜4 文の段落に膨らませるなど、段落の長さに変化をつけてください",
                "warning",
            )

    # 総量規制
    if len(counts) >= min_paragraphs:
        freq: dict[int, int] = {}
        for n in counts:
            freq[n] = freq.get(n, 0) + 1
        dom_n, dom_count = 0, 0
        for n, f in freq.items():
            if f > dom_count:
                dom_n, dom_count = n, f
        ratio = dom_count * 100 // len(counts)
        if ratio > max_percent:
            detail = (
                f"{dom_n}文段落が全{len(counts)}段落中{dom_count}個"
                f"（{ratio}%）で上限 {max_percent}% を超過"
            )
            return check_fail(
                _NAME_PARAGRAPH_UNIFORMITY,
                detail,
                "記事全体で段落の文数が均質です。1 文で言い切る段落や 3〜4 文で論を運ぶ"
                "段落を織り交ぜ、スライドの箇条書きのような等間隔リズムを崩してください",
                "warning",
            )

    return check_pass(
        _NAME_PARAGRAPH_UNIFORMITY,
        f"paragraph lengths varied ({len(counts)} paragraphs, run limit {run_max}, "
        f"ratio limit {max_percent}%)",
        "warning",
    )


def check_hard_line_breaks(
    prose: str,
    *,
    max_percent: int = config.HARD_LINE_BREAK_MAX_PERCENT,
    min_joints: int = config.HARD_LINE_BREAK_MIN_JOINTS,
) -> Finding:
    """段落内の行継ぎ目(同一段落内で行が次の行へ続く箇所)のうち、行末スペース 2 個の
    強制改行(markdown の <br>)が占める割合を検査する(checkHardLineBreaks の移植。
    軸 d)。1 文ごとに強制改行を入れる詩型の生成癖は、段落を文の羅列に見せる。
    継ぎ目が min_joints 未満の記事は判定をスキップする。
    """
    joints, hard = 0, 0
    prev_is_prose, prev_hard = False, False
    for line in prose.split("\n"):
        t = line.strip()
        is_prose = _is_prose_paragraph_line(t)
        if is_prose and prev_is_prose:
            joints += 1
            if prev_hard:
                hard += 1
        prev_is_prose = is_prose
        prev_hard = line.endswith("  ")
    if joints < min_joints:
        return check_pass(
            _NAME_HARD_LINE_BREAKS,
            f"skip: only {joints} intra-paragraph joints (< {min_joints})",
            "warning",
        )
    pct = hard * 100 // joints
    if pct <= max_percent:
        return check_pass(
            _NAME_HARD_LINE_BREAKS,
            f"hard line break ratio {pct}% ({hard}/{joints} joints) within limit {max_percent}%",
            "warning",
        )
    detail = f"hard line break ratio {pct}% ({hard}/{joints} joints) exceeds limit {max_percent}%"
    return check_fail(
        _NAME_HARD_LINE_BREAKS,
        detail,
        "段落内のほぼ全ての文が行末スペース 2 個の強制改行で区切られています。"
        "段落内の文は改行せずに続けて書き、改行は段落の区切り（空行）でのみ行ってください",
        "warning",
    )


def check_first_person_freq(
    prose: str,
    *,
    patterns: list[str] = config.FIRST_PERSON_PATTERNS,
    max_total: int = config.FIRST_PERSON_MAX,
) -> Finding:
    """一人称の意見マーカー(「私は」「筆者は」等)の合計出現数が max_total を超えた
    場合に warning とする(checkFirstPersonFreq の移植。軸 e: 意見ルールのスタンプ化
    対策)。意見の表明そのものは必須要件のため、禁止ではなく頻度制限に留める。
    """
    total, breakdown = _count_phrases_longest_first(prose, patterns)
    if total <= max_total:
        return check_pass(
            _NAME_FIRST_PERSON_FREQ,
            f"first-person marker occurrences {total} within limit {max_total}",
            "warning",
        )
    detail = (
        f"{total} first-person marker occurrence(s) exceed limit {max_total}: "
        f"{', '.join(breakdown)}"
    )
    return check_fail(
        _NAME_FIRST_PERSON_FREQ,
        detail,
        "「私は〜と考えます」のような一人称の意見マーカーが多すぎます。"
        "主張自体は維持したまま、一部を地の文の直接的な断定や根拠を主語にした文に書き換え、"
        "スタンプ的な前置きを減らしてください",
        "warning",
    )


def check_reason_template_freq(
    prose: str,
    *,
    patterns: list[str] = config.REASON_TEMPLATE_PATTERNS,
    max_total: int = config.REASON_TEMPLATE_MAX,
) -> Finding:
    """理由提示の定型構文(「理由は」「〜ためです」等)の合計出現数が max_total を超えた
    場合に warning とする(checkReasonTemplateFreq の移植。軸 e: 「主張文+理由文」テンプレ
    対策)。理由を添えること自体は必須要件のため、禁止ではなく頻度制限に留める。
    """
    total, breakdown = _count_phrases_longest_first(prose, patterns)
    if total <= max_total:
        return check_pass(
            _NAME_REASON_TEMPLATE_FREQ,
            f"reason template occurrences {total} within limit {max_total}",
            "warning",
        )
    detail = (
        f"{total} reason template occurrence(s) exceed limit {max_total}: "
        f"{', '.join(breakdown)}"
    )
    return check_fail(
        _NAME_REASON_TEMPLATE_FREQ,
        detail,
        "「主張。理由は〜ためです。」の理由提示構文が繰り返されています。"
        "理由を主張と同じ文に織り込む・データや事例で理由を示すなど、"
        "提示の形に変化をつけてください（理由を削らないこと）",
        "warning",
    )
