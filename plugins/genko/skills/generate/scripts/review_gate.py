#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "regex"]
# ///
"""genko レビューゲート CLI。

サブコマンド:
- aspects: rules.json（qualitycheck.py の出力）の facts と --mode/--round/--research-present
  から LLM judge の評価観点を選定し、aspects.json を出力する
  （wlq.aspects.load_aspects / select_aspects の薄いエントリ）。
- decide: rules.json（ルールベース findings）と judge.json（LLM judge findings）を
  マージし、本番 `runQualityCheckLoop` の verdict 判定（passed/continue/stalled/
  retries_exhausted）を再現して decision.json と決定論的な report.md を出力する
  （wlq.gate.decide / wlq.report.render_report の薄いエントリ）。

使い方:
    review_gate.py aspects --aspects-file <judge-aspects.yaml> --rules <rules.json>
                            --mode article|document --round <N> [--research-present]
                            --out <path|->

    review_gate.py decide --rules <rules.json> --judge <judge.json>
                           --aspects <aspects.json> --round <N>
                           [--max-retries 2] [--prev <前回 decision.json>]
                           --out <decision.json> --report <report.md>

exit code: 判定結果（aspects の選定件数、decide の verdict）に関わらず 0。
実行エラー（ファイル不存在、JSON/YAML 不正、スキーマ違反、引数不正等）のみ
非ゼロ + stderr にメッセージ。
"""
import argparse
import json
import os
import sys

import yaml

# uv run / `python3 review_gate.py` のどちらで実行しても `wlq` パッケージを
# import できるよう、自ディレクトリを sys.path に追加してから import する。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wlq.aspects import load_aspects, select_aspects  # noqa: E402
from wlq.config import MAX_AUTO_FIX_RETRIES  # noqa: E402
from wlq.gate import GateError, decide  # noqa: E402
from wlq.model import Finding  # noqa: E402
from wlq.report import render_report  # noqa: E402

_JUDGE_FINDING_REQUIRED_FIELDS = ("aspect", "passed", "severity", "location", "detail", "suggestion")


