# ported from: internal/infrastructure/quality/checker_ai_style.go,
#              internal/infrastructure/quality/checker_code.go:265-294 @ autopostd 20c740b
"""AI 生成に特有の文体・構造パターンの機械チェック（頻度系）。

textlint-rule-preset-ai-writing の検出パターンを移植し、箇条書きの「**太字**: 」濫用・
見出し/箇条書き先頭の絵文字マーカー・誇大表現・文末表現の連続/偏り・対比構文や
定型フレーズ・否定先行ムーブの頻度・長すぎるコード行を warning として検出する。
全て合否には影響しない（severity="warning"）。

対象範囲の扱い（チェックごとに異なるため注意）:
- check_bold_colon_list / check_emoji_markers: extract_prose 前の body を行単位で
  判定し、fenced code block 内部（フェンス行含む）は数えない。
- check_code_line_length: 各 fenced code block の内部行（フェンス行を除く）を対象に
  行の長さ（文字数）を計測する。
- check_hype_expressions / check_sentence_ending_run / check_sentence_ending_variety /
  check_rhetorical_contrast_freq / check_negation_first_freq / check_cliche_phrases は
  prose（extract_prose 済み。fenced code block は空行に置き換わっている）に対して
  判定するため、呼び出し側が extract_prose を通した文字列を渡すことを前提とする。
"""
import regex

from . import config
from .fences import parse_fenced_code_blocks
from .model import Finding, check_fail, check_pass
from .prose import split_sentences

_NAME_BOLD_COLON_LIST = "bold_colon_list"
_NAME_EMOJI_MARKERS = "emoji_markers"
_NAME_HYPE_EXPRESSIONS = "hype_expressions"
_NAME_CODE_LINE_LENGTH = "code_line_length"
_NAME_SENTENCE_ENDING_RUN = "sentence_ending_run"
_NAME_SENTENCE_ENDING_VARIETY = "sentence_ending_variety"
_NAME_RHETORICAL_CONTRAST_FREQ = "rhetorical_contrast_freq"
_NAME_NEGATION_FIRST_FREQ = "negation_first_freq"
_NAME_CLICHE_PHRASES = "cliche_phrases"

# boldColonRe（checker_ai_style.go:35）の移植。箇条書きの「**太字**: 説明」プレフィックス
# （行頭 -/*/+ の直後、半角/全角コロン）を検出する。
_BOLD_COLON_RE = regex.compile(r"^\s*[-*+]\s+\*\*[^*]+\*\*\s*[:：]")

# emojiMarkerRe（checker_ai_style.go:40）の移植。箇条書き（-/*/+）または見出し
# （#〜######）の先頭に置かれた絵文字マーカーを検出する。主要な絵文字ブロック
# （矢印・記号・装飾記号・補助シンボル・異体字セレクタ）を列挙する。
_EMOJI_MARKER_RE = regex.compile(
    r"^\s*(?:[-*+]\s+|#{1,6}\s+)"
    r"[←-⇿⌀-➿⬀-⯿\U0001F000-\U0001FAFF️]"
)

# hypeRes（checker_ai_style.go:45-49）の移植。誇大表現を絶対性・抽象性・予言性の
# 3 カテゴリで検出する。
_HYPE_RES = [
    regex.compile(r"革命的|画期的|劇的に|圧倒的|究極の|完璧な|完全に解決"),  # 絶対性
    regex.compile(r"ゲームチェンジャー|魔法のよう|銀の弾丸|無限の可能性|次元が違う"),  # 抽象性
    regex.compile(r"未来を変える|世界を変える|時代が変わる|もう戻れない"),  # 予言性
]

# sentenceEndingCandidates（checker_ai_style.go:54-63）の移植。文末からの最長一致判定に
# 使うため、この順序を変えないこと。「です」と「ます」は別表現として扱う。
_SENTENCE_ENDING_CANDIDATES = [
    "でしょう",  # 4 rune
    "ました",  # 3 rune
    "でした",  # 3 rune
    "ません",  # 3 rune
    "である",  # 3 rune
    "です",  # 2 rune
    "ます",  # 2 rune
    "だ",  # 1 rune
]

# rhetoricalContrastPhrase（checker_ai_style.go:66）の移植。
_RHETORICAL_CONTRAST_PHRASE = "ではなく"


def _first_runes(s: str, n: int) -> str:
    """s の先頭 n rune を返す。rune 数が n 以下なら s をそのまま返す（firstRunes の移植）。"""
    if len(s) <= n:
        return s
    return s[:n]


