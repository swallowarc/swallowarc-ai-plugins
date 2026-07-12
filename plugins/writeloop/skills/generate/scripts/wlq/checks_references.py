# ported from: internal/infrastructure/quality/checker_references.go:16 (refURLRe),
#              :21 (normalizeURL), :40 (normalizedURLs), :53,55-63 (referencesSectionNames/
#              refH2Re/verificationDateRe), :65 (findReferencesSection), :90 (isReferencesHeading),
#              :101 (normalizeRefParens), :106 (referenceEntryLines), :120 (newReferenceCheck),
#              :131 (checkReferences), :152 (checkReferencesSection), :160 (checkReferenceEntries),
#              :195 (checkVerificationDate), :210 (checkResearchReferenceMatch)
#              @ autopostd 20c740b
"""参考情報チェック 4 件（references_section / reference_entries / verification_date /
research_reference_match）の移植。

対象判定（skip=pass の条件）について: 本番 `checkReferences` は
`domain.RequiresReferences(plan)`（generation_profile=="research" または
article_type=="news"）が false の Plan では 4 件とも skip=pass にする
（checker_references.go:131-150）。writeloop には Go の Plan 型・
generation_profile という概念が存在せず（wlq 全体で generation_profile を
扱うモジュールは無い。qualitycheck.py の run_checks も article_type と
research_content のみを扱う設計）、この移植では
`research_content is not None`（リサーチ結果が渡されていること）を
generation_profile=="research" の代替シグナルとして扱う。すなわち

    required = article_type == "news" or research_content is not None

とする。これは task-11.md の代表テスト（article_type="impl" だが
research_content 有りで references_section が fail する）および
Task 12 の run_checks インターフェース仕様と整合する設計判断であり、
Go の Plan ベースの判定（generation_profile と実際の research_content の
有無が独立に変化しうる）とは異なる。具体的な差異は
report-task-11.md に記録する。

skip=pass 時の detail 文字列（checker_references.go:133-134）は
`fmt.Sprintf("skipped: references not required (generation_profile=%s, article_type=%s)",
plan.GenerationProfile(), plan.ArticleType())` だが、GenerationProfile は
"basic"/"research" の 2 値しかなく（generation_profile.go:8-9）、かつ
"research" は常に required=true 側に倒れるため、skip 分岐に到達する時点で
generation_profile は必ず "basic" になる。よって
`generation_profile=basic` は Go 実装の実際の出力と完全に一致する
（近似ではなく必然的に同じ値になる）。
"""
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

import regex

from .mdscan import REF_H2_RE, _strip_fenced_code_blocks, is_references_heading
from .model import Finding, check_fail, check_pass

_SEVERITY_ERROR = "error"

_NAME_SECTION = "references_section"
_NAME_ENTRIES = "reference_entries"
_NAME_DATE = "verification_date"
_NAME_MATCH = "research_reference_match"

# checkReferences (checker_references.go:132) が束ねる 4 チェックの名前。
_REFERENCE_CHECK_NAMES = (_NAME_SECTION, _NAME_ENTRIES, _NAME_DATE, _NAME_MATCH)

# refURLRe (checker_references.go:16): 本文・リサーチ結果から URL を抽出する。
# scheme の大文字（HTTPS:// 等）も拾えるよう大文字小文字を無視する（(?i)）。
# Markdown リンクの閉じ括弧・全角括弧・引用符・空白・角括弧は URL に含めない。
_REF_URL_RE = regex.compile(r'(?i)https?://[^\s<>\[\]()（）"\']+')

# verificationDateRe (checker_references.go:60): 「情報確認日: YYYY-MM-DD」行に
# マッチする（全角コロン許容）。
_VERIFICATION_DATE_RE = regex.compile(r"情報確認日[:：]\s*(\d{4}-\d{2}-\d{2})")


def _normalize_url(raw: str) -> str | None:
    """normalizeURL（checker_references.go:21）の移植。

    URL を照合用に正規化する。scheme と host を小文字化し、フラグメントと
    末尾スラッシュを除去する。クエリは保持する。文末の句読点（。、.,;:）が
    正規表現抽出で紛れ込むため事前に除去する。正規化できない（絶対 URL で
    ない）場合は None を返す（Go の error 相当）。
    """
    raw = raw.rstrip(".,;:。、")
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    if not parts.scheme or not parts.netloc:
        return None
    path = parts.path
    if path.endswith("/"):
        path = path[:-1]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def _normalized_urls(text: str) -> set[str]:
    """normalizedURLs（checker_references.go:40）の移植。

    text から URL を抽出し、正規化済み URL の集合を返す。正規化に失敗した
    URL は無視する。
    """
    out: set[str] = set()
    for raw in _REF_URL_RE.findall(text):
        n = _normalize_url(raw)
        if n is not None:
            out.add(n)
    return out


def _normalize_ref_parens(s: str) -> str:
    """normalizeRefParens（checker_references.go:101）の移植。半角括弧を全角括弧に
    揃える（一次/二次情報ラベルの照合用）。
    """
    return s.replace("(", "（").replace(")", "）")


def _reference_entry_lines(section: str) -> list[str]:
    """referenceEntryLines（checker_references.go:106）の移植。参考情報セクション内の
    「URL を含む箇条書き行」を返す。
    """
    entries: list[str] = []
    for line in section.split("\n"):
        t = line.strip()
        if not (t.startswith("- ") or t.startswith("* ")):
            continue
        if _REF_URL_RE.search(t):
            entries.append(t)
    return entries


