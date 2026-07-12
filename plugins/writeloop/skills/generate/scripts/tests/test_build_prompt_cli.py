import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def run_cli(args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "build_prompt.py"), *args],
        capture_output=True, text=True,
    )


# ARTICLE_PLAN は test_promptbuild.py と同一内容の定数をこのファイル冒頭にも定義する
# （conftest 経由の共有はしない。fixture 文字列の重複は許容する）
ARTICLE_PLAN = """---
mode: article
article_type: impl
profile: research
created: 2026-07-12
title_draft: "Temporal で学ぶ Durable Execution"
slug: durable-execution
tags: [go, temporal]
target_audience: "Go で API サーバーを運用していてリトライ処理を自作している中級者。"
goal: "Durable Execution の価値を判断できるようになる"
topics_in_scope: ["Workflow の再実行モデル"]
topics_out_of_scope: []
constraints: []
---
## 壁打ちメモ
"""


def test_writer_cli_writes_prompt(tmp_path):
    plan = tmp_path / "plan.md"; plan.write_text(ARTICLE_PLAN, encoding="utf-8")
    out = tmp_path / "writer-prompt.md"
    r = run_cli(["writer", "--plan", str(plan), "--mode", "article", "--out", str(out)])
    assert r.returncode == 0, r.stderr
    assert out.read_text(encoding="utf-8").startswith("[文体ガイド（記事タイプ: impl）]")


def test_writer_cli_mode_mismatch(tmp_path):
    plan = tmp_path / "plan.md"; plan.write_text(ARTICLE_PLAN, encoding="utf-8")
    r = run_cli(["writer", "--plan", str(plan), "--mode", "document", "--out", "-"])
    assert r.returncode == 1 and r.stderr.startswith("error:")
