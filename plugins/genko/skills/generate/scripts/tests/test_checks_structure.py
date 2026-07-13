"""checks_structure.py のテスト。

移植元テスト: internal/infrastructure/quality/checker_test.go @ autopostd 20c740b
（HeadingStructure 系 5 件・RequiredSections 系 2 件。全件移植・取捨選択なし）。

Go テストは RuleBasedChecker.Check() 経由で frontmatter 込みの content を渡すが、
Check() 内部では parseFrontmatter で fm/body に分離した上で
checkHeadingStructure(body) には body のみを渡す（checker.go:272,278）。
そのため heading_structure 側のテストは、Go テスト本文から frontmatter 部分
（"---\ntitle: X\n---\n"）を除いた body を直接 check_heading_structure に渡す形に
変換する。一方 checkRequiredSections(plan, content) は Go でも frontmatter 込みの
content をそのまま受け取る（checker.go:316）ため、required_sections 側は
frontmatter 込みの文字列をそのまま check_required_sections に渡す。

Go テストケース対応表（全件移植。取捨選択なし）:

TestRuleBasedChecker_HeadingStructure_H1Fails
    -> test_check_heading_structure_h1_fails
TestRuleBasedChecker_HeadingStructure_FirstHeadingNotH2Fails
    -> test_check_heading_structure_first_heading_not_h2_fails
TestRuleBasedChecker_HeadingStructure_LevelJumpFails
    -> test_check_heading_structure_level_jump_fails
TestRuleBasedChecker_HeadingStructure_CleanStructurePasses
    -> test_check_heading_structure_clean_structure_passes
TestRuleBasedChecker_HeadingStructure_IgnoresFencedCodeBlock
    -> test_check_heading_structure_ignores_fenced_code_block
TestRuleBasedChecker_RequiredSections
    -> test_check_required_sections_intro_pass
    -> test_check_required_sections_intro_missing_fails
TestRuleBasedChecker_RequiredSections_FencedHeadingDoesNotSatisfy
    -> test_check_required_sections_fenced_heading_does_not_satisfy
    -> test_check_required_sections_real_heading_passes

--- 移植対象外（意図的な除外。取捨選択ではなく checker_test.go の対象範囲外） ---

domain/required_sections_test.go（TestRequiredSectionsFor /
TestRequiredSectionsFor_LeadSectionsMergedIntoIntro / TestRequiredSection_Matches_Alias）:
    domain パッケージ側の単体テストであり、checker_test.go の対象ではない
    （task-09.md が明示する移植対象は checker_test.go の HeadingStructure 系 5 件・
    RequiredSections 系 2 件のみ）。ただし domain/required_sections.go 由来の
    news ラベル要件（重要度/影響範囲/推奨アクション）は checker_test.go の既存 2 ケースが
    news 型を扱っていないため検証されないままになる。挙動を固定するため、下記に
    checker_test.go 由来ではない補足テストを追加する（1:1 対応表には含めない）。
"""

from wlq.checks_structure import check_heading_structure, check_required_sections


def test_check_heading_structure_h1_fails():
    body = "# X\n\n## 概要\n本文\n"
    f = check_heading_structure(body)
    assert f.passed is False
    assert f.severity == "error"
    assert f.detail == "body must not contain H1"


def test_check_heading_structure_first_heading_not_h2_fails():
    body = "### 概要\n本文\n"
    f = check_heading_structure(body)
    assert f.passed is False
    assert f.detail == "top heading must be H2"


def test_check_heading_structure_level_jump_fails():
    body = "## 概要\n本文\n#### 詳細\n本文\n"
    f = check_heading_structure(body)
    assert f.passed is False
    assert f.detail == "heading level jump from H2 to H4"


def test_check_heading_structure_clean_structure_passes():
    body = "## 概要\n本文\n### 詳細\n本文\n## まとめ\n本文\n"
    f = check_heading_structure(body)
    assert f.passed is True
    assert f.detail == "heading structure ok"


def test_check_heading_structure_ignores_fenced_code_block():
    body = "## 概要\n本文\n```bash\n# install deps\n## step 2\n```\n## まとめ\n本文\n"
    f = check_heading_structure(body)
    assert f.passed is True
    assert f.detail == "heading structure ok"


def test_check_required_sections_intro_pass():
    content = (
        "---\ntitle: X\n---\n"
        "## はじめに\n..\n## 結論・要点\n..\n## 次にやること\n.."
    )
    f = check_required_sections("intro", content)
    assert f.passed is True
    assert f.detail == "all required sections present"


def test_check_required_sections_intro_missing_fails():
    content = "---\ntitle: X\n---\n## 結論・要点\n.."
    f = check_required_sections("intro", content)
    assert f.passed is False
    assert f.detail == "missing sections: はじめに, 次にやること"


def test_check_required_sections_fenced_heading_does_not_satisfy():
    # general 記事タイプは "結論・要点" のみが必須。フェンス内の見出しは
    # 見出しとしてカウントされてはならないため、required_sections は FAIL する。
    content = "---\ntitle: X\n---\n```\n## 結論・要点\n```\n"
    f = check_required_sections("general", content)
    assert f.passed is False
    assert f.detail == "missing sections: 結論・要点"


def test_check_required_sections_real_heading_passes():
    # 対照実験: フェンス外の本物の見出しであれば required_sections は PASS する。
    content = "---\ntitle: X\n---\n## 結論・要点\n本文\n"
    f = check_required_sections("general", content)
    assert f.passed is True
    assert f.detail == "all required sections present"


# --- 補足テスト（checker_test.go 由来ではない。news ラベル要件の固定用） ---


def test_check_required_sections_news_missing_labels_fails():
    content = (
        "---\ntitle: X\n---\n"
        "## はじめに\n..\n## 結論・要点\n..\n## 次にやること\n..\n"
        "重要度: 高\n影響範囲: 全体\n"
    )
    f = check_required_sections("news", content)
    assert f.passed is False
    assert f.detail == "missing sections: 推奨アクション"


def test_check_required_sections_news_all_labels_present_passes():
    content = (
        "---\ntitle: X\n---\n"
        "## はじめに\n..\n## 結論・要点\n..\n## 次にやること\n..\n"
        "重要度: 高\n影響範囲: 全体\n推奨アクション: 様子見\n"
    )
    f = check_required_sections("news", content)
    assert f.passed is True
    assert f.detail == "all required sections present"
