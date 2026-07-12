"""mdscan.py のテスト。

移植元:
- internal/infrastructure/quality/checker_structure.go @ autopostd 20c740b
  (headingRe:13, anyHeadingRe:18, extractHeadings:101-110, stripFencedCodeBlocks:120-135)
- internal/infrastructure/quality/checker_references.go @ autopostd 20c740b
  (referencesSectionNames:53, refH2Re:57, isReferencesHeading:90-97)

Go 側専用ユニットテストの有無（重要）:
extractHeadings / isReferencesHeading にはそれぞれを直接呼ぶ専用のテスト関数が
Go 側に存在しない。checker_structure_test.go というファイル自体が無く、
checker_references_test.go にも isReferencesHeading を直接呼ぶテストは無い
（isReferencesHeading は findReferencesSection 経由でのみ間接的に使われる）。
したがって「Go テストケースの全件移植」の対象となる Go テストテーブルは
両関数について空であり、下記のテストは Go 実装本文を読んで確定させた挙動を
直接検証するものである（.kata/task-03.md の指示どおり、実装を読んで期待値を
確定させてから書いている）。

間接的に挙動を裏付ける既存の Go テスト（参考。直接の移植対象ではない）:
- TestRuleBasedChecker_RequiredSections（checker_test.go:61）
- TestRuleBasedChecker_RequiredSections_FencedHeadingDoesNotSatisfy（checker_test.go:346）
  -> フェンス内の "## 見出し" は required_sections の判定に寄与しない。
     checkRequiredSections は extractHeadings の結果を使うため、これは
     extractHeadings がフェンス内行を除外することの根拠になる。
- TestCheckReferences_AllPass（checker_references_test.go:164）
- TestCheckReferences_SectionAliases（checker_references_test.go:174）
  -> 正規名「参考情報」・別名「参考文献」「参考リンク」がいずれも
     references_section を PASS させる。isReferencesHeading がこれら 3 表記を
     受理することの根拠になる。

タスク本文 (.kata/task-03.md) Step 1 の代表ケース test_is_references_heading は
そのまま収録する。
"""

from wlq.mdscan import extract_headings, is_references_heading


# --- タスク本文 Step 1 の代表ケース（そのまま収録） ---

def test_is_references_heading():
    assert is_references_heading("参考情報")
    assert is_references_heading("参考文献")
    assert is_references_heading("参考リンク")
    assert not is_references_heading("まとめ")


# --- is_references_heading: Go 実装 checker_references.go:90-97 から確定させた挙動 ---

def test_is_references_heading_trims_surrounding_whitespace():
    """Go: h := strings.TrimSpace(heading) (checker_references.go:91)。"""
    assert is_references_heading("  参考情報  ")


def test_is_references_heading_requires_exact_match_not_substring():
    """Go は referencesSectionNames との完全一致のみ判定する（部分一致・前方一致は
    不可）(checker_references.go:92-96)。
    """
    assert not is_references_heading("参考情報について")
    assert not is_references_heading("参考")
    assert not is_references_heading("References")


# --- extract_headings: Go 実装 checker_structure.go:101-110 から確定させた挙動 ---

def test_extract_headings_returns_heading_text_without_hashes():
    """headingRe = `^#{2,}\\s+(.*)$` (checker_structure.go:13) の capture group
    (見出し記号・空白を除いたテキスト部分) を trim して返す。「## A」→「A」。
    """
    content = "## A\n本文\n### B\n"
    assert extract_headings(content) == ["A", "B"]


def test_extract_headings_excludes_h1():
    """headingRe は `#{2,}` のため H1（# 1 個）にはマッチしない
    （H1 除外は checker_structure.go:16-17 のコメントどおり）。
    """
    content = "# Title\n## A\n"
    assert extract_headings(content) == ["A"]


def test_extract_headings_ignores_fenced_code_block_content():
    """stripFencedCodeBlocks によりフェンス内の行は事前に除外され、コード中の
    "# install" 等が見出しとして誤検出されない（checker_structure.go:98-100）。
    """
    content = (
        "## 概要\n本文\n"
        "```bash\n# install deps\n## step 2\n```\n"
        "## まとめ\n本文\n"
    )
    assert extract_headings(content) == ["概要", "まとめ"]


def test_extract_headings_no_headings_returns_empty_list():
    assert extract_headings("本文のみ\n") == []


def test_extract_headings_trims_surrounding_whitespace_in_heading_text():
    content = "##   見出し   \n"
    assert extract_headings(content) == ["見出し"]


def test_extract_headings_fence_toggle_ignores_symbol_and_indentation_mismatch():
    """stripFencedCodeBlocks (checker_structure.go:120-135) は単純なトグル方式で
    あり、開始・終了フェンスの記号一致や長さの厳密な検証を行わない
    （parse_fenced_code_blocks とは意図的に別実装。checker_code.go:20-24 の
    コメント「既存の stripFencedCodeBlocks（単純トグル方式）とは異なり」を参照）。
    ``` で始まったフェンスが ~~~ 行でトグルオフされても正しく非フェンス扱いに戻る。
    """
    content = "```\n## フェンス内は除外\n~~~\n## フェンス外なので見出し\n"
    assert extract_headings(content) == ["フェンス外なので見出し"]
