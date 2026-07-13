# ported from: internal/infrastructure/quality/checker_frontmatter.go:203 (series==nil 分岐),
#              internal/infrastructure/quality/checker_series.go:21 (series==nil 分岐)
#              @ autopostd 20c740b
# genko は series 非対応（spec スコープ外）。findings の形を本番と揃えるため
# nil 分岐の skip=pass 定数のみを出力する。
from .model import Finding


def check_series_consistency() -> Finding:
    return Finding(name="series_consistency", passed=True, severity="error", detail="no series")


def check_series_navigation() -> Finding:
    return Finding(name="series_navigation", passed=True, severity="error",
                   detail="skipped: plan has no series")
