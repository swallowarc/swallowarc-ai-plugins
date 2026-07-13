# ported from: internal/infrastructure/quality/checker_structure.go:13,18,101-135
#              @ autopostd 20c740b
#              internal/infrastructure/quality/checker_references.go:53,57,90-97
#              @ autopostd 20c740b
"""Markdown 見出し走査の共有ヘルパー。

- ANY_HEADING_RE: 全レベル（H1〜H6）の見出し行検出用（anyHeadingRe の移植）。
  heading_structure 系チェック（H1 有無・見出しレベル飛びの検査）が使う想定。
- extract_headings: H1 を除く見出し（H2 以上）のテキスト部分を抽出する
  （extractHeadings の移植）。required_sections 系チェックが使う想定。
- REF_H2_RE: H2 見出し行の検出用（refH2Re の移植）。参考情報セクション探索
  （findReferencesSection）が使う想定。
- is_references_heading: 見出しテキストが参考情報セクションの正規名・別名の
  いずれかに完全一致するかを判定する（isReferencesHeading の移植）。
"""
import regex

# anyHeadingRe (checker_structure.go:18): 全レベル（H1〜H6）の見出し行を検出する。
# heading_structure チェックでは H1 の有無やレベルの階層飛びも検査するため、
# H1 を除外する headingRe とは別に、全レベルを対象とする正規表現を用いる。
ANY_HEADING_RE = regex.compile(r"^(#{1,6})\s+")

# headingRe (checker_structure.go:13): H1 を除く見出し（H2 以上）のテキスト部分を
# キャプチャする。extract_headings 専用の内部正規表現で、mdscan の公開 API では
# 意図的に export しない（Go 側でも headingRe は extractHeadings 以外から
# 参照されていない）。
_HEADING_RE = regex.compile(r"^#{2,}\s+(.*)$")

# refH2Re (checker_references.go:57): H2 見出し行にマッチし、見出しテキストを
# キャプチャする。
REF_H2_RE = regex.compile(r"^##\s+(.*)$")

# referencesSectionNames (checker_references.go:53): 参考情報セクションとして
# 認める H2 見出し名（正規名 + 別名）。
_REFERENCES_SECTION_NAMES = ("参考情報", "参考文献", "参考リンク")


def _strip_fenced_code_blocks(content: str) -> str:
    """content からフェンスコードブロック（``` または ~~~ で囲まれた範囲）内の
    行を取り除いた文字列を返す（stripFencedCodeBlocks の移植）。

    フェンスの開始行はトリム後の先頭が ``` または ~~~ である行とみなし、次に
    そのような行が現れるまでをフェンス内として扱う（トグル方式）。フェンスの
    区切り行自体も結果には含めない。fences.py の parse_fenced_code_blocks
    （CommonMark 準拠・フェンス記号/長さの一致を検査・入れ子対応）とは意図的に
    別実装であり、開始・終了で記号の種類や長さが一致している必要はない
    （``` で開いて ~~~ で閉じても正しくトグルオフする）。見出し検出
    （extract_headings）がコードサンプル中の "# install" のような行を Markdown
    見出しと誤認しないようにするための、意図的にシンプルな実装。
    """
    out: list[str] = []
    in_fence = False
    for line in content.split("\n"):
        trimmed = line.strip()
        if trimmed.startswith("```") or trimmed.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        out.append(line)
    return "\n".join(out)


def extract_headings(content: str) -> list[str]:
    """Markdown の見出し行（## 以上）からテキスト部分を抽出する
    （extractHeadings の移植）。

    フェンスコードブロック内の行は _strip_fenced_code_blocks であらかじめ
    除外し、コード例中のコメント行を見出しとして扱わないようにする。戻り値は
    見出し記号（##…）と直後の空白を除いたテキスト部分のみで、前後の空白は
    trim される。H1（# 1 個）は headingRe が `#{2,}` のため対象外。
    """
    headings: list[str] = []
    for line in _strip_fenced_code_blocks(content).split("\n"):
        m = _HEADING_RE.search(line.strip())
        if m is not None:
            headings.append(m.group(1).strip())
    return headings


def is_references_heading(heading: str) -> bool:
    """見出しテキストが参考情報セクションの正規名・別名のいずれかに完全一致
    するかを判定する（isReferencesHeading の移植）。前後の空白は trim してから
    比較する。部分一致・前方一致は不可。
    """
    h = heading.strip()
    return h in _REFERENCES_SECTION_NAMES