def _fenced_code_line_set(lines: list[str]) -> set[int]:
    """lines のうち fenced code block 内部（フェンス行を含む）の行 index を集合で返す
    （fencedCodeLineSet の移植）。body の行単位チェックがコード例を除外するために使う。
    """
    in_code: set[int] = set()
    for b in parse_fenced_code_blocks(lines):
        for i in range(b.start_line, min(b.end_line, len(lines) - 1) + 1):
            in_code.add(i)
    return in_code


def check_bold_colon_list(
    body: str, *, max_count: int = config.BOLD_COLON_LIST_MAX
) -> Finding:
    """「- **太字**: 」形式の箇条書きが max_count を超えた場合に warning とする
    （checkBoldColonList の移植）。fenced code block 内部の行は数えない。
    """
    lines = body.split("\n")
    in_code = _fenced_code_line_set(lines)

    count = 0
    for i, line in enumerate(lines):
        if i in in_code:
            continue
        if _BOLD_COLON_RE.match(line):
            count += 1
    if count <= max_count:
        return check_pass(
            _NAME_BOLD_COLON_LIST,
            f"bold-colon list items {count} within limit {max_count}",
            "warning",
        )
    detail = f"{count} bold-colon list items exceed limit {max_count}"
    return check_fail(
        _NAME_BOLD_COLON_LIST,
        detail,
        "「- **項目**: 説明」形式の強調ラベル箇条書きが多すぎます。"
        "地の文で説明する、通常の箇条書きにする、表にまとめる等で機械的な列挙を減らしてください",
        "warning",
    )


def check_emoji_markers(body: str) -> Finding:
    """箇条書き・見出しの先頭に置かれた絵文字マーカーを warning とする（1 件でも fail）
    （checkEmojiMarkers の移植）。fenced code block 内部の行は数えない。
    本文中の絵文字は対象外。
    """
    lines = body.split("\n")
    in_code = _fenced_code_line_set(lines)

    offenders = []
    for i, line in enumerate(lines):
        if i in in_code:
            continue
        if _EMOJI_MARKER_RE.match(line):
            offenders.append(f"line {i + 1}: {line.strip()}")
    if not offenders:
        return check_pass(
            _NAME_EMOJI_MARKERS, "no emoji markers on list/heading prefixes", "warning"
        )
    detail = (
        f"{len(offenders)} emoji marker(s) on list/heading prefixes: "
        f"{' / '.join(offenders)}"
    )
    return check_fail(
        _NAME_EMOJI_MARKERS,
        detail,
        "箇条書きや見出しの先頭に絵文字（✅💡⚠ 等）を使わないでください。"
        "強調は文章と見出し構造で行い、絵文字マーカーは削除してください",
        "warning",
    )


def check_hype_expressions(prose: str) -> Finding:
    """誇大表現（_HYPE_RES）の検出を warning とする（1 件でも fail）
    （checkHypeExpressions の移植）。見出し行を誤検知しないよう、prose を直接
    スキャンせず split_sentences(prose)（見出し行を除外する）の文単位でスキャンする。
    detail は検出語を重複なく列挙する。
    """
    sentences = split_sentences(prose)
    found = []
    seen: set[str] = set()
    for pattern in _HYPE_RES:
        for s in sentences:
            for m in pattern.findall(s):
                if m in seen:
                    continue
                seen.add(m)
                found.append(m)
    if not found:
        return check_pass(_NAME_HYPE_EXPRESSIONS, "no hype expressions found", "warning")
    detail = f"hype expressions found: {', '.join(found)}"
    return check_fail(
        _NAME_HYPE_EXPRESSIONS,
        detail,
        "誇大・煽り表現（革命的/ゲームチェンジャー/完全に解決 等）が使われています。"
        "効果は計測値や具体的な事実で示し、大げさな形容は削除してください",
        "warning",
    )


def _sentence_ending(s: str) -> tuple[str, bool]:
    """文 s の末尾（終止符 。！？ を除く）から _SENTENCE_ENDING_CANDIDATES に最長一致する
    文末表現を返す（sentenceEnding の移植）。どの候補にもマッチしない場合は ok=False を
    返し、呼び出し側はこれを「連続カウントのリセット」として扱う。
    """
    trimmed = s.rstrip("。！？")
    for cand in _SENTENCE_ENDING_CANDIDATES:
        if trimmed.endswith(cand):
            return cand, True
    return "", False