def _find_references_section(content: str) -> tuple[str, bool]:
    """findReferencesSection（checker_references.go:65）の移植。

    本文から参考情報セクション（H2）を探し、見出しの次行から次の見出し
    （H1/H2）の手前までの本文を返す。フェンスコードブロック内の行は
    mdscan._strip_fenced_code_blocks で事前に除外する（Task 9 の共有ヘルパー
    を再利用し、ロジックを複製しない）。
    """
    in_section = False
    body: list[str] = []
    for line in _strip_fenced_code_blocks(content).split("\n"):
        trimmed = line.strip()
        m = REF_H2_RE.match(trimmed)
        if m is not None:
            if in_section:
                break  # 次の H2 でセクション終了
            in_section = is_references_heading(m.group(1))
            continue
        if in_section and trimmed.startswith("# "):
            break  # H1 でも終了（通常は出現しない）
        if in_section:
            body.append(line)
    if not in_section:
        return "", False
    return "\n".join(body), True


def _check_references_section(found: bool) -> Finding:
    """checkReferencesSection（checker_references.go:152）の移植。"""
    if not found:
        return check_fail(
            _NAME_SECTION,
            "references section (## 参考情報 / 参考文献 / 参考リンク) not found",
            "",
            _SEVERITY_ERROR,
        )
    return check_pass(_NAME_SECTION, "references section found", _SEVERITY_ERROR)


def _check_reference_entries(found: bool, section: str) -> Finding:
    """checkReferenceEntries（checker_references.go:160）の移植。"""
    if not found:
        return check_fail(
            _NAME_ENTRIES,
            "references section not found, no entries to check",
            "",
            _SEVERITY_ERROR,
        )
    entries = _reference_entry_lines(section)
    if not entries:
        return check_fail(
            _NAME_ENTRIES,
            "no reference entries with URL found in references section",
            "",
            _SEVERITY_ERROR,
        )
    primary = 0
    secondary_labeled = 0
    for e in entries:
        n = _normalize_ref_parens(e)
        if "（一次情報）" in n:
            primary += 1
        if "（二次情報）" in n:
            secondary_labeled += 1
    # （二次情報）ラベルは冗長のため廃止(2026-07-06 ユーザ要望)。ラベル無し = 二次情報とみなす。
    # 修正はラベル文字列の削除のみでよい(本文の書き直しは不要)。
    if secondary_labeled > 0:
        return check_fail(
            _NAME_ENTRIES,
            f"{secondary_labeled} reference entries have redundant （二次情報） label; "
            "remove the label text only (unlabeled entries are treated as secondary sources)",
            "",
            _SEVERITY_ERROR,
        )
    # 一次情報優先の規律を残すため、（一次情報）付きエントリを 1 件以上要求する。
    if primary == 0:
        return check_fail(
            _NAME_ENTRIES,
            f"no reference entry labeled （一次情報） among {len(entries)} entries; "
            "label primary sources (official release/docs, CVE/NVD, GitHub release)",
            "",
            _SEVERITY_ERROR,
        )
    return check_pass(
        _NAME_ENTRIES,
        f"{len(entries)} reference entries found ({primary} primary-labeled)",
        _SEVERITY_ERROR,
    )


def _check_verification_date(found: bool, section: str) -> Finding:
    """checkVerificationDate（checker_references.go:195）の移植。"""
    if not found:
        return check_fail(
            _NAME_DATE,
            "references section not found, no verification date to check",
            "",
            _SEVERITY_ERROR,
        )
    m = _VERIFICATION_DATE_RE.search(section)
    if m is None:
        return check_fail(
            _NAME_DATE,
            "verification date line (情報確認日: YYYY-MM-DD) not found in references section",
            "",
            _SEVERITY_ERROR,
        )
    date_str = m.group(1)
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return check_fail(
            _NAME_DATE,
            f'verification date "{date_str}" is not a valid date',
            "",
            _SEVERITY_ERROR,
        )
    return check_pass(_NAME_DATE, f"verification date {date_str} found", _SEVERITY_ERROR)


def _check_research_reference_match(
    found: bool, section: str, research_content: str | None
) -> Finding:
    """checkResearchReferenceMatch（checker_references.go:210）の移植。"""
    if research_content is None:
        return check_pass(
            _NAME_MATCH, "skipped: no research result for this plan", _SEVERITY_ERROR
        )
    research_urls = _normalized_urls(research_content)
    if not research_urls:
        return check_pass(
            _NAME_MATCH, "skipped: research content contains no URLs", _SEVERITY_ERROR
        )
    if not found:
        return check_fail(
            _NAME_MATCH,
            "references section not found, cannot match research URLs",
            "",
            _SEVERITY_ERROR,
        )
    for u in _normalized_urls(section):
        if u in research_urls:
            return check_pass(
                _NAME_MATCH, f"reference URL matches research URL: {u}", _SEVERITY_ERROR
            )
    return check_fail(
        _NAME_MATCH, "no reference URL matches URLs in research content", "", _SEVERITY_ERROR
    )


def check_references(
    article_type: str, research_content: str | None, content: str
) -> list[Finding]:
    """checkReferences（checker_references.go:131）の移植。

    references_section / reference_entries / verification_date /
    research_reference_match の 4 findings を返す。対象外の記事
    （article_type != "news" かつ research_content is None）では 4 件とも
    skip=pass にする。対象判定の詳細はモジュール docstring を参照。
    """
    required = article_type == "news" or research_content is not None
    if not required:
        detail = (
            "skipped: references not required "
            f"(generation_profile=basic, article_type={article_type})"
        )
        return [check_pass(n, detail, _SEVERITY_ERROR) for n in _REFERENCE_CHECK_NAMES]

    section, found = _find_references_section(content)
    return [
        _check_references_section(found),
        _check_reference_entries(found, section),
        _check_verification_date(found, section),
        _check_research_reference_match(found, section, research_content),
    ]
