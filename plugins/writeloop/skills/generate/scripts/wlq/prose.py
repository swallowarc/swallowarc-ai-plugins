# ported from: internal/infrastructure/quality/prose.go @ autopostd 20c740b
"""可読性・AI 文体チェックが共通で使う散文抽出・文分割ユーティリティ。

fenced code block の除去は fences.py の parse_fenced_code_blocks を再利用する。

- extract_prose: 本文から「文章として読む対象ではない部分」を取り除いた散文を返す。
  具体的には、
    - fenced code block（``` / ~~~ で囲まれた範囲）を 1 行の空行に置き換える
    - 参考情報セクション（## 参考情報 / 参考文献 / 参考リンク の H2 見出しから
      次の H2 または EOF まで）を丸ごと除去する
    - インラインリンク [text](url) をリンクテキストのみに、画像 ![alt](url) を
      alt テキストのみに置き換える
  を行う。コードブロックを空行に潰すのは、前後の文章の連結を避けつつ行番号の
  大きなズレを防ぐため。参考情報セクションは URL や日付が多く散文の統計を歪める
  ため置換ではなく除去する。インラインリンクの正規化は、文長・読点数などの統計を
  読者に見える文字数で計測するため（URL を含めて数えると本文インライン引用のある
  文がほぼ確実に文長超過の誤検知になる）。
- strip_inline_links: 行中のインラインリンクをリンクテキストへ、画像を alt テキストへ
  置き換える。行の構造（行末の強制改行スペースを含む）には手を付けない。参照形式
  （[text][ref]）と自動リンク（<url>）は対象外。
- split_sentences: 散文を文単位に分割する。行ごとに処理し、見出し行（ANY_HEADING_RE。
  H1〜H6）・空行・markdown の表行（trim 後 `|` で始まる行）は除外したうえで、各行を
  「。」「！」「？」の直後で区切る。終止符を持たない行末の断片も 1 文として返す。
  返す各文の前後の空白は除去する。
- count_prose_runes: 散文の文字数を返す。空白文字（半角/全角スペース・タブ・改行）は
  数えない。可読性指標（漢字比率・平均文長など）の分母として用いる。
"""
import regex

from .fences import parse_fenced_code_blocks
from .mdscan import ANY_HEADING_RE, REF_H2_RE, is_references_heading

# inlineLinkRe (prose.go:86): Markdown のインラインリンク（[text](url)）と画像
# （![alt](url)）にマッチする。リンクテキスト内の「]」や URL 内の「)」を含む形には
# 対応しない。参照形式（[text][ref]）と自動リンク（<url>）は対象外。
INLINE_LINK_RE = regex.compile(r"!?\[([^\]]*)\]\([^)]*\)")


def strip_inline_links(line: str) -> str:
    return INLINE_LINK_RE.sub(r"\1", line)


def extract_prose(body: str) -> str:
    lines = body.split("\n")
    blocks = parse_fenced_code_blocks(lines)

    # コードブロックの開始行と、ブロック内（フェンス行を含む）の行を記録する。
    block_by_start = {b.start_line: b for b in blocks}
    in_code = set()
    for b in blocks:
        for i in range(b.start_line, min(b.end_line, len(lines) - 1) + 1):
            in_code.add(i)

    # 参考情報セクションの行範囲 [ref_start, ref_end) を特定する。
    # 見出し検出はコードブロック内の行を無視する（コード例中の "## 参考情報" 誤検出防止）。
    # ref_end == -1 はセクションが EOF まで続くことを表す。
    ref_start, ref_end = -1, -1
    for i, line in enumerate(lines):
        if i in in_code:
            continue
        m = REF_H2_RE.search(line.strip())
        if m is None:
            continue
        if ref_start == -1:
            if is_references_heading(m.group(1)):
                ref_start = i
            continue
        ref_end = i  # 参考情報セクションの次に現れた H2 で終端
        break

    out = []
    i = 0
    while i < len(lines):
        # 参考情報セクションは丸ごと読み飛ばす（空行プレースホルダも残さない）。
        if ref_start != -1 and i == ref_start:
            if ref_end == -1:
                break
            i = ref_end
            continue
        # コードブロックは 1 行の空行に置き換える。
        if i in block_by_start:
            out.append("")
            i = block_by_start[i].end_line + 1
            continue
        out.append(strip_inline_links(lines[i]))
        i += 1
    return "\n".join(out)


def split_sentences(prose: str) -> list[str]:
    sentences: list[str] = []

    def flush(buf: list[str]) -> None:
        s = "".join(buf).strip()
        if s:
            sentences.append(s)

    for line in prose.split("\n"):
        trimmed = line.strip()
        if not trimmed or ANY_HEADING_RE.search(trimmed) or trimmed.startswith("|"):
            continue
        buf: list[str] = []
        for ch in trimmed:
            buf.append(ch)
            if ch in "。！？":
                flush(buf)
                buf = []
        flush(buf)
    return sentences


def count_prose_runes(prose: str) -> int:
    return sum(1 for ch in prose if ch not in " \t\n\r　")
