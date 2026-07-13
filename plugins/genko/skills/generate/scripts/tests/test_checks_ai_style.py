"""checks_ai_style.py のテスト。

移植元テスト:
- internal/infrastructure/quality/checker_ai_style_test.go @ autopostd 20c740b（685行）
- internal/infrastructure/quality/checker_ai_style_calibration_test.go @ autopostd 20c740b（112行）
- internal/infrastructure/quality/checker_code_test.go の checkCodeLineLength 系
  @ autopostd 20c740b

Go テストケース対応表（全件移植。テーブル駆動の t.Run サブテスト名を左に示す）:

TestCheckBoldColonList（4 サブテスト）:
- "3 bold-colon list items fail" -> test_check_bold_colon_list_3_items_fail
- "2 bold-colon list items pass" -> test_check_bold_colon_list_2_items_pass
- "full-width colon is counted" -> test_check_bold_colon_list_full_width_colon_is_counted
- "items inside code block are not counted"
    -> test_check_bold_colon_list_items_inside_code_block_not_counted

TestCheckEmojiMarkers（5 サブテスト）:
- "list emoji marker fails (even 1)" -> test_check_emoji_markers_list_emoji_marker_fails_even_1
- "heading emoji marker fails (even 1)"
    -> test_check_emoji_markers_heading_emoji_marker_fails_even_1
- "arrow emoji marker fails" -> test_check_emoji_markers_arrow_emoji_marker_fails
- "body emoji not at marker start passes"
    -> test_check_emoji_markers_body_emoji_not_at_marker_start_passes
- "emoji inside code block is not counted"
    -> test_check_emoji_markers_emoji_inside_code_block_not_counted

TestCheckHypeExpressions（3 サブテスト）:
- "hype expressions across categories fail"
    -> test_check_hype_expressions_across_categories_fail
- "neutral evidence-based prose passes"
    -> test_check_hype_expressions_neutral_evidence_based_prose_passes
- "heading hype is excluded from scan (splitSentences drops heading lines)"
    -> test_check_hype_expressions_heading_hype_excluded_from_scan

TestCheckSentenceEndingRun（4 サブテスト + 2 個別 t.Run）:
- "4 consecutive です sentences fail" -> test_check_sentence_ending_run_4_consecutive_desu_fail
- "3 consecutive です sentences pass (at boundary)"
    -> test_check_sentence_ending_run_3_consecutive_desu_pass_at_boundary
- "です2+ます2 alternating passes (です and ます are tracked separately)"
    -> test_check_sentence_ending_run_desu_masu_alternating_passes
- "a non-matching sentence resets the run"
    -> test_check_sentence_ending_run_non_matching_sentence_resets_run
- "fail detail reports the ending, run length, and first offending sentence"
    -> test_check_sentence_ending_run_fail_detail_reports_ending_length_and_first_sentence
- "fail detail truncates a long first sentence with ellipsis"
    -> test_check_sentence_ending_run_fail_detail_truncates_long_first_sentence

TestCheckRhetoricalContrastFreq（2 サブテスト + 1 個別 t.Run）:
- "4 occurrences fail" -> test_check_rhetorical_contrast_freq_4_occurrences_fail
- "3 occurrences pass (at boundary)"
    -> test_check_rhetorical_contrast_freq_3_occurrences_pass_at_boundary
- "fail detail reports occurrence count and limit; suggestion is verbatim"
    -> test_check_rhetorical_contrast_freq_fail_detail_and_suggestion

TestCheckClichePhrases（2 サブテスト + 1 個別 t.Run）:
- "4 total occurrences fail" -> test_check_cliche_phrases_4_total_occurrences_fail
- "3 total occurrences pass (at boundary)"
    -> test_check_cliche_phrases_3_total_occurrences_pass_at_boundary
- "fail detail reports a per-phrase breakdown"
    -> test_check_cliche_phrases_fail_detail_reports_per_phrase_breakdown

TestCheckNegationFirstFreq_NoDoubleCount -> test_check_negation_first_freq_no_double_count

TestCheckNegationFirstFreq（4 サブテスト + 2 個別 t.Run）:
- "4 occurrences pass (at boundary)"
    -> test_check_negation_first_freq_4_occurrences_pass_at_boundary
- "5 occurrences fail" -> test_check_negation_first_freq_5_occurrences_fail
- "single わけではありません is not double-counted with ではありません"
    -> test_check_negation_first_freq_single_wake_dewa_not_double_counted
- "neutral prose passes" -> test_check_negation_first_freq_neutral_prose_passes
- "empty pattern elements are ignored" -> test_check_negation_first_freq_empty_pattern_elements_ignored
- "fail detail reports count, limit and per-phrase breakdown"
    -> test_check_negation_first_freq_fail_detail_reports_breakdown

TestCheckSentenceEndingVariety（3 サブテスト + 2 個別 t.Run）:
- "40 sentences with 36 desu/masu (90%) fail"
    -> test_check_sentence_ending_variety_90_percent_fail
- "40 sentences with 32 desu/masu (80%) pass"
    -> test_check_sentence_ending_variety_80_percent_pass
- "only 20 sentences is skipped (< 30) and passes"
    -> test_check_sentence_ending_variety_20_sentences_skipped_passes
- "fail detail reports the measured ratio and sentence counts"
    -> test_check_sentence_ending_variety_fail_detail_reports_ratio_and_counts
- "skip detail reports the sentence count and threshold"
    -> test_check_sentence_ending_variety_skip_detail_reports_count_and_threshold

TestCheckCodeLineLength（5 サブテスト）:
- "81-rune line inside code block fails" -> test_check_code_line_length_81_rune_line_fails
- "80-rune line inside code block passes" -> test_check_code_line_length_80_rune_line_passes
- "long line counted by runes not bytes (80 multibyte runes pass)"
    -> test_check_code_line_length_multibyte_runes_counted_not_bytes
- "long line outside code block is ignored (pass)"
    -> test_check_code_line_length_outside_code_block_ignored
- "no code block skips (pass)" -> test_check_code_line_length_no_code_block_skips

TestCheckCodeLineLength_DetailReportsBlockStartAndLength
    -> test_check_code_line_length_detail_reports_block_start_and_length

TestRuleBasedChecker_SpecExample1_NoPrematureDetection（本体は checker.checkSentenceEndingRun /
checker.checkRhetoricalContrastFreq を直接呼ぶ純粋関数レベルのアサーションのため、
Check() 統合部分ではなく検証内容のみユニットテストとして移植する）:
- sentence_ending_run 部分 -> test_spec_example1_sentence_ending_run_passes
- rhetorical_contrast_freq 部分 -> test_spec_example1_rhetorical_contrast_freq_passes

checker_ai_style_calibration_test.go（checker.checkNegationFirstFreq /
checker.checkSentenceEndingVariety を直接呼ぶ純粋関数レベルのテストのため、そのまま移植）:
- TestCalibration_DefaultThresholds_DoNotOverDetect
    -> test_calibration_default_thresholds_do_not_over_detect
- TestCalibration_NegationFirstFreq_AggregateCorpusTrips
    -> test_calibration_negation_first_freq_aggregate_corpus_trips

--- 移植対象外（意図的な除外。RuleBasedChecker.Check() 経由の統合テストは Task 12 スコープ） ---

- TestRuleBasedChecker_RhetoricalContrastFreq_ExcludesCodeFence
- TestRuleBasedChecker_NegationFirstFreq_ExcludesCodeFence
- TestRuleBasedChecker_SentenceEndingVarietyRegistered
- TestRuleBasedChecker_Phase2AIStyleChecksRegistered
- TestRuleBasedChecker_DisabledChecks_SkipsNamedCheck
- TestRuleBasedChecker_AIStyleChecksRegistered

これらは Check() のオーケストレーション（prose 抽出パイプライン経由の fenced code
除外・チェック登録・disabled_checks 機構）を検証する回帰テストであり、本タスクの
インターフェース（9 個の純粋チェック関数）の範囲外（Task 12: qualitycheck.py CLI が
該当）。report-task-06.md に除外テスト名として記録する。

--- 追加: .kata/task-06.md 記載の代表テスト（そのまま収録） ---

test_bold_colon_list_over_limit_fails
test_bold_colon_list_inside_code_fence_is_ignored
test_cliche_phrases_total_over_limit_fails
"""

