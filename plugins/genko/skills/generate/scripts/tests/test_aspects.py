"""wlq/aspects.py（load_aspects / select_aspects）と judge-aspects.yaml のテスト。

Go 側対応（`~/workspace/autopostd/internal/domain/judge_aspect*_test.go` @ 20c740b）:

judge_aspect_test.go:
    TestNewJudgeAspect
        -> 除外。Python 側の AspectDef は YAML ロード結果を保持するだけの
           プレーンな dataclass で、Go の NewJudgeAspect が行う「空 key / 空
           instruction を拒否する」コンストラクタバリデーションに対応する
           API を持たない。データ品質は load_aspects 側の存在チェックで代替する
           -> test_load_aspects_rejects_missing_instruction
    TestNewAspectKey
        -> 除外（同上理由。AspectKey という別型を持たず str をそのまま使う）
           -> test_load_aspects_rejects_empty_key
    TestJudgeAspectsFor_GeneralHasReadabilityAndMetaphorAspects
        -> test_general_gets_only_readability_and_metaphor（task-13.md 記載を
           そのまま採用）、test_general_has_no_code_self_containment
    TestJudgeAspectsFor_NoDiagramCodeAspectsWhenInapplicable
        -> test_diagram_code_keys_absent_for_general_even_with_fenced_block
           test_diagram_code_keys_absent_without_fenced_block

judge_aspects_practical_test.go:
    TestPracticalValueAspects_KeysAndAllowError
        -> test_practical_value_keys_and_allow_error_by_article_type
    TestPracticalValueAspects_GeneralIsEmpty
        -> test_practical_value_empty_for_general（下記 JudgeAspectsFor 系と統合）
    TestJudgeAspectsFor_ReturnsPracticalValueAspects
        -> test_practical_value_keys_and_allow_error_by_article_type（presence 部分を統合）
    TestJudgeAspectsFor_GeneralHasNoPracticalAspects
        -> test_practical_value_empty_for_general

judge_aspects_diagram_code_test.go:
    TestContainsFencedBlock
        -> 除外。containsFencedBlock 相当のブール判定（has_fenced_block /
           contains_triple_backtick）は Task 12 の wlq/runner.py で移植済み
           （tests/test_runner.py 参照）。select_aspects はブール値を受け取る
           だけで文字列を解析しないため、ここでの再移植は不要。
    TestDiagramCodeAspects_ByArticleType
        -> test_diagram_code_keys_by_article_type
    TestDiagramCodeAspects_MermaidOnlyContentIncludesAspects
        -> 除外。Mermaid ブロックの有無を本文から判定するのは Task 12 の
           _contains_fenced_block（既に test_runner.py でカバー済み）の責務。
           select_aspects は has_fenced_block=True/False の2値のみを見るため、
           コンテンツ種別（```/mermaid の違い）による分岐は存在しない。
    TestDiagramCodeAspects_NoCodeReturnsEmpty
        -> test_diagram_code_keys_absent_without_fenced_block に統合
    TestDiagramCodeAspects_GeneralReturnsEmpty
        -> test_diagram_code_keys_absent_for_general_even_with_fenced_block に統合
    TestJudgeAspectsFor_ReturnsDiagramCodeAspects
        -> test_diagram_code_keys_by_article_type（impl ケースに統合）
    TestJudgeAspectsFor_NoDiagramCodeAspectsWithoutCode
        -> test_diagram_code_keys_absent_without_fenced_block に統合

judge_aspects_metaphor_test.go:
    TestMetaphorAspects
        -> test_metaphor_discipline_def_is_single_warning_aspect
    TestJudgeAspectsFor_IncludesMetaphorAspects
        -> test_metaphor_discipline_present_for_all_article_types

judge_aspects_style_test.go:
    TestStyleAspects_GeneralIsEmpty
        -> test_style_aspects_empty_for_general
    TestStyleAspects_NonGeneralHasThreeWarningAspects
        -> test_style_aspects_three_keys_and_allow_error_false
    TestStyleAspects_StyleConformanceEmbedsStyleGuide
        -> 適応版に置換: test_style_conformance_local_adaptation_references_style_guide_md
           （task-13.md 記載の局所適応仕様: 本番は StyleGuideFor(t) を埋め込むが、
           genko は style-guide.md 参照文 + {article_type} 置換に置き換える）
    TestStyleAspects_FactOpinionEmphasisForNewsAndOpinion
        -> test_fact_opinion_separation_emphasis_for_news_and_opinion
    TestJudgeAspectsFor_IncludesStyleAspects
        -> test_style_aspects_present_for_non_general_absent_for_general

judge_aspects_readability_test.go:
    TestReadabilityAspects
        -> test_readability_aspects_by_article_type_and_code_fence（表を移植）
    TestJudgeAspectsFor_IncludesReadabilityAspects
        -> test_lead_quality_and_heading_present_for_all_article_types
    TestLeadQualityInstruction_ContainsAbstractDeclarationCheck
        -> test_lead_quality_instruction_contains_abstract_declaration_check
    TestJudgeAspectsFor_CodeSelfContainmentImplOnly
        -> test_code_self_containment_impl_only

judge_aspects_source_fidelity_test.go:
    TestSourceFidelityAspects
        -> test_source_fidelity_def_allow_error_and_presence
    TestJudgeAspectsFor_IncludesSourceFidelityWhenResearchPresent
        -> test_source_fidelity_only_on_first_round_with_research（task-13.md 記載を
           そのまま採用。round_num==1 条件は Go に無い genko 独自の requires
           拡張であり、Go に対応する単一テストは無い）

task-13.md 記載の代表テスト（そのまま採用。以下 5 件）:
    test_intro_without_code_or_research
    test_general_gets_only_readability_and_metaphor
    test_impl_with_code_gets_code_aspects
    test_source_fidelity_only_on_first_round_with_research
    test_document_mode_reduced_set（document モードは spec 由来の縮退定義のため
        Go に対応する経路は無い）

instruction 一致検証（task-13.md 「instruction 文字列の検証は Go 原文と一致する
こと」の指示に対応。Go 原文はスクリプトで抽出した文字列リテラルの結合結果を
そのままハードコードしている。抽出手順はセルフレビューで報告）:
    test_instruction_matches_go_source_concrete_examples
    test_instruction_matches_go_source_lead_quality
    test_instruction_matches_go_source_source_fidelity
    test_instruction_matches_go_source_style_conformance_after_substitution

genko 独自観点（jp-writing 由来の meta_commentary / redundancy。Go に対応なし。
judge-aspects.yaml ヘッダコメント参照）:
    test_meta_commentary_and_redundancy_defs_are_single_warning_aspects
    test_meta_commentary_and_redundancy_present_for_all_article_types
    test_meta_commentary_and_redundancy_present_in_document_mode
    ※ この 2 観点は全 article_type と document モードで選ばれるため、Go 移植由来の
    「厳密な観点集合」テスト（test_general_gets_only_readability_and_metaphor /
    test_document_mode_reduced_set）の期待リストにも追加されている。

load_aspects のローダー固有テスト（Go に対応なし。YAML データ品質の検証）:
    test_load_aspects_returns_all_aspects_in_yaml_order
    test_load_aspects_rejects_empty_key
    test_load_aspects_rejects_missing_instruction
    test_load_aspects_rejects_unknown_mode
    test_load_aspects_rejects_unknown_article_type
    test_load_aspects_rejects_unknown_requirement
    test_load_aspects_rejects_unsupported_schema_version

select_aspects の引数バリデーション（wlq/runner.py の run_checks の未知 mode
バリデーションと同じ流儀に揃える。Go に対応なし）:
    test_select_aspects_unknown_mode_raises_value_error
"""
from pathlib import Path

