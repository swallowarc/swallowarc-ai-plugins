"""checks_code.py のテスト。

移植元テスト: internal/infrastructure/quality/checker_code_test.go @ autopostd 20c740b
（292行のうち checkCodeLanguageTag / checkCodeKindLabel / checkMermaidContext に
対応する 4 テーブル・21 サブテストを全件移植。取捨選択なし）。

Go テストは checkWithBody(t, articleType, body) ヘルパー経由で
"---\\ntitle: X\\n---\\n" + body を content として RuleBasedChecker.Check() に渡すが、
Check() 内部では parseFrontmatter で fm/body に分離した上で checkCodeLanguageTag(body) /
checkCodeKindLabel(plan.ArticleType(), body) / checkMermaidContext(body) には
frontmatter を除いた body のみを渡す（checker.go:264-326, parseFrontmatter:
lines[closing+1:] を join したものが元の body 引数と同一になる）。そのため本ファイルの
テストは Go テスト本文の body をそのまま各 check_* 関数に直接渡す形に変換する
（checks_structure.py の heading_structure 系テストと同じ変換方針）。

Go テストケース対応表（全件移植。テーブル駆動の t.Run サブテスト名を左に示す）:

TestRuleBasedChecker_CodeLanguageTag（7 サブテスト）:
- "no code blocks passes" -> test_code_language_tag_no_code_blocks_passes
- "tagged block passes" -> test_code_language_tag_tagged_block_passes
- "untagged backtick block fails" -> test_code_language_tag_untagged_backtick_block_fails
- "untagged tilde block fails" -> test_code_language_tag_untagged_tilde_block_fails
- "closing fences tracked correctly" -> test_code_language_tag_closing_fences_tracked_correctly
- "nested fence content ignored" -> test_code_language_tag_nested_fence_content_ignored
- "one of two blocks untagged fails" -> test_code_language_tag_one_of_two_blocks_untagged_fails

TestRuleBasedChecker_CodeKindLabel_Impl（8 サブテスト）:
- "fullwidth label passes" -> test_code_kind_label_fullwidth_label_passes
- "halfwidth label passes" -> test_code_kind_label_halfwidth_label_passes
- "label with extra spaces passes" -> test_code_kind_label_label_with_extra_spaces_passes
- "missing label fails" -> test_code_kind_label_missing_label_fails
- "heading directly before fence fails" -> test_code_kind_label_heading_directly_before_fence_fails
- "unknown label fails" -> test_code_kind_label_unknown_label_fails
- "mermaid block excluded" -> test_code_kind_label_mermaid_block_excluded
- "no code blocks skip passes" -> test_code_kind_label_no_code_blocks_skip_passes

TestRuleBasedChecker_CodeKindLabel_NonImplSkips
    -> test_code_kind_label_non_impl_skips

TestRuleBasedChecker_MermaidContext（5 サブテスト）:
- "text before and after passes" -> test_mermaid_context_text_before_and_after_passes
- "heading immediately before fails" -> test_mermaid_context_heading_immediately_before_fails
- "code block immediately after fails" -> test_mermaid_context_code_block_immediately_after_fails
- "document end after mermaid fails" -> test_mermaid_context_document_end_after_mermaid_fails
- "no mermaid skip passes" -> test_mermaid_context_no_mermaid_skip_passes

--- 移植対象外（意図的な除外。理由付き） ---

- parseFencedCodeBlocks 系（TestParseFencedCodeBlocks_*）: Task 3 で wlq/fences.py /
  tests/test_fences.py に移植済みのため対象外。
- TestCheckCodeLineLength / TestCheckCodeLineLength_DetailReportsBlockStartAndLength:
  Task 6 で wlq/checks_ai_style.py / tests/test_checks_ai_style.py に
  check_code_line_length として移植済みのため対象外。
- checkWithBody / mustFindCheck 自体（テストヘルパー。RuleBasedChecker.Check() の
  オーケストレーション経由でチェックを取得する仕組みそのものは Task 12
  （qualitycheck.py CLI）スコープであり、本タスクのインターフェース
  （check_code_language_tag / check_code_kind_label / check_mermaid_context の
  3 純粋関数）の範囲外。ただし各テーブルケースが検証する「特定の body に対する
  当該チェックの pass/fail」という内容自体は上記の通り全件移植する。
"""

from wlq.checks_code import (
    check_code_kind_label,
    check_code_language_tag,
    check_mermaid_context,
)


# --- check_code_language_tag ---


def test_code_language_tag_no_code_blocks_passes():
    f = check_code_language_tag("## 結論・要点\n本文のみ。")
    assert f.passed is True
    assert f.severity == "error"


def test_code_language_tag_tagged_block_passes():
    f = check_code_language_tag("## 結論・要点\n\n```go\nfmt.Println(1)\n```\n")
    assert f.passed is True
    assert f.severity == "error"


