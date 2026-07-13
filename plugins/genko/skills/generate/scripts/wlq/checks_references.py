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
（checker_references.go:131-150）。genko には Go の Plan 型・
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


# net/url shouldEscape(c, encodePath) が false（escape しない）とする文字。
# 英数字と -_.~（§2.3 unreserved）、および予約文字 $&+,/:;=?@ のうち
# encodePath では ? のみ escape 対象のため ? を除いた残り。
_GO_PATH_NO_ESCAPE = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    "-_.~$&+,/:;=@"
)

# net/url validEncoded(s, encodePath) が「エスケープ済みパスとして妥当」と
# 認める文字。shouldEscape が false の文字に加え、明示的に許される
# !'()*;[]（sub-delims 等）と %（percent-encoding の開始）。
_GO_PATH_VALID_ENCODED = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    "-_.~!$&'()*+,;=:@[]%/"
)

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def _go_escape_path(path: bytes) -> str:
    """net/url の escape(s, encodePath) の移植。UTF-8 バイト単位で、encodePath で
    escape 対象のバイトを %XX（大文字 hex）に符号化する。
    """
    out: list[str] = []
    for b in path:
        c = chr(b)
        if c in _GO_PATH_NO_ESCAPE:
            out.append(c)
        else:
            out.append(f"%{b:02X}")
    return "".join(out)


def _go_unescape_path(raw: str) -> bytes | None:
    """net/url の unescape(s, encodePath) の移植。%XX（hex 2 桁必須）を検証しつつ
    バイト列へ復号する。不正なエスケープは None（url.Parse のエラー相当）。
    パスモードでは + を空白に復号しない。
    """
    data = raw.encode("utf-8")
    out = bytearray()
    i = 0
    while i < len(data):
        if data[i] == 0x25:  # "%"
            if i + 2 >= len(data):
                return None
            h1, h2 = chr(data[i + 1]), chr(data[i + 2])
            if h1 not in _HEX_DIGITS or h2 not in _HEX_DIGITS:
                return None
            out.append(int(h1 + h2, 16))
            i += 3
        else:
            out.append(data[i])
            i += 1
    return bytes(out)


def _normalize_url(raw: str) -> str | None:
    """normalizeURL（checker_references.go:21）の移植。

    URL を照合用に正規化する。scheme と host を小文字化し、フラグメントと
    末尾スラッシュを除去する。クエリは保持する。文末の句読点（。、.,;:）が
    正規表現抽出で紛れ込むため事前に除去する。正規化できない（絶対 URL で
    ない・不正な %エスケープを含む）場合は None を返す（Go の error 相当）。

    Go は u.String() 経由で net/url の EscapedPath によるパス再エンコードを
    行うため、それを忠実に再現する:
    (1) setPath 相当 — raw パスを復号して u.Path 相当を得る。canonical に
        再エンコードした結果が raw と一致する場合は RawPath 相当を保持しない。
    (2) 復号後のパスから末尾スラッシュを除去（TrimSuffix は u.Path に対して
        行われる）。
    (3) EscapedPath 相当 — 保持した元表記が valid なエスケープ済みパスで、
        かつ復号結果が現在のパスと一致するならそのまま使い、そうでなければ
        canonical（%XX 大文字 hex）に再エンコードする。
    この結果、生の日本語・スペースを含むパスは %XX に符号化され、既に
    percent-encoded 済みのパスはパス未変更なら元表記（小文字 hex 含む）の
    まま保持され、末尾スラッシュ除去でパスが変更された場合は canonical に
    再符号化される。query（RawQuery 相当）は Go の String() 同様に素通しする。
    期待値は使い捨て Go スニペットのゴールデン出力と突き合わせて検証済み
    （テスト側 docstring 参照）。
    """
    raw = raw.rstrip(".,;:。、")
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    if not parts.scheme or not parts.netloc:
        return None

    # url.Parse の ForceQuery 相当: フラグメント除去後の残りが末尾の「?」1 個
    # だけで終わる場合、Go の String() は空クエリでも「?」を出力する。
    without_fragment = raw.split("#", 1)[0]
    force_query = without_fragment.endswith("?") and without_fragment.count("?") == 1

    # (1) url.Parse の setPath 相当
    decoded = _go_unescape_path(parts.path)
    if decoded is None:
        return None  # url.Parse が invalid URL escape エラーになるケース
    raw_path = parts.path if _go_escape_path(decoded) != parts.path else ""

    # (2) u.Path = strings.TrimSuffix(u.Path, "/")
    if decoded.endswith(b"/"):
        decoded = decoded[:-1]

    # (3) u.String() が使う u.EscapedPath() 相当
    if (
        raw_path
        and all(c in _GO_PATH_VALID_ENCODED for c in raw_path)
        and _go_unescape_path(raw_path) == decoded
    ):
        escaped_path = raw_path
    else:
        escaped_path = _go_escape_path(decoded)

    # Go は u.Host（userinfo を含まない）のみ小文字化する
    netloc = parts.netloc
    if "@" in netloc:
        userinfo, host = netloc.rsplit("@", 1)
        netloc = f"{userinfo}@{host.lower()}"
    else:
        netloc = netloc.lower()

    out = urlunsplit((parts.scheme.lower(), netloc, escaped_path, parts.query, ""))
    if force_query and not parts.query:
        out += "?"
    return out


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