import pytest
import yaml

from wlq.aspects import AspectDef, load_aspects, select_aspects

YAML_PATH = Path(__file__).resolve().parent.parent.parent / "references" / "judge-aspects.yaml"
DEFS = load_aspects(YAML_PATH)


def keys(**kw):
    base = dict(mode="article", article_type="intro", has_fenced_block=False,
                contains_triple_backtick=False, research_present=False, round_num=1)
    base.update(kw)
    return [a.key for a in select_aspects(DEFS, **base)]


def selected(**kw):
    base = dict(mode="article", article_type="intro", has_fenced_block=False,
                contains_triple_backtick=False, research_present=False, round_num=1)
    base.update(kw)
    return select_aspects(DEFS, **base)


def defs_by_key(key: str) -> list[AspectDef]:
    return [d for d in DEFS if d.key == key]


# --- task-13.md 記載の代表テスト（そのまま採用） ---

def test_intro_without_code_or_research():
    got = keys()
    assert "concrete_examples" in got
    assert "lead_quality" in got and "metaphor_discipline" in got
    assert "diagram_readability" not in got
    assert "source_fidelity" not in got


def test_general_gets_only_readability_and_metaphor():
    # Go 移植当時の観点（readability 2 件 + metaphor）に加え、genko 独自の
    # meta_commentary / redundancy が全 article_type で選ばれる。
    got = keys(article_type="general")
    assert got == [
        "lead_quality", "heading_informativeness", "metaphor_discipline",
        "meta_commentary", "redundancy",
    ]


