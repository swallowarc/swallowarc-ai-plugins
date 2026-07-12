"""writer / judge / fixer プロンプトの決定論組立。

組立仕様の移植元: internal/infrastructure/llm/openai.go, prompt_sections.go,
judge_common.go, draft_fixer.go @ autopostd 20c740b
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import regex

from wlq import config
from wlq.checks_structure import required_section_names
from wlq.frontmatter import parse_frontmatter

_JST = timezone(timedelta(hours=9))
_HEADER_COMMENT_RE = regex.compile(r"\A(?:<!--.*?-->\n)+", regex.DOTALL)
_REQUIRED_ARTICLE_FIELDS = ("article_type", "title_draft", "slug", "target_audience", "goal", "topics_in_scope")
_REQUIRED_DOCUMENT_FIELDS = ("title_draft", "slug", "questions")

# ported from: internal/infrastructure/llm/prompt_sections.go buildStyleGuideSuffix @ autopostd 20c740b
_STYLE_GUIDE_INTRO = "Persona の口調・キャラクター性は維持したまま、以下の文体原則に従ってください。"


@dataclass(frozen=True)
class PlanData:
    mode: str
    profile: str
    article_type: str
    title_draft: str
    slug: str
    tags: tuple[str, ...]
    target_audience: str
    goal: str
    topics_in_scope: tuple[str, ...]
    topics_out_of_scope: tuple[str, ...]
    constraints: tuple[str, ...]
    questions: tuple[str, ...]
    depth: str


def load_plan(path: str) -> PlanData:
    with open(path, encoding="utf-8") as f:
        meta, _ = parse_frontmatter(f.read())
    mode = meta.get("mode")
    if mode not in ("article", "document"):
        raise ValueError(f"plan frontmatter の mode が不正: {mode!r}")
    profile = meta.get("profile")
    if profile not in ("basic", "research"):
        raise ValueError(f"plan frontmatter の profile が不正: {profile!r}")
    required = _REQUIRED_ARTICLE_FIELDS if mode == "article" else _REQUIRED_DOCUMENT_FIELDS
    for key in required:
        if not meta.get(key):
            raise ValueError(f"plan frontmatter に {key} がない")

    def _tuple(key: str) -> tuple[str, ...]:
        value = meta.get(key)
        if value is None:
            return ()
        if not isinstance(value, list):
            raise ValueError(f"plan frontmatter の {key} はリストでなければならない")
        return tuple(str(v) for v in value)

    return PlanData(
        mode=mode, profile=profile,
        article_type=str(meta.get("article_type") or "general"),
        title_draft=str(meta["title_draft"]), slug=str(meta["slug"]),
        tags=_tuple("tags"), target_audience=str(meta.get("target_audience") or ""),
        goal=str(meta.get("goal") or ""),
        topics_in_scope=_tuple("topics_in_scope"),
        topics_out_of_scope=_tuple("topics_out_of_scope"),
        constraints=_tuple("constraints"), questions=_tuple("questions"),
        depth=str(meta.get("depth") or ""),
    )


def requires_references(plan: PlanData) -> bool:
    # ported from: domain.RequiresReferences — research プロファイル または news
    return plan.profile == "research" or (plan.mode == "article" and plan.article_type == "news")


def load_reference(refs_dir: str, filename: str) -> str:
    with open(os.path.join(refs_dir, filename), encoding="utf-8") as f:
        return _HEADER_COMMENT_RE.sub("", f.read(), count=1).strip() + "\n"


def _split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current, lines = None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current, lines = line[3:].strip(), []
        else:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    return sections


def style_guide_block(refs_dir: str, article_type: str) -> str:
    sections = _split_sections(load_reference(refs_dir, "style-guide.md"))
    type_key = article_type if article_type in sections else "general"
    return (f"[文体ガイド（記事タイプ: {article_type}）]\n{_STYLE_GUIDE_INTRO}\n"
            f"{sections[type_key]}\n{sections['common']}\n")


def reference_requirements_block(refs_dir: str, now: datetime) -> str:
    # 実行時改訂: 原文の Go 書式指定子 %s（情報確認日）を実行時の JST 日付で置換する。
    # ported from: internal/infrastructure/llm/prompt_sections.go:165 @ autopostd 20c740b
    body = load_reference(refs_dir, "reference-requirements.md")
    return "[参考情報要件]\n" + body.replace("%s", now.astimezone(_JST).strftime("%Y-%m-%d"))


def required_sections_block(refs_dir: str, article_type: str) -> str:
    sections = _split_sections(load_reference(refs_dir, "required-sections.md"))
    names = required_section_names(article_type)
    body = sections["common"].replace("{sections}", "\n".join(f"- {n}" for n in names))
    parts = [body]
    if "はじめに" in names:
        parts.append(sections["intro-integration"])
    if article_type == "news":
        parts.append(sections["news"])
    return "[必須セクション]\n" + "\n".join(parts) + "\n"


def diagram_code_rules_block(refs_dir: str, article_type: str) -> str:
    # 実行時改訂: 本番の排他 if/else と行順を保持するため、impl / default の2変種から
    # どちらか一方を丸ごと選択する（common + 追加連結ではない）。
    sections = _split_sections(load_reference(refs_dir, "diagram-code-rules.md"))
    variant = "impl" if article_type == "impl" else "default"
    return "[図とコード例のルール]\n" + sections[variant] + "\n"


def quality_rules_block(mode: str) -> str:
    # ported from: internal/domain/quality_rules.go String() @ autopostd 20c740b
    lines = ["以下のルールに必ず従ってください。", "- 禁止ワード（記事中に含めてはいけない語句）:"]
    if config.FORBIDDEN_WORDS:
        lines += [f"  - {w}" for w in config.FORBIDDEN_WORDS]
    else:
        lines.append("  - なし")
    if mode == "article":
        lines.append("- 必須 Frontmatter キー（--- ブロック内に必ず含める）:")
        lines += [f"  - {k}" for k in config.REQUIRED_FRONTMATTER]
    return "[品質ルール]\n" + "\n".join(lines) + "\n"


def plan_section(plan: PlanData) -> str:
    # ported from: internal/infrastructure/llm/openai.go writePlanSection @ autopostd 20c740b
    if plan.mode == "document":
        lines = ["[投稿計画]", f"- テーマ: {plan.title_draft}", "- 知りたいこと:"]
        lines += [f"  - {q}" for q in plan.questions]
        if plan.depth:
            lines.append(f"- 深さ: {plan.depth}")
        return "\n".join(lines) + "\n"
    lines = [
        "[投稿計画]",
        f"- タイトル: {plan.title_draft}",
        f"- 記事タイプ: {plan.article_type}",
        f"- 想定読者: {plan.target_audience}",
        f"- ゴール: {plan.goal}",
        "- 必須トピック:",
        *[f"  - {t}" for t in plan.topics_in_scope],
        "- 書かないこと:",
        *([f"  - {t}" for t in plan.topics_out_of_scope] or ["  - なし"]),
        "- 制約:",
        *([f"  - {c}" for c in plan.constraints] or ["  - なし"]),
    ]
    return "\n".join(lines) + "\n"
