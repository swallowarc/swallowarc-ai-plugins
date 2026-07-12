"""checks_ai_style_structure.py のテスト。

移植元テスト: internal/infrastructure/quality/checker_ai_style_structure_test.go
@ autopostd 20c740b（228行、すべて t.Run を使わないトップレベル func Test）。

Go テストケース対応表（全件移植。1 関数 = 1 ケースとして 1:1 対応させる）:

- TestCheckParagraphUniformity_RunTrips
    -> test_check_paragraph_uniformity_run_trips
- TestCheckParagraphUniformity_RunNotResetByHeadings
    -> test_check_paragraph_uniformity_run_not_reset_by_headings
- TestCheckParagraphUniformity_VariedPasses
    -> test_check_paragraph_uniformity_varied_passes
- TestCheckParagraphUniformity_RatioTripsWithoutRun
    -> test_check_paragraph_uniformity_ratio_trips_without_run
- TestCheckParagraphUniformity_RatioSkippedBelowMinParagraphs
    -> test_check_paragraph_uniformity_ratio_skipped_below_min_paragraphs
- TestCheckHardLineBreaks_PerSentenceBreaksTrip
    -> test_check_hard_line_breaks_per_sentence_breaks_trip
- TestCheckHardLineBreaks_FlowingParagraphsSkip
    -> test_check_hard_line_breaks_flowing_paragraphs_skip
- TestCheckHardLineBreaks_SoftWrapPasses
    -> test_check_hard_line_breaks_soft_wrap_passes
- TestCheckFirstPersonFreq -> test_check_first_person_freq
- TestCheckReasonTemplateFreq -> test_check_reason_template_freq
- TestProseParagraphs_SeparatorsAndJoining
    -> test_prose_paragraphs_separators_and_joining

--- 移植対象外（意図的な除外。RuleBasedChecker.Check() 経由の統合テストは Task 12 スコープ） ---

- TestNormalizedDraftPassesHardLineBreaks (normalize_regression_test.go)
    checker.Check(ctx, ...) を通した正規化前後の回帰テスト。domain.NormalizeProseHardLineBreaks
    という本タスクのインターフェース外（プロンプト生成側の正規化ロジック）に依存するうえ、
    Check() のオーケストレーション（extractProse パイプライン込み）を検証するものであり、
    本タスクが移植する 4 個の純粋チェック関数の単体挙動の範囲外（Task 12 スコープ）。

--- 追加: .kata/task-07.md 記載の代表テスト（そのまま収録） ---

test_first_person_within_limit_passes
test_first_person_over_limit_fails
"""

from wlq.checks_ai_style_structure import (
    _prose_paragraphs,
    check_first_person_freq,
    check_hard_line_breaks,
    check_paragraph_uniformity,
    check_reason_template_freq,
)


def _para(i: int, n: int) -> str:
    """para(i, n) の移植: n 文の段落テキストを 1 つ生成する。i で内容を変えて重複を避ける。"""
    return "".join(f"第{i}段落の{j + 1}文目はサンプルです。" for j in range(n))


def _join_paras(*paras: str) -> str:
    """joinParas の移植: 段落テキスト群を空行区切りの prose に連結する。"""
    return "\n\n".join(paras)


# --- TestCheckParagraphUniformity_RunTrips ---


def test_check_paragraph_uniformity_run_trips():
    # 2 文段落 x 8 連続(デフォルト上限 7 を超過)。
    paras = [_para(i, 2) for i in range(8)]
    c = check_paragraph_uniformity(_join_paras(*paras))
    assert c.name == "paragraph_uniformity"
    assert c.severity == "warning"
    assert c.passed is False
    assert "8個連続" in c.detail


# --- TestCheckParagraphUniformity_RunNotResetByHeadings ---


def test_check_paragraph_uniformity_run_not_reset_by_headings():
    # 見出し・箇条書きを挟んでも読者のリズムは連続するため、リセットしない。
    parts = []
    for i in range(8):
        if i == 4:
            parts.append("## 途中の見出し\n\n- 箇条書き項目\n\n")
        parts.append(_para(i, 2) + "\n\n")
    prose = "".join(parts)
    c = check_paragraph_uniformity(prose)
    assert c.passed is False


# --- TestCheckParagraphUniformity_VariedPasses ---


def test_check_paragraph_uniformity_varied_passes():
    # 文数 1〜4 を循環させた 24 段落: run=1、最頻文数比率 25% で両条件とも合格。
    paras = [_para(i, i % 4 + 1) for i in range(24)]
    c = check_paragraph_uniformity(_join_paras(*paras))
    assert c.passed is True


# --- TestCheckParagraphUniformity_RatioTripsWithoutRun ---


