"""checks_references.py のテスト。

移植元: internal/infrastructure/quality/checker_references_test.go @ autopostd 20c740b
（369 行。TestNormalizeURL / TestNormalizedURLs はモジュール内 private ヘルパー
_normalize_url / _normalized_urls の直接テスト。それ以外は公開 API
check_references(article_type, research_content, content) 経由で個別 finding を
検証する形に変換する）。

--- 対象判定の設計判断（重要）---

Go の checkReferences は domain.Plan（generation_profile を含む）を受け取り、
domain.RequiresReferences(plan) = (generation_profile=="research" または
article_type=="news") で「参考情報が必須か」を判定する。writeloop には
generation_profile という概念自体が存在しない（qualitycheck.py の run_checks も
article_type と research_content のみを扱う）。そのため本移植では

    required = article_type == "news" or research_content is not None

を対象判定として採用する（task-11.md の代表テストと同じ設計）。この結果、
Go テストのうち「generation_profile=research だが実際の research_content は
None」という、writeloop の 2 引数では表現不能な組み合わせ（下記
TestCheckReferences_SectionMissing の "required by research profile" サブケース）
は移植対象外とし、理由を付して以下に明記する。

Go テストケース対応表（全件照合。取捨選択ではなく上記設計判断による除外のみ）:

TestNormalizeURL
    table: lowercases scheme and host
        -> test_normalize_url_lowercases_scheme_and_host
    table: removes fragment
        -> test_normalize_url_removes_fragment
    table: removes trailing slash
        -> test_normalize_url_removes_trailing_slash
    table: removes trailing slash on root
        -> test_normalize_url_removes_trailing_slash_on_root
    table: keeps query
        -> test_normalize_url_keeps_query
    table: keeps query and removes fragment
        -> test_normalize_url_keeps_query_and_removes_fragment
    table: trims trailing japanese punctuation
        -> test_normalize_url_trims_trailing_japanese_punctuation
    "relative url is error"
        -> test_normalize_url_relative_url_is_error
TestNormalizedURLs
    -> test_normalized_urls_dedupes_and_normalizes
TestCheckReferences_SkippedWhenNotRequired
    -> test_check_references_skipped_when_not_required
TestCheckReferences_SectionMissing
    "required by research profile" -> 除外（下記「移植対象外」参照）
    "required by news type"
        -> test_check_references_section_missing_required_by_news_type
TestCheckReferences_AllPass
    -> test_check_references_all_pass
       （変換注記: Go は generation_profile="research"・researchContent=nil で
       required=True にするが、writeloop の required シグナルは research_content
       の有無のため、本文中の URL を含む research_content を渡して required=True
       にし、4 チェックすべてが skip でなく実ロジックで pass することを検証する。
       Go 側の researchContent=nil による research_reference_match の nil-skip
       経路は test_check_research_reference_match_nil_research_is_skip で
       別途カバーする）
TestCheckReferences_SectionAliases
    -> test_check_references_section_aliases
TestCheckReferences_SectionHeadingInsideCodeFenceIgnored
    -> test_check_references_section_heading_inside_code_fence_ignored
TestCheckReferenceEntries
    table: no url bullets
        -> test_check_reference_entries_no_url_bullets
    table: entry without label
        -> test_check_reference_entries_entry_without_label
    table: one primary one unlabeled
        -> test_check_reference_entries_one_primary_one_unlabeled
    table: half-width paren label accepted
        -> test_check_reference_entries_half_width_paren_label_accepted
    table: asterisk bullets accepted
        -> test_check_reference_entries_asterisk_bullets_accepted
    table: secondary label forbidden
        -> test_check_reference_entries_secondary_label_forbidden_table
TestCheckReferenceEntries_SecondaryLabelForbidden
    -> test_check_reference_entries_secondary_label_forbidden_standalone
TestCheckReferenceEntries_UnlabeledSecondaryAllowed
    -> test_check_reference_entries_unlabeled_secondary_allowed_standalone
TestCheckReferenceEntries_RequiresPrimaryLabel
    -> test_check_reference_entries_requires_primary_label_standalone
TestCheckVerificationDate
    table: missing line
        -> test_check_verification_date_missing_line
    table: invalid date
        -> test_check_verification_date_invalid_date
    table: full-width colon accepted
        -> test_check_verification_date_full_width_colon_accepted
TestCheckResearchReferenceMatch
    table: match after normalization (case, fragment, trailing slash)
        -> test_check_research_reference_match_after_normalization
    table: no matching url
        -> test_check_research_reference_match_no_matching_url
    table: research without urls is skip=pass
        -> test_check_research_reference_match_research_without_urls_is_skip
    table: nil research is skip=pass
        -> test_check_research_reference_match_nil_research_is_skip
    table: section missing but research has urls
        -> test_check_research_reference_match_section_missing_but_research_has_urls
TestCheck_IncludesReferenceChecks
    -> 除外（下記「移植対象外」参照）

--- 移植対象外（理由付き）---

1. TestCheckReferences_SectionMissing の "required by research profile" サブケース:
   refPlan(t, "intro", "research") で research_content=nil を渡す組み合わせ
   （generation_profile=research により必須だが、実際の research_content は
   まだ無い状態）。writeloop の check_references は generation_profile を
   引数に持たず、required は article_type=="news" or research_content is not
   None でのみ判定するため、「research_content が None なのに research 由来で
   必須」という状態は 2 引数のインターフェースでは表現できない。
   article_type="news" 側のサブケース（research_content=None でも必須）は
   test_check_references_section_missing_required_by_news_type としてそのまま
   移植し、「必須なのに research_content が無く research_reference_match が
   skip=pass になる」という挙動自体は news 型で検証できているため、
   カバレッジの欠落はない。

2. TestCheck_IncludesReferenceChecks:
   RuleBasedChecker.Check() 経由で 4 findings が結果配列に含まれることを見る
   統合テスト（本番のチェック登録・実行順序の検証）。writeloop 側の対応物は
   Task 12 の qualitycheck.py / wlq/runner.py（run_checks の実行順序）であり、
   check_references 単体のテストスコープ外のため Task 12 に送る。

--- 補足テスト（Go テスト由来ではない）---

test_check_references_required_by_research_content_present_section_missing:
   上記の除外 1 で失われる「research 由来で必須」の観点を、writeloop の
   実際のシグナル（research_content is not None）を使って別途カバーする。
   article_type を news 以外にし、URL を含む research_content を渡すことで
   required=True かつ research_reference_match も skip にならないケースを
   検証する。

test_normalize_url_golden_path_reencoding /
test_normalize_url_invalid_escape_is_error /
test_check_research_reference_match_mixed_raw_and_encoded_url:
   Go の normalizeURL は url.Parse(...).String() 経由で net/url の
   EscapedPath によるパス再エンコードを行う（生の日本語・スペースは %XX に
   符号化、canonical な percent-encoded パスや小文字 hex の既存エスケープは
   パス未変更なら元表記のまま保持、末尾スラッシュ除去でパスが変更されると
   canonical（大文字 hex）に再符号化、query（RawQuery）は素通し、不正な
   %エスケープは Parse エラー）。この挙動の期待値は、autopostd の
   normalizeURL と同一ロジックを複製した使い捨て Go スニペット
   （scratchpad 配下、リポジトリ外）を `go run` して得たゴールデン出力を
   一字一句移植したもの。checker_references_test.go には無いケースだが、
   生 Unicode URL と percent-encoded URL の混在時に research_reference_match
   の照合結果が Go と一致することを保証するために追加した（レビュー指摘対応）。
"""
from wlq.checks_references import _normalize_url, _normalized_urls, check_references


