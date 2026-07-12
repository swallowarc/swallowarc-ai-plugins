"""checks_frontmatter.py のテスト。

移植元テスト: internal/infrastructure/quality/checker_test.go @ autopostd 20c740b
（510行。frontmatter 系 5 チェック: checkForbiddenWords / checkFrontmatterYAML /
checkFrontmatterValues / checkDescriptionQuality / checkTagsFormat に対応する部分）。

Go の対象 5 チェックはすべて RuleBasedChecker のプライベートメソッドで、
checker_test.go では RuleBasedChecker.Check()（オーケストレータ）を経由した統合テストと
してのみ検証されている。Task 8 のインターフェースは各チェックの純粋関数
（frontmatter dict / パースエラーを直接受け取る）なので、各 Go テストから
「対象チェックの pass/fail 挙動」の部分だけを抽出し、必要な fm は
wlq.frontmatter.parse_frontmatter で Go テストと同じ YAML 本文をパースして作る。

Go テストケース対応表（全件移植。取捨選択なし）:

TestRuleBasedChecker_Frontmatter_ValidPasses
    -> test_check_frontmatter_yaml_valid_passes（frontmatter_yaml 部分）
    -> test_check_frontmatter_values_valid_passes（frontmatter_values 部分）
TestRuleBasedChecker_Frontmatter_MalformedYAMLFails
    -> test_check_frontmatter_yaml_malformed_fails（frontmatter_yaml 部分のみ。
       「frontmatter_values がスキップされる」という同テスト内のアサーションは
       RuleBasedChecker.Check() のオーケストレーション挙動であり、Task 8 の
       対象関数（check_frontmatter_values 単体）では検証不能なため除外。
       Task 12（qualitycheck.py CLI）スコープ）
TestRuleBasedChecker_Frontmatter_MissingTagsKeyFails
    -> test_check_frontmatter_values_missing_tags_key_fails
TestRuleBasedChecker_Frontmatter_TagsAsScalarFails
    -> test_check_frontmatter_values_tags_as_scalar_fails
TestRuleBasedChecker_Frontmatter_EmptyValueFails
    -> test_check_frontmatter_values_empty_value_fails
TestRuleBasedChecker_DescriptionQuality_MissingFails
    -> test_check_description_quality_missing_fails
TestRuleBasedChecker_DescriptionQuality_EqualsTitleFails
    -> test_check_description_quality_equals_title_fails（detail 文字列も照合）
TestRuleBasedChecker_DescriptionQuality_TooShortFails
    -> test_check_description_quality_too_short_fails
TestRuleBasedChecker_DescriptionQuality_BoilerplateFails
    -> test_check_description_quality_boilerplate_fails（detail 文字列も照合）
TestRuleBasedChecker_DescriptionQuality_GoodDescriptionPasses
    -> test_check_description_quality_good_description_passes
TestRuleBasedChecker_TagsFormat_ValidListPasses
    -> test_check_tags_format_valid_list_passes
TestRuleBasedChecker_TagsFormat_EmptyListFails
    -> test_check_tags_format_empty_list_fails
TestRuleBasedChecker_TagsFormat_DuplicatesAfterNormalizeFails
    -> test_check_tags_format_duplicates_after_normalize_fails
TestRuleBasedChecker_TagsFormat_DuplicatesAfterTrimAndNormalizeFails
    -> test_check_tags_format_duplicates_after_trim_and_normalize_fails

--- 移植対象外（意図的な除外。取捨選択ではなく Task 8 のインターフェース範囲外） ---

TestRuleBasedChecker_QualityRules / TestRuleBasedChecker_QualityRules_EmptyForbiddenWords:
    domain.QualityRules（設定値の保持）を検証するテストであり、checkForbiddenWords 等の
    チェック関数自体の pass/fail 挙動は検証していない。config.py の定数移植は Task 2 で
    完了済みのためここでは対象外。

TestRuleBasedChecker_HeadingStructure_* / TestRuleBasedChecker_RequiredSections*:
    heading_structure / required_sections チェックのテストであり、Task 8 の対象
    （forbidden_words / frontmatter_yaml / frontmatter_values / description_quality /
    tags_format）に含まれない。

TestRuleBasedChecker_SeriesConsistency:
    checkSeriesConsistency（checker_frontmatter.go:203〜）はタスク仕様で明示的に対象外
    （Task 9 スコープ）。

TestParseFrontmatter_LineAnchored:
    parseFrontmatter（YAML frontmatter ブロックの区切り判定）自体のテストであり、
    wlq.frontmatter.parse_frontmatter は既存タスクで移植済み（tests/test_frontmatter.py）。
    Task 8 の check_frontmatter_yaml はパースエラーの有無だけを受け取る薄いラッパーで
    あり、パース処理そのものは対象外。

--- checkForbiddenWords: Go に直接対応するテストケースが存在しない ---

checker_test.go には checkForbiddenWords の pass/fail 挙動（禁止語を含む本文を実際に
チェックする）を検証する Go テストが存在しない（QualityRules 系テストは設定値の保持のみ
検証しており、本チェック関数は素通りしている）。そのため、Go テストからの移植ではなく、
task-08.md 記載の代表テスト＋関数の基本仕様（Go 実装のロジックそのまま）から
pass/fail の最小ケースを book に追加した:
- test_forbidden_word_in_content_fails（task-08.md 記載の代表テストそのもの）
- test_no_forbidden_word_passes（pass 側の基本ケース）
- test_forbidden_words_found_are_joined_in_config_order（複数該当時の detail 文字列の
  組み立て順序を Go 実装（forbiddenWords のイテレーション順）どおりに確認する）

--- 追加ケース（Go テーブルにはないが、直接呼び出し可能になったことで到達可能な分岐） ---

check_tags_format の "tags key not found"・"tags must be a list"・"tag contains
empty value after normalization" は、Go のコメントで「checkFrontmatterValues で
捕捉済みのはずなので到達しない」と明記されている防御的分岐。Task 8 では
check_tags_format を fm dict を直接受け取る単体関数として公開するため、これらの
分岐にも直接到達できる。挙動の実装が Go と一致することを確認するため追加した:
- test_check_tags_format_tags_key_not_found_fails
- test_check_tags_format_tags_not_a_list_fails
- test_check_tags_format_empty_value_after_normalization_fails

check_tags_format の float タグ正規化は既知の乖離（wlq/checks_frontmatter.py の
モジュールヘッダ docstring 参照）: Go の fmt.Sprint(1.0) は "1"、Python の str(1.0) は
"1.0" になる。通常運用のタグは文字列のみのため実装は変更せず、Python 側の挙動を
テストで固定する:
- test_check_tags_format_float_tag_normalizes_via_python_str（既知乖離の挙動固定）

--- task-08.md 記載の代表テスト（Go テストと 1:1 対応ではない追加確認） ---

test_missing_required_key_fails は task-08.md 本文に明記された代表テスト。Go の
MissingTagsKeyFails は tags 欠落パターンだが、こちらは draft 欠落パターンで同じ
「missing」分岐を確認する（同じロジックパスの追加確認であり期待値の相違はない）。
"""
from wlq.checks_frontmatter import (
    check_description_quality,
    check_forbidden_words,
    check_frontmatter_values,
    check_frontmatter_yaml,
    check_tags_format,
)
from wlq.frontmatter import parse_frontmatter