from wlq.checks_ai_style import (
    check_bold_colon_list,
    check_cliche_phrases,
    check_code_line_length,
    check_emoji_markers,
    check_hype_expressions,
    check_negation_first_freq,
    check_rhetorical_contrast_freq,
    check_sentence_ending_run,
    check_sentence_ending_variety,
)

# --- TestCheckBoldColonList ---


def test_check_bold_colon_list_3_items_fail():
    body = "- **項目1**: 説明1\n- **項目2**: 説明2\n- **項目3**: 説明3\n"
    c = check_bold_colon_list(body)
    assert c.name == "bold_colon_list"
    assert c.severity == "warning"
    assert c.passed is False


def test_check_bold_colon_list_2_items_pass():
    body = "- **項目1**: 説明1\n- **項目2**: 説明2\n"
    c = check_bold_colon_list(body)
    assert c.passed is True


def test_check_bold_colon_list_full_width_colon_is_counted():
    body = "* **項目1**：説明1\n+ **項目2**：説明2\n- **項目3**：説明3\n"
    c = check_bold_colon_list(body)
    assert c.passed is False


def test_check_bold_colon_list_items_inside_code_block_not_counted():
    body = "```md\n- **A**: a\n- **B**: b\n- **C**: c\n```\n- **D**: d\n"
    c = check_bold_colon_list(body)
    assert c.passed is True