def test_impl_with_code_gets_code_aspects():
    got = keys(article_type="impl", has_fenced_block=True, contains_triple_backtick=True)
    assert "code_self_containment" in got
    assert "diagram_readability" in got and "code_explanation" in got


def test_source_fidelity_only_on_first_round_with_research():
    assert "source_fidelity" in keys(research_present=True, round_num=1)
    assert "source_fidelity" not in keys(research_present=True, round_num=2)
    assert "source_fidelity" not in keys(research_present=False, round_num=1)


def test_document_mode_reduced_set():
    # 縮退セット + genko 独自の meta_commentary / redundancy（modes に document を含む）。
    got = keys(mode="document", research_present=True)
    assert got == [
        "lead_quality", "heading_informativeness", "metaphor_discipline",
        "meta_commentary", "redundancy", "source_fidelity",
    ]


# --- TestJudgeAspectsFor_GeneralHasReadabilityAndMetaphorAspects /
#     TestJudgeAspectsFor_NoDiagramCodeAspectsWhenInapplicable ---

def test_general_has_no_code_self_containment():
    got = keys(article_type="general", has_fenced_block=True, contains_triple_backtick=True)
    assert "code_self_containment" not in got


def test_diagram_code_keys_absent_for_general_even_with_fenced_block():
    got = keys(article_type="general", has_fenced_block=True, contains_triple_backtick=True)
    for k in ("diagram_readability", "diagram_terminology", "code_explanation"):
        assert k not in got


def test_diagram_code_keys_absent_without_fenced_block():
    for at in ("intro", "news", "impl", "opinion", "general"):
        got = keys(article_type=at, has_fenced_block=False)
        for k in ("diagram_readability", "diagram_terminology", "code_explanation"):
            assert k not in got, f"{at}: unexpected {k} without fenced block"


# --- TestPracticalValueAspects_KeysAndAllowError /
#     TestJudgeAspectsFor_ReturnsPracticalValueAspects /
#     TestPracticalValueAspects_GeneralIsEmpty ---

_PRACTICAL_EXPECTED = {
    "intro": [
        ("concrete_examples", True),
        ("failure_cases", False),
        ("minimal_adoption", False),
        ("learning_path", False),
    ],
    "impl": [
        ("alternatives_tradeoffs", True),
        ("when_not_to_use", False),
        ("operational_notes", False),
    ],
    "opinion": [
        ("claim_clarity", True),
        ("evidence", False),
        ("counterarguments", False),
        ("applicability", False),
    ],
    "news": [
        ("impact_substance", False),
    ],
}


@pytest.mark.parametrize("article_type", ["intro", "impl", "opinion", "news"])
def test_practical_value_keys_and_allow_error_by_article_type(article_type):
    want = _PRACTICAL_EXPECTED[article_type]
    got = selected(article_type=article_type)
    got_practical = [a for a in got if a.key in {k for k, _ in want}]
    assert [(a.key, a.allow_error) for a in got_practical] == want
    for a in got_practical:
        assert a.instruction.strip() != ""
        # Go テストの assertion をそのまま移植: error 許可観点の instruction は
        # error 条件（完全欠落時のみ）を明記し、warning 専用観点の instruction は
        # error に言及しない（判定文字列は Go と同じ "severity=error"）。
        assert ("severity=error" in a.instruction) == a.allow_error, (
            f"{a.key}: instruction の severity=error 言及と allow_error={a.allow_error} が不整合"
        )


