# genko 独自チェック（autopostd に対応する移植元は無い）。
"""進行実況（メタ文）の頻度チェック。

jp-writing:cognitive-rhythm-writing の「緩みと駄文の見分け方」が定義する
「文書を更新する文」（記事自身の進行・構成だけを述べ、対象の新情報がない文）のうち、
定型パターンで検出できる進行実況（「ここまで見てきたように」「次のセクションでは〜を
見ていきます」等）を頻度制限する（原典: k16shikano 氏 gist、Unlicense）。

導入での予告（「本記事では〜」）のような正当な用途が少数あるため、禁止ではなく
頻度制限とする（severity="warning"。合否には影響しない）。パターン化できない
文脈依存の変異形は、judge の meta_commentary 観点（references/judge-aspects.yaml）が
質的に評価する。

対象範囲: 呼び出し側が extract_prose 済みの文字列を渡すことを前提とする
（checks_ai_style.py の prose 系チェックと同じ扱い）。
"""
from . import config
from .checks_ai_style import _count_phrases_longest_first
from .model import Finding, check_fail, check_pass

_NAME_PROGRESS_NARRATION_FREQ = "progress_narration_freq"


def check_progress_narration_freq(
    prose: str,
    *,
    patterns: list[str] = config.PROGRESS_NARRATION_PATTERNS,
    max_total: int = config.PROGRESS_NARRATION_MAX,
) -> Finding:
    """進行実況フレーズの合計出現数が max_total を超えた場合に warning とする。

    カウントは checks_ai_style.py の「長いパターン優先で消費」ロジックを再利用し、
    包含関係にあるパターンを追加しても二重計上しないようにする。
    """
    total, breakdown = _count_phrases_longest_first(prose, patterns)
    if total <= max_total:
        return check_pass(
            _NAME_PROGRESS_NARRATION_FREQ,
            f"progress narration occurrences {total} within limit {max_total}",
            "warning",
        )
    detail = (
        f"{total} progress narration occurrence(s) exceed limit {max_total}: "
        f"{', '.join(breakdown)}"
    )
    return check_fail(
        _NAME_PROGRESS_NARRATION_FREQ,
        detail,
        "記事の進行や構成を実況する文（「ここまで見てきたように」「次のセクションでは〜を"
        "見ていきます」等）が多すぎます。対象の新しい情報（技術・事実・手順・判断）を"
        "伝える文に書き換えるか、削除してください（導入での予告 1 回程度は残してよい）",
        "warning",
    )
