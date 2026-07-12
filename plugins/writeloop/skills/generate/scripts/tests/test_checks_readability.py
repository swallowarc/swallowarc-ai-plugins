"""checks_readability.py のテスト。

移植元テスト: internal/infrastructure/quality/checker_readability_test.go @ autopostd 20c740b
（281行）

Go テストケース対応表（全件移植。テーブル駆動の t.Run サブテスト名を左に示す）:

TestCheckSentenceLength（5 サブテスト、共通アサーションとして checks 件数 2・両方の
name=="sentence_length"・101字ケースの detail 内容も各テストで確認する）:
- "101 runes exceeds error and warning"
    -> test_check_sentence_length_101_runes_exceeds_error_and_warning
- "81 runes warning fails but error passes"
    -> test_check_sentence_length_81_runes_warning_fails_but_error_passes
- "60 runes both pass"
    -> test_check_sentence_length_60_runes_both_pass
- "100 runes at error boundary passes (not exceeding)"
    -> test_check_sentence_length_100_runes_at_error_boundary_passes
- "80 runes at warning boundary passes (not exceeding)"
    -> test_check_sentence_length_80_runes_at_warning_boundary_passes

TestCheckSentenceLength_TableRowExcluded
    -> test_check_sentence_length_table_row_excluded

TestCheckSentenceLength_InlineLinkURLExcluded
    -> test_check_sentence_length_inline_link_url_excluded

TestCheckSentenceCommas（2 サブテスト）:
- "4 commas fails"  -> test_check_sentence_commas_4_commas_fails
- "3 commas passes" -> test_check_sentence_commas_3_commas_passes

TestCheckKanjiRun（4 サブテスト）:
- "7 consecutive kanji fails" -> test_check_kanji_run_7_consecutive_kanji_fails
- "6 consecutive kanji passes" -> test_check_kanji_run_6_consecutive_kanji_passes
- "allowlisted run passes" -> test_check_kanji_run_allowlisted_run_passes
- "heading kanji run is excluded from scan (splitSentences drops heading lines)"
    -> test_check_kanji_run_heading_kanji_run_excluded_from_scan

TestCheckWeakExpressions（3 サブテスト）:
- "weak phrases and exclamation fail"
    -> test_check_weak_expressions_weak_phrases_and_exclamation_fail
- "clean assertive prose passes"
    -> test_check_weak_expressions_clean_assertive_prose_passes
- "heading exclamation is excluded from scan (splitSentences drops heading lines)"
    -> test_check_weak_expressions_heading_exclamation_excluded_from_scan

上記、テーブル駆動 4 関数（TestCheckSentenceLength=5 / TestCheckSentenceCommas=2 /
TestCheckKanjiRun=4 / TestCheckWeakExpressions=3、計 14 サブテスト）+ 単独回帰 2 関数
（TestCheckSentenceLength_TableRowExcluded / TestCheckSentenceLength_InlineLinkURLExcluded）
= 16 件で、checker_readability_test.go の TestCheckSentenceLength〜TestCheckWeakExpressions
（6 関数）を全件移植済み（取捨選択なし）。

--- 移植対象外（意図的な除外。取捨選択ではなく Task 5 のインターフェース範囲外） ---

TestRuleBasedChecker_ReadabilityChecksRegistered は、この 4 チェック関数が
RuleBasedChecker.Check()（オーケストレータ）に登録され実行順序どおりに動作することを
検証する回帰テストである。Task 5 の Produces は
check_sentence_length / check_sentence_commas / check_kanji_run / check_weak_expressions
の 4 純粋関数のみで、Check() 相当のオーケストレータ（本文全体からの findings 一覧生成、
frontmatter 分離等）は本タスクのインターフェースに含まれない
（docs/kata/plans/2026-07-12-writeloop-scripts.md の Task 12: qualitycheck.py CLI が該当）。
そのため本ファイルでは移植せず、report-task-05.md の懸念事項として
Task 12 へ申し送りする。

--- 追加: .kata/task-05.md Step 1 記載の代表テスト（そのまま収録） ---

test_sentence_over_100_runes_is_error
test_sentence_within_80_runes_passes
test_kanji_run_of_7_fails_and_allowlist_passes
"""

from wlq.checks_readability import (
    check_kanji_run,
    check_sentence_commas,
    check_sentence_length,
    check_weak_expressions,
)
from wlq.prose import extract_prose


def _sentence_of_runes(rune_len: int) -> str:
    """Go: sentenceOfRunes(runeLen)（checker_readability_test.go:12-14）の移植。

    末尾の「。」を含めて runeLen rune ちょうどの 1 文からなる散文を返す。
    """
    return "あ" * (rune_len - 1) + "。"


def _assert_sentence_length(findings, want_err_pass, want_warn_pass):
    assert len(findings) == 2
    err = next(f for f in findings if f.severity == "error")
    warn = next(f for f in findings if f.severity == "warning")
    assert err.name == "sentence_length"
    assert warn.name == "sentence_length"
    assert err.passed == want_err_pass
    assert warn.passed == want_warn_pass
    return err, warn