def test_practical_value_empty_for_general():
    all_practical_keys = {k for exp in _PRACTICAL_EXPECTED.values() for k, _ in exp}
    got = keys(article_type="general")
    assert not (set(got) & all_practical_keys)


# --- TestDiagramCodeAspects_ByArticleType 系 ---

@pytest.mark.parametrize(
    "article_type,want",
    [
        ("intro", ["diagram_readability", "diagram_terminology"]),
        ("news", ["diagram_readability", "diagram_terminology"]),
        ("opinion", ["diagram_readability", "diagram_terminology"]),
        ("impl", ["diagram_readability", "diagram_terminology", "code_explanation"]),
    ],
)
def test_diagram_code_keys_by_article_type(article_type, want):
    got = selected(article_type=article_type, has_fenced_block=True, contains_triple_backtick=True)
    got_diagram = [a.key for a in got if a.key in {"diagram_readability", "diagram_terminology", "code_explanation"}]
    assert got_diagram == want
    for a in got:
        if a.key in want:
            assert a.allow_error is False


# --- TestMetaphorAspects / TestJudgeAspectsFor_IncludesMetaphorAspects ---

def test_metaphor_discipline_def_is_single_warning_aspect():
    defs = defs_by_key("metaphor_discipline")
    assert len(defs) == 1
    d = defs[0]
    assert d.allow_error is False
    assert d.instruction != ""


@pytest.mark.parametrize("article_type", ["intro", "news", "opinion", "impl", "general"])
def test_metaphor_discipline_present_for_all_article_types(article_type):
    assert "metaphor_discipline" in keys(article_type=article_type)


# --- TestStyleAspects_* / TestJudgeAspectsFor_IncludesStyleAspects ---

def test_style_aspects_empty_for_general():
    got = keys(article_type="general")
    for k in ("style_conformance", "fact_opinion_separation", "excessive_rhetoric"):
        assert k not in got


@pytest.mark.parametrize("article_type", ["intro", "news", "impl", "opinion"])
def test_style_aspects_three_keys_and_allow_error_false(article_type):
    got = selected(article_type=article_type)
    style_keys = [a.key for a in got if a.key in {"style_conformance", "fact_opinion_separation", "excessive_rhetoric"}]
    assert style_keys == ["style_conformance", "fact_opinion_separation", "excessive_rhetoric"]
    for a in got:
        if a.key in style_keys:
            assert a.allow_error is False
            assert a.instruction != ""


def test_style_conformance_local_adaptation_references_style_guide_md():
    for article_type in ("intro", "news", "impl", "opinion"):
        got = selected(article_type=article_type)
        sc = next(a for a in got if a.key == "style_conformance")
        assert "style-guide.md" in sc.instruction
        assert f"記事タイプ: {article_type}" in sc.instruction
        assert "{article_type}" not in sc.instruction  # 置換済みであること


def test_fact_opinion_separation_emphasis_for_news_and_opinion():
    for article_type in ("news", "opinion"):
        got = selected(article_type=article_type)
        fo = next(a for a in got if a.key == "fact_opinion_separation")
        assert "重点的" in fo.instruction
    for article_type in ("intro", "impl"):
        got = selected(article_type=article_type)
        fo = next(a for a in got if a.key == "fact_opinion_separation")
        assert "重点的" not in fo.instruction


def test_style_aspects_present_for_non_general_absent_for_general():
    style_keys = {"style_conformance", "fact_opinion_separation", "excessive_rhetoric"}
    got_impl = keys(article_type="impl")
    assert style_keys <= set(got_impl)
    got_general = keys(article_type="general")
    assert not (style_keys & set(got_general))


# --- TestReadabilityAspects / TestJudgeAspectsFor_IncludesReadabilityAspects /
#     TestJudgeAspectsFor_CodeSelfContainmentImplOnly ---

@pytest.mark.parametrize(
    "article_type,contains_triple_backtick,want",
    [
        ("intro", False, ["lead_quality", "heading_informativeness"]),
        ("news", False, ["lead_quality", "heading_informativeness"]),
        ("opinion", False, ["lead_quality", "heading_informativeness"]),
        ("general", False, ["lead_quality", "heading_informativeness"]),
        ("impl", True, ["lead_quality", "heading_informativeness", "code_self_containment"]),
        ("impl", False, ["lead_quality", "heading_informativeness"]),
        ("general", True, ["lead_quality", "heading_informativeness"]),
    ],
)
def test_readability_aspects_by_article_type_and_code_fence(article_type, contains_triple_backtick, want):
    got = selected(article_type=article_type, contains_triple_backtick=contains_triple_backtick)
    got_readability = [
        a for a in got if a.key in {"lead_quality", "heading_informativeness", "code_self_containment"}
    ]
    assert [a.key for a in got_readability] == want
    for a in got_readability:
        assert a.allow_error is False
        assert a.instruction != ""