def _find(findings, name):
    return next(f for f in findings if f.name == name)


# --- _normalize_url ---


def test_normalize_url_lowercases_scheme_and_host():
    assert _normalize_url("HTTPS://Example.COM/Path") == "https://example.com/Path"


def test_normalize_url_removes_fragment():
    assert _normalize_url("https://example.com/a#section") == "https://example.com/a"


def test_normalize_url_removes_trailing_slash():
    assert _normalize_url("https://example.com/a/") == "https://example.com/a"


def test_normalize_url_removes_trailing_slash_on_root():
    assert _normalize_url("https://example.com/") == "https://example.com"


def test_normalize_url_keeps_query():
    assert _normalize_url("https://example.com/a?b=1&c=2") == "https://example.com/a?b=1&c=2"


def test_normalize_url_keeps_query_and_removes_fragment():
    assert _normalize_url("https://example.com/a?b=1#frag") == "https://example.com/a?b=1"


def test_normalize_url_trims_trailing_japanese_punctuation():
    assert _normalize_url("https://example.com/a。") == "https://example.com/a"


def test_normalize_url_relative_url_is_error():
    assert _normalize_url("/relative/path") is None


# --- _normalize_url: net/url パス再エンコードのゴールデンテスト ---
# 期待値は autopostd の normalizeURL と同一ロジックの使い捨て Go スニペットを
# `go run` して生成したゴールデン出力（詳細はモジュール docstring 参照）。