def check_sentence_ending_run(
    prose: str, *, run_max: int = config.SENTENCE_ENDING_RUN_MAX
) -> Finding:
    """同一文末表現（_sentence_ending で正規化）が run_max を超えて連続した場合に
    warning とする（checkSentenceEndingRun の移植。軸 d: リズム均質性）。「です」と
    「ます」は別表現として扱うため、両者が交互に現れる分には連続とみなさない。
    detail には最初に閾値超過した連続箇所のみを報告する。
    """
    sentences = split_sentences(prose)

    runs: list[dict] = []
    cur: dict | None = None
    for s in sentences:
        ending, ok = _sentence_ending(s)
        if not ok:
            cur = None  # どの文末表現にもマッチしない文は連続カウントをリセットする
            continue
        if cur is not None and cur["ending"] == ending:
            cur["count"] += 1
            continue
        cur = {"ending": ending, "count": 1, "first": s}
        runs.append(cur)

    for r in runs:
        if r["count"] > run_max:
            # 位置表示は先頭 30 rune。切り詰めたときだけ省略記号を付ける。
            pos = _first_runes(r["first"], 30)
            if pos != r["first"]:
                pos += "…"
            detail = f"『{r['ending']}』が{r['count']}文連続（位置: {pos}）"
            return check_fail(
                _NAME_SENTENCE_ENDING_RUN,
                detail,
                "文末に変化をつける（体言止めは使わない）",
                "warning",
            )
    return check_pass(
        _NAME_SENTENCE_ENDING_RUN,
        f"no sentence ending repeats more than {run_max} times in a row",
        "warning",
    )


def check_rhetorical_contrast_freq(
    prose: str, *, max_count: int = config.RHETORICAL_CONTRAST_MAX
) -> Finding:
    """本文中の「ではなく」の出現数が max_count を超えた場合に warning とする
    （checkRhetoricalContrastFreq の移植。軸 a: 定型レトリック）。禁止ではなく頻度制限
    のため、対比構文そのものは一定数まで許容する。
    """
    count = prose.count(_RHETORICAL_CONTRAST_PHRASE)
    if count <= max_count:
        return check_pass(
            _NAME_RHETORICAL_CONTRAST_FREQ,
            f"「{_RHETORICAL_CONTRAST_PHRASE}」 {count} occurrence(s) within limit {max_count}",
            "warning",
        )
    detail = (
        f"「{_RHETORICAL_CONTRAST_PHRASE}」 {count} occurrence(s) exceed limit {max_count}"
    )
    return check_fail(
        _NAME_RHETORICAL_CONTRAST_FREQ,
        detail,
        "対比構文を減らし、肯定形で直接述べる",
        "warning",
    )


def check_cliche_phrases(
    prose: str,
    *,
    phrases: list[str] = config.CLICHE_PHRASES,
    max_total: int = config.CLICHE_PHRASES_MAX,
) -> Finding:
    """phrases 辞書の合計出現数が max_total を超えた場合に warning とする
    （checkClichePhrases の移植。軸 a: 定型レトリック）。detail にはフレーズ別の
    内訳（例: が重要です=3, がポイントです=1）を、出現したフレーズのみ列挙する。
    """
    breakdown = []
    total = 0
    for phrase in phrases:
        if not phrase:
            continue
        n = prose.count(phrase)
        if n == 0:
            continue
        total += n
        breakdown.append(f"{phrase}={n}")
    if total <= max_total:
        return check_pass(
            _NAME_CLICHE_PHRASES,
            f"cliche phrase occurrences {total} within limit {max_total}",
            "warning",
        )
    detail = (
        f"{total} cliche phrase occurrence(s) exceed limit {max_total}: "
        f"{', '.join(breakdown)}"
    )
    return check_fail(
        _NAME_CLICHE_PHRASES,
        detail,
        "同じ定型フレーズを繰り返さず、具体的な内容や別の言い回しで言い換える",
        "warning",
    )


def _count_phrases_longest_first(
    prose: str, phrases: list[str]
) -> tuple[int, list[str]]:
    """phrases を rune 長の降順で消費しながら数える（countPhrasesLongestFirst の移植）。
    「わけではありません」と「ではありません」のような包含関係の二重計上を防ぐため、
    マッチ済み箇所は NUL 文字に置換してから次のパターンを数える。
    """
    sorted_phrases = sorted(phrases, key=lambda p: -len(p))
    rest = prose
    counts: dict[str, int] = {}
    total = 0
    for p in sorted_phrases:
        if not p:
            continue
        n = rest.count(p)
        if n == 0:
            continue
        total += n
        counts[p] = n
        rest = rest.replace(p, "\x00")
    breakdown = []
    for p in phrases:
        n = counts.get(p, 0)
        if n > 0:
            breakdown.append(f"{p}={n}")
    return total, breakdown