# --- TestCheckEmojiMarkers ---


def test_check_emoji_markers_list_emoji_marker_fails_even_1():
    c = check_emoji_markers("- ✅ 完了\n")
    assert c.name == "emoji_markers"
    assert c.severity == "warning"
    assert c.passed is False


def test_check_emoji_markers_heading_emoji_marker_fails_even_1():
    c = check_emoji_markers("## 💡 ヒント\n")
    assert c.passed is False


def test_check_emoji_markers_arrow_emoji_marker_fails():
    c = check_emoji_markers("- ⚠ 注意\n")
    assert c.passed is False


def test_check_emoji_markers_body_emoji_not_at_marker_start_passes():
    c = check_emoji_markers("これは絵文字✅を含む本文です。\n")
    assert c.passed is True


def test_check_emoji_markers_emoji_inside_code_block_not_counted():
    c = check_emoji_markers("```text\n- ✅ done\n## 💡 hint\n```\n")
    assert c.passed is True


# --- TestCheckHypeExpressions ---


def test_check_hype_expressions_across_categories_fail():
    prose = "これは革命的な手法です。まさにゲームチェンジャーであり、この問題を完全に解決します。"
    c = check_hype_expressions(prose)
    assert c.name == "hype_expressions"
    assert c.severity == "warning"
    assert c.passed is False
    for w in ["革命的", "ゲームチェンジャー", "完全に解決"]:
        assert w in c.detail


def test_check_hype_expressions_neutral_evidence_based_prose_passes():
    c = check_hype_expressions("この手法は計測の結果、処理時間を半分にした。")
    assert c.passed is True


def test_check_hype_expressions_heading_hype_excluded_from_scan():
    c = check_hype_expressions("## 革命的なアーキテクチャ\nこの構成は計測結果に基づく。")
    assert c.passed is True


# --- TestCheckSentenceEndingRun ---


def test_check_sentence_ending_run_4_consecutive_desu_fail():
    prose = "これは最初の文です。これは二番目の文です。これは三番目の文です。これは四番目の文です。"
    c = check_sentence_ending_run(prose)
    assert c.name == "sentence_ending_run"
    assert c.severity == "warning"
    assert c.passed is False


def test_check_sentence_ending_run_3_consecutive_desu_pass_at_boundary():
    prose = "これは最初の文です。これは二番目の文です。これは三番目の文です。"
    c = check_sentence_ending_run(prose)
    assert c.passed is True


def test_check_sentence_ending_run_desu_masu_alternating_passes():
    prose = "これは最初の文です。これを最初に見ます。これは二番目の文です。これを二番目に見ます。"
    c = check_sentence_ending_run(prose)
    assert c.passed is True