def test_check_paragraph_uniformity_ratio_trips_without_run():
    # 2文x7 -> 3文x1 -> 2文x7 -> 3文x1 -> 2文x5 = 21 段落。
    # 最長 run は 7(上限内)だが、2 文段落が 19/21 = 90% で比率上限 70% を超過。
    paras: list[str] = []
    idx = 0

    def add(n: int, times: int) -> None:
        nonlocal idx
        for _ in range(times):
            paras.append(_para(idx, n))
            idx += 1

    add(2, 7)
    add(3, 1)
    add(2, 7)
    add(3, 1)
    add(2, 5)
    c = check_paragraph_uniformity(_join_paras(*paras))
    assert c.passed is False
    assert "90%" in c.detail


# --- TestCheckParagraphUniformity_RatioSkippedBelowMinParagraphs ---


def test_check_paragraph_uniformity_ratio_skipped_below_min_paragraphs():
    # 15 段落(< 20)は比率判定をスキップ。run も 7 以内なので合格。
    paras: list[str] = []
    idx = 0

    def add(n: int, times: int) -> None:
        nonlocal idx
        for _ in range(times):
            paras.append(_para(idx, n))
            idx += 1

    add(2, 7)
    add(3, 1)
    add(2, 7)
    c = check_paragraph_uniformity(_join_paras(*paras))
    assert c.passed is True


# --- TestCheckHardLineBreaks_PerSentenceBreaksTrip ---


def test_check_hard_line_breaks_per_sentence_breaks_trip():
    # 全段落が「1 文目(行末スペース 2 個)\n2 文目」の 2 行段落 x 12:
    # 継ぎ目 12(>= 最小 10)が全て強制改行 -> 100% > 50% で warning。
    parts = []
    for i in range(12):
        parts.append(f"第{i}段落の1文目です。  \n第{i}段落の2文目です。\n\n")
    prose = "".join(parts)
    c = check_hard_line_breaks(prose)
    assert c.name == "hard_line_breaks"
    assert c.severity == "warning"
    assert c.passed is False
    assert "100%" in c.detail


# --- TestCheckHardLineBreaks_FlowingParagraphsSkip ---


def test_check_hard_line_breaks_flowing_paragraphs_skip():
    # 段落内改行のない流し書きは継ぎ目 0 -> 最小継ぎ目数未満でスキップ合格。
    c = check_hard_line_breaks(_join_paras(_para(0, 3), _para(1, 2), _para(2, 4)))
    assert c.passed is True


# --- TestCheckHardLineBreaks_SoftWrapPasses ---


def test_check_hard_line_breaks_soft_wrap_passes():
    # 行末スペースなしの折り返し(ソフトラップ)は markdown 上 1 段落に結合されるため、
    # 継ぎ目は多くても強制改行 0 件 -> 0% で合格。
    parts = []
    for i in range(12):
        parts.append(f"第{i}段落の1文目です。\n第{i}段落の2文目です。\n\n")
    prose = "".join(parts)
    c = check_hard_line_breaks(prose)
    assert c.passed is True


# --- TestCheckFirstPersonFreq ---


def test_check_first_person_freq():
    within = "私は良い設計だと考えます。" * 8
    c = check_first_person_freq(within)
    assert c.passed is True

    over = "私は良い設計だと考えます。" * 7 + "筆者としては反対です。私の評価は変わりません。"
    c = check_first_person_freq(over)
    assert c.name == "first_person_freq"
    assert c.severity == "warning"
    assert c.passed is False
    # 「筆者として」は「筆者は」より長いパターンとして優先消費され、breakdown に現れる。
    assert "私は=7" in c.detail
    assert "筆者として=1" in c.detail
    assert "私の=1" in c.detail


# --- TestCheckReasonTemplateFreq ---


def test_check_reason_template_freq():
    within = "これが安全です。理由は復旧が容易なためです。" * 3
    c = check_reason_template_freq(within)
    assert c.passed is True

    over = within + "根拠は調査結果が同じ方向を示すからです。"
    c = check_reason_template_freq(over)
    assert c.name == "reason_template_freq"
    assert c.severity == "warning"
    assert c.passed is False
    assert "理由は=3" in c.detail
    assert "ためです=3" in c.detail


# --- TestProseParagraphs_SeparatorsAndJoining ---


def test_prose_paragraphs_separators_and_joining():
    prose = (
        "## 見出し\n\n一文目です。\n二文目です。\n\n| 表 | 行 |\n|---|---|\n\n"
        "- 箇条書き\n1. 番号リスト\n> 引用\n\n三文目です。"
    )
    paras = _prose_paragraphs(prose)
    assert len(paras) == 2
    assert paras[0] == "一文目です。二文目です。"
    assert paras[1] == "三文目です。"


# --- .kata/task-07.md 記載の代表テスト ---


def test_first_person_within_limit_passes():
    assert check_first_person_freq("私は考える。", max_total=8).passed


def test_first_person_over_limit_fails():
    prose = "私は思う。" * 9
    assert not check_first_person_freq(prose, max_total=8).passed
