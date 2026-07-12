"""wlq/gate.py（decide/convert_judge_findings/failed_error_check_keys）のテスト。

task-14.md 記載の完全仕様テスト（そのまま採用）。

Go 側対応（@ autopostd 20c740b）:

judge_common_test.go の TestJudgeFindingsToChecks（judgeFindingsToChecks）:
    "converts findings to llm_judge checks" (allowError=true は error 維持)
        -> test_convert_names_and_categories
    "demotes error to warning when allowError=false"
        -> test_error_downgraded_to_warning_when_not_allowed
    "skips findings for unknown aspects"
        -> test_hallucinated_aspect_is_dropped
    "invalid severity is an error"
        -> test_invalid_severity_raises

helpers_test.go の TestFailedErrorCheckKeys（failedErrorCheckKeys）:
    -> test_failed_error_check_keys_dedup_and_format（重複排除・warning 除外を統合）

helpers_test.go の TestEqualKeySets（equalKeySets）は decide() の内部実装として
使うのみで公開関数ではないため、単体テストとしては移植せず decide() の verdict
テスト（stalled 判定）で間接的に固定する:
    "same order" / "different order" -> test_verdict_stalled_when_same_error_keys_as_prev
    "different size" / "different keys" -> test_verdict_continue_on_first_failing_round
      （prev=None なので stalled 判定自体が走らないケースだが、equalKeySets が
      True になり得ない不一致ケースの代替として round_num/failed_error_keys の
      表明で固定）
    "both empty" -> 該当なし。全 error 通過時は decide() が passed 分岐で先に
      抜けるため both-empty での equalKeySets 呼び出しは発生しない（Go の
      runQualityCheckLoop も !passed を条件に含むため同様）。

helpers_test.go の TestFailedCheckKeys / TestIntersect:
    -> 移植対象外。failedCheckKeys（severity 無視の全不合格キー）と intersect
    （前回転との共通キー）はどちらも Task 14 の produced interface
    （GateError/convert_judge_findings/failed_error_check_keys/Decision/decide/
    render_report）に含まれない。intersect は Go でもログ出力のみに使い verdict
    判定に影響しないため、決定論的な decide() には移植しない。

draft_generation_test.go: runQualityCheckLoop の verdict 判定順序
（passed -> stalled -> retries_exhausted -> continue）を直接検証する単体テストは
Go 側に無い（workflow 統合テストのみ）。本ファイルの
test_stall_check_precedes_retry_exhaustion で Python 側に固定する。
"""
import pytest
from wlq.gate import GateError, convert_judge_findings, decide, failed_error_check_keys
from wlq.model import Finding, check_fail, check_pass

ASPECTS = [
    {"key": "concrete_examples", "allow_error": True, "instruction": "i"},
    {"key": "lead_quality", "allow_error": False, "instruction": "i"},
]


def jf(aspect, passed=False, severity="error"):
    return {"aspect": aspect, "passed": passed, "severity": severity,
            "location": "", "detail": "d", "suggestion": "s"}


def test_convert_names_and_categories():
    checks = convert_judge_findings([jf("concrete_examples")], ASPECTS)
    assert checks[0].name == "llm_judge"
    assert checks[0].category == "concrete_examples"
    assert checks[0].severity == "error"


def test_error_downgraded_to_warning_when_not_allowed():
    checks = convert_judge_findings([jf("lead_quality", severity="error")], ASPECTS)
    assert checks[0].severity == "warning"


def test_hallucinated_aspect_is_dropped():
    assert convert_judge_findings([jf("unknown_aspect")], ASPECTS) == []


def test_invalid_severity_raises():
    with pytest.raises(GateError):
        convert_judge_findings([jf("concrete_examples", severity="fatal")], ASPECTS)


def test_failed_error_check_keys_dedup_and_format():
    findings = [
        check_fail("body_length", "d", "s", "error"),
        Finding(name="llm_judge", passed=False, severity="error",
                detail="d", category="concrete_examples"),
        check_fail("body_length", "d2", "s2", "error"),
        check_fail("kanji_run", "d", "s", "warning"),  # warning は含まれない
    ]
    assert failed_error_check_keys(findings) == ["body_length/", "llm_judge/concrete_examples"]


def _decide(rule_findings, judge_findings, round_num=1, prev=None):
    return decide(rule_findings, judge_findings, ASPECTS,
                  round_num=round_num, max_retries=2, prev_failed_error_keys=prev)


def test_verdict_passed_when_all_errors_pass():
    d = _decide([check_pass("body_length", "ok", "error"),
                 check_fail("kanji_run", "d", "s", "warning")], [])
    assert d.verdict == "passed" and d.passed


def test_verdict_continue_on_first_failing_round():
    d = _decide([check_fail("body_length", "d", "s", "error")], [])
    assert d.verdict == "continue"
    assert d.failed_error_keys == ["body_length/"]


def test_verdict_stalled_when_same_error_keys_as_prev():
    d = _decide([check_fail("body_length", "d", "s", "error")], [],
                round_num=2, prev=["body_length/"])
    assert d.verdict == "stalled"


def test_verdict_retries_exhausted_at_final_round():
    d = _decide([check_fail("body_length", "d", "s", "error")], [],
                round_num=3, prev=["kanji_run/"])
    assert d.verdict == "retries_exhausted"


def test_stall_check_precedes_retry_exhaustion():
    d = _decide([check_fail("body_length", "d", "s", "error")], [],
                round_num=3, prev=["body_length/"])
    assert d.verdict == "stalled"