def test_check_sentence_ending_run_non_matching_sentence_resets_run():
    prose = (
        "これは最初の文です。これは二番目の文です。今日は晴れ。"
        "これは三番目の文です。これは四番目の文です。"
    )
    c = check_sentence_ending_run(prose)
    assert c.passed is True


def test_check_sentence_ending_run_fail_detail_reports_ending_length_and_first_sentence():
    prose = "これは最初の文です。これは二番目の文です。これは三番目の文です。これは四番目の文です。"
    c = check_sentence_ending_run(prose)
    assert c.passed is False
    assert "です" in c.detail
    assert "4文連続" in c.detail
    assert "これは最初の文です" in c.detail
    assert c.suggestion == "文末に変化をつける（体言止めは使わない）"
    # 30 rune 以下の文は切り詰めていないため、省略記号を付けない。
    assert "…" not in c.detail


def test_check_sentence_ending_run_fail_detail_truncates_long_first_sentence():
    long = "あ" * 40
    prose = long + "です。" + long + "です。" + long + "です。" + long + "です。"
    c = check_sentence_ending_run(prose)
    assert c.passed is False
    assert ("あ" * 30 + "…") in c.detail
    assert ("あ" * 31) not in c.detail


# --- TestCheckRhetoricalContrastFreq ---


def test_check_rhetorical_contrast_freq_4_occurrences_fail():
    c = check_rhetorical_contrast_freq("AではなくBではなくCではなくDではなくEにする。")
    assert c.name == "rhetorical_contrast_freq"
    assert c.severity == "warning"
    assert c.passed is False


def test_check_rhetorical_contrast_freq_3_occurrences_pass_at_boundary():
    c = check_rhetorical_contrast_freq("AではなくBではなくCではなくDにする。")
    assert c.passed is True


def test_check_rhetorical_contrast_freq_fail_detail_and_suggestion():
    c = check_rhetorical_contrast_freq("AではなくBではなくCではなくDではなくEにする。")
    assert "4" in c.detail
    assert "3" in c.detail
    assert c.suggestion == "対比構文を減らし、肯定形で直接述べる"


# --- TestCheckClichePhrases ---


def test_check_cliche_phrases_4_total_occurrences_fail():
    prose = "速度が重要です。品質が重要です。コストが重要です。納期が重要です。"
    c = check_cliche_phrases(prose)
    assert c.name == "cliche_phrases"
    assert c.severity == "warning"
    assert c.passed is False


def test_check_cliche_phrases_3_total_occurrences_pass_at_boundary():
    prose = "速度が重要です。品質が重要です。コストが重要です。"
    c = check_cliche_phrases(prose)
    assert c.passed is True


def test_check_cliche_phrases_fail_detail_reports_per_phrase_breakdown():
    prose = "速度が重要です。品質が重要です。コストが重要です。それがポイントです。あれが鍵です。"
    c = check_cliche_phrases(prose)
    assert c.passed is False
    for want in ["が重要です=3", "がポイントです=1", "が鍵です=1"]:
        assert want in c.detail


# --- TestCheckNegationFirstFreq_NoDoubleCount ---


def test_check_negation_first_freq_no_double_count():
    # 「わけではありません」1 回のみ -> 「ではありません」と二重計上せず合計 1 で上限内
    c = check_negation_first_freq(
        "全員が同じ作業をするわけではありません。",
        patterns=["わけではありません", "ではありません"],
        max_total=1,
    )
    assert c.passed is True


# --- TestCheckNegationFirstFreq ---


def test_check_negation_first_freq_4_occurrences_pass_at_boundary():
    prose = "AではありませんBとは限りませんCを指しませんDに閉じません。"
    c = check_negation_first_freq(prose)
    assert c.name == "negation_first_freq"
    assert c.severity == "warning"
    assert c.passed is True


def test_check_negation_first_freq_5_occurrences_fail():
    prose = "AではありませんBとは限りませんCを指しませんDに閉じませんEというより。"
    c = check_negation_first_freq(prose)
    assert c.passed is False


