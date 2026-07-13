"""checks_narration.py（genko 独自。対応する Go 移植元テストは無い）のテスト。

check_progress_narration_freq は jp-writing:cognitive-rhythm-writing の
「文書を更新する文（駄文）」のうち定型化できる進行実況を頻度制限する
（詳細は wlq/checks_narration.py のモジュール docstring 参照）。

- test_three_or_more_occurrences_fail: 上限（既定 2）超過で warning fail
- test_two_occurrences_pass_at_boundary: 境界値ちょうどは pass
- test_single_lead_announcement_passes: 導入の予告 1 回は pass（正当な用途を許す設計）
- test_neutral_prose_passes: 進行実況を含まない地の文は pass
- test_fail_detail_reports_per_phrase_breakdown: detail にフレーズ別内訳を出す
- test_multiple_patterns_in_one_sentence_are_each_counted: 1 文に複数パターンが
  あればそれぞれ数える（文単位ではなくフレーズ単位のカウントであることの固定）
"""
from wlq.checks_narration import check_progress_narration_freq


def test_three_or_more_occurrences_fail():
    prose = (
        "本記事では Temporal の運用を扱います。"
        "ここまで見てきたように設定は単純です。"
        "次は監視の仕組みを紹介していきます。"
    )
    c = check_progress_narration_freq(prose)
    assert c.name == "progress_narration_freq"
    assert c.severity == "warning"
    assert c.passed is False


def test_two_occurrences_pass_at_boundary():
    prose = (
        "本記事では Temporal の運用を扱います。"
        "ワーカーの再起動手順を紹介していきます。"
    )
    c = check_progress_narration_freq(prose)
    assert c.passed is True


def test_single_lead_announcement_passes():
    prose = "本記事では Temporal ワーカーの安全な再起動手順を説明します。"
    c = check_progress_narration_freq(prose)
    assert c.passed is True


def test_neutral_prose_passes():
    prose = (
        "ワーカーは SIGTERM を受けると、実行中のアクティビティを完了させてから停止します。"
        "この挙動により、再起動中もワークフローの状態は失われません。"
    )
    c = check_progress_narration_freq(prose)
    assert c.passed is True


def test_fail_detail_reports_per_phrase_breakdown():
    prose = (
        "本記事では設定を扱います。"
        "ここまで見てきたように単純です。"
        "次のセクションでは監視を見ていきます。"
    )
    c = check_progress_narration_freq(prose)
    assert c.passed is False
    for want in ["本記事では=1", "ここまで見てき=1", "次のセクションでは=1", "見ていきます=1"]:
        assert want in c.detail


def test_multiple_patterns_in_one_sentence_are_each_counted():
    # 「次のセクションでは〜を見ていきます」は 2 カウント。上限 1 なら fail する。
    prose = "次のセクションでは監視を見ていきます。"
    c = check_progress_narration_freq(prose, max_total=1)
    assert c.passed is False
    assert "2" in c.detail