@pytest.mark.parametrize("article_type", ["intro", "news", "opinion", "impl", "general"])
def test_lead_quality_and_heading_present_for_all_article_types(article_type):
    got = keys(article_type=article_type)
    assert "lead_quality" in got
    assert "heading_informativeness" in got


def test_lead_quality_instruction_contains_abstract_declaration_check():
    d = defs_by_key("lead_quality")[0]
    assert "冒頭 2 文が抽象的な宣言（格言調）の連続で始まっていないかも確認する" in d.instruction


def test_code_self_containment_impl_only():
    assert "code_self_containment" in keys(article_type="impl", contains_triple_backtick=True)
    assert "code_self_containment" not in keys(article_type="impl", contains_triple_backtick=False)
    assert "code_self_containment" not in keys(article_type="intro", contains_triple_backtick=True)
    assert "code_self_containment" not in keys(article_type="general", contains_triple_backtick=True)


# --- TestSourceFidelityAspects / TestJudgeAspectsFor_IncludesSourceFidelityWhenResearchPresent ---

def test_source_fidelity_def_allow_error_and_presence():
    defs = defs_by_key("source_fidelity")
    assert len(defs) == 1
    d = defs[0]
    assert d.allow_error is True
    assert d.instruction != ""

    assert "source_fidelity" in keys(research_present=True, round_num=1)
    assert "source_fidelity" not in keys(research_present=False, round_num=1)


# --- genko 独自観点（jp-writing 由来。Go に対応なし） ---

def test_meta_commentary_and_redundancy_defs_are_single_warning_aspects():
    for key in ("meta_commentary", "redundancy"):
        defs = defs_by_key(key)
        assert len(defs) == 1, key
        d = defs[0]
        assert d.allow_error is False
        assert d.group == "writing_norms"
        assert d.instruction.strip() != ""
        # allow_error=false の観点は error 条件を instruction に書かない
        # （practical_value 系の検証と同じ流儀）。
        assert "severity=error" not in d.instruction


@pytest.mark.parametrize("article_type", ["intro", "news", "opinion", "impl", "general"])
def test_meta_commentary_and_redundancy_present_for_all_article_types(article_type):
    got = keys(article_type=article_type)
    assert "meta_commentary" in got
    assert "redundancy" in got


def test_meta_commentary_and_redundancy_present_in_document_mode():
    got = keys(mode="document")
    assert "meta_commentary" in got
    assert "redundancy" in got


# --- instruction 一致検証（Go 原文との一字一句一致。代表観点） ---

_GO_CONCRETE_EXAMPLES = (
    "具体例: 説明が抽象論に留まらず、読者が自分の環境で再現・応用できる具体例（コード、設定、手順、"
    "ユースケース）を伴っているかを評価してください。読者が「自分の場合はこう適用する」と判断できる"
    "具体性があるかが評価軸です。不足がある場合、suggestion にはどのセクションにどのような具体例を"
    "追加すべきかを具体的に書いてください。具体例が記事全体で完全に欠落している場合のみ "
    "severity=error とし、それ以外は warning としてください。"
)

_GO_LEAD_QUALITY = (
    "導入(最初の 2 段落以内)に、記事の要点・結論・読者がこの記事で得られるものが"
    "提示されているかを評価してください。背景説明や一般論だけで始まり、"
    "要点の提示が後回しになっている場合は指摘し、導入に前置きすべき要点を suggestion に書いてください。"
    "冒頭 2 文が抽象的な宣言（格言調）の連続で始まっていないかも確認する。"
    "読者の具体的な状況・問い・事実・数値・固有名詞のいずれかへの接地が冒頭 2 段落内にあること。"
)

