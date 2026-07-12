# ported from: internal/infrastructure/quality/checker_title.go @ autopostd 20c740b
"""タイトル長のソフトチェック（phase4 #7 の一部）。

check_title_length は frontmatter の title を rune 数で計測し、len_min 未満または
len_max 超で warning とする。error にはしない: 検証済みエビデンスが英語データの
外挿であり、日本語タイトルの最適長を error で強制できる確度が無いため（spec 決定事項。
checker_title.go:12-14 のコメントに準拠）。title が無い/空の場合は skip pass とする
（欠落自体は frontmatter_values が error で拾う）。シリーズ prefix 付きタイトル
（「シリーズ名 #01 〜」）も prefix を含めて全体で計測する。
"""
from . import config
from .model import Finding, check_fail, check_pass

_NAME_TITLE_LENGTH = "title_length"
_SEVERITY_WARNING = "warning"

# titleLengthSuggestion（checker_title.go:19）の移植。
_TITLE_LENGTH_SUGGESTION = "重要キーワードを先頭側に置き、全角20〜32文字を目安にタイトルを調整してください"


def check_title_length(
    fm: dict,
    *,
    len_min: int = config.TITLE_LEN_MIN,
    len_max: int = config.TITLE_LEN_MAX,
) -> Finding:
    """checkTitleLength（checker_title.go:22）の移植。"""
    title = fm.get("title")
    if not isinstance(title, str):
        title = ""
    title = title.strip()
    if title == "":
        return check_pass(_NAME_TITLE_LENGTH, "skip: no title", _SEVERITY_WARNING)

    n = len(title)
    if n < len_min:
        return check_fail(
            _NAME_TITLE_LENGTH,
            f"title length {n} is below soft minimum {len_min}",
            _TITLE_LENGTH_SUGGESTION,
            _SEVERITY_WARNING,
        )
    if n > len_max:
        return check_fail(
            _NAME_TITLE_LENGTH,
            f"title length {n} exceeds soft maximum {len_max}",
            _TITLE_LENGTH_SUGGESTION,
            _SEVERITY_WARNING,
        )
    return check_pass(
        _NAME_TITLE_LENGTH, f"title length {n} within {len_min}-{len_max}", _SEVERITY_WARNING
    )