def test_check_negation_first_freq_single_wake_dewa_not_double_counted():
    c = check_negation_first_freq("全員が同じ作業をするわけではありません。")
    assert c.passed is True


def test_check_negation_first_freq_neutral_prose_passes():
    c = check_negation_first_freq("この手法は計測の結果、処理時間を半分にした。")
    assert c.passed is True


def test_check_negation_first_freq_empty_pattern_elements_ignored():
    # 空要素は無視され「ではありません」1 回のみ -> 上限 1 で pass
    c = check_negation_first_freq(
        "それは正解ではありません。",
        patterns=["", "ではありません", ""],
        max_total=1,
    )
    assert c.passed is True


def test_check_negation_first_freq_fail_detail_reports_breakdown():
    prose = "AではありませんBではありませんCではありませんDを指しませんEに閉じません。"
    c = check_negation_first_freq(prose)
    assert c.passed is False
    assert "5" in c.detail
    assert "4" in c.detail
    assert "ではありません=3" in c.detail


# --- TestCheckSentenceEndingVariety ---


def _desu(n: int) -> str:
    return "これは本文です。" * n


def _other(m: int) -> str:
    return "今日は晴れ。" * m


def test_check_sentence_ending_variety_90_percent_fail():
    c = check_sentence_ending_variety(_desu(36) + _other(4))
    assert c.name == "sentence_ending_variety"
    assert c.severity == "warning"
    assert c.passed is False


def test_check_sentence_ending_variety_80_percent_pass():
    c = check_sentence_ending_variety(_desu(32) + _other(8))
    assert c.passed is True


def test_check_sentence_ending_variety_20_sentences_skipped_passes():
    c = check_sentence_ending_variety(_desu(20))
    assert c.passed is True


def test_check_sentence_ending_variety_fail_detail_reports_ratio_and_counts():
    c = check_sentence_ending_variety(_desu(36) + _other(4))
    assert c.passed is False
    assert "90%" in c.detail
    assert "36/40" in c.detail


def test_check_sentence_ending_variety_skip_detail_reports_count_and_threshold():
    c = check_sentence_ending_variety(_desu(20))
    assert c.passed is True
    assert "20" in c.detail
    assert "30" in c.detail


# --- TestCheckCodeLineLength ---


def test_check_code_line_length_81_rune_line_fails():
    body = "```go\n" + "あ" * 81 + "\n```\n"
    c = check_code_line_length(body)
    assert c.name == "code_line_length"
    assert c.severity == "warning"
    assert c.passed is False


def test_check_code_line_length_80_rune_line_passes():
    body = "```go\n" + "あ" * 80 + "\n```\n"
    c = check_code_line_length(body)
    assert c.passed is True


def test_check_code_line_length_multibyte_runes_counted_not_bytes():
    body = "```go\n" + "漢" * 80 + "\n```\n"
    c = check_code_line_length(body)
    assert c.passed is True


def test_check_code_line_length_outside_code_block_ignored():
    body = "あ" * 200 + "\n"
    c = check_code_line_length(body)
    assert c.passed is True


def test_check_code_line_length_no_code_block_skips():
    c = check_code_line_length("これは本文です。\n")
    assert c.passed is True


def test_check_code_line_length_detail_reports_block_start_and_length():
    # 先頭に本文 1 行を置き、コードブロックは body 2 行目（1 始まり）から始まる。
    body = "説明文。\n```go\n" + "あ" * 81 + "\n```\n"
    c = check_code_line_length(body)
    assert c.passed is False
    assert "line 2" in c.detail
    assert "81" in c.detail


# --- TestRuleBasedChecker_SpecExample1_NoPrematureDetection（純粋関数部分のみ） ---


def test_spec_example1_sentence_ending_run_passes():
    prose = (
        "DevOpsの進み具合は、施策の数ではなく流れと安定性の変化で見ます。"
        "Four Keysは、その変化を三つの道の健康状態として観測する入口です。"
    )
    c = check_sentence_ending_run(prose)
    assert c.name == "sentence_ending_run"
    assert c.passed is True


