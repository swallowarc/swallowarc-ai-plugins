---
name: generate
description: 壁打ち→（必要なら）リサーチ→本文生成→品質チェック→自動修正ループで、ブログ記事（article）または調査ドキュメント（document）を生成する。引数はテーマ、または既存 plan.md のパス。
---

# generate

このスキルは決定論スクリプト（rules 判定・観点選定・verdict 決定・プロンプト組立）とサブエージェント（リサーチ・執筆・評価・修正）を順にディスパッチする手順書である。**あなた（メイン会話の Claude）自身は記事本文を書かない。合否判断もスクリプトの verdict に従うだけで、独自に下さない。**

## 0. 実行環境

このファイル（SKILL.md）が置かれているディレクトリを base とし、以降 `$BASE` と表記する。`$BASE/scripts/` を `$SCRIPTS`、`$BASE/references/` を references ディレクトリとする。プラグインのインストール先パスに依存しないよう、常に `$BASE` から相対的に解決すること。

スクリプト実行は次の優先順位:
1. `uv run $SCRIPTS/<name>.py ...`（第一候補）
2. `uv` が使えない場合は `python3 $SCRIPTS/<name>.py ...`（pyyaml / regex 導入済み前提）
3. どちらも実行できない場合は **工程全体を中断してユーザーに報告する**。LLM が自分でチェック・判定・プロンプト組立を代替することは一切しない。

## 1. 成果物ディレクトリ

既定は `./writeloop-runs/<YYYY-MM-DD>-<slug>/`（引数で変更可）。以下 `$RUN_DIR` と表記する。

```
$RUN_DIR/
  plan.md
  research.md                     # profile=research のときのみ
  writer-prompt.md
  draft-v1.md, draft-v2.md, ...
  review-1/rules.json
  review-1/aspects.json
  review-1/judge-prompt.md
  review-1/judge.json
  review-1/decision.json
  review-1/report.md
  review-1/fix-prompt.md          # verdict=continue のときのみ
  review-2/...（同様、ラウンドごと）
  summary.md
```

## 2. 壁打ち

引数がテーマなら壁打ちを実施する。引数が既存 `plan.md` のパスなら壁打ちを省略し、5章の再開判定に進む。

質問は一度に全項目をまとめて聞かず、少しずつ聞く。

- **article**: テーマ → 記事タイプ（intro/impl/opinion/news/general）→ 想定読者（役割・技術レベル・現状の課題・記事に求めるもの等、複数の観点を聞き取り 1〜3 文にまとめる）→ ゴール → スコープ（扱う話題 / 扱わない話題）→ 制約 → タグ → slug → リサーチ要否。
- **document**: テーマ → 知りたいこと（questions）→ 深さ（depth）→ リサーチ要否 → slug。

リサーチ要否の判断基準は「ネット調査が記事の本体になるか」。要否に迷う場合はユーザーに確認する。

**最終確認は AskUserQuestion の選択肢の `preview`（または `description`）に plan.md の全文を埋め込んで提示する。** ターン途中の通常テキストで plan 内容を提示し、それを確認前提にした手順は書かない（AskUserQuestion 直前のターン途中テキストが表示されない既知の表示 issue のため）。

確定後、`$RUN_DIR/plan.md` を次の frontmatter 書式で書く（`load_plan` が検証する契約。リスト型フィールドは必ず YAML リストで書く。スカラーで書くと `ValueError` になる）:

```yaml
---
mode: article            # article | document
article_type: impl       # article のみ: intro | impl | opinion | news | general
profile: research         # basic | research
created: 2026-07-13
title_draft: "記事タイトル案"
slug: some-slug
tags: [go, temporal]                       # article のみ
target_audience: "1〜3文の想定読者"          # article のみ
goal: "この記事のゴール"                     # article のみ
topics_in_scope: ["扱う話題1"]              # article のみ
topics_out_of_scope: []                    # article のみ
constraints: []                            # article のみ
questions: ["知りたいこと1"]                 # document のみ
depth: "深さの指定"                          # document のみ
---
## 壁打ちメモ
（壁打ちで得た背景・経緯を書く）

## リサーチ観点
（profile=research のときのみ。researcher エージェントの調査入力になる）
```

`## 壁打ちメモ` は mode を問わず必ず書く。`## リサーチ観点` は `profile: research` のときのみ書く（researcher.md が本文からこの節を読む契約）。

## 3. 工程シーケンス

`$MODE` は plan.md frontmatter の `mode`。以下、$RUN_DIR 配下の相対パスで表記する。

1. `profile: research` のときのみ: researcher エージェントに `plan.md` のパスと `research.md` の出力先パスだけを渡して起動する。

2. writer 用プロンプトを組み立ててから writer エージェントを起動する。

```
uv run $SCRIPTS/build_prompt.py writer --plan plan.md --mode $MODE [--research research.md] --out writer-prompt.md
```

→ writer エージェントに `writer-prompt.md` のパスと出力先 `draft-v1.md` のパスだけを渡す。