def test_normalize_url_golden_path_reencoding():
    golden = [
        # 生の日本語パスは %XX（大文字 hex）に符号化される
        ("https://example.com/こんにちは",
         "https://example.com/%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF"),
        # 生スペースは %20 に符号化される
        ("https://example.com/a b", "https://example.com/a%20b"),
        # canonical（大文字 hex）に percent-encoded 済みのパスは不変
        ("https://example.com/%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF",
         "https://example.com/%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF"),
        ("https://example.com/a%20b", "https://example.com/a%20b"),
        # 小文字 hex の既存エスケープは、パス未変更なら元表記のまま保持される
        ("https://example.com/%e3%81%93%e3%82%93",
         "https://example.com/%e3%81%93%e3%82%93"),
        # 末尾スラッシュ除去でパスが変更されると canonical（大文字）に再符号化される
        ("https://example.com/%e3%81%93%e3%82%93/",
         "https://example.com/%E3%81%93%E3%82%93"),
        ("https://example.com/%E3%81%93%E3%82%93/",
         "https://example.com/%E3%81%93%E3%82%93"),
        ("https://example.com/こんにちは/",
         "https://example.com/%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF"),
        # query（RawQuery）は素通し（日本語も符号化されない）
        ("https://example.com/a?q=こんにちは", "https://example.com/a?q=こんにちは"),
        # sub-delims の ! は escape 対象だが、パス未変更なら元表記が保持される
        ("https://example.com/a!b", "https://example.com/a!b"),
        # パス変更（末尾スラッシュ除去）で ! も %21 に再符号化される
        ("https://example.com/a!b/", "https://example.com/a%21b"),
        # + はパスの予約文字として不変（空白扱いの復号もしない）
        ("https://example.com/a+b", "https://example.com/a+b"),
        # 末尾の裸 ? は Go の ForceQuery として保持される
        ("https://example.com/a?", "https://example.com/a?"),
    ]
    for raw, want in golden:
        got = _normalize_url(raw)
        assert got == want, f"_normalize_url({raw!r}) = {got!r}, want {want!r}"


def test_normalize_url_invalid_escape_is_error():
    # Go: url.Parse が invalid URL escape "%zz" でエラー → normalizeURL もエラー
    assert _normalize_url("https://example.com/%zz") is None


# --- _normalized_urls ---


def test_normalized_urls_dedupes_and_normalizes():
    # Markdown リンク・裸 URL・全角括弧内・大文字/フラグメント違いの重複を含むテキスト
    text = (
        "参考: [リリース](https://example.com/release) と "
        "https://EXAMPLE.com/release#notes を確認。"
        "補足（https://example.com/other/）も参照。"
    )
    got = _normalized_urls(text)
    want = {"https://example.com/release", "https://example.com/other"}
    assert got == want


# --- check_references: 対象判定（required gate） ---


def test_check_references_skipped_when_not_required():
    # basic 相当（news でなく research_content も無い）は対象外:
    # セクションが無くても全チェック skip=pass
    findings = check_references("intro", None, "## まとめ\n本文のみ")
    assert len(findings) == 4
    for name in ("references_section", "reference_entries", "verification_date",
                 "research_reference_match"):
        f = _find(findings, name)
        assert f.passed, f"{name} should be skip=pass, got failed ({f.detail})"
        assert "skipped" in f.detail
        assert f.severity == "error"
    # Go 実装の出力文字列と一致することも確認する（generation_profile は
    # skip 分岐に到達する時点で必ず "basic" になるため厳密比較できる）
    assert _find(findings, "references_section").detail == (
        "skipped: references not required (generation_profile=basic, article_type=intro)"
    )


def test_check_references_section_missing_required_by_news_type():
    findings = check_references("news", None, "## まとめ\n本文のみ")
    for name in ("references_section", "reference_entries", "verification_date"):
        assert not _find(findings, name).passed, f"expected {name} to fail"
    # research が無いので research_reference_match は skip=pass
    match = _find(findings, "research_reference_match")
    assert match.passed, f"expected skip=pass, got failed ({match.detail})"


