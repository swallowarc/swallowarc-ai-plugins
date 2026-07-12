"""prose.py のテスト。

移植元テスト: internal/infrastructure/quality/prose_test.go @ autopostd 20c740b

Go テストケース対応表（全件移植。テーブル駆動の t.Run サブテスト名を左に示す）:

TestExtractProse:
- コードブロック除去                     -> test_extract_prose_code_block_removed
- 参考情報セクション除去                 -> test_extract_prose_references_section_removed
- 参考情報の後の H2 は残す               -> test_extract_prose_keeps_h2_after_references_section
- インラインリンクは表示テキストのみ残す -> test_extract_prose_inline_link_keeps_display_text_only
- 画像は alt テキストのみ残す            -> test_extract_prose_image_keeps_alt_text_only
- 複数リンクも全て正規化する             -> test_extract_prose_normalizes_multiple_links
- リンクを含む行の行末強制改行は保持     -> test_extract_prose_preserves_trailing_hard_break

TestSplitSentences:
- 三種の終止符で分割                     -> test_split_sentences_splits_on_three_terminators
- 見出し行は除外                         -> test_split_sentences_excludes_heading_lines
- 空行は除外                             -> test_split_sentences_excludes_blank_lines
- 表行は除外                             -> test_split_sentences_excludes_table_rows

TestCountProseRunes:
- 空白と改行を除外                       -> test_count_prose_runes_excludes_whitespace_and_newlines
- タブも除外                             -> test_count_prose_runes_excludes_tab
- 全角スペースも除外                     -> test_count_prose_runes_excludes_fullwidth_space
- 空文字列                               -> test_count_prose_runes_empty_string

上記 15 件で prose_test.go の全テーブル行を移植済み（取捨選択なし）。

加えて、.kata/task-04.md Step 1 に記載された代表ケース（Go のテストデータとは
異なる独自の入力例）をそのまま収録する（test_extract_prose_replaces_code_block_with_blank_line /
test_extract_prose_removes_references_section_and_keeps_following_body /
test_extract_prose_strips_inline_links_and_images /
test_split_sentences_splits_on_terminators_and_skips_tables /
test_count_prose_runes_ignores_whitespace）。これらは全件移植の対象（Go 側テーブル）
とは別に、タスク本文が指定した代表ケースとして重複を許容して残す。

strip_inline_links には Go 側に専用のユニットテスト（TestStripInlineLinks 等）が
存在せず、TestExtractProse の各ケースを通じて間接的にのみ検証されている。
Go のドキュメントコメント（prose.go: inlineLinkRe 定義の直前）に明記された
「参照形式（[text][ref]）と自動リンク（<url>）は対象外」という設計上の制限は
Go に専用テストが無いため、実装コメントを読んで確定させた追加確認として
test_strip_inline_links_does_not_touch_reference_style_links_or_autolinks を足す
（Go 側に対応テストなし。ソースコメントからの導出）。
"""

from wlq.prose import count_prose_runes, extract_prose, split_sentences, strip_inline_links


# --- タスク本文 (.kata/task-04.md) Step 1 の代表ケース（そのまま収録） ---


def test_extract_prose_replaces_code_block_with_blank_line():
    body = "文A。\n```go\ncode\n```\n文B。"
    assert extract_prose(body) == "文A。\n\n文B。"


def test_extract_prose_removes_references_section_and_keeps_following_body():
    body = "文A。\n## 参考情報\n- [x](http://e)\n## 次\n文B。"
    prose = extract_prose(body)
    assert "参考情報" not in prose
    assert "文B。" in prose


def test_extract_prose_strips_inline_links_and_images():
    assert extract_prose("これは[リンク](http://e)と![画像](i.png)です。") == "これはリンクと画像です。"


def test_split_sentences_splits_on_terminators_and_skips_tables():
    prose = "一文目。二文目！三文目？\n| a | b |\n## 見出し\n断片"
    assert split_sentences(prose) == ["一文目。", "二文目！", "三文目？", "断片"]


def test_count_prose_runes_ignores_whitespace():
    # 非空白は あ・い・う・e・x の 5 文字（半角/全角スペース・タブ・改行は数えない）
    assert count_prose_runes("あい う\te\n　x") == 5


# --- TestExtractProse (prose_test.go:8-32) の全件移植 ---


def test_extract_prose_code_block_removed():
    body = "文章。\n```go\ncode\n```\n続き。"
    assert extract_prose(body) == "文章。\n\n続き。"


def test_extract_prose_references_section_removed():
    body = "本文。\n## 参考情報\n- [a](http://x)\n情報確認日: 2026-07-04"
    assert extract_prose(body) == "本文。"


def test_extract_prose_keeps_h2_after_references_section():
    body = "## A\n本文。\n## 参考情報\n- [a](http://x)\n## B\n残る。"
    assert extract_prose(body) == "## A\n本文。\n## B\n残る。"


def test_extract_prose_inline_link_keeps_display_text_only():
    body = "詳細は[公式ドキュメント](https://example.com/very/long/path)を参照。"
    assert extract_prose(body) == "詳細は公式ドキュメントを参照。"


def test_extract_prose_image_keeps_alt_text_only():
    body = "![構成図](https://example.com/diagram.png)を示す。"
    assert extract_prose(body) == "構成図を示す。"


def test_extract_prose_normalizes_multiple_links():
    body = "[A](http://a)と[B](http://b)。"
    assert extract_prose(body) == "AとB。"


def test_extract_prose_preserves_trailing_hard_break():
    body = "文A[リンク](https://x)。  \n文B。"
    assert extract_prose(body) == "文Aリンク。  \n文B。"


# --- TestSplitSentences (prose_test.go:34-55) の全件移植 ---


def test_split_sentences_splits_on_three_terminators():
    prose = "短い文。これは二つ目！三つ目？"
    assert split_sentences(prose) == ["短い文。", "これは二つ目！", "三つ目？"]


def test_split_sentences_excludes_heading_lines():
    prose = "## 見出し\n本文です。"
    assert split_sentences(prose) == ["本文です。"]


def test_split_sentences_excludes_blank_lines():
    prose = "文A。\n\n文B。"
    assert split_sentences(prose) == ["文A。", "文B。"]


def test_split_sentences_excludes_table_rows():
    prose = "本文です。\n| 列1 | 列2 |\n| --- | --- |\n次の文。"
    assert split_sentences(prose) == ["本文です。", "次の文。"]


# --- TestCountProseRunes (prose_test.go:57-78) の全件移植 ---


def test_count_prose_runes_excludes_whitespace_and_newlines():
    assert count_prose_runes("あい うえ\nお") == 5


def test_count_prose_runes_excludes_tab():
    assert count_prose_runes("a\tb") == 2


def test_count_prose_runes_excludes_fullwidth_space():
    assert count_prose_runes("あ　い　う") == 3


def test_count_prose_runes_empty_string():
    assert count_prose_runes("") == 0


# --- strip_inline_links: Go 実装のドキュメントコメントから確定させた追加確認 ---


def test_strip_inline_links_does_not_touch_reference_style_links_or_autolinks():
    """prose.go の inlineLinkRe 直前コメント「参照形式（[text][ref]）と自動リンク
    （<url>）は対象外」を確認する。Go に専用テストは無い。
    """
    line = "[text][ref]や<http://example.com>はそのまま。"
    assert strip_inline_links(line) == line
