# ported from: internal/infrastructure/quality/checker_structure.go:27-58 (checkHeadingStructure),
#              internal/infrastructure/quality/checker_structure.go:60-96 (checkRequiredSections),
#              internal/domain/required_sections.go (RequiredSection / RequiredSectionsFor / NewsLabels)
#              @ autopostd 20c740b
"""見出し構造・必須セクション系のチェック 2 関数（heading_structure /
required_sections）。

- check_heading_structure: 本文（frontmatter を除いた body）の見出し構造を検査する
  （checkHeadingStructure の移植）。タイトルは Frontmatter 側にあるため、本文は H1 を
  含んではならず、最初の見出しは H2 から始まる必要がある。見出しレベルが 1 段階を
  超えて飛ぶ（例: H2 -> H4）のも構造として不自然なため失敗とする。フェンスコード
  ブロック内の行は mdscan._strip_fenced_code_blocks で事前に除外し、コード中の
  コメント（"# install" 等）を見出しとして誤検出しないようにする。Go 側は
  checkHeadingStructure と extractHeadings が同じ package 内の stripFencedCodeBlocks
  を共有しているため、Python 側でも mdscan.py が保持する同名ヘルパーをそのまま再利用し、
  ロジックを複製しない。

- check_required_sections: article_type ごとの必須セクション見出しが content 中に
  存在するかを検査する（checkRequiredSections の移植）。必須セクション・別名は
  domain/required_sections.go の値をこのモジュール内の定数として写す。news 型のみ、
  見出しとは別に "重要度" "影響範囲" "推奨アクション" ラベルが content に
  部分文字列として含まれることも要求する（NewsLabels）。
"""
from dataclasses import dataclass, field

from .mdscan import ANY_HEADING_RE, _strip_fenced_code_blocks, extract_headings
from .model import Finding, check_fail, check_pass

_NAME_HEADING_STRUCTURE = "heading_structure"
_NAME_REQUIRED_SECTIONS = "required_sections"
_SEVERITY_ERROR = "error"


@dataclass(frozen=True)
class _RequiredSection:
    """RequiredSection（required_sections.go:5）の移植。"""

    canonical: str
    aliases: tuple[str, ...] = field(default=())

    def matches(self, heading: str) -> bool:
        """RequiredSection.Matches（required_sections.go:13）の移植。"""
        h = heading.strip().lower()
        if h == self.canonical.lower():
            return True
        return any(h == a.lower() for a in self.aliases)


# secIntro / secConclusion / secNextSteps（required_sections.go:32-34）の移植。
# secIntro は旧「対象読者」「この記事でわかること」「前提と扱わないこと」を 1 見出しに
# 統合した導入セクション（旧見出しはエイリアスにしない）。
_SEC_INTRO = _RequiredSection("はじめに")
_SEC_CONCLUSION = _RequiredSection("結論・要点", ("まとめ",))
_SEC_NEXT_STEPS = _RequiredSection("次にやること")

# commonSections（required_sections.go:37-39）の移植。
_COMMON_SECTIONS = (_SEC_INTRO, _SEC_CONCLUSION, _SEC_NEXT_STEPS)
# ArticleTypeGeneral および default（required_sections.go:45-49）の移植。
_GENERAL_SECTIONS = (_SEC_CONCLUSION,)

# NewsLabels（required_sections.go:52-54）の移植。
_NEWS_LABELS = ("重要度", "影響範囲", "推奨アクション")

_COMMON_ARTICLE_TYPES = frozenset({"intro", "impl", "opinion", "news"})


def _required_sections_for(article_type: str) -> tuple[_RequiredSection, ...]:
    """RequiredSectionsFor（required_sections.go:41-50）の移植。"""
    if article_type in _COMMON_ARTICLE_TYPES:
        return _COMMON_SECTIONS
    return _GENERAL_SECTIONS


def check_heading_structure(body: str) -> Finding:
    """checkHeadingStructure（checker_structure.go:27）の移植。"""
    reason = ""
    prev_level = 0
    for line in _strip_fenced_code_blocks(body).split("\n"):
        m = ANY_HEADING_RE.search(line.strip())
        if m is None:
            continue
        level = len(m.group(1))

        if level == 1:
            reason = "body must not contain H1"
            break
        if prev_level == 0 and level != 2:
            reason = "top heading must be H2"
            break
        if prev_level != 0 and level > prev_level + 1:
            reason = f"heading level jump from H{prev_level} to H{level}"
            break
        prev_level = level

    if reason:
        return check_fail(_NAME_HEADING_STRUCTURE, reason, "", _SEVERITY_ERROR)
    return check_pass(_NAME_HEADING_STRUCTURE, "heading structure ok", _SEVERITY_ERROR)


def check_required_sections(article_type: str, content: str) -> Finding:
    """checkRequiredSections（checker_structure.go:60）の移植。"""
    headings = extract_headings(content)
    missing: list[str] = []
    for sec in _required_sections_for(article_type):
        found = any(sec.matches(h) for h in headings)
        if not found:
            missing.append(sec.canonical)

    if article_type == "news":
        for label in _NEWS_LABELS:
            if label not in content:
                missing.append(label)

    if missing:
        return check_fail(
            _NAME_REQUIRED_SECTIONS,
            f"missing sections: {', '.join(missing)}",
            "",
            _SEVERITY_ERROR,
        )
    return check_pass(_NAME_REQUIRED_SECTIONS, "all required sections present", _SEVERITY_ERROR)


# build_prompt の [必須セクション] 描画と資産テストが使う公開アクセサ。
NEWS_LABELS = _NEWS_LABELS


def required_section_names(article_type: str) -> tuple[str, ...]:
    return tuple(sec.canonical for sec in _required_sections_for(article_type))
