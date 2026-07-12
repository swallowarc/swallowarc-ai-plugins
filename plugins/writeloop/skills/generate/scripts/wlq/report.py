# ported from: (該当する Go ファイルなし。writeloop 独自の決定論的レポート整形)
#              参考: internal/infrastructure/temporal/workflow/draft_generation.go の
#              NotifyAutoFixStalled / NotifyAutoFixRetriesExhausted 通知内容
#              （failedFindings/failedWarningFindings を渡す点）と役割は対応するが、
#              本番は Slack 通知文言を組み立てるのみでレポートファイルは持たない。
#              @ autopostd 20c740b
"""`wlq.gate.decide` の結果（`Decision`）を人が読む Markdown レポートに整形する。

`render_report` は LLM を使わず、同一の `Decision`/`mode` から常に同一の文字列を
返す純粋関数である。run 間で report.md を diff できることが用途（同じ draft を
2 回 decide した際の判定再現性の目視確認）であるため、findings の順序保存
（マージ順 = rule_findings + judge findings の変換順）以外の並べ替えは行わない。
"""
from __future__ import annotations

from .gate import Decision
from .model import Finding


def _escape_cell(value: str) -> str:
    """Markdown テーブルのセル内で `|` と改行がレイアウトを壊さないようにする。"""
    return value.replace("|", "\\|").replace("\n", " ")


def _findings_table(findings: list[Finding]) -> list[str]:
    lines = [
        "| name | category | detail | suggestion | location |",
        "| --- | --- | --- | --- | --- |",
    ]
    for f in findings:
        lines.append(
            f"| {_escape_cell(f.name)} | {_escape_cell(f.category)} | "
            f"{_escape_cell(f.detail)} | {_escape_cell(f.suggestion)} | "
            f"{_escape_cell(f.location)} |"
        )
    return lines


def render_report(decision: Decision, *, mode: str) -> str:
    """`decision` を決定論的な Markdown レポートに整形する。

    構成: 見出し（round と verdict）/ mode / error findings 表
    （name/category/detail/suggestion/location、findings 配列順）/
    warning findings 表（同形式）/ 件数サマリ（total / error fail / warning fail）。
    """
    lines: list[str] = [
        f"# writeloop review — round {decision.round} — {decision.verdict}",
        "",
        f"mode: {mode}",
        "",
        f"## Error findings ({len(decision.error_findings)})",
        "",
    ]
    if decision.error_findings:
        lines.extend(_findings_table(decision.error_findings))
    else:
        lines.append("(none)")

    lines.extend(
        [
            "",
            f"## Warning findings ({len(decision.warning_findings)})",
            "",
        ]
    )
    if decision.warning_findings:
        lines.extend(_findings_table(decision.warning_findings))
    else:
        lines.append("(none)")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- total: {len(decision.all_findings)}",
            f"- error fail: {len(decision.error_findings)}",
            f"- warning fail: {len(decision.warning_findings)}",
        ]
    )

    return "\n".join(lines) + "\n"
