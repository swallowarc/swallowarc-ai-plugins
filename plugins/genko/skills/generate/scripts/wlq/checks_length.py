# ported from: internal/infrastructure/quality/checker_length.go @ autopostd 20c740b
"""本文長のチェック（parseLengthConstraint / checkBodyLength の移植）。

字数の定義: frontmatter・fenced code block・「## 参考情報」セクションを除いた本文の、
空白文字を除く rune 数（spec 決定事項。prose.extract_prose / count_prose_runes を使う）。
"""
import regex

from .model import Finding, check_fail, check_pass
from .prose import count_prose_runes, extract_prose

# lengthRangeRe（checker_length.go:13）の移植。「3000〜5000字」「3000~5000文字」の
# ような字数レンジ表記にマッチする。区切りは全角チルダ〜/半角チルダ~/波ダッシュ～/
# ハイフン- を許容する。
LENGTH_RANGE_RE = regex.compile(r"(\d{3,6})\s*[〜~～-]\s*(\d{3,6})\s*(?:字|文字)")
# lengthMaxRe（checker_length.go:16）の移植。「5000字以内」「5000文字以下」
# 「5000字まで」のような単一上限表記にマッチする。
LENGTH_MAX_RE = regex.compile(r"(\d{3,6})\s*(?:字|文字)\s*(?:以内|以下|まで)")


def parse_length_constraint(constraints: list[str]) -> tuple[int, int, bool]:
    """parseLengthConstraint（checker_length.go:21）の移植。

    constraints の各要素に対して、レンジ regex -> 単一上限 regex の順でマッチを試し、
    最初に見つかった字数指定の [lo, hi] を返す。単一上限表記の場合は lo=0。
    字数指定が見つからなければ found=False。
    """
    for c in constraints:
        m = LENGTH_RANGE_RE.search(c)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if lo > hi:
                lo, hi = hi, lo
            return lo, hi, True
        m = LENGTH_MAX_RE.search(c)
        if m:
            return 0, int(m.group(1)), True
    return 0, 0, False


def check_body_length(constraints: list[str], body: str) -> Finding:
    """checkBodyLength（checker_length.go:42）の移植。"""
    name = "body_length"
    lo, hi, found = parse_length_constraint(constraints)
    if not found:
        return check_pass(name, "skip: no length constraint", "error")
    n = count_prose_runes(extract_prose(body))
    if n < lo:
        return check_fail(
            name,
            f"prose length {n} is below constraint {lo}-{hi} (excluding frontmatter/code/references)",
            f"本文の散文が {n} 字で下限 {lo} 字を下回っています。必須トピックの説明を具体例や理由づけで肉付けしてください",
            "error")
    if n > hi:
        return check_fail(
            name,
            f"prose length {n} exceeds constraint {lo}-{hi} (excluding frontmatter/code/references)",
            f"本文の散文が {n} 字で上限 {hi} 字を超えています。冗長な説明や本筋から外れる話題を削ってください",
            "error")
    return check_pass(name, f"prose length {n} within {lo}-{hi}", "error")