def check_negation_first_freq(
    prose: str,
    *,
    patterns: list[str] = config.RHETORICAL_NEGATION_PATTERNS,
    max_total: int = config.RHETORICAL_NEGATION_MAX,
) -> Finding:
    """否定先行ムーブ（誤解の否定から入るレトリック）の「ではなく」以外の変異形の
    合計出現数が max_total を超えた場合に warning とする（checkNegationFirstFreq の
    移植。軸 a の変異形対策。「ではなく」自体は check_rhetorical_contrast_freq が数える）。
    """
    total, breakdown = _count_phrases_longest_first(prose, patterns)
    if total <= max_total:
        return check_pass(
            _NAME_NEGATION_FIRST_FREQ,
            f"negation-first phrase occurrences {total} within limit {max_total}",
            "warning",
        )
    detail = (
        f"{total} negation-first phrase occurrence(s) exceed limit {max_total}: "
        f"{', '.join(breakdown)}"
    )
    return check_fail(
        _NAME_NEGATION_FIRST_FREQ,
        detail,
        "「〜ではありません」「単なる〜ではない」のような誤解の否定から入る段落が多すぎます。"
        "一部を、肯定形で直接定義・説明する形に書き換えてください(すべて排除する必要はありません)",
        "warning",
    )


def check_sentence_ending_variety(
    prose: str,
    *,
    max_percent: int = config.DESU_MASU_RATIO_MAX_PERCENT,
    min_sentences: int = config.DESU_MASU_RATIO_MIN_SENTENCES,
) -> Finding:
    """prose 文のうち「です」「ます」で終わる文の比率が max_percent を超えた場合に
    warning とする（checkSentenceEndingVariety の移植。軸 d: リズム均質性）。
    sentence_ending_run（連続規制）と対になる総量規制。文数が min_sentences 未満の
    場合は比率が不安定なためスキップする。
    """
    sentences = split_sentences(prose)
    if len(sentences) < min_sentences:
        return check_pass(
            _NAME_SENTENCE_ENDING_VARIETY,
            f"skip: only {len(sentences)} sentences (< {min_sentences})",
            "warning",
        )
    desu_masu = 0
    for s in sentences:
        ending, ok = _sentence_ending(s)
        if ok and (ending == "です" or ending == "ます"):
            desu_masu += 1
    ratio = desu_masu * 100 // len(sentences)
    if ratio <= max_percent:
        return check_pass(
            _NAME_SENTENCE_ENDING_VARIETY,
            f"desu/masu ending ratio {ratio}% within limit {max_percent}%",
            "warning",
        )
    detail = (
        f"desu/masu ending ratio {ratio}% ({desu_masu}/{len(sentences)} sentences) "
        f"exceeds limit {max_percent}%"
    )
    return check_fail(
        _NAME_SENTENCE_ENDING_VARIETY,
        detail,
        "文末が「です」「ます」に偏っています。疑問形・「〜ません」「〜でした」「〜でしょう」・"
        "かぎ括弧止めなどを織り交ぜて文末に変化をつけてください(体言止めは使わない)",
        "warning",
    )


def check_code_line_length(
    body: str, *, max_len: int = config.CODE_LINE_MAX_LEN
) -> Finding:
    """各 fenced code block の内部行（フェンス行を除く start_line+1 .. end_line-1）に
    ついて、行の長さが max_len を超えるものを warning とする（checkCodeLineLength の
    移植。ported from checker_code.go:270）。横スクロールを誘発する長いコード行を検出
    する目的。コードブロックが無い場合は skip=pass。detail には超過行の位置
    （コードブロック開始行番号・行番号）と実測文字数を列挙する。
    """
    lines = body.split("\n")
    blocks = parse_fenced_code_blocks(lines)
    if not blocks:
        return check_pass(_NAME_CODE_LINE_LENGTH, "skip: no code blocks", "warning")

    offenders = []
    for b in blocks:
        for i in range(b.start_line + 1, min(b.end_line - 1, len(lines) - 1) + 1):
            n = len(lines[i])
            if n > max_len:
                offenders.append(
                    f"line {i + 1} in code block at line {b.start_line + 1} "
                    f"({n} runes): {_first_runes(lines[i], 40)}"
                )
    if not offenders:
        return check_pass(
            _NAME_CODE_LINE_LENGTH, f"no code line exceeds {max_len} runes", "warning"
        )
    detail = f"{len(offenders)} code line(s) exceed {max_len} runes: {' / '.join(offenders)}"
    return check_fail(
        _NAME_CODE_LINE_LENGTH,
        detail,
        f"コード行が長すぎます（{max_len}文字超）。"
        "変数への分割・改行・折り返しで 1 行を短くし、横スクロールを避けてください",
        "warning",
    )