_GO_SOURCE_FIDELITY = (
    "記事本文中の中核概念の定義・数値・主要な主張が、[リサーチ結果] の記述"
    "（特に原典からの逐語引用と出典）と整合しているかを評価してください。\n"
    "- 原典の定義より意味を狭めている（矮小化）、または広げている（拡大解釈）箇所を指摘してください。\n"
    "- 定義の意味が変わる水準の重大な逸脱は severity=\"error\" としてください。"
    "ニュアンスの弱まりに留まる場合は severity=\"warning\" とします。\n"
    "- 指摘には、リサーチ結果側の該当記述（引用）と記事側の記述を対で示し、"
    "どう修正すべきかを suggestion に書いてください。"
)

# style_conformance: Go 原文の t.String() 埋め込み直前まで（styleConformanceInstruction の
# 先頭 4 文字列リテラルの結合）はそのまま一致することを要求し、末尾は genko の局所適応
# 文言に置き換わっていることを別途検証する（test_style_conformance_local_adaptation_...）。
_GO_STYLE_CONFORMANCE_PREFIX = (
    "本文が以下の記事タイプ別文体ガイドに適合しているかを評価してください。"
    "口調や文体が途中で揺れていないか、過剰な断定や過剰に曖昧な表現がないかを確認し、"
    "逸脱している箇所とその修正案を指摘してください。\n"
    "文体ガイド（記事タイプ: "
)


def test_instruction_matches_go_source_concrete_examples():
    d = defs_by_key("concrete_examples")[0]
    assert d.instruction == _GO_CONCRETE_EXAMPLES


def test_instruction_matches_go_source_lead_quality():
    d = defs_by_key("lead_quality")[0]
    assert d.instruction == _GO_LEAD_QUALITY


def test_instruction_matches_go_source_source_fidelity():
    d = defs_by_key("source_fidelity")[0]
    assert d.instruction == _GO_SOURCE_FIDELITY


def test_instruction_matches_go_source_style_conformance_after_substitution():
    got = selected(article_type="intro")
    sc = next(a for a in got if a.key == "style_conformance")
    assert sc.instruction.startswith(_GO_STYLE_CONFORMANCE_PREFIX)
    tail = sc.instruction[len(_GO_STYLE_CONFORMANCE_PREFIX):]
    assert tail == "intro）は同ディレクトリの style-guide.md の該当節を参照して評価してください。"


# --- load_aspects 固有テスト（Go に対応なし） ---

def test_load_aspects_returns_all_aspects_in_yaml_order():
    raw = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    want_order = [item["key"] for item in raw["aspects"]]
    assert [d.key for d in DEFS] == want_order
    # Go 移植の 24 観点 + genko 独自の meta_commentary / redundancy。
    assert len(DEFS) == 26


def test_load_aspects_rejects_empty_key(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: 1\naspects:\n  - key: ''\n    group: g\n    allow_error: false\n"
        "    article_types: []\n    modes: [article]\n    requires: []\n    instruction: x\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_aspects(bad)


def test_load_aspects_rejects_missing_instruction(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: 1\naspects:\n  - key: k\n    group: g\n    allow_error: false\n"
        "    article_types: []\n    modes: [article]\n    requires: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_aspects(bad)


def test_load_aspects_rejects_unknown_mode(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: 1\naspects:\n  - key: k\n    group: g\n    allow_error: false\n"
        "    article_types: []\n    modes: [blog]\n    requires: []\n    instruction: x\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_aspects(bad)


def test_load_aspects_rejects_unknown_article_type(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: 1\naspects:\n  - key: k\n    group: g\n    allow_error: false\n"
        "    article_types: [intr]\n    modes: [article]\n    requires: []\n    instruction: x\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_aspects(bad)


def test_load_aspects_rejects_unknown_requirement(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: 1\naspects:\n  - key: k\n    group: g\n    allow_error: false\n"
        "    article_types: []\n    modes: [article]\n    requires: [nonexistent]\n    instruction: x\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_aspects(bad)


def test_load_aspects_rejects_unsupported_schema_version(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("schema_version: 2\naspects: []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_aspects(bad)


def test_select_aspects_unknown_mode_raises_value_error():
    with pytest.raises(ValueError):
        select_aspects(
            DEFS, mode="blog", article_type="intro", has_fenced_block=False,
            contains_triple_backtick=False, research_present=False, round_num=1,
        )
