# ported from: internal/infrastructure/quality/checker_readability.go @ autopostd 20c740b
"""日本語可読性の機械チェック（phase4 #3）。

textlint-rule-preset-ja-technical-writing のデフォルト値を基準に、文長・読点数・
漢字連続・弱い表現を正規表現／文分割ベースで検査する。散文抽出（extract_prose）と
文分割（split_sentences）は prose.py の共通基盤（Task 4）を利用する。弱い表現・
感嘆符は既存 forbidden_words（error・部分一致）とは別枠の warning として扱う。

- check_sentence_length: 一文の長さを計測し、max_len 超（既定 error）と
  warn_len 超（既定 warning）の 2 件の Finding を返す。
- check_sentence_commas: 一文中の読点「、」が max_commas を超える文を warning とする。
- check_kanji_run: run_max+1 文字以上連続する漢字を warning とする。マッチ語が
  allowlist のいずれかの部分文字列に内包される場合は固有名詞として除外する。
- check_weak_expressions: 弱い表現・感嘆符（半角/全角）の検出を warning とする。

kanji_run / weak_expressions は、見出し行の長い漢字複合語や「!」等を誤検知
しないよう、prose を直接スキャンせず split_sentences(prose)（見出し行を除外する）
の文単位でスキャンする。
"""
import regex

from . import config
from .model import Finding, check_fail, check_pass
from .prose import split_sentences

_NAME_SENTENCE_LENGTH = "sentence_length"
_NAME_SENTENCE_COMMAS = "sentence_commas"
_NAME_KANJI_RUN = "kanji_run"
_NAME_WEAK_EXPRESSIONS = "weak_expressions"

# weakExpressionRes（checker_readability.go の package var）の移植。
# 感嘆符は半角/全角の両方を対象にする。
_WEAK_EXPRESSION_RES = [
    regex.compile(r"かもしれない|かもしれません"),
    regex.compile(r"と思います|と思われます"),
    regex.compile(r"ではないでしょうか"),
    regex.compile(r"な気がします"),
    regex.compile(r"[!！]"),
]


def _first_runes(s: str, n: int) -> str:
    """s の先頭 n rune を返す。rune 数が n 以下なら s をそのまま返す（firstRunes の移植）。"""
    if len(s) <= n:
        return s
    return s[:n]


def _sentence_length_check(
    sentences: list[str], limit: int, severity: str, suggestion: str
) -> Finding:
    """limit を超える文を集計して 1 件の Finding を組み立てる（sentenceLengthCheck の移植）。"""
    offenders = []
    for s in sentences:
        n = len(s)
        if n > limit:
            offenders.append(f"「{_first_runes(s, 20)}…」（{n}字）")
    if not offenders:
        return check_pass(_NAME_SENTENCE_LENGTH, f"no sentence exceeds {limit} runes", severity)
    detail = f"{len(offenders)} sentence(s) exceed {limit} runes: {' / '.join(offenders)}"
    return check_fail(_NAME_SENTENCE_LENGTH, detail, suggestion, severity)


def check_sentence_length(
    prose: str,
    *,
    max_len: int = config.SENTENCE_MAX_LEN,
    warn_len: int = config.SENTENCE_WARN_LEN,
) -> list[Finding]:
    sentences = split_sentences(prose)
    err_check = _sentence_length_check(
        sentences,
        max_len,
        "error",
        f"一文が長すぎます（{max_len}字超）。60〜80字を目安に、"
        "接続助詞（〜が、〜ので、〜ため）で繋がれた文を分割してください",
    )
    warn_check = _sentence_length_check(
        sentences,
        warn_len,
        "warning",
        f"一文がやや長めです（{warn_len}字超）。60〜80字を目安に、"
        "一文一義になるよう文を分割してください",
    )
    return [err_check, warn_check]


def check_sentence_commas(
    prose: str, *, max_commas: int = config.SENTENCE_MAX_COMMAS
) -> Finding:
    offenders = []
    for s in split_sentences(prose):
        cnt = s.count("、")
        if cnt > max_commas:
            offenders.append(f"「{_first_runes(s, 20)}…」（読点{cnt}個）")
    if not offenders:
        return check_pass(
            _NAME_SENTENCE_COMMAS, f"no sentence has more than {max_commas} commas", "warning"
        )
    detail = f"{len(offenders)} sentence(s) exceed {max_commas} commas: {' / '.join(offenders)}"
    return check_fail(
        _NAME_SENTENCE_COMMAS,
        detail,
        "一文に読点が多すぎます。文を分割するか、要素を箇条書きに展開して係り受けを明確にしてください",
        "warning",
    )


def _kanji_run_allowed(match: str, allowlist: list[str]) -> bool:
    """match が allowlist のいずれかの語に内包される（部分文字列である）場合に True。"""
    return any(match in a for a in allowlist)


def check_kanji_run(
    prose: str,
    *,
    run_max: int = config.KANJI_RUN_MAX,
    allowlist: list[str] = config.KANJI_RUN_ALLOWLIST,
) -> Finding:
    kanji_run_re = regex.compile(rf"\p{{Han}}{{{run_max + 1},}}")
    offenders = []
    seen: set[str] = set()
    for s in split_sentences(prose):
        for m in kanji_run_re.findall(s):
            if _kanji_run_allowed(m, allowlist):
                continue
            if m in seen:
                continue
            seen.add(m)
            offenders.append(f"「{m}」（{len(m)}字連続）")
    if not offenders:
        return check_pass(_NAME_KANJI_RUN, f"no kanji run exceeds {run_max} chars", "warning")
    detail = f"{len(offenders)} kanji run(s) exceed {run_max} chars: {' / '.join(offenders)}"
    return check_fail(
        _NAME_KANJI_RUN,
        detail,
        "漢字が連続しすぎて読みにくくなっています。複合語を助詞で分ける、"
        "一部をかな書きにする、送り仮名を補う等で漢字の連続を断ってください",
        "warning",
    )


def check_weak_expressions(prose: str) -> Finding:
    sentences = split_sentences(prose)
    found = []
    seen: set[str] = set()
    for pattern in _WEAK_EXPRESSION_RES:
        for s in sentences:
            for m in pattern.findall(s):
                if m in seen:
                    continue
                seen.add(m)
                found.append(m)
    if not found:
        return check_pass(_NAME_WEAK_EXPRESSIONS, "no weak expressions found", "warning")
    detail = f"weak expressions found: {', '.join(found)}"
    return check_fail(
        _NAME_WEAK_EXPRESSIONS,
        detail,
        "曖昧・弱い表現や感嘆符が使われています。"
        "「かもしれない/と思います/ではないでしょうか/な気がします」は根拠を添えて断定形にし、"
        "感嘆符（!／！）は削除してください",
        "warning",
    )
