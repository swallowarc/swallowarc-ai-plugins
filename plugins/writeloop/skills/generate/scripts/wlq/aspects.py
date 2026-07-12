# ported from: internal/domain/judge_aspect.go (JudgeAspectsFor:88-97),
#              internal/domain/judge_aspects_practical.go,
#              internal/domain/judge_aspects_diagram_code.go,
#              internal/domain/judge_aspects_style.go,
#              internal/domain/judge_aspects_readability.go,
#              internal/domain/judge_aspects_metaphor.go,
#              internal/domain/judge_aspects_source_fidelity.go
#              @ autopostd 20c740b
"""LLM judge の評価観点データ（references/judge-aspects.yaml）のロードと選定。

本番の `JudgeAspectsFor`（domain/judge_aspect.go:88-97）は Plan（article_type）と
本文・リサーチ結果から観点関数を順に呼び出して観点リストを組み立てる。各観点関数
（practicalValueAspects / diagramCodeAspects / styleAspects / readabilityAspects /
metaphorAspects / sourceFidelityAspects）は Go のコードとして「article_type ごとに
何を返すか」を実装している。writeloop ではこれを機械可読な YAML
（judge-aspects.yaml）に持たせ、各観点の適用条件（article_types / modes / requires）
を宣言的なデータとして表現し、`select_aspects` が単一の選定ロジックで解釈する。

## AspectDef の各フィールド

- key: 観点の識別子（本番の AspectKey）。
- group: どの観点関数由来か（practical_value / diagram_code / style / readability /
  metaphor / source_fidelity）。選定ロジックでは使わないが、YAML の可読性と
  移植元との対応付けのために保持する。
- allow_error: 本番の allowError（NewJudgeAspect 第3引数）。true の観点のみ、
  観点が記事全体で完全に欠落している場合に severity=error を許容する。
- article_types: article モードでこの観点が適用される article_type の集合。
  document モードでは無視される（後述）。
- modes: この観点が有効なモード（"article" | "document"）。
- requires: 追加で満たすべき前提条件のキー（後述）。
- instruction: judge プロンプトに列挙する評価観点文（Go の文字列連結を解決した
  完全形を一字一句移植。style_conformance のみ `{article_type}` プレースホルダを
  含み、select_aspects が実値に置換する）。

## Go との差分（意図的な設計判断）

- style_conformance: 本番は instruction 末尾に `StyleGuideFor(t)`（記事タイプ別
  文体ガイド本文）を埋め込むが、writeloop はプラグイン単体で完結させるため
  文体ガイド本文を持たない。代わりに同ディレクトリの style-guide.md（後続プラン
  で作成）を参照させる一文を末尾に置く。
- fact_opinion_separation: 本番は 1 つの関数内で article_type に応じて instruction
  文字列に追記するかどうかを分岐するが、YAML は宣言的データであるため同じ key で
  article_types だけが異なる 2 エントリ（intro/impl 用と news/opinion 用）に分ける。
  article_type は排他的にどちらか一方にしか一致しないため、select_aspects は常に
  最大 1 件を選ぶ。
- source_fidelity の requires に `first_round` を追加している。本番は
  `researchContent == nil` のみで判定するが、usecase 層（judge_quality.go）が
  再 judge（fix 後の 2 round 目以降）で `excludeResearch=true` を渡すことで
  researchContent を意図的に nil にし、同じ効果（2 round 目以降は source_fidelity
  を評価しない）を得ている。writeloop にはラウンドという概念を明示的に持たせる
  ため、この副作用を `requires: [research, first_round]` という明示的な条件として
  表現する。
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml

_VALID_MODES = frozenset(("article", "document"))
_VALID_REQUIRES = frozenset(("fenced_block", "triple_backtick", "research", "first_round"))


@dataclasses.dataclass(frozen=True)
class AspectDef:
    """judge-aspects.yaml の 1 エントリ（AspectKey + 適用条件 + instruction）。"""

    key: str
    group: str
    allow_error: bool
    article_types: tuple[str, ...]
    modes: tuple[str, ...]
    requires: tuple[str, ...]
    instruction: str


def _require_str_list(value, *, field: str, key: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"aspect {key!r}: {field} must be a list of strings, got {value!r}")
    return tuple(value)


def load_aspects(path: str | Path) -> list[AspectDef]:
    """judge-aspects.yaml を読み、AspectDef のリストを YAML 記載順で返す。

    schema_version は 1 のみサポートする。各観点は key / group / allow_error /
    article_types / modes / requires / instruction をすべて持つ必要がある。
    modes / requires の値は既知の語彙（_VALID_MODES / _VALID_REQUIRES）のみ許可する。
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a mapping")
    if data.get("schema_version") != 1:
        raise ValueError(f"{path}: unsupported schema_version {data.get('schema_version')!r}")

    raw_aspects = data.get("aspects")
    if not isinstance(raw_aspects, list):
        raise ValueError(f"{path}: 'aspects' must be a list")

    defs: list[AspectDef] = []
    for i, item in enumerate(raw_aspects):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: aspects[{i}] must be a mapping")

        key = item.get("key")
        if not isinstance(key, str) or not key:
            raise ValueError(f"{path}: aspects[{i}].key must be a non-empty string")

        group = item.get("group")
        if not isinstance(group, str) or not group:
            raise ValueError(f"aspect {key!r}: group must be a non-empty string")

        allow_error = item.get("allow_error")
        if not isinstance(allow_error, bool):
            raise ValueError(f"aspect {key!r}: allow_error must be a bool")

        instruction = item.get("instruction")
        if not isinstance(instruction, str) or not instruction:
            raise ValueError(f"aspect {key!r}: instruction must be a non-empty string")

        article_types = _require_str_list(item.get("article_types", []), field="article_types", key=key)
        modes = _require_str_list(item.get("modes", []), field="modes", key=key)
        requires = _require_str_list(item.get("requires", []), field="requires", key=key)

        unknown_modes = set(modes) - _VALID_MODES
        if unknown_modes:
            raise ValueError(f"aspect {key!r}: unknown modes {sorted(unknown_modes)}")
        unknown_requires = set(requires) - _VALID_REQUIRES
        if unknown_requires:
            raise ValueError(f"aspect {key!r}: unknown requires {sorted(unknown_requires)}")

        defs.append(
            AspectDef(
                key=key,
                group=group,
                allow_error=allow_error,
                article_types=article_types,
                modes=modes,
                requires=requires,
                instruction=instruction,
            )
        )
    return defs


