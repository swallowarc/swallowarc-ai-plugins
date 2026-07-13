#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "regex"]
# ///
"""genko 品質チェック CLI。

wlq.runner.run_checks に draft/plan/research の内容を渡し、結果を rules.json
スキーマの JSON として出力する薄いエントリ。順序保証・モード分岐・facts 算出は
すべて wlq/runner.py の責務であり、ここでは argparse・ファイル IO・JSON 出力のみを
行う。

使い方:
    qualitycheck.py --draft <path> --mode article|document
                     [--plan <path>] [--type <article_type>] [--research <path>]
                     --out <path|->

exit code: findings の合否に関わらず 0。実行エラー（draft/plan/research ファイル
不存在、引数不正、--mode の値不正等）のみ非ゼロ + stderr にメッセージ。
"""
import argparse
import json
import os
import sys

# uv run / `python3 qualitycheck.py` のどちらで実行しても `wlq` パッケージを
# import できるよう、自ディレクトリを sys.path に追加してから import する。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wlq.frontmatter import FrontmatterError, parse_frontmatter  # noqa: E402
from wlq.runner import run_checks  # noqa: E402


def _read_text_file(path: str, label: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"error: failed to read {label} file {path!r}: {e}", file=sys.stderr)
        sys.exit(1)


def _resolve_plan(plan_path: str | None) -> tuple[str | None, list[str]]:
    """--plan の frontmatter から article_type / constraints を読む。

    plan_path が None なら (None, []) を返す。article_type キーが無い、または
    文字列でない場合は None。constraints キーが無い、またはリストでない場合は []。
    """
    if plan_path is None:
        return None, []

    text = _read_text_file(plan_path, "plan")
    try:
        fm, _ = parse_frontmatter(text)
    except FrontmatterError as e:
        print(f"error: failed to parse plan frontmatter: {e}", file=sys.stderr)
        sys.exit(1)

    article_type = fm.get("article_type")
    if not isinstance(article_type, str):
        article_type = None

    constraints = fm.get("constraints")
    if isinstance(constraints, list):
        constraints = [str(c) for c in constraints]
    else:
        constraints = []

    return article_type, constraints


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qualitycheck.py", description="genko 品質チェック CLI"
    )
    parser.add_argument("--draft", required=True, help="draft markdown ファイルのパス")
    parser.add_argument("--mode", required=True, choices=["article", "document"])
    parser.add_argument("--plan", default=None, help="plan.md のパス（任意）")
    parser.add_argument(
        "--type", dest="article_type", default=None, help="article_type（--plan より優先）"
    )
    parser.add_argument("--research", default=None, help="research 結果ファイルのパス（任意）")
    parser.add_argument("--out", required=True, help="出力先パス。'-' で stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    draft_text = _read_text_file(args.draft, "draft")
    plan_article_type, constraints = _resolve_plan(args.plan)
    article_type = args.article_type or plan_article_type or "general"

    research_content = None
    if args.research is not None:
        research_content = _read_text_file(args.research, "research")

    try:
        findings, facts = run_checks(
            draft_text,
            mode=args.mode,
            article_type=article_type,
            constraints=constraints,
            research_content=research_content,
        )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    result = {
        "schema_version": 1,
        "mode": args.mode,
        "findings": [f.to_dict() for f in findings],
        "facts": facts,
    }
    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.out == "-":
        print(output)
    else:
        try:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(output)
                f.write("\n")
        except OSError as e:
            print(f"error: failed to write output file {args.out!r}: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
