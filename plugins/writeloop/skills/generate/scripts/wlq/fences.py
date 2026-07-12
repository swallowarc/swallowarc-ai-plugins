# ported from: internal/infrastructure/quality/checker_code.go:12-115 @ autopostd 20c740b
"""Fenced code block（``` / ~~~）を検出する CommonMark 準拠のパーサ。

checker_code.go の codeBlock struct / parseFencedCodeBlocks / parseFenceOpening /
isFenceClosing / firstInfoToken を移植する。開始フェンス（` または ~ を 3 つ以上）
と閉じフェンス（開始と同じ記号・同じ長さ以上・後続テキストなし）を区別し、
フェンス内に現れる別記号・より短いフェンス風の行はブロックの内容として扱う
（入れ子対策）。mdscan.py の strip_fenced_code_blocks（単純トグル方式）とは
意図的に別実装であり、言語タグ検査・ブロック位置の特定が必要な用途専用。
"""
from dataclasses import dataclass


@dataclass
class CodeBlock:
    """本文中の 1 つの fenced code block を表す（codeBlock 構造体の移植）。"""

    start_line: int  # 開始フェンス行の index（0 始まり）
    end_line: int     # 閉じフェンス行の index。閉じフェンスが無い場合は len(lines)
    lang: str = ""    # 開始フェンスの info string の先頭トークン（言語タグ）。無ければ空


def _parse_fence_opening(trimmed: str) -> tuple[str, int, str] | None:
    """trim 済みの行が開始フェンスかを判定する（parseFenceOpening の移植）。

    フェンス記号・記号の連続数・info string（言語タグ等）を返す。開始フェンスで
    なければ None を返す。
    """
    if len(trimmed) < 3:
        return None
    ch = trimmed[0]
    if ch != "`" and ch != "~":
        return None
    n = 0
    while n < len(trimmed) and trimmed[n] == ch:
        n += 1
    if n < 3:
        return None
    rest = trimmed[n:]
    # CommonMark: backtick フェンスの info string に ` は含められない
    if ch == "`" and "`" in rest:
        return None
    return ch, n, rest.strip()


def _is_fence_closing(trimmed: str, ch: str, min_len: int) -> bool:
    """trim 済みの行が、記号 ch・長さ min_len 以上の閉じフェンス（記号の後に何も
    続かない）かを判定する（isFenceClosing の移植）。
    """
    if len(trimmed) < min_len:
        return False
    n = 0
    while n < len(trimmed) and trimmed[n] == ch:
        n += 1
    return n >= min_len and trimmed[n:].strip() == ""


def _first_info_token(info: str) -> str:
    """info string の先頭トークン（言語タグ）を返す（firstInfoToken の移植）。"""
    fields = info.split()
    if not fields:
        return ""
    return fields[0]


def parse_fenced_code_blocks(lines: list[str]) -> list[CodeBlock]:
    """Markdown 本文の行リストから fenced code block を抽出する
    （parseFencedCodeBlocks の移植）。

    閉じフェンスが無いままリスト末尾に達した場合もブロックとして数え、
    end_line は len(lines) になる。
    """
    blocks: list[CodeBlock] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    current: CodeBlock | None = None

    for i, line in enumerate(lines):
        trimmed = line.strip()
        if not in_fence:
            opening = _parse_fence_opening(trimmed)
            if opening is None:
                continue
            fence_char, fence_len, info = opening
            in_fence = True
            current = CodeBlock(start_line=i, end_line=len(lines), lang=_first_info_token(info))
            continue
        if _is_fence_closing(trimmed, fence_char, fence_len):
            current.end_line = i
            blocks.append(current)
            in_fence = False

    if in_fence:
        # 閉じフェンスが無いままファイル末尾に達した場合もブロックとして数える
        blocks.append(current)
    return blocks