# --- check_forbidden_words --------------------------------------------------

def test_forbidden_word_in_content_fails():
    assert not check_forbidden_words("これは絶対に動きます。").passed


def test_no_forbidden_word_passes():
    f = check_forbidden_words("これは動きます。")
    assert f.passed
    assert f.detail == "no forbidden words found"


def test_forbidden_words_found_are_joined_in_config_order():
    # config.FORBIDDEN_WORDS = ["絶対", "必ず", "間違いなく", "TODO", ...]
    f = check_forbidden_words("必ず動きます。絶対に大丈夫です。TODO: 直す")
    assert not f.passed
    assert f.detail == "forbidden words found: 絶対, 必ず, TODO"


# --- check_frontmatter_yaml --------------------------------------------------

def test_check_frontmatter_yaml_valid_passes():
    body = "---\ntitle: X\ndate: 2026-01-01\ntags:\n  - go\n  - test\ndraft: false\n---\nbody"
    parse_frontmatter(body)  # parse error なし = None を渡す
    f = check_frontmatter_yaml(None)
    assert f.passed
    assert f.detail == "frontmatter is valid yaml"


def test_check_frontmatter_yaml_malformed_fails():
    body = '---\ntitle: "unterminated\n---\nbody'
    try:
        parse_frontmatter(body)
        parse_error = None
    except Exception as e:  # noqa: BLE001 - Go 実装同様、任意の parse error を受け取る
        parse_error = e
    assert parse_error is not None
    f = check_frontmatter_yaml(parse_error)
    assert not f.passed
    # 既知の乖離（モジュールヘッダ参照）: detail の YAML パーサ由来の詳細文言は Go と
    # 一致しないが、プレフィックスの構成は Go の fmt.Errorf("invalid frontmatter
    # yaml: %w", err) に合わせてある。その構成だけを検証する。
    assert f.detail.startswith("invalid frontmatter yaml:")


# --- check_frontmatter_values -------------------------------------------------

def test_check_frontmatter_values_valid_passes():
    body = "---\ntitle: X\ndate: 2026-01-01\ntags:\n  - go\n  - test\ndraft: false\n---\nbody"
    fm, _ = parse_frontmatter(body)
    f = check_frontmatter_values(fm)
    assert f.passed
    assert f.detail == "all required frontmatter values present"


def test_check_frontmatter_values_missing_tags_key_fails():
    body = "---\ntitle: X\ndate: 2026-01-01\ndraft: false\n---\nbody"
    fm, _ = parse_frontmatter(body)
    f = check_frontmatter_values(fm)
    assert not f.passed