def test_spec_example1_rhetorical_contrast_freq_passes():
    prose = (
        "DevOpsの進み具合は、施策の数ではなく流れと安定性の変化で見ます。"
        "Four Keysは、その変化を三つの道の健康状態として観測する入口です。"
    )
    c = check_rhetorical_contrast_freq(prose)
    assert c.name == "rhetorical_contrast_freq"
    assert c.passed is True


# --- checker_ai_style_calibration_test.go ---

# calibrationArticles（checker_ai_style_calibration_test.go 34-54行）の移植。
# record 引用断片を記事番号ごとにまとめた 7 記事相当フィクスチャ。
_CALIBRATION_ARTICLES = [
    # #1: 冒頭定型 + 否定先行 2 文(「に閉じません」「を指しません」)
    "DevOps推進担当になると、CI/CDや可観測性に出会います。"
    "フローは単なる速度の話に閉じません。"
    "サイロを減らすとは、全員が同じ作業をする状態を指しません。",
    # #2: 冒頭定型 + 「ではなく」(negation_first_freq の対象外。rhetorical_contrast_freq が数える)
    "DevOps推進担当になると、『改善が進んだ』と何で言えるのかを聞かれます。"
    "Four Keysは成績表ではなく、三つの道の健康診断として見ます。",
    # #3: 「ではなく」(対象外)
    "CI/CDはツール導入ではなく、変更を小さく流すための作業設計です。",
    # #4: 否定先行 1 文(「ではありません」)
    "単にアラートを増やす話ではありません。",
    # #5: 冒頭定型 + 否定先行 1 文(「ではありません」)
    "DevOps推進担当になると、『CI/CDは入れたが、組織は良くなっているのか』という問いに向き合う場面が増えます。"
    "CALMSは完成度を競う表ではありません。",
    # #6: 冒頭定型 + 否定先行 1 文(「ではありません」)
    "DevOps推進担当になると、『SREチームを作るべきか』と相談されることがあります。"
    "二者択一を固定することではありません。",
    # #7: 否定先行 1 文(「一点にありません」= どのパターンにも一致しない変異形)
    "Fable 5 の価値は『速くコードを書く』一点にありません。",
]


def test_calibration_default_thresholds_do_not_over_detect():
    want_negation_warnings = 0  # measured: 記事別否定数 [2,0,0,1,1,1,0] は全て <= 4
    want_variety_warnings = 0  # measured: 各記事 1~3 文で MinSentences=30 未満 -> 全て skip
    design_ceiling = 2  # plan の「1~2 本相当」上限(過剰検知の回帰防止ライン)

    neg_warnings, variety_warnings = 0, 0
    for article in _CALIBRATION_ARTICLES:
        neg = check_negation_first_freq(article)
        assert neg.severity == "warning"
        if not neg.passed:
            neg_warnings += 1
        variety = check_sentence_ending_variety(article)
        if not variety.passed:
            variety_warnings += 1

    assert neg_warnings == want_negation_warnings
    assert variety_warnings == want_variety_warnings
    assert neg_warnings + variety_warnings <= design_ceiling


def test_calibration_negation_first_freq_aggregate_corpus_trips():
    corpus = "".join(_CALIBRATION_ARTICLES)
    c = check_negation_first_freq(corpus)
    assert c.passed is False
    # 8 例中パターン一致は 5 回(ではありません=3, を指しません=1, に閉じません=1)。「ではなく」×2・
    # 「一点にありません」×1 は対象外。5 > 4 で超過することを detail からも確認する。
    assert "5" in c.detail
    assert "4" in c.detail


# --- .kata/task-06.md 記載の代表テスト（そのまま収録） ---


def test_bold_colon_list_over_limit_fails():
    body = "\n".join(["- **要点**: 説明です"] * 3)
    assert not check_bold_colon_list(body).passed


def test_bold_colon_list_inside_code_fence_is_ignored():
    body = "```\n" + "\n".join(["- **要点**: 説明"] * 5) + "\n```"
    assert check_bold_colon_list(body).passed


def test_cliche_phrases_total_over_limit_fails():
    prose = "これが重要です。あれがポイントです。それが鍵です。言い換えると全部です。"
    assert not check_cliche_phrases(prose).passed