def test_check_references_required_by_research_content_present_section_missing():
    """補足テスト（Go テスト由来ではない）。除外 1 の代替カバレッジ。"""
    findings = check_references("impl", "出典: https://go.dev/doc/go1.24", "## まとめ\n本文のみ")
    for name in ("references_section", "reference_entries", "verification_date"):
        assert not _find(findings, name).passed, f"expected {name} to fail"
    match = _find(findings, "research_reference_match")
    assert not match.passed, "expected fail (section missing but research has urls)"


# --- check_references: 代表テスト（task-11.md） ---


def test_research_plan_without_references_section_fails():
    findings = check_references("impl", "リサーチ結果テキスト", "## はじめに\n本文のみ")
    section = next(f for f in findings if f.name == "references_section")
    assert not section.passed


_VALID_REFERENCES_BODY = """本文です。

## 参考情報

- [Go 1.24 Release Notes](https://go.dev/doc/go1.24)（一次情報）
- [解説記事](https://example.com/blog/go124)

情報確認日: 2026-07-03
"""


def test_check_references_all_pass():
    # Go は generation_profile="research"・researchContent=nil で required=True に
    # するが、writeloop の required シグナルは research_content の有無のため、
    # 本文中の URL を含む research_content を渡して required=True にし、
    # 4 チェックすべてが skip でなく実ロジックで pass することを検証する。
    research = "参考: https://go.dev/doc/go1.24 を確認"
    findings = check_references("intro", research, _VALID_REFERENCES_BODY)
    for name in ("references_section", "reference_entries", "verification_date",
                 "research_reference_match"):
        f = _find(findings, name)
        assert f.passed, f"expected {name} to pass, got failed ({f.detail})"
    # skip 分岐でなく実ロジックを通ったことを detail で確認する
    assert _find(findings, "references_section").detail == "references section found"
    assert _find(findings, "research_reference_match").detail == (
        "reference URL matches research URL: https://go.dev/doc/go1.24"
    )


def test_check_references_section_aliases():
    for heading in ("参考文献", "参考リンク"):
        body = (
            f"## {heading}\n\n- [x](https://example.com/a)（一次情報）\n\n"
            "情報確認日: 2026-07-03\n"
        )
        findings = check_references("intro", "dummy", body)
        f = _find(findings, "references_section")
        assert f.passed, f"expected alias heading {heading!r} to pass, got failed ({f.detail})"


def test_check_references_section_heading_inside_code_fence_ignored():
    body = "```\n## 参考情報\n```\n本文のみ"
    findings = check_references("intro", "dummy", body)
    assert not _find(findings, "references_section").passed


# --- check_references: reference_entries (via public API, found=True) ---


def _entries_finding(section_with_heading: str):
    # required=True にするため article_type/research_content は news 以外 + dummy を使う。
    findings = check_references("intro", "dummy", section_with_heading)
    return _find(findings, "reference_entries")


def test_check_reference_entries_no_url_bullets():
    section = "## 参考情報\n\n出典なし\n\n情報確認日: 2026-07-03\n"
    assert not _entries_finding(section).passed


def test_check_reference_entries_entry_without_label():
    section = "## 参考情報\n\n- [x](https://example.com/a)\n\n情報確認日: 2026-07-03\n"
    assert not _entries_finding(section).passed


def test_check_reference_entries_one_primary_one_unlabeled():
    section = (
        "## 参考情報\n\n- [a](https://example.com/a)（一次情報）\n"
        "- [b](https://example.com/b)\n\n情報確認日: 2026-07-03\n"
    )
    assert _entries_finding(section).passed


def test_check_reference_entries_half_width_paren_label_accepted():
    section = "## 参考情報\n\n- [x](https://example.com/a)(一次情報)\n\n情報確認日: 2026-07-03\n"
    assert _entries_finding(section).passed


def test_check_reference_entries_asterisk_bullets_accepted():
    section = "## 参考情報\n\n* [x](https://example.com/a)（一次情報）\n\n情報確認日: 2026-07-03\n"
    assert _entries_finding(section).passed


