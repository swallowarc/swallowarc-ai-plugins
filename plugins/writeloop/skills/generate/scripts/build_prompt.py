#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "regex"]
# ///
"""writeloop プロンプト組立 CLI（writer / judge / fixer）。"""
import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml  # noqa: E402

from wlq.promptbuild import _JST, build_writer_prompt, load_plan  # noqa: E402

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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.command == "writer":
        return _cmd_writer(args)
    raise AssertionError(f"unknown command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