def test_code_language_tag_untagged_backtick_block_fails():
    f = check_code_language_tag("## 結論・要点\n\n```\nplain\n```\n")
    assert f.passed is False
    assert f.severity == "error"


def test_code_language_tag_untagged_tilde_block_fails():
    f = check_code_language_tag("## 結論・要点\n\n~~~\nplain\n~~~\n")
    assert f.passed is False
    assert f.severity == "error"


def test_code_language_tag_closing_fences_tracked_correctly():
    # 閉じフェンスが「タグ無しの新規開始フェンス」と誤認されないこと
    body = "## 結論・要点\n\n```go\na := 1\n```\n\n本文。\n\n```yaml\nkey: v\n```\n"
    f = check_code_language_tag(body)
    assert f.passed is True


def test_code_language_tag_nested_fence_content_ignored():
    # 外側フェンス（backtick 4 つ）内の ``` は内容として扱う
    body = "## 結論・要点\n\n````markdown\n```\ninner\n```\n````\n"
    f = check_code_language_tag(body)
    assert f.passed is True


def test_code_language_tag_one_of_two_blocks_untagged_fails():
    body = "## 結論・要点\n\n```go\na := 1\n```\n\n```\nb\n```\n"
    f = check_code_language_tag(body)
    assert f.passed is False


# --- check_code_kind_label (article_type="impl") ---


def test_code_kind_label_fullwidth_label_passes():
    body = "## 実装\n\n（コード種別: 実行可能）\n\n```go\ncode\n```\n\n説明。"
    f = check_code_kind_label("impl", body)
    assert f.passed is True


def test_code_kind_label_halfwidth_label_passes():
    body = "## 実装\n\n(コード種別:疑似コード)\n```python\ncode\n```\n\n説明。"
    f = check_code_kind_label("impl", body)
    assert f.passed is True


def test_code_kind_label_label_with_extra_spaces_passes():
    body = "## 実装\n\n（ コード種別 : 概念例 ）\n\n```go\ncode\n```\n\n説明。"
    f = check_code_kind_label("impl", body)
    assert f.passed is True


def test_code_kind_label_missing_label_fails():
    body = "## 実装\n\n手順の説明のみ。\n\n```go\ncode\n```\n"
    f = check_code_kind_label("impl", body)
    assert f.passed is False


def test_code_kind_label_heading_directly_before_fence_fails():
    body = "## 実装\n\n```go\ncode\n```\n"
    f = check_code_kind_label("impl", body)
    assert f.passed is False


def test_code_kind_label_unknown_label_fails():
    body = "## 実装\n\n（コード種別: サンプル）\n\n```go\ncode\n```\n"
    f = check_code_kind_label("impl", body)
    assert f.passed is False


def test_code_kind_label_mermaid_block_excluded():
    body = "## 構成\n\n図の目的。\n\n```mermaid\ngraph TD\n```\n\n読み取りポイント。"
    f = check_code_kind_label("impl", body)
    assert f.passed is True


def test_code_kind_label_no_code_blocks_skip_passes():
    f = check_code_kind_label("impl", "## 実装\n\n本文のみ。")
    assert f.passed is True


def test_code_kind_label_non_impl_skips():
    # impl 以外はラベル無しコードブロックがあっても skip=pass
    f = check_code_kind_label("intro", "## 実装\n\n```go\ncode\n```\n")
    assert f.passed is True
    assert "skip" in f.detail


# --- check_mermaid_context ---


def test_mermaid_context_text_before_and_after_passes():
    body = (
        "## 構成\n\nこの図はデータの流れを示す。\n\n```mermaid\ngraph TD\n"
        "  A --> B\n```\n\nA から B へ一方向に流れる点がポイント。"
    )
    f = check_mermaid_context(body)
    assert f.passed is True


def test_mermaid_context_heading_immediately_before_fails():
    body = "## 構成\n\n```mermaid\ngraph TD\n```\n\n読み取りポイント。"
    f = check_mermaid_context(body)
    assert f.passed is False


def test_mermaid_context_code_block_immediately_after_fails():
    body = "## 構成\n\n図の目的。\n\n```mermaid\ngraph TD\n```\n\n```go\ncode\n```\n\n本文。"
    f = check_mermaid_context(body)
    assert f.passed is False


def test_mermaid_context_document_end_after_mermaid_fails():
    body = "## 構成\n\n図の目的。\n\n```mermaid\ngraph TD\n```\n"
    f = check_mermaid_context(body)
    assert f.passed is False


def test_mermaid_context_no_mermaid_skip_passes():
    f = check_mermaid_context("## 実装\n\n```go\ncode\n```\n\n説明。")
    assert f.passed is True
