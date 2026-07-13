"""checks_title.py のテスト。

移植元テスト: internal/infrastructure/quality/checker_title_test.go @ autopostd 20c740b
（120行）。

TestCheckTitleLength は checker.checkTitleLength(fm) を直接呼ぶ表形式テストで、
Task 9 のインターフェース（check_title_length(fm, *, len_min, len_max)）とそのまま
1:1 対応するため、テーブルの 9 ケース全件を test_check_title_length の
parametrize にそのまま移植する。

Go テストケース対応表（全件移植。取捨選択なし）:

TestCheckTitleLength の 9 サブケース（すべて test_check_title_length に
pytest.mark.parametrize で移植）:
    "19 runes is warning fail (too short)"
    "33 runes is warning fail (too long)"
    "20 runes boundary passes"
    "32 runes boundary passes"
    "26 runes mid-range passes"
    "title missing is skip pass"
    "title empty is skip pass"
    "title whitespace-only is skip pass"
    "series-prefixed title is measured as a whole"

--- 移植対象外（意図的な除外。取捨選択ではなく統合テストのため） ---

TestRuleBasedChecker_TitleLengthRegistered:
    RuleBasedChecker.Check() 経由で title_length チェックが実際に登録・配線されて
    いることを検証する回帰（配線）テスト。Task 9 のインターフェースは
    check_title_length(fm) を直接呼ぶ純粋関数であり、Check() オーケストレータへの
    配線は qualitycheck.py 側（Task 12 スコープ）で検証する。
"""

import pytest

from wlq.checks_title import check_title_length


@pytest.mark.parametrize(
    "case, fm, want_passed, want_skip",
    [
        ("19 runes is warning fail (too short)", {"title": "あ" * 19}, False, False),
        ("33 runes is warning fail (too long)", {"title": "あ" * 33}, False, False),
        ("20 runes boundary passes", {"title": "あ" * 20}, True, False),
        ("32 runes boundary passes", {"title": "あ" * 32}, True, False),
        ("26 runes mid-range passes", {"title": "あ" * 26}, True, False),
        ("title missing is skip pass", {"description": "x"}, True, True),
        ("title empty is skip pass", {"title": ""}, True, True),
        ("title whitespace-only is skip pass", {"title": "   "}, True, True),
        (
            "series-prefixed title is measured as a whole",
            {"title": "連載 #01 " + "あ" * 18},
            True,
            False,
        ),
    ],
)
def test_check_title_length(case, fm, want_passed, want_skip):
    f = check_title_length(fm)
    assert f.name == "title_length"
    assert f.severity == "warning"
    assert f.passed == want_passed
    assert f.detail.startswith("skip:") == want_skip
    if not want_passed:
        assert f.suggestion != ""
