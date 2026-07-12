#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "regex"]
# ///
"""writeloop プロンプト組立 CLI（writer / judge / fixer）。"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml  # noqa: E402

from wlq.promptbuild import (  # noqa: E402
    _JST, build_fixer_prompt, build_judge_prompt, build_writer_prompt, load_plan,
)

DEFAULT_REFS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references")


def _read_text(path: str, label: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"error: failed to read {label} file {path!r}: {e}", file=sys.stderr)
        sys.exit(1)


def _write_text(text: str, out: str) -> int:
    if out == "-":
        print(text, end="")
        return 0
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError as e:
        print(f"error: failed to write output file {out!r}: {e}", file=sys.stderr)
        return 1
    return 0


def _load_plan_checked(args: argparse.Namespace):
    try:
        plan = load_plan(args.plan)
    except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as e:
        print(f"error: failed to load plan {args.plan!r}: {e}", file=sys.stderr)
        sys.exit(1)
    if plan.mode != args.mode:
        print(f"error: --mode {args.mode!r} が plan の mode {plan.mode!r} と一致しない", file=sys.stderr)
        sys.exit(1)
    return plan


def _cmd_writer(args: argparse.Namespace) -> int:
    plan = _load_plan_checked(args)
    research = _read_text(args.research, "research") if args.research else None
    try:
        prompt = build_writer_prompt(plan, research, args.refs_dir, datetime.now(_JST))
    except (OSError, UnicodeDecodeError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return _write_text(prompt, args.out)


def _cmd_judge(args: argparse.Namespace) -> int:
    plan = _load_plan_checked(args)
    draft = _read_text(args.draft, "draft")
    try:
        data = json.loads(_read_text(args.aspects, "aspects"))
    except json.JSONDecodeError as e:
        print(f"error: failed to parse aspects file {args.aspects!r} as JSON: {e}", file=sys.stderr)
        return 1
    aspects = data.get("aspects") if isinstance(data, dict) else None
    if not isinstance(aspects, list):
        print(f"error: aspects file {args.aspects!r} is missing an 'aspects' array", file=sys.stderr)
        return 1
    research = _read_text(args.research, "research") if args.research else None
    try:
        prompt = build_judge_prompt(plan, draft, aspects, research)
    except (OSError, UnicodeDecodeError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return _write_text(prompt, args.out)


def _cmd_fixer(args: argparse.Namespace) -> int:
    plan = _load_plan_checked(args)
    draft = _read_text(args.draft, "draft")
    try:
        decision = json.loads(_read_text(args.decision, "decision"))
    except json.JSONDecodeError as e:
        print(f"error: failed to parse decision file {args.decision!r} as JSON: {e}", file=sys.stderr)
        return 1
    if not isinstance(decision, dict):
        print(f"error: decision file {args.decision!r} must contain a JSON object", file=sys.stderr)
        return 1
    try:
        prompt = build_fixer_prompt(plan, draft, decision, args.refs_dir, datetime.now(_JST))
    except (OSError, UnicodeDecodeError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return _write_text(prompt, args.out)


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--plan", required=True, help="plan.md のパス")
    p.add_argument("--mode", required=True, choices=["article", "document"])
    p.add_argument("--refs-dir", default=DEFAULT_REFS_DIR, dest="refs_dir", help="references ディレクトリ")
    p.add_argument("--out", required=True, help="出力先パス。'-' で stdout")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_prompt.py", description="writeloop プロンプト組立 CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    writer_p = sub.add_parser("writer", help="writer 用プロンプトを組み立てる")
    _add_common(writer_p)
    writer_p.add_argument("--research", default=None, help="research.md のパス（任意）")
    judge_p = sub.add_parser("judge", help="judge 用プロンプトを組み立てる")
    _add_common(judge_p)
    judge_p.add_argument("--draft", required=True, help="draft markdown ファイルのパス")
    judge_p.add_argument("--aspects", required=True, help="review_gate aspects が出力した aspects.json のパス")
    judge_p.add_argument("--research", default=None, help="research.md のパス（任意）")
    fixer_p = sub.add_parser("fixer", help="fixer 用プロンプトを組み立てる")
    _add_common(fixer_p)
    fixer_p.add_argument("--draft", required=True, help="修正前 draft のパス")
    fixer_p.add_argument("--decision", required=True, help="review_gate decide が出力した decision.json のパス")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.command == "writer":
        return _cmd_writer(args)
    if args.command == "judge":
        return _cmd_judge(args)
    if args.command == "fixer":
        return _cmd_fixer(args)
    raise AssertionError(f"unknown command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