3. N = 1, 2, 3 でループする。

   a. ルールベースチェック:
   ```
   uv run $SCRIPTS/qualitycheck.py --draft draft-vN.md --mode $MODE --plan plan.md [--research research.md] --out review-N/rules.json
   ```

   b. LLM judge の評価観点選定:
   ```
   uv run $SCRIPTS/review_gate.py aspects --aspects-file $BASE/references/judge-aspects.yaml --rules review-N/rules.json --mode $MODE --round N [--research-present] --out review-N/aspects.json
   ```

   c. judge 用プロンプト組立 → judge エージェント起動:
   ```
   uv run $SCRIPTS/build_prompt.py judge --plan plan.md --mode $MODE --draft draft-vN.md --aspects review-N/aspects.json [--research research.md] --out review-N/judge-prompt.md
   ```
   → judge エージェントに `judge-prompt.md` のパスと出力先 `review-N/judge.json` のパスだけを渡す。

   d. 判定:
   ```
   uv run $SCRIPTS/review_gate.py decide --rules review-N/rules.json --judge review-N/judge.json --aspects review-N/aspects.json --round N [--prev review-(N-1)/decision.json] --out review-N/decision.json --report review-N/report.md
   ```
   （N=1 のときは `--prev` を付けない。`--max-retries` は既定値 2 を使う限り付けない。）

   e. `review-N/decision.json` の `verdict` に従う（他の基準で合否を判断しない）:
      - `passed` / `stalled` / `retries_exhausted` → ループを抜けて 7章（summary.md）へ進む。
      - `continue` → fixer 用プロンプトを組み立てて fixer エージェントを起動し、`draft-v(N+1).md` を得てから次の N へ進む。
      ```
      uv run $SCRIPTS/build_prompt.py fixer --plan plan.md --mode $MODE --draft draft-vN.md --decision review-N/decision.json --out review-N/fix-prompt.md
      ```
      → fixer エージェントに `fix-prompt.md` のパスと出力先 `draft-v(N+1).md` のパスだけを渡す。

`research.md` が存在する限り、qualitycheck / build_prompt には `--research <パス>`、`review_gate.py aspects` には `--research-present`（フラグのみ、パスは渡さない）を毎回付ける。両者は別物なので混同しない。

`stalled` と `retries_exhausted` は**エラーではなく正常終了**である。ループはそこで終わり、7章の summary.md 作成に進む。

## 4. 工程検証と再実行

- researcher / writer / fixer: エージェント完了後、期待する出力ファイル（research.md / draft-vN.md）の存在と非空を確認する。不正なら同じ工程を1回だけ再実行し、それでも失敗したら中断してユーザーに報告する。
- judge: `review_gate.py decide` が exit 1 で終了し、かつ stderr が `--judge` ファイル起因（例: `error: judge file ... is missing field(s) ...`、`error: judge file ... has unknown field(s) ...`、`error: judge file ... field(s) ... must be strings`、`error: invalid severity from judge (aspect=...)` など、"judge" ファイルの JSON 構文・フィールド欠落・未知フィールド・型・severity に関するもの）と読み取れる場合に限り、judge エージェントを1回だけ再実行する（同じ `judge-prompt.md` から、直前の stderr を添えて再生成させる）。再実行後も同種のエラーなら中断する。
- 上記2つに該当しない、スクリプトの exit 非ゼロは理由を問わず**即座に中断**し、stderr の内容をそのままユーザーに報告する。CLI の不合格判定（findings が error を含む等）は exit 0 のデータであり、これは中断理由にはならない。

## 5. 再開

引数が既存 `plan.md` のパスのとき、壁打ちを省略し次のように再開する:

- `plan.md` の場所から `$RUN_DIR` を特定する。
- `review-N/decision.json` が存在する round は完了済みとして扱い、飛ばす。
- `decision.json` が存在しない最初の round から、その round を丸ごとやり直す（rules.json 等の中間ファイルが残っていても再生成する）。
- `research.md` が既に存在する場合のみ、再利用してよいかをユーザーに確認する。他のファイル（plan.md 本体、writer-prompt.md 等）の再利用については確認しない。

## 6. リサーチ不能時

WebSearch が使えない、または権限が拒否された場合、黙って basic に降格しない。ユーザーに次を確認する:
- (a) `profile: basic` に落として続行する（plan.md の frontmatter を書き換えて記録する）
- (b) 中断する

## 7. summary.md

ループを抜けたら `$RUN_DIR/summary.md` に次を記載する:
- 最終 verdict（passed / stalled / retries_exhausted）と回転数（最終 round N）
- 残存する error findings / warning findings の件数（`decision.json` の `error_findings` / `warning_findings`）
- 成果物一覧へのインデックス（plan.md / research.md / draft-vN.md / review-N/* / このファイル自身）
- mode（article/document）と profile（basic/research）
- 使用モデル（このセッションで動作しているモデル）

`stalled` / `retries_exhausted` はエラーではなく正常終了として扱い、残存する error findings をそのまま記録して報告する。「失敗した」ではなく「これ以上の自動修正では収束しなかった」として報告し、続きはユーザーの判断に委ねる。