def _requirement_satisfied(
    requirement: str,
    *,
    has_fenced_block: bool,
    contains_triple_backtick: bool,
    research_present: bool,
    round_num: int,
) -> bool:
    if requirement == "fenced_block":
        return has_fenced_block
    if requirement == "triple_backtick":
        return contains_triple_backtick
    if requirement == "research":
        return research_present
    if requirement == "first_round":
        return round_num == 1
    # load_aspects が既知語彙のみ許可するため、到達しないはずの防御的分岐。
    raise ValueError(f"unknown requirement: {requirement!r}")


def select_aspects(
    defs: list[AspectDef],
    *,
    mode: str,
    article_type: str,
    has_fenced_block: bool,
    contains_triple_backtick: bool,
    research_present: bool,
    round_num: int,
) -> list[AspectDef]:
    """本番 JudgeAspectsFor の選定規則を YAML データに対して適用する。

    規則（YAML 記載順を保存して評価・出力する）:
    1. `mode` が `modes` に含まれること。
    2. mode="article" のときのみ `article_type` が `article_types` に含まれること
       を追加で要求する（document モードは spec 由来の縮退定義のため article_type
       条件を評価しない。document の観点集合は modes フィールドだけで決まる）。
    3. `requires` の全条件を満たすこと。
    4. style_conformance の instruction 中 `{article_type}` を実値に置換する。

    mode が "article"/"document" 以外の場合 ValueError（wlq.runner.run_checks の
    未知 mode バリデーションと同じ流儀）。
    """
    if mode not in _VALID_MODES:
        raise ValueError(f"unknown mode: {mode!r} (must be one of {sorted(_VALID_MODES)})")

    selected: list[AspectDef] = []
    for d in defs:
        if mode not in d.modes:
            continue
        if mode == "article" and article_type not in d.article_types:
            continue
        if not all(
            _requirement_satisfied(
                r,
                has_fenced_block=has_fenced_block,
                contains_triple_backtick=contains_triple_backtick,
                research_present=research_present,
                round_num=round_num,
            )
            for r in d.requires
        ):
            continue

        if "{article_type}" in d.instruction:
            d = dataclasses.replace(d, instruction=d.instruction.replace("{article_type}", article_type))
        selected.append(d)
    return selected