def _read_json_file(path: str, label: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"error: failed to read {label} file {path!r}: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"error: failed to parse {label} file {path!r} as JSON: {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, dict):
        print(f"error: {label} file {path!r} must contain a JSON object", file=sys.stderr)
        sys.exit(1)
    return data


def _write_output(payload: dict, out: str) -> int:
    output = json.dumps(payload, ensure_ascii=False, indent=2)
    if out == "-":
        print(output)
        return 0
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(output)
            f.write("\n")
    except OSError as e:
        print(f"error: failed to write output file {out!r}: {e}", file=sys.stderr)
        return 1
    return 0


def _cmd_aspects(args: argparse.Namespace) -> int:
    rules = _read_json_file(args.rules, "rules")
    facts = rules.get("facts")
    if not isinstance(facts, dict):
        print(f"error: rules file {args.rules!r} is missing a 'facts' object", file=sys.stderr)
        return 1

    # rules.json は qualitycheck.py の出力であり facts.article_type を必ず持つ。
    # 欠落・不正型は入力データの破損なので黙ってフォールバックせずエラーにする。
    article_type = facts.get("article_type")
    if not isinstance(article_type, str) or not article_type:
        print(
            f"error: rules file {args.rules!r} is missing a valid 'facts.article_type' string",
            file=sys.stderr,
        )
        return 1

    try:
        defs = load_aspects(args.aspects_file)
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(f"error: failed to load aspects file {args.aspects_file!r}: {e}", file=sys.stderr)
        return 1

    try:
        selected = select_aspects(
            defs,
            mode=args.mode,
            article_type=article_type,
            has_fenced_block=bool(facts.get("has_fenced_block", False)),
            contains_triple_backtick=bool(facts.get("contains_triple_backtick", False)),
            research_present=args.research_present,
            round_num=args.round_num,
        )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    result = {
        "schema_version": 1,
        "aspects": [
            {"key": a.key, "allow_error": a.allow_error, "instruction": a.instruction}
            for a in selected
        ],
    }
    return _write_output(result, args.out)


def _rule_findings_from_rules(rules: dict, path: str) -> list[Finding] | None:
    """rules.json の 'findings' 配列を `Finding` のリストへ復元する。

    Finding.to_dict() は空の category/location/suggestion をキーごと省略する
    ため、逆変換は各 dict をそのまま `Finding(**d)` のキーワード引数として渡せば
    足りる（未指定フィールドは dataclass の既定値 "" で補われる）。
    """
    findings_raw = rules.get("findings")
    if not isinstance(findings_raw, list):
        print(f"error: rules file {path!r} is missing a 'findings' array", file=sys.stderr)
        return None
    try:
        return [Finding(**f) for f in findings_raw]
    except (TypeError, AttributeError) as e:
        print(f"error: rules file {path!r} has an invalid finding entry: {e}", file=sys.stderr)
        return None


def _judge_findings_from_judge(judge: dict, path: str) -> list[dict] | None:
    """judge.json の 'findings' 配列をスキーマ検証する（judgeOutputSchema 相当）。

    Go 側は judge LLM の structured output を `json.Unmarshal` で型付き struct
    （judgeFinding）に変換した後に `judgeFindingsToChecks` へ渡すため、その型
    検証の境界をここで再現する。個々の finding の意味検証（severity の妥当性・
    未要求観点の無視）は `wlq.gate.convert_judge_findings` の責務。
    """
    findings = judge.get("findings")
    if not isinstance(findings, list):
        print(f"error: judge file {path!r} is missing a 'findings' array", file=sys.stderr)
        return None
    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            print(f"error: judge file {path!r} findings[{i}] must be an object", file=sys.stderr)
            return None
        missing = [k for k in _JUDGE_FINDING_REQUIRED_FIELDS if k not in f]
        if missing:
            print(
                f"error: judge file {path!r} findings[{i}] is missing field(s) {missing}",
                file=sys.stderr,
            )
            return None
        # 本番 judgeOutputSchema（judge_common.go:27-）は finding オブジェクトに
        # additionalProperties: false を課す。未知フィールドはスキーマ違反。
        unknown = [k for k in f if k not in _JUDGE_FINDING_REQUIRED_FIELDS]
        if unknown:
            print(
                f"error: judge file {path!r} findings[{i}] has unknown field(s) {unknown}",
                file=sys.stderr,
            )
            return None
        string_fields = ("aspect", "severity", "location", "detail", "suggestion")
        bad_strings = [k for k in string_fields if not isinstance(f[k], str)]
        if bad_strings:
            print(
                f"error: judge file {path!r} findings[{i}] field(s) {bad_strings} must be strings",
                file=sys.stderr,
            )
            return None
        if not isinstance(f["passed"], bool):
            print(
                f"error: judge file {path!r} findings[{i}] 'passed' must be a bool",
                file=sys.stderr,
            )
            return None
    return findings


def _aspects_list_from_aspects_file(aspects_data: dict, path: str) -> list[dict] | None:
    aspects = aspects_data.get("aspects")
    if not isinstance(aspects, list):
        print(f"error: aspects file {path!r} is missing an 'aspects' array", file=sys.stderr)
        return None
    for i, a in enumerate(aspects):
        if (
            not isinstance(a, dict)
            or not isinstance(a.get("key"), str)
            or not isinstance(a.get("allow_error"), bool)
        ):
            print(
                f"error: aspects file {path!r} aspects[{i}] must have a string 'key' "
                "and a bool 'allow_error'",
                file=sys.stderr,
            )
            return None
    return aspects


def _prev_failed_error_keys(args: argparse.Namespace) -> tuple[list[str] | None, bool]:
    """--prev が与えられていれば failed_error_keys を読む。戻り値は (keys, ok)。"""
    if args.prev is None:
        return None, True
    prev = _read_json_file(args.prev, "prev decision")
    keys = prev.get("failed_error_keys")
    if not isinstance(keys, list):
        print(
            f"error: prev decision file {args.prev!r} is missing a 'failed_error_keys' array",
            file=sys.stderr,
        )
        return None, False
    return keys, True


def _cmd_decide(args: argparse.Namespace) -> int:
    rules = _read_json_file(args.rules, "rules")
    mode = rules.get("mode")
    if not isinstance(mode, str) or not mode:
        print(f"error: rules file {args.rules!r} is missing a valid 'mode' string", file=sys.stderr)
        return 1
    rule_findings = _rule_findings_from_rules(rules, args.rules)
    if rule_findings is None:
        return 1

    judge = _read_json_file(args.judge, "judge")
    judge_findings = _judge_findings_from_judge(judge, args.judge)
    if judge_findings is None:
        return 1

    aspects_data = _read_json_file(args.aspects, "aspects")
    aspects = _aspects_list_from_aspects_file(aspects_data, args.aspects)
    if aspects is None:
        return 1

    prev_failed_error_keys, ok = _prev_failed_error_keys(args)
    if not ok:
        return 1

    try:
        decision = decide(
            rule_findings,
            judge_findings,
            aspects,
            round_num=args.round_num,
            max_retries=args.max_retries,
            prev_failed_error_keys=prev_failed_error_keys,
        )
    except GateError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    payload = {
        "schema_version": 1,
        "verdict": decision.verdict,
        "round": decision.round,
        "passed": decision.passed,
        "failed_error_keys": decision.failed_error_keys,
        "error_findings": [f.to_dict() for f in decision.error_findings],
        "warning_findings": [f.to_dict() for f in decision.warning_findings],
        "all_findings": [f.to_dict() for f in decision.all_findings],
    }
    rc = _write_output(payload, args.out)
    if rc != 0:
        return rc

    report_md = render_report(decision, mode=mode)
    if args.report == "-":
        print(report_md)
        return 0
    try:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report_md)
    except OSError as e:
        print(f"error: failed to write report file {args.report!r}: {e}", file=sys.stderr)
        return 1
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="review_gate.py", description="genko レビューゲート CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # allow_abbrev=False: 廃止した --research（真偽フラグ）が --research-present の
    # 曖昧でない省略形として argparse に暗黙で受理されてしまうのを防ぐ。
    aspects_parser = sub.add_parser(
        "aspects", help="rules.json から LLM judge 観点を選定する", allow_abbrev=False
    )
    aspects_parser.add_argument(
        "--aspects-file", required=True, dest="aspects_file", help="judge-aspects.yaml のパス"
    )
    aspects_parser.add_argument("--rules", required=True, help="qualitycheck.py が出力した rules.json のパス")
    aspects_parser.add_argument("--mode", required=True, choices=["article", "document"])
    aspects_parser.add_argument("--round", required=True, type=int, dest="round_num", help="レビューの回転数（1 始まり）")
    aspects_parser.add_argument(
        "--research-present", action="store_true", dest="research_present",
        help="リサーチ結果が存在する（research_present）。qualitycheck の --research（パス）とは別物",
    )
    aspects_parser.add_argument("--out", required=True, help="出力先パス。'-' で stdout")

    decide_parser = sub.add_parser(
        "decide", help="rules.json と judge.json をマージして verdict を決定する"
    )
    decide_parser.add_argument("--rules", required=True, help="qualitycheck.py が出力した rules.json のパス")
    decide_parser.add_argument("--judge", required=True, help="judge エージェントが出力した judge.json のパス")
    decide_parser.add_argument(
        "--aspects", required=True, help="review_gate.py aspects が出力した aspects.json のパス"
    )
    decide_parser.add_argument(
        "--round", required=True, type=int, dest="round_num", help="レビューの回転数（1 始まり）"
    )
    decide_parser.add_argument(
        "--max-retries", type=int, default=MAX_AUTO_FIX_RETRIES, dest="max_retries",
        help="自動修正の最大リトライ回数（既定値は config.MAX_AUTO_FIX_RETRIES）",
    )
    decide_parser.add_argument("--prev", default=None, help="前回転の decision.json のパス（任意）")
    decide_parser.add_argument("--out", required=True, help="decision.json の出力先パス。'-' で stdout")
    decide_parser.add_argument("--report", required=True, help="report.md の出力先パス。'-' で stdout")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "aspects":
        return _cmd_aspects(args)
    if args.command == "decide":
        return _cmd_decide(args)

    # argparse の required=True により command は必ずどれかにマッチするため、
    # ここには到達しない防御的分岐。
    parser.error(f"unknown command: {args.command!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