# --- TestCheckSentenceLength ---


def test_check_sentence_length_101_runes_exceeds_error_and_warning():
    findings = check_sentence_length(_sentence_of_runes(101))
    err, warn = _assert_sentence_length(findings, False, False)
    # error fail の detail には超過文の先頭 20 文字と実測長を含めること。
    assert "あ" * 20 in err.detail
    assert "101字" in err.detail


def test_check_sentence_length_81_runes_warning_fails_but_error_passes():
    findings = check_sentence_length(_sentence_of_runes(81))
    _assert_sentence_length(findings, True, False)


def test_check_sentence_length_60_runes_both_pass():
    findings = check_sentence_length(_sentence_of_runes(60))
    _assert_sentence_length(findings, True, True)


def test_check_sentence_length_100_runes_at_error_boundary_passes():
    findings = check_sentence_length(_sentence_of_runes(100))
    _assert_sentence_length(findings, True, False)


def test_check_sentence_length_80_runes_at_warning_boundary_passes():
    findings = check_sentence_length(_sentence_of_runes(80))
    _assert_sentence_length(findings, True, True)


def test_check_sentence_length_table_row_excluded():
    """markdown の表行（| ... | ... |）が「。」を含まない 100 字超の 1 文として
    誤検知され error になる回帰を防ぐ（表行は split_sentences で除外される）。
    """
    table_row = "| " + "あ" * 60 + " | " + "い" * 60 + " |"
    prose = "本文です。\n" + table_row + "\n次の文です。"
    findings = check_sentence_length(prose)
    assert len(findings) == 2
    for f in findings:
        assert f.passed


def test_check_sentence_length_inline_link_url_excluded():
    """本文インライン引用リンクの URL が文字数に含まれて文長超過（error）に
    誤検知される回帰を防ぐ。表示文字数は 28 字だが URL を含めた raw は 113 字。
    extract_prose のリンク正規化を経れば pass する。
    """
    body = (
        "エージェントが[一度に一機能を進める構成]"
        "(https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)"
        "を採用しています。"
    )
    assert len(body) > 100  # テスト前提: raw 長は error 閾値 100 を超えること
    findings = check_sentence_length(extract_prose(body))
    assert len(findings) == 2
    for f in findings:
        assert f.passed


# --- TestCheckSentenceCommas ---


def test_check_sentence_commas_4_commas_fails():
    c = check_sentence_commas("これは、とても、長くて、読点が、多い文です。")
    assert c.name == "sentence_commas"
    assert c.severity == "warning"
    assert c.passed is False


def test_check_sentence_commas_3_commas_passes():
    c = check_sentence_commas("これは、読点が、三個の、文です。")
    assert c.name == "sentence_commas"
    assert c.severity == "warning"
    assert c.passed is True


# --- TestCheckKanjiRun ---


def test_check_kanji_run_7_consecutive_kanji_fails():
    c = check_kanji_run("これは機械学習基盤群の話です。")
    assert c.name == "kanji_run"
    assert c.severity == "warning"
    assert c.passed is False


def test_check_kanji_run_6_consecutive_kanji_passes():
    c = check_kanji_run("これは機械学習基盤の話です。")
    assert c.passed is True


def test_check_kanji_run_allowlisted_run_passes():
    c = check_kanji_run("これは機械学習基盤群の話です。", allowlist=["機械学習基盤群"])
    assert c.passed is True


def test_check_kanji_run_heading_kanji_run_excluded_from_scan():
    c = check_kanji_run("## 機械学習基盤構築運用のポイント\nこれはきれいな文章です。")
    assert c.passed is True


# --- TestCheckWeakExpressions ---


def test_check_weak_expressions_weak_phrases_and_exclamation_fail():
    c = check_weak_expressions("これは正しいかもしれない。とても良いと思います！")
    assert c.name == "weak_expressions"
    assert c.severity == "warning"
    assert c.passed is False
    for w in ["かもしれない", "と思います", "！"]:
        assert w in c.detail


def test_check_weak_expressions_clean_assertive_prose_passes():
    c = check_weak_expressions("これはベンチマーク結果に基づく事実である。処理時間は半分になった。")
    assert c.passed is True


def test_check_weak_expressions_heading_exclamation_excluded_from_scan():
    c = check_weak_expressions("## 注目のポイント！\nこれはとても良い結果でした。")
    assert c.passed is True


# --- .kata/task-05.md Step 1 の代表テスト（そのまま収録） ---


def test_sentence_over_100_runes_is_error():
    prose = "あ" * 101 + "。"
    findings = check_sentence_length(prose)
    errors = [f for f in findings if f.severity == "error"]
    assert errors and not errors[0].passed


def test_sentence_within_80_runes_passes():
    findings = check_sentence_length("短い文です。")
    assert all(f.passed for f in findings)


def test_kanji_run_of_7_fails_and_allowlist_passes():
    assert not check_kanji_run("国際標準化機構認証取得を目指す。").passed
    assert check_kanji_run(
        "国際標準化機構認証取得を目指す。", allowlist=["国際標準化機構認証取得"]
    ).passed
