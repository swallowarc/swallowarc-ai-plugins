"""fences.py のテスト。

移植元テスト: internal/infrastructure/quality/checker_code_test.go @ autopostd 20c740b

Go テストケース対応表（parseFencedCodeBlocks 系。全件移植）:
- TestParseFencedCodeBlocks_BasicBlocks             -> test_basic_blocks
- TestParseFencedCodeBlocks_NestedFences            -> test_nested_fences
- TestParseFencedCodeBlocks_ClosingFenceMustBeBare  -> test_closing_fence_must_be_bare
- TestParseFencedCodeBlocks_UnclosedFence           -> test_unclosed_fence
- TestParseFencedCodeBlocks_NoBlocks                -> test_no_blocks

checker_code_test.go には他にも TestRuleBasedChecker_CodeLanguageTag /
TestRuleBasedChecker_CodeKindLabel_* / TestRuleBasedChecker_MermaidContext /
TestCheckCodeLineLength があるが、これらは checkCodeLanguageTag 等の別チェック
関数（Task 3 のスコープ外。fences.py が提供する parse_fenced_code_blocks を
利用する側の後続タスク）のテストであり、parseFencedCodeBlocks 系ではないため
対象外。

タスク本文 (.kata/task-03.md) Step 1 の代表ケースは以下にそのまま収録する:
- test_detects_backtick_fenced_block
- test_tilde_fence_and_unclosed_block

加えて、Go 実装 (checker_code.go:33 `trimmed := strings.TrimSpace(line)`) を
読んで確定させた「インデント付きフェンスの扱い」（フェンス判定は行を trim して
から行うため、行頭インデントの有無はフェンス開始/終了の判定に影響しない）を
確認する test_indented_fence_is_still_detected を追加する（Go 側に対応する
専用テストは無く、実装コメントの読解から導出した確認用テスト）。
"""

from wlq.fences import parse_fenced_code_blocks


# --- タスク本文 Step 1 の代表ケース（そのまま収録） ---

def test_detects_backtick_fenced_block():
    lines = ["前文", "```go", "code", "```", "後文"]
    blocks = parse_fenced_code_blocks(lines)
    assert len(blocks) == 1
    assert (blocks[0].start_line, blocks[0].end_line) == (1, 3)


def test_tilde_fence_and_unclosed_block():
    assert len(parse_fenced_code_blocks(["~~~", "x", "~~~"])) == 1
    unclosed = parse_fenced_code_blocks(["```", "x"])
    assert len(unclosed) == 1  # 閉じフェンス無しの扱いは Go 実装に一致させる


# --- checker_code_test.go の parseFencedCodeBlocks 系（全件移植） ---

def test_basic_blocks():
    """TestParseFencedCodeBlocks_BasicBlocks (checker_code_test.go:11-33) の移植。"""
    lines = [
        "text",          # 0
        "```go",         # 1 開始（言語タグあり）
        "fmt.Println()",  # 2
        "```",           # 3 閉じ
        "",              # 4
        "~~~",           # 5 開始（言語タグなし）
        "plain",         # 6
        "~~~",           # 7 閉じ
    ]
    blocks = parse_fenced_code_blocks(lines)
    assert len(blocks) == 2
    assert (blocks[0].start_line, blocks[0].end_line, blocks[0].lang) == (1, 3, "go")
    assert (blocks[1].start_line, blocks[1].end_line, blocks[1].lang) == (5, 7, "")


def test_nested_fences():
    """TestParseFencedCodeBlocks_NestedFences (checker_code_test.go:35-58) の移植。
    外側フェンスより短い・別記号のフェンス風の行はブロックの内容として扱う。
    """
    lines = [
        "````markdown",  # 0 開始（backtick 4 つ）
        "```",           # 1 内容（3 つなので閉じない）
        "echo hi",       # 2 内容
        "```",           # 3 内容
        "````",          # 4 閉じ
        "~~~text",       # 5 開始（tilde）
        "```",           # 6 内容（記号が違うので閉じない）
        "~~~",           # 7 閉じ
    ]
    blocks = parse_fenced_code_blocks(lines)
    assert len(blocks) == 2
    assert (blocks[0].start_line, blocks[0].end_line, blocks[0].lang) == (0, 4, "markdown")
    assert (blocks[1].start_line, blocks[1].end_line, blocks[1].lang) == (5, 7, "text")


def test_closing_fence_must_be_bare():
    """TestParseFencedCodeBlocks_ClosingFenceMustBeBare (checker_code_test.go:60-75) の移植。
    フェンス記号の後にテキストが続く行は閉じフェンスではない。
    """
    lines = [
        "```go",      # 0 開始
        "``` inner",  # 1 内容（閉じではない）
        "```",        # 2 閉じ
    ]
    blocks = parse_fenced_code_blocks(lines)
    assert len(blocks) == 1
    assert blocks[0].end_line == 2


def test_unclosed_fence():
    """TestParseFencedCodeBlocks_UnclosedFence (checker_code_test.go:77-87) の移植。
    閉じフェンスが無いままファイル末尾に達した場合も 1 ブロックとして数え、
    end_line は len(lines) になる。
    """
    lines = ["```go", "code"]
    blocks = parse_fenced_code_blocks(lines)
    assert len(blocks) == 1
    assert (blocks[0].start_line, blocks[0].end_line, blocks[0].lang) == (0, 2, "go")


def test_no_blocks():
    """TestParseFencedCodeBlocks_NoBlocks (checker_code_test.go:89-95) の移植。"""
    blocks = parse_fenced_code_blocks(["## 見出し", "本文のみ。"])
    assert len(blocks) == 0


# --- Go 実装の読解から確定させた追加確認（Go 側に専用テストなし） ---

def test_indented_fence_is_still_detected():
    """Go 実装 checker_code.go:33 (`trimmed := strings.TrimSpace(line)`) に準拠。
    フェンス判定は行を trim してから行うため、CommonMark の「4 スペース以上の
    インデントはコードブロックになりフェンスと解釈されない」という規則は適用
    されない。インデント付きの ```/~~~ 行もフェンスとして検出される。
    """
    lines = ["    ```go", "    code", "    ```"]
    blocks = parse_fenced_code_blocks(lines)
    assert len(blocks) == 1
    assert (blocks[0].start_line, blocks[0].end_line, blocks[0].lang) == (0, 2, "go")
