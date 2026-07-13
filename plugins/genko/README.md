# genko

原稿生成パイプライン（旧称 writeloop）。
壁打ちで plan を固め、必要なら Web リサーチを行い、本文を生成し、品質チェックと自動修正のループを回して、ブログ記事または調査ドキュメントを仕上げる。

品質の合否はスクリプトの判定（verdict）に従う。
メイン会話の Claude は本文を書かず、合否も独自に判断しない。
執筆と評価は工程ごとの専用サブエージェント（researcher、writer、judge、fixer）が担う。

## インストール

```
/plugin marketplace add swallowarc/swallowarc-ai-plugins
/plugin install genko@swallowarc-ai-plugins
```

旧称 writeloop をインストール済みの場合は、writeloop をアンインストールしてから genko をインストールし直す。

## 前提条件

品質チェックとプロンプト組立は Python スクリプトで行う。
`uv`、または pyyaml と regex を導入済みの `python3` が必要である。
どちらも使えない環境では、工程を LLM が代替せず全体を中断する。

## 使い方

テーマを渡すと壁打ちから始まる。

```
/genko:generate <テーマ>
```

中断したランは、既存 plan.md のパスを渡すと途中から再開する。

```
/genko:generate <RUN_DIR>/plan.md
```

## モード

壁打ちの冒頭でどちらかを選ぶ。

- **article**：ブログ記事。記事タイプ（intro / impl / opinion / news / general）、想定読者、ゴール、スコープを壁打ちで確定する
- **document**：調査ドキュメント。知りたいこと（questions）と深さ（depth）を確定する

## 工程

1. **壁打ち**：対話で `plan.md` を確定する
2. **リサーチ**（`profile: research` のときのみ）：researcher エージェントが出典 URL と逐語引用つきの `research.md` を書く
3. **本文生成**：writer エージェントが `draft-v1.md` を書く
4. **品質チェック**：ルールベースのスクリプト判定と、judge エージェントによる観点別評価を行う
5. **判定と修正**：不合格（`continue`）なら fixer エージェントが指摘を修正して次の draft を作り、再チェックする。ループは最大 3 ラウンド

ループが `passed` 以外（`stalled` / `retries_exhausted`）で終わるのはエラーではない。
「これ以上の自動修正では収束しなかった」状態として残存指摘つきで報告され、続きはユーザーの判断に委ねられる。

## 成果物

既定の出力先は `./genko-runs/<YYYY-MM-DD>-<slug>/`（引数で変更可）。
`plan.md`、draft の各版、ラウンドごとのレビュー結果（`review-N/`）、最終レポートの `summary.md` が残る。

## 構成

- `skills/generate/`：工程全体の手順書（SKILL.md）、品質チェックとプロンプト組立のスクリプト、評価観点などの references
- `agents/`：researcher、writer、judge、fixer の 4 エージェント定義。いずれも genko:generate の工程専用で、単独での自動起用は想定しない
