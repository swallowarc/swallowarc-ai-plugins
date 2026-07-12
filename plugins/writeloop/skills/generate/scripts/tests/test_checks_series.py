"""checks_series.py のテスト。

移植元: internal/infrastructure/quality/checker_frontmatter.go:203
（checkSeriesConsistency の series==nil 分岐）、
internal/infrastructure/quality/checker_series.go:21
（checkSeriesNavigation の series==nil 分岐）@ autopostd 20c740b。

writeloop は series 非対応（spec スコープ外）のため、series==nil 分岐の
skip=pass 定数のみを検証する。detail 文字列は Go 実装を直接確認して一字一句
移植した（"no series" / "skipped: plan has no series"）。series ありの場合の
本体ロジック（frontmatter series とのマッチ判定・"シリーズの位置づけ" 見出し検出）
は writeloop の対象外のため移植しない。
"""
from wlq.checks_series import check_series_consistency, check_series_navigation


def test_series_checks_are_constant_skip_pass():
    c = check_series_consistency()
    assert (c.passed, c.severity, c.detail) == (True, "error", "no series")
    n = check_series_navigation()
    assert (n.passed, n.severity, n.detail) == (True, "error", "skipped: plan has no series")
