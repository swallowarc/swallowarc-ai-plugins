#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "regex"]
# ///
"""writeloop レビューゲート CLI。

サブコマンド:
- aspects: rules.json（qualitycheck.py の出力）の facts と --mode/--round/--research
  から LLM judge の評価観点を選定し、aspects.json を出力する
  （wlq.aspects.load_aspects / select_aspects の薄いエントリ）。
- decide: 未実装（Task 14 でこの CLI に追加される）。

使い方:
    review_gate.py aspects --aspects-file <judge-aspects.yaml> --rules <rules.json>
                            --mode article|document --round <N> [--research]
                            --out <path|->

exit code: aspects の選定結果（0 件を含む）に関わらず 0。実行エラー（ファイル
不存在、JSON/YAML 不正、引数不正等）のみ非ゼロ + stderr にメッセージ。
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


def _read_json_file(path: str, label: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
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

    article_type = facts.get("article_type", "general")
    if not isinstance(article_type, str) or not article_type:
        article_type = "general"

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
            research_present=args.research,
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


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="review_gate.py", description="writeloop レビューゲート CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    aspects_parser = sub.add_parser("aspects", help="rules.json から LLM judge 観点を選定する")
    aspects_parser.add_argument(
        "--aspects-file", required=True, dest="aspects_file", help="judge-aspects.yaml のパス"
    )
    aspects_parser.add_argument("--rules", required=True, help="qualitycheck.py が出力した rules.json のパス")
    aspects_parser.add_argument("--mode", required=True, choices=["article", "document"])
    aspects_parser.add_argument("--round", required=True, type=int, dest="round_num", help="レビューの回転数（1 始まり）")
    aspects_parser.add_argument(
        "--research", action="store_true", help="リサーチ結果が存在する（research_present）"
    )
    aspects_parser.add_argument("--out", required=True, help="出力先パス。'-' で stdout")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "aspects":
        return _cmd_aspects(args)

    # argparse の required=True により command は必ずどれかにマッチするため、
    # ここには到達しない防御的分岐。
    parser.error(f"unknown command: {args.command!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