def test_check_reference_entries_secondary_label_forbidden_table():
    section = (
        "## 参考情報\n\n- [a](https://example.com/a)（一次情報）\n"
        "- [b](https://example.com/b)（二次情報）\n\n情報確認日: 2026-07-03\n"
    )
    assert not _entries_finding(section).passed


def test_check_reference_entries_secondary_label_forbidden_standalone():
    section = (
        "## 参考情報\n\n- [a](https://example.com/a)（一次情報）\n"
        "- [b](https://example.com/b)（二次情報）\n\n情報確認日: 2026-07-06\n"
    )
    f = _entries_finding(section)
    assert not f.passed
    assert f.detail == (
        "1 reference entries have redundant （二次情報） label; "
        "remove the label text only (unlabeled entries are treated as secondary sources)"
    )


def test_check_reference_entries_unlabeled_secondary_allowed_standalone():
    section = (
        "## 参考情報\n\n- [a](https://example.com/a)（一次情報）\n"
        "- [b](https://example.com/b)\n\n情報確認日: 2026-07-06\n"
    )
    f = _entries_finding(section)
    assert f.passed
    assert f.detail == "2 reference entries found (1 primary-labeled)"


def test_check_reference_entries_requires_primary_label_standalone():
    section = "## 参考情報\n\n- [a](https://example.com/a)\n\n情報確認日: 2026-07-06\n"
    f = _entries_finding(section)
    assert not f.passed
    assert f.detail == (
        "no reference entry labeled （一次情報） among 1 entries; "
        "label primary sources (official release/docs, CVE/NVD, GitHub release)"
    )


# --- check_references: verification_date (via public API, found=True) ---


def _date_finding(section: str):
    findings = check_references("intro", "dummy", section)
    return _find(findings, "verification_date")


def test_check_verification_date_missing_line():
    section = "## 参考情報\n\n- [x](https://example.com/a)（一次情報）\n"
    assert not _date_finding(section).passed


def test_check_verification_date_invalid_date():
    section = "## 参考情報\n\n- [x](https://example.com/a)（一次情報）\n\n情報確認日: 2026-13-99\n"
    assert not _date_finding(section).passed


def test_check_verification_date_full_width_colon_accepted():
    section = "## 参考情報\n\n- [x](https://example.com/a)（一次情報）\n\n情報確認日：2026-07-03\n"
    assert _date_finding(section).passed


# --- check_references: research_reference_match ---


def test_check_research_reference_match_after_normalization():
    research = "公式リリース HTTPS://Go.DEV/doc/go1.24/#intro を参照"
    findings = check_references("intro", research, _VALID_REFERENCES_BODY)
    assert _find(findings, "research_reference_match").passed


def test_check_research_reference_match_no_matching_url():
    research = "出典: https://other.example.com/news"
    findings = check_references("intro", research, _VALID_REFERENCES_BODY)
    assert not _find(findings, "research_reference_match").passed


def test_check_research_reference_match_research_without_urls_is_skip():
    research = "URL の無いリサーチ結果"
    findings = check_references("intro", research, _VALID_REFERENCES_BODY)
    assert _find(findings, "research_reference_match").passed


def test_check_research_reference_match_nil_research_is_skip():
    # research_content=None かつ article_type=news で required=True にしつつ、
    # research_reference_match のみを見る（required 自体は news 型が担保する）。
    findings = check_references("news", None, _VALID_REFERENCES_BODY)
    assert _find(findings, "research_reference_match").passed


def test_check_research_reference_match_section_missing_but_research_has_urls():
    research = "出典: https://go.dev/doc/go1.24"
    findings = check_references("intro", research, "## まとめ\n本文のみ")
    assert not _find(findings, "research_reference_match").passed


def test_check_research_reference_match_mixed_raw_and_encoded_url():
    """補足テスト（Go テスト由来ではない。レビュー指摘対応）。

    research 側が生の日本語 URL・記事側が percent-encoded URL でも、
    net/url 相当のパス再エンコードにより正規化後は一致する。
    """
    research = "出典: https://example.com/こんにちは を参照"
    body = (
        "## 参考情報\n\n"
        "- [x](https://example.com/%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF)（一次情報）\n\n"
        "情報確認日: 2026-07-03\n"
    )
    findings = check_references("intro", research, body)
    f = _find(findings, "research_reference_match")
    assert f.passed, f"expected pass, got failed ({f.detail})"
    assert f.detail == (
        "reference URL matches research URL: "
        "https://example.com/%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF"
    )
