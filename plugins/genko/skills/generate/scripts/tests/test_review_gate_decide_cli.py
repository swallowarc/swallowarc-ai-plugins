"""review_gate.py decide サブコマンド（CLI エントリ）のテスト。

subprocess で sys.executable 実行する（tests/test_qualitycheck_cli.py /
tests/test_review_gate_aspects_cli.py と同じ流儀）。CLI 自体（引数構成・
ファイル IO・decision.json/report.md の書き出し・スキーマ検証によるエラー終了）は
本移植独自の成果物であり、対応する単一の Go テストは無い。verdict 判定ロジック
そのものの Go 対応は tests/test_gate.py の docstring を参照。

- test_cli_writes_decision_and_report_for_passed_verdict: 全 error 合格時に
  decision.json の verdict="passed"、report.md が生成されること。
- test_cli_continue_without_prev: --prev 無し経路。round=1 で失敗 findings が
  あれば verdict="continue"、failed_error_keys が記録されること。
- test_cli_stalled_with_prev: --prev 有り経路。前回と同一の failed_error_keys
  なら verdict="stalled"。
- test_cli_retries_exhausted_at_final_round: round=max_retries+1 かつ
  停滞していない（prev と failed_error_keys が異なる）場合は
  verdict="retries_exhausted"。
- test_cli_judge_schema_violation_exits_nonzero: judge.json の findings に
  必須フィールド欠落があるとき非ゼロ終了。
- test_cli_judge_unknown_field_exits_nonzero: findings に未知フィールドが
  あるとき非ゼロ終了（judgeOutputSchema の additionalProperties: false 相当）。
- test_cli_judge_invalid_severity_exits_nonzero: severity が error/warning
  以外のとき非ゼロ終了（GateError 経路）。
- test_cli_exit_code_zero_regardless_of_verdict: verdict が
  passed/continue/stalled/retries_exhausted のどれであっても exit code は 0
  （実行エラーのみ非ゼロという規約の固定）。
- test_cli_missing_rules_file_exits_nonzero / test_cli_malformed_judge_json_exits_nonzero:
  既存 CLI 群と同様の実行時エラー系。
- test_cli_rejects_non_utf8_judge: judge.json が UTF-8 として読めないバイト列の
  とき、トレースバックではなく error: + exit 1 で正規化終了すること。
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "review_gate.py"), "decide", *args],
        capture_output=True,
        text=True,
    )


ASPECTS_JSON = {
    "schema_version": 1,
    "aspects": [
        {"key": "concrete_examples", "allow_error": True, "instruction": "i"},
        {"key": "lead_quality", "allow_error": False, "instruction": "i"},
    ],
}


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _rules(findings, mode="article"):
    return {"schema_version": 1, "mode": mode, "findings": findings, "facts": {}}


def _judge(findings=None):
    return {"findings": findings or []}


def _run_decide(tmp_path, rules, judge, aspects=None, *, round_num=1, max_retries=2, prev=None):
    rules_path = _write_json(tmp_path / "rules.json", rules)
    judge_path = _write_json(tmp_path / "judge.json", judge)
    aspects_path = _write_json(tmp_path / "aspects.json", aspects if aspects is not None else ASPECTS_JSON)
    out_path = tmp_path / "decision.json"
    report_path = tmp_path / "report.md"

    args = [
        "--rules", str(rules_path),
        "--judge", str(judge_path),
        "--aspects", str(aspects_path),
        "--round", str(round_num),
        "--max-retries", str(max_retries),
        "--out", str(out_path),
        "--report", str(report_path),
    ]
    if prev is not None:
        prev_path = _write_json(tmp_path / "prev_decision.json", prev)
        args += ["--prev", str(prev_path)]

    r = run_cli(*args)
    return r, out_path, report_path


def test_cli_writes_decision_and_report_for_passed_verdict(tmp_path):
    rules = _rules([{"name": "body_length", "passed": True, "severity": "error", "detail": "ok"}])
    r, out_path, report_path = _run_decide(tmp_path, rules, _judge())
    assert r.returncode == 0, r.stderr

    decision = json.loads(out_path.read_text(encoding="utf-8"))
    assert decision["schema_version"] == 1
    assert decision["verdict"] == "passed"
    assert decision["passed"] is True
    assert decision["failed_error_keys"] == []
    assert decision["error_findings"] == []

    report = report_path.read_text(encoding="utf-8")
    assert "passed" in report
    assert "round 1" in report


def test_cli_continue_without_prev(tmp_path):
    rules = _rules([
        {"name": "body_length", "passed": False, "severity": "error",
         "detail": "too short", "suggestion": "肉付けする"},
    ])
    r, out_path, report_path = _run_decide(tmp_path, rules, _judge(), round_num=1)
    assert r.returncode == 0, r.stderr

    decision = json.loads(out_path.read_text(encoding="utf-8"))
    assert decision["verdict"] == "continue"
    assert decision["failed_error_keys"] == ["body_length/"]
    assert decision["error_findings"][0]["name"] == "body_length"

    report = report_path.read_text(encoding="utf-8")
    assert "continue" in report
    assert "body_length" in report and "肉付けする" in report


def test_cli_stalled_with_prev(tmp_path):
    rules = _rules([
        {"name": "body_length", "passed": False, "severity": "error", "detail": "too short"},
    ])
    prev = {"schema_version": 1, "verdict": "continue", "round": 1, "passed": False,
            "failed_error_keys": ["body_length/"], "error_findings": [], "warning_findings": [],
            "all_findings": []}
    r, out_path, _ = _run_decide(tmp_path, rules, _judge(), round_num=2, prev=prev)
    assert r.returncode == 0, r.stderr

    decision = json.loads(out_path.read_text(encoding="utf-8"))
    assert decision["verdict"] == "stalled"


def test_cli_retries_exhausted_at_final_round(tmp_path):
    rules = _rules([
        {"name": "body_length", "passed": False, "severity": "error", "detail": "too short"},
    ])
    prev = {"schema_version": 1, "verdict": "continue", "round": 2, "passed": False,
            "failed_error_keys": ["kanji_run/"], "error_findings": [], "warning_findings": [],
            "all_findings": []}
    r, out_path, _ = _run_decide(tmp_path, rules, _judge(), round_num=3, max_retries=2, prev=prev)
    assert r.returncode == 0, r.stderr

    decision = json.loads(out_path.read_text(encoding="utf-8"))
    assert decision["verdict"] == "retries_exhausted"


def test_cli_judge_findings_are_merged_and_converted(tmp_path):
    rules = _rules([{"name": "body_length", "passed": True, "severity": "error", "detail": "ok"}])
    judge = _judge([
        {"aspect": "lead_quality", "passed": False, "severity": "error",
         "location": "冒頭", "detail": "弱い", "suggestion": "書き直す"},
    ])
    r, out_path, _ = _run_decide(tmp_path, rules, judge)
    assert r.returncode == 0, r.stderr

    decision = json.loads(out_path.read_text(encoding="utf-8"))
    # lead_quality は allow_error=False のため error -> warning に降格し、
    # 合否には影響しない(passed のまま)。
    assert decision["verdict"] == "passed"
    assert decision["warning_findings"][0]["name"] == "llm_judge"
    assert decision["warning_findings"][0]["category"] == "lead_quality"


def test_cli_judge_schema_violation_exits_nonzero(tmp_path):
    rules = _rules([])
    judge = {"findings": [{"aspect": "concrete_examples", "passed": False}]}  # severity 等が欠落
    r, _, _ = _run_decide(tmp_path, rules, judge)
    assert r.returncode != 0
    assert r.stderr.startswith("error:")


def test_cli_judge_unknown_field_exits_nonzero(tmp_path):
    # 本番 judgeOutputSchema は finding オブジェクトに additionalProperties: false
    # を課す（judge_common.go:27-）。余分なキーを持つ finding はスキーマ違反。
    rules = _rules([])
    judge = _judge([
        {"aspect": "concrete_examples", "passed": False, "severity": "error",
         "location": "", "detail": "d", "suggestion": "s", "extra_field": "x"},
    ])
    r, _, _ = _run_decide(tmp_path, rules, judge)
    assert r.returncode != 0
    assert r.stderr.startswith("error:")
    assert "extra_field" in r.stderr


def test_cli_judge_invalid_severity_exits_nonzero(tmp_path):
    rules = _rules([])
    judge = _judge([
        {"aspect": "concrete_examples", "passed": False, "severity": "fatal",
         "location": "", "detail": "d", "suggestion": "s"},
    ])
    r, _, _ = _run_decide(tmp_path, rules, judge)
    assert r.returncode != 0
    assert r.stderr.startswith("error:")


def test_cli_missing_rules_file_exits_nonzero(tmp_path):
    judge_path = _write_json(tmp_path / "judge.json", _judge())
    aspects_path = _write_json(tmp_path / "aspects.json", ASPECTS_JSON)
    r = run_cli(
        "--rules", str(tmp_path / "nai.json"), "--judge", str(judge_path),
        "--aspects", str(aspects_path), "--round", "1",
        "--out", str(tmp_path / "decision.json"), "--report", str(tmp_path / "report.md"),
    )
    assert r.returncode != 0
    assert r.stderr.startswith("error:")


def test_cli_malformed_judge_json_exits_nonzero(tmp_path):
    rules_path = _write_json(tmp_path / "rules.json", _rules([]))
    aspects_path = _write_json(tmp_path / "aspects.json", ASPECTS_JSON)
    judge_path = tmp_path / "judge.json"
    judge_path.write_text("{not valid json", encoding="utf-8")
    r = run_cli(
        "--rules", str(rules_path), "--judge", str(judge_path),
        "--aspects", str(aspects_path), "--round", "1",
        "--out", str(tmp_path / "decision.json"), "--report", str(tmp_path / "report.md"),
    )
    assert r.returncode != 0
    assert r.stderr.startswith("error:")


def test_cli_rejects_non_utf8_judge(tmp_path):
    rules_path = _write_json(tmp_path / "rules.json", _rules([]))
    aspects_path = _write_json(tmp_path / "aspects.json", ASPECTS_JSON)
    judge_path = tmp_path / "judge.json"
    judge_path.write_bytes(b"\xff\xfe\x00broken")
    r = run_cli(
        "--rules", str(rules_path), "--judge", str(judge_path),
        "--aspects", str(aspects_path), "--round", "1",
        "--out", str(tmp_path / "decision.json"), "--report", str(tmp_path / "report.md"),
    )
    assert r.returncode == 1
    assert r.stderr.startswith("error:")


def test_cli_exit_code_zero_regardless_of_verdict(tmp_path):
    # stalled や retries_exhausted のような「品質ゲート的には失敗」の verdict でも
    # CLI 実行そのものは正常終了(exit 0)であることを固定する
    # （findings 不合格と実行エラーを区別する global-constraints の規約）。
    rules = _rules([{"name": "body_length", "passed": False, "severity": "error", "detail": "d"}])
    prev = {"schema_version": 1, "verdict": "continue", "round": 1, "passed": False,
            "failed_error_keys": ["body_length/"], "error_findings": [], "warning_findings": [],
            "all_findings": []}
    r, _, _ = _run_decide(tmp_path, rules, _judge(), round_num=2, prev=prev)
    assert r.returncode == 0, r.stderr
