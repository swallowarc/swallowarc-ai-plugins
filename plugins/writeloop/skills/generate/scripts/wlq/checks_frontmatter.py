# ported from: internal/infrastructure/quality/checker_frontmatter.go:14-201 @ autopostd 20c740b
"""Frontmatter 系のチェック 5 関数（forbidden_words / frontmatter_yaml /
frontmatter_values / description_quality / tags_format）。

checkSeriesConsistency（checker_frontmatter.go:203〜）は Task 9 スコープのためここには
含めない。

既知の乖離（Task 2 レビューからの申し送り。frontmatter_yaml のみ）:
    Go の checkFrontmatterYAML はパースエラー時に parseErr.Error() をそのまま detail に
    使う。Python では PyYAML のエラー文言が go-yaml と一致し得ないため、fail 時の
    detail は str(parse_error)（= wlq.frontmatter.FrontmatterError のメッセージ。
    "invalid frontmatter yaml: ..." 等、プレフィックスの組み立て方は Go に合わせてある）
    を使う。文言そのもの（YAML パーサ由来の詳細部分）は Go と一致しない。
    pass 時の detail（"frontmatter is valid yaml"）は Go と一字一句一致させている。
    正常な記事では frontmatter は valid なので、この乖離は通常運用では発現しない。

既知の乖離（tags_format の float タグ正規化）:
    check_tags_format のタグ正規化は Go の
    `strings.ToLower(strings.TrimSpace(fmt.Sprint(v)))` を `str(v).strip().lower()` で
    再現しているが、float タグ（例: tags: [1.0]）では Go の `fmt.Sprint(1.0)` が "1" に
    なるのに対し Python の `str(1.0)` は "1.0" になり、正規化結果（重複判定・detail 文言）
    が乖離する。bool / int / str タグでは実質等価。通常運用のタグは文字列のみで
    float タグは存在しないため、実装は Python の `str(v)` のまま固定する
    （tests/test_checks_frontmatter.py で Python 側の挙動を固定済み）。
"""
from typing import Any

from . import config
from .model import Finding, check_fail, check_pass

_NAME_FORBIDDEN_WORDS = "forbidden_words"
_NAME_FRONTMATTER_YAML = "frontmatter_yaml"
_NAME_FRONTMATTER_VALUES = "frontmatter_values"
_NAME_DESCRIPTION_QUALITY = "description_quality"
_NAME_TAGS_FORMAT = "tags_format"

_SEVERITY_ERROR = "error"


def check_forbidden_words(content: str, *, words: list[str] = config.FORBIDDEN_WORDS) -> Finding:
    """checkForbiddenWords（checker_frontmatter.go:14）の移植。

    words を宣言順に走査し、content に部分文字列として含まれるものを列挙する
    （strings.Contains と同じ部分一致・単語境界なし）。
    """
    found = [word for word in words if word in content]

    if found:
        return check_fail(
            _NAME_FORBIDDEN_WORDS,
            f"forbidden words found: {', '.join(found)}",
            "",
            _SEVERITY_ERROR,
        )

    return check_pass(_NAME_FORBIDDEN_WORDS, "no forbidden words found", _SEVERITY_ERROR)


def check_frontmatter_yaml(parse_error: Exception | None) -> Finding:
    """checkFrontmatterYAML（checker_frontmatter.go:39）の移植。

    parse_error は「frontmatter のパースに失敗したかどうか」だけを表す
    （Go の checkFrontmatterYAML(parseErr error) と同じシグネチャ）。
    """
    if parse_error is not None:
        return check_fail(_NAME_FRONTMATTER_YAML, str(parse_error), "", _SEVERITY_ERROR)
    return check_pass(_NAME_FRONTMATTER_YAML, "frontmatter is valid yaml", _SEVERITY_ERROR)


def _is_empty_frontmatter_value(value: Any) -> bool:
    """isEmptyFrontmatterValue（checker_frontmatter.go:97）の移植。

    Frontmatter の値が「未設定」とみなせるかを判定する。
    """
    if value is None:
        return True
    if isinstance(value, str):
        return value == ""
    if isinstance(value, list):
        return len(value) == 0
    return False


def check_frontmatter_values(
    fm: dict, *, required: list[str] = config.REQUIRED_FRONTMATTER
) -> Finding:
    """checkFrontmatterValues（checker_frontmatter.go:56）の移植。"""
    problems = []
    for key in required:
        if key not in fm:
            problems.append(f"{key} is missing")
            continue
        value = fm[key]
        if _is_empty_frontmatter_value(value):
            problems.append(f"{key} is empty")
            continue
        if key == "tags" and not isinstance(value, list):
            problems.append("tags must be a list")

    if problems:
        return check_fail(
            _NAME_FRONTMATTER_VALUES, ", ".join(problems), "", _SEVERITY_ERROR
        )

    return check_pass(
        _NAME_FRONTMATTER_VALUES, "all required frontmatter values present", _SEVERITY_ERROR
    )


def check_description_quality(
    fm: dict,
    *,
    boilerplate: str = config.DESCRIPTION_BOILERPLATE,
    min_len: int = config.DESCRIPTION_MIN_LEN,
) -> Finding:
    """checkDescriptionQuality（checker_frontmatter.go:106）の移植。"""
    desc = fm.get("description")
    if not isinstance(desc, str):
        desc = ""
    title = fm.get("title")
    if not isinstance(title, str):
        title = ""

    d = desc.strip()
    reason = ""
    if d == "":
        reason = "description is empty"
    elif len(d) < min_len:
        reason = f"description shorter than {min_len} chars"
    elif boilerplate != "" and d == boilerplate.strip():
        reason = "description equals site boilerplate"
    elif d == title.strip():
        reason = "description equals title"

    if reason:
        return check_fail(_NAME_DESCRIPTION_QUALITY, reason, "", _SEVERITY_ERROR)
    return check_pass(_NAME_DESCRIPTION_QUALITY, "description ok", _SEVERITY_ERROR)


def check_tags_format(fm: dict) -> Finding:
    """checkTagsFormat（checker_frontmatter.go:128）の移植。"""
    if "tags" not in fm:
        # tags key not present - this should have been caught by frontmatter_values
        return check_fail(_NAME_TAGS_FORMAT, "tags key not found", "", _SEVERITY_ERROR)

    tags_value = fm["tags"]
    if not isinstance(tags_value, list):
        # Not a list - this should have been caught by frontmatter_values
        return check_fail(_NAME_TAGS_FORMAT, "tags must be a list", "", _SEVERITY_ERROR)

    if len(tags_value) == 0:
        return check_fail(_NAME_TAGS_FORMAT, "tags list is empty", "", _SEVERITY_ERROR)

    seen: set[str] = set()
    for v in tags_value:
        normalized = str(v).strip().lower()

        if normalized == "":
            return check_fail(
                _NAME_TAGS_FORMAT,
                "tag contains empty value after normalization",
                "",
                _SEVERITY_ERROR,
            )

        if normalized in seen:
            return check_fail(
                _NAME_TAGS_FORMAT,
                f"duplicate tag found: {normalized}",
                "",
                _SEVERITY_ERROR,
            )
        seen.add(normalized)

    return check_pass(_NAME_TAGS_FORMAT, "tags format ok", _SEVERITY_ERROR)
