"""checks_length.py のテスト。

移植元テスト: internal/infrastructure/quality/checker_length_test.go @ autopostd
20c740b（97行）。task-09.md に記載の完全実装例をそのまま使用する。

TestCheckBodyLength の 7 サブケースは、下記 parametrize の case 名（Go の
t.Run(tt.name...) と同じ日本語ラベル）でそのまま 1:1 対応する（全件移植・
取捨選択なし）:
    "レンジ内" / "超過" / "不足" / "字数指定なしは skip" / "半角チルダ表記" /
    "単一上限表記「5000字以内」" / "逆転レンジは swap して解釈"

--- 移植対象外（意図的な除外。取捨選択ではなく統合テストのため） ---

TestRuleBasedChecker_BodyLengthRegistered:
    RuleBasedChecker.Check() 経由で body_length チェックが実際に登録・配線されて
    いることを検証する回帰（配線）テスト。Task 9 のインターフェースは
    check_body_length(constraints, body) を直接呼ぶ純粋関数であり、Check()
    オーケストレータへの配線は qualitycheck.py 側（Task 12 スコープ）で検証する。
"""
import pytest
from wlq.checks_length import check_body_length


@pytest.mark.parametrize("case, constraints, prose_len, want_passed, want_skip", [
    ("レンジ内", ["3000〜5000字"], 4000, True, False),
    ("超過", ["3000〜5000字"], 6000, False, False),
    ("不足", ["3000〜5000字"], 1000, False, False),
    ("字数指定なしは skip", ["コードを含める"], 100, True, True),
    ("半角チルダ表記", ["3000~5000字"], 4000, True, False),
    ("単一上限表記「5000字以内」", ["5000字以内"], 4000, True, False),
    ("逆転レンジは swap して解釈", ["5000〜3000字"], 4000, True, False),
])
def test_check_body_length(case, constraints, prose_len, want_passed, want_skip):
    body = "あ。" * (prose_len // 2)
    f = check_body_length(constraints, body)
    assert f.passed == want_passed
    assert f.detail.startswith("skip") == want_skip
