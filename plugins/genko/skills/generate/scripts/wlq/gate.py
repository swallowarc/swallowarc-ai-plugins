# ported from: internal/infrastructure/llm/judge_common.go:130-164 (judgeFindingsToChecks),
#              internal/infrastructure/temporal/workflow/helpers.go
#              (allErrorChecksPassed:32, failedFindings:44, failedWarningFindings:56,
#              failedErrorCheckKeys:87, equalKeySets:105),
#              internal/infrastructure/temporal/workflow/draft_generation.go
#              runQualityCheckLoop（verdict 判定順序、203-392 付近）
#              @ autopostd 20c740b
"""ルールベースチェック（rules.json）と LLM judge（judge.json）の findings を
マージし、本番 `runQualityCheckLoop` の合否・停滞・回数上限判定を再現する。

## round 数のマッピング（本プラン独自定義。task-14.md 記載のまま）

Go の `runQualityCheckLoop` は `attempt`（0 始まり。FixDraft を実行した回数）で
回転を数える。本プランの `round_num` は「レビュー実行回数」として 1 始まりで
数える: 初回レビュー = round 1（Go の attempt=0 時点のレビュー）、修正 N 回目
実行後のレビュー = round N+1（Go の attempt=N 時点のレビュー）。
そのため `attempt >= maxAutoFixRetries` は `round_num >= max_retries + 1` に対応する。

## verdict 判定順序

`decide()` は `runQualityCheckLoop` の分岐順序をそのまま踏襲する:

1. `passed`（`allErrorChecksPassed`）: severity=error の findings が全て passed。
2. `stalled`（停滞打ち切り）: `prev_failed_error_keys` が与えられており、かつ
   マージ後の `failed_error_check_keys` が `equalKeySets` で前回と集合一致。
   passed が確定した場合はこの判定自体を行わない（Go も `passed` なら即 return
   し、`stalled` 分岐に進まない）。
3. `retries_exhausted`: `round_num >= max_retries + 1`。
4. それ以外: `continue`。

Go の `intersect`（前回転との共通キーをログ出力するだけの補助）と
`failedCheckKeys`（severity を無視した全不合格キー。定義はあるが呼び出し箇所が
無い）は、この decide() が公開する意思決定（verdict/failed_error_keys/report）に
一切影響しないため移植しない。テストの docstring 参照。
"""
from __future__ import annotations

import dataclasses

from .model import Finding

_VALID_SEVERITIES = ("error", "warning")


class GateError(Exception):
    """judge findings が不正なときに送出する。

    Go の `judgeFindingsToChecks`（judge_common.go:142-145）は severity が
    error/warning 以外の場合に error を返す。この例外はその移植。
    """


def convert_judge_findings(judge_findings: list[dict], aspects: list[dict]) -> list[Finding]:
    """judge.json の findings を `Finding` のリストへ変換する（judgeFindingsToChecks の移植）。

    - name は全て "llm_judge"、category に観点キーが入る。
    - `allow_error=False` の観点で severity="error" が返された場合、warning に
      降格する（プロンプトで制約していても LLM 出力は信用しない、という
      Go 側コメントの意図をそのまま踏襲）。
    - 要求していない観点（LLM の幻覚）の finding は無視する。
    - severity が "error"/"warning" 以外の場合は `GateError` を送出する。

    judge_findings の各要素は aspect/passed/severity/location/detail/suggestion を
    持つ整形済み dict であることを前提とする（judgeOutputSchema 相当の構造検証は
    呼び出し側の CLI 層で行う。Go では `json.Unmarshal` による型検証が
    `judgeFindingsToChecks` 呼び出し前に完了しているのと同じ責務分担）。
    """
    allow_error = {a["key"]: a["allow_error"] for a in aspects}

    checks: list[Finding] = []
    for f in judge_findings:
        aspect = f["aspect"]
        if aspect not in allow_error:
            continue  # 未要求観点（幻覚）は無視

        severity = f["severity"]
        if severity not in _VALID_SEVERITIES:
            raise GateError(f"invalid severity from judge (aspect={aspect}): {severity!r}")
        if severity == "error" and not allow_error[aspect]:
            severity = "warning"

        checks.append(
            Finding(
                name="llm_judge",
                passed=bool(f["passed"]),
                severity=severity,
                detail=f.get("detail", ""),
                category=aspect,
                location=f.get("location", ""),
                suggestion=f.get("suggestion", ""),
            )
        )
    return checks


def _all_error_checks_passed(findings: list[Finding]) -> bool:
    """severity=error の findings が全て passed か（Go: `allErrorChecksPassed` helpers.go:32）。

    warning の fail は合否に影響しない。
    """
    return all(f.passed for f in findings if f.severity == "error")


def failed_error_check_keys(findings: list[Finding]) -> list[str]:
    """不合格の severity=error findings を `name/category` キーで返す（重複排除・出現順）。

    Go: `failedErrorCheckKeys`（helpers.go:87）の移植。
    """
    seen: set[str] = set()
    keys: list[str] = []
    for f in findings:
        if f.passed or f.severity != "error":
            continue
        key = f"{f.name}/{f.category}"
        if key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


def _equal_key_sets(a: list[str], b: list[str]) -> bool:
    """集合として等しいか（順序無視。Go: `equalKeySets` helpers.go:105）。"""
    return len(a) == len(b) and set(a) == set(b)


@dataclasses.dataclass
class Decision:
    verdict: str  # "passed" | "continue" | "stalled" | "retries_exhausted"
    round: int
    passed: bool
    failed_error_keys: list[str]
    error_findings: list[Finding]
    warning_findings: list[Finding]
    all_findings: list[Finding]


def decide(
    rule_findings: list[Finding],
    judge_findings: list[dict],
    aspects: list[dict],
    *,
    round_num: int,
    max_retries: int,
    prev_failed_error_keys: list[str] | None,
) -> Decision:
    """rule_findings と judge_findings をマージし、verdict を決定する。

    判定順序はモジュール docstring 記載の通り `runQualityCheckLoop` の移植:
    passed -> stalled -> retries_exhausted -> continue。
    """
    merged = list(rule_findings) + convert_judge_findings(judge_findings, aspects)

    passed = _all_error_checks_passed(merged)
    failed_keys = failed_error_check_keys(merged)

    if passed:
        verdict = "passed"
    elif prev_failed_error_keys is not None and _equal_key_sets(prev_failed_error_keys, failed_keys):
        verdict = "stalled"
    elif round_num >= max_retries + 1:
        verdict = "retries_exhausted"
    else:
        verdict = "continue"

    error_findings = [f for f in merged if f.severity == "error" and not f.passed]
    warning_findings = [f for f in merged if f.severity == "warning" and not f.passed]

    return Decision(
        verdict=verdict,
        round=round_num,
        passed=passed,
        failed_error_keys=failed_keys,
        error_findings=error_findings,
        warning_findings=warning_findings,
        all_findings=merged,
    )
