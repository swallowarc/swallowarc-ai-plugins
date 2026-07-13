import pytest
from wlq.frontmatter import FrontmatterError, parse_frontmatter


def test_parses_valid_frontmatter_and_returns_body():
    content = '---\ntitle: "t"\ntags: [a, b]\n---\n本文です。\n'
    fm, body = parse_frontmatter(content)
    assert fm["title"] == "t"
    assert fm["tags"] == ["a", "b"]
    assert body == "本文です。\n"


@pytest.mark.parametrize("case, content", [
    ("先頭が --- でない", "title: t\n---\n本文"),
    ("閉じ --- が無い", "---\ntitle: t\n本文"),
    ("YAML 不正", "---\ntitle: [unclosed\n---\n本文"),
    ("frontmatter が空", "---\n---\n本文"),
    ("マッピングでない", "---\njust a string\n---\n本文"),
])
def test_invalid_frontmatter_raises(case, content):
    with pytest.raises(FrontmatterError):
        parse_frontmatter(content)