def test_check_frontmatter_values_tags_as_scalar_fails():
    body = "---\ntitle: X\ndate: 2026-01-01\ntags: go\ndraft: false\n---\nbody"
    fm, _ = parse_frontmatter(body)
    f = check_frontmatter_values(fm)
    assert not f.passed


def test_check_frontmatter_values_empty_value_fails():
    body = "---\ntitle:\ndate: 2026-01-01\ntags:\n  - go\ndraft: false\n---\nbody"
    fm, _ = parse_frontmatter(body)
    f = check_frontmatter_values(fm)
    assert not f.passed


def test_missing_required_key_fails():
    fm = {"title": "t", "date": "2026-07-12", "tags": ["a"]}  # draft 欠落
    assert not check_frontmatter_values(fm).passed


# --- check_description_quality -------------------------------------------------

def test_check_description_quality_missing_fails():
    body = "---\ntitle: X\n---\nbody"
    fm, _ = parse_frontmatter(body)
    f = check_description_quality(fm, boilerplate="共通ボイラープレート", min_len=20)
    assert not f.passed


def test_check_description_quality_equals_title_fails():
    # descriptionMinLen=5・boilerplate なし: too-short / boilerplate 一致分岐が
    # 「description が title と一致」分岐をマスクしないようにする（Go テストの意図通り）。
    body = '---\ntitle: "何らかのタイトル"\ndescription: "何らかのタイトル"\n---\nbody'
    fm, _ = parse_frontmatter(body)
    f = check_description_quality(fm, boilerplate="", min_len=5)
    assert not f.passed
    assert f.detail == "description equals title"


def test_check_description_quality_too_short_fails():
    body = '---\ntitle: X\ndescription: "短い説明"\n---\nbody'
    fm, _ = parse_frontmatter(body)
    f = check_description_quality(fm, boilerplate="共通ボイラープレート", min_len=20)
    assert not f.passed


def test_check_description_quality_boilerplate_fails():
    # descriptionMinLen=5（description は 14 rune で min を超える）・title は
    # description と異なるため、「boilerplate と一致」分岐だけが発火する。
    body = '---\ntitle: "別のタイトルです"\ndescription: "共通のボイラープレート説明文"\n---\nbody'
    fm, _ = parse_frontmatter(body)
    f = check_description_quality(fm, boilerplate="共通のボイラープレート説明文", min_len=5)
    assert not f.passed
    assert f.detail == "description equals site boilerplate"


def test_check_description_quality_good_description_passes():
    body = ('---\ntitle: X\n'
            'description: "この記事ではGoの並行処理についてわかりやすく解説します。"\n'
            '---\nbody')
    fm, _ = parse_frontmatter(body)
    f = check_description_quality(fm, boilerplate="共通ボイラープレート", min_len=20)
    assert f.passed


# --- check_tags_format -------------------------------------------------

def test_check_tags_format_valid_list_passes():
    body = "---\ntitle: X\ntags:\n  - go\n  - api\n---\nbody"
    fm, _ = parse_frontmatter(body)
    f = check_tags_format(fm)
    assert f.passed


def test_check_tags_format_empty_list_fails():
    body = "---\ntitle: X\ntags: []\n---\nbody"
    fm, _ = parse_frontmatter(body)
    f = check_tags_format(fm)
    assert not f.passed


def test_check_tags_format_duplicates_after_normalize_fails():
    body = "---\ntitle: X\ntags:\n  - Go\n  - go\n---\nbody"
    fm, _ = parse_frontmatter(body)
    f = check_tags_format(fm)
    assert not f.passed


def test_check_tags_format_duplicates_after_trim_and_normalize_fails():
    body = '---\ntitle: X\ntags:\n  - go\n  - " go "\n---\nbody'
    fm, _ = parse_frontmatter(body)
    f = check_tags_format(fm)
    assert not f.passed


def test_check_tags_format_tags_key_not_found_fails():
    f = check_tags_format({"title": "X"})
    assert not f.passed
    assert f.detail == "tags key not found"


def test_check_tags_format_tags_not_a_list_fails():
    f = check_tags_format({"title": "X", "tags": "go"})
    assert not f.passed
    assert f.detail == "tags must be a list"


def test_check_tags_format_empty_value_after_normalization_fails():
    f = check_tags_format({"title": "X", "tags": ["go", "   "]})
    assert not f.passed
    assert f.detail == "tag contains empty value after normalization"


def test_check_tags_format_float_tag_normalizes_via_python_str():
    # 既知の乖離の挙動固定（wlq/checks_frontmatter.py モジュールヘッダ参照）:
    # Python の正規化は str(v) 基準のため float 1.0 は "1.0" になる
    # （Go の fmt.Sprint(1.0) は "1" のため、Go では ["1.0", 1.0] は重複扱いにならない）。
    # 通常運用のタグは文字列のみで float タグは存在しないため、実装は変更しない。
    f = check_tags_format({"title": "X", "tags": ["1.0", 1.0]})
    assert not f.passed
    assert f.detail == "duplicate tag found: 1.0"
