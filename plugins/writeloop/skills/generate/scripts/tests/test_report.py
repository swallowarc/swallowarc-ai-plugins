"""wlq/report.py（render_report）のテスト。task-14.md 記載の完全仕様テスト。

render_report は本番 Go 側に対応物を持たない（writeloop 独自の決定論的整形物。
本番はレポートを持たず Slack 通知文言を組み立てるのみ）。決定論性（同一入力
から常に同一出力）そのものが要求仕様であるため、それを直接固定する。
"""
from wlq.gate import decide
from wlq.model import check_fail
from wlq.report import render_report


def test_report_contains_verdict_and_error_table():
    d = decide([check_fail("body_length", "too short", "肉付けする", "error")], [], [],
               round_num=1, max_retries=2, prev_failed_error_keys=None)
    md = render_report(d, mode="article")
    assert "continue" in md
    assert "body_length" in md and "肉付けする" in md


def test_report_is_deterministic():
    d = decide([check_fail("body_length", "too short", "肉付けする", "error")], [], [],
               round_num=1, max_retries=2, prev_failed_error_keys=None)
    assert render_report(d, mode="article") == render_report(d, mode="article")
