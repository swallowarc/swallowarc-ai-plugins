# ported from: internal/infrastructure/quality/checker.go:328-358 @ autopostd 20c740b
import yaml


class FrontmatterError(Exception):
    pass


def parse_frontmatter(content: str) -> tuple[dict, str]:
    lines = content.split("\n")
    if not lines or lines[0].rstrip(" \t\r") != "---":
        raise FrontmatterError("frontmatter block not found")
    closing = -1
    for i in range(1, len(lines)):
        if lines[i].rstrip(" \t\r") == "---":
            closing = i
            break
    if closing == -1:
        raise FrontmatterError("frontmatter closing delimiter not found")
    try:
        fm = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError as e:
        raise FrontmatterError(f"invalid frontmatter yaml: {e}") from e
    if fm is None:
        raise FrontmatterError("frontmatter is empty")
    if not isinstance(fm, dict):
        raise FrontmatterError("invalid frontmatter yaml: not a mapping")
    return fm, "\n".join(lines[closing + 1:])
