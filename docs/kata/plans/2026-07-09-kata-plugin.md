# kata プラグイン実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** superpowers のエッセンスを Claude Code 専用に再構成した 10 スキル構成のプラグイン kata を、Markdown のみで `claude-plugins` リポジトリに構築する。

**Architecture:** マーケットプレイス兼用リポジトリ（swallowarc-ai-plugins と同形式）に `plugins/kata/skills/<skill>/SKILL.md` を配置。各スキルは原典（`/home/acrobatkame/workspace/superpowers/skills/`）を読んでエッセンスを抽出し、日本語で書き直す。実行可能コードは一切含めない。

**Tech Stack:** Markdown、Claude Code plugin/marketplace 形式（JSON）。ビルド・テストフレームワークなし（検証はシェルコマンドによる静的チェックと手動インストール確認）。

**Spec:** `docs/kata/specs/2026-07-09-kata-plugin-design.md`（本プランの上位文書。齟齬があれば spec が優先）

## Global Constraints

- 追加してよいファイルは `.md`・`.json` のみ。hooks・シェルスクリプト・Node スクリプト等の実行可能コードは絶対に追加しない。
- SKILL.md の frontmatter は `name`（短縮名）と `description`（英語、"Use when ..." で始まる三人称）のみ。name は本プラン各タスクに記載の値を一字一句そのまま使う。
- 本文は日本語。コマンド・コード例・固有名詞（RED/GREEN/REFACTOR 等）は原語のまま。
- スキル間の相互参照は必ず `kata:<skill-name>` 形式。`superpowers:` という文字列を `plugins/` 配下に残してはならない（検証コマンドで 0 件を確認）。
- 原典の文章を段落単位でコピーしない。構造（フェーズ、チェックリスト、Iron Law、Red Flags、Rationalization 表）は維持し、文章は自分の言葉で書く。
- ネイティブツール（AskUserQuestion、Artifact、TaskCreate/TaskUpdate、EnterWorktree、Agent、SendMessage）とビルトインスキル（/code-review、verify）への言及は、必ず「利用可能なら使う。なければ〈フォールバック手段〉」の二段構えで書く。
- 分量目安: コアスキル（design/plan/execute/tdd/debug）は 150〜300 行、補助スキル（verify-done/request-review/finish/parallel）と using-kata は 50〜100 行。
- spec・プランの保存先は `docs/kata/specs/`・`docs/kata/plans/`（スキル本文内の記載もこのパス）。
- コミットメッセージは conventional commits（日本語）。各タスク末尾で必ずコミットする。
- 原典の場所: `/home/acrobatkame/workspace/superpowers/skills/`（読み取り専用。変更しない）。

---

### Task 1: リポジトリ基盤（marketplace.json / plugin.json / LICENSE）

**Files:**
- Create: `.claude-plugin/marketplace.json`
- Create: `plugins/kata/.claude-plugin/plugin.json`
- Create: `LICENSE`

**Interfaces:**
- Produces: プラグイン名 `kata`（以降の全タスクのスキルは `plugins/kata/skills/` 配下に置く）

- [ ] **Step 1: marketplace.json を作成**

```json
{
  "$schema": "https://json.schemastore.org/claude-code-marketplace.json",
  "name": "claude-plugins",
  "owner": {
    "name": "mjkt"
  },
  "description": "個人用 Claude Code プラグイン配布マーケットプレイス",
  "plugins": [
    {
      "name": "kata",
      "source": "./plugins/kata",
      "description": "開発プロセスに規律を与えるスキル集。設計（design）→プラン（plan）→実行（execute）のワークフローと、tdd・debug・verify-done 等の横断ゲートを提供する。/kata:<skill-name> で呼び出す。"
    }
  ]
}
```

- [ ] **Step 2: plugin.json を作成**

```json
{
  "$schema": "https://json.schemastore.org/claude-code-plugin.json",
  "name": "kata",
  "displayName": "Kata - Disciplined Development Skills",
  "version": "0.1.0",
  "description": "開発プロセスに規律を与えるスキル集。design→plan→execute のワークフローと tdd・debug・verify-done 等の横断ゲートを /kata:<skill-name> で提供する。",
  "author": {
    "name": "mjkt"
  },
  "keywords": [
    "workflow",
    "discipline",
    "tdd",
    "debugging",
    "planning"
  ],
  "license": "MIT"
}
```

- [ ] **Step 3: LICENSE を作成**

MIT License 全文（標準テンプレート）に `Copyright (c) 2026 mjkt` を入れて保存する。

- [ ] **Step 4: 検証**

Run: `cat .claude-plugin/marketplace.json | python3 -m json.tool > /dev/null && cat plugins/kata/.claude-plugin/plugin.json | python3 -m json.tool > /dev/null && echo OK`
Expected: `OK`（両 JSON が構文的に妥当）

- [ ] **Step 5: コミット**

```bash
git add .claude-plugin plugins/kata/.claude-plugin LICENSE
git commit -m "feat(kata): マーケットプレイスとプラグインの基盤を追加"
```

---

### Task 2: tdd スキル

**Files:**
- Create: `plugins/kata/skills/tdd/SKILL.md`
- Create: `plugins/kata/skills/tdd/references/testing-anti-patterns.md`

**Interfaces:**
- Produces: `kata:tdd`（execute・debug から参照される）

- [ ] **Step 1: 原典を読む**

Read: `/home/acrobatkame/workspace/superpowers/skills/test-driven-development/SKILL.md` と同ディレクトリの `testing-anti-patterns.md`

- [ ] **Step 2: SKILL.md を書く**

frontmatter（完全文）:

```yaml
---
name: tdd
description: Use when implementing any feature or bugfix, before writing implementation code - enforces RED-GREEN-REFACTOR with mandatory failure verification
---
```

本文構成（各節に含める要素）:

1. **概要**: 中核原則「テストが失敗するのを見ていないなら、そのテストが正しいものを検証している保証はない」。文言でなく精神への違反も違反。
2. **鉄の掟**: `失敗するテストより先にプロダクションコードを書かない`。テストより先に書いたコードは削除してやり直す（「参照用に残す」「見ながら書き直す」も禁止。削除は削除）。
3. **適用範囲**: 常時（新機能・バグ修正・リファクタリング・挙動変更）。例外（使い捨てプロトタイプ、生成コード、設定ファイル）はユーザーに確認してから。
4. **RED-GREEN-REFACTOR サイクル**: 原典の dot 図を維持（RED→失敗の確認→GREEN→成功の確認→REFACTOR→green 維持）。各フェーズの要件:
   - RED: 1 挙動 1 テスト、明確な名前、モック最小。
   - RED 検証（必須・スキップ禁止）: 失敗すること／期待どおりの理由で失敗すること（typo でなく機能欠如で）を実行して確認。即座に通ったら既存挙動のテスト＝テストを直す。
   - GREEN: テストを通す最小のコードのみ。YAGNI。
   - GREEN 検証（必須）: 対象テストと既存テストが全部通ること、出力が汚れていないこと。
   - REFACTOR: green のまま重複除去・命名改善のみ。挙動追加禁止。
5. **良いテストの条件表**: Minimal / Clear / Shows intent（Good/Bad の対比例をコード付きで 1 組。原典の retryOperation 例を自分の言葉・例に置き換えてよい）。
6. **順序が重要な理由**: 「後からテストを書く」が無意味な理由（即座に通るテストは何も証明しない／実装に引きずられ要求でなく実装をテストする／手動テストは記録も再実行もできない／サンクコスト論の反駁）を Q&A でなく断定で書く。
7. **合理化への反論表**: 原典の Common Rationalizations 表から最低 8 行（「単純すぎてテスト不要」「後でテストする」「手動で確認済み」「X 時間分の削除はもったいない」「参照用に残す」「TDD は教条的」「先に探索が必要」「テストしにくい＝設計が悪い」）。
8. **Red Flags**: 「テストより先にコード」「テストが即座に通った」「なぜ失敗したか説明できない」「今回だけ」等 → 全て「コードを削除して TDD でやり直し」。
9. **references への誘導**: モックやテストユーティリティを足すときは `references/testing-anti-patterns.md` を読む。
10. **関連スキル**: 検証の主張は `kata:verify-done`、バグ修正の失敗テスト作成は `kata:debug` の Phase 4 から呼ばれる旨。

- [ ] **Step 3: references/testing-anti-patterns.md を書く**

原典 `testing-anti-patterns.md`（299 行）から以下のアンチパターンを要点化（各 10〜20 行、Bad/Good コード対比付き）: モックの挙動をテストする／プロダクションクラスへのテスト専用メソッド追加／依存を理解せずにモックする。

- [ ] **Step 4: 検証**

Run: `head -4 plugins/kata/skills/tdd/SKILL.md && grep -c "superpowers" plugins/kata/skills/tdd/SKILL.md plugins/kata/skills/tdd/references/testing-anti-patterns.md`
Expected: frontmatter に `name: tdd` が見え、grep は各ファイル `0`（grep の exit code 1 は正常）

- [ ] **Step 5: コミット**

```bash
git add plugins/kata/skills/tdd
git commit -m "feat(kata): tdd スキルを追加"
```

---

### Task 3: debug スキル

**Files:**
- Create: `plugins/kata/skills/debug/SKILL.md`

**Interfaces:**
- Consumes: `kata:tdd`（Phase 4 の失敗テスト作成）、`kata:verify-done`（修正確認）
- Produces: `kata:debug`

- [ ] **Step 1: 原典を読む**

Read: `/home/acrobatkame/workspace/superpowers/skills/systematic-debugging/SKILL.md`。補助ファイル `root-cause-tracing.md`・`defense-in-depth.md`・`condition-based-waiting.md` は見出しと要点のみ拾う（本文へ統合するため）。

- [ ] **Step 2: SKILL.md を書く**

frontmatter（完全文）:

```yaml
---
name: debug
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes - four-phase root cause investigation
---
```

本文構成:

1. **概要**: 中核原則「修正の前に必ず根本原因を特定する。症状への対処は失敗」。
2. **鉄の掟**: `根本原因の調査なしに修正しない`。Phase 1 完了前に修正を提案してはならない。
3. **適用場面**: あらゆる技術的問題。特に「時間的プレッシャーがあるとき」「すでに複数の修正を試したとき」「簡単に見えるとき」こそ使う。
4. **4 フェーズ**（各フェーズ完了までに次へ進まない）:
   - Phase 1 根本原因調査: エラーメッセージを最後まで読む／確実に再現させる／直近の変更を確認する（git diff・新依存・設定）／多層システムでは各層の境界にログを入れて「どの層で壊れるか」の証拠を先に集める（原典の層別 echo 例のような bash 例を 1 つ入れる）／悪い値を呼び出し元へ遡って発生源を特定する（symptom でなく source を直す）。
   - Phase 2 パターン分析: 同一コードベースの動く類似例を探す／リファレンス実装は全部読む（流し読み禁止）／動くものと壊れているものの差分を全部列挙する。
   - Phase 3 仮説と検証: 仮説は 1 つずつ明文化（「X が原因だと考える。理由は Y」）／最小の変更で検証／ダメなら新仮説（修正を積み重ねない）／わからないときは「わからない」と言う。
   - Phase 4 実装: まず失敗する再現テストを作る（`kata:tdd` を使う）→根本原因への修正を 1 つだけ実施（ついで改善・同時リファクタリング禁止）→検証（`kata:verify-done`）。
5. **3 回失敗ルール**: 修正が 3 回失敗したら Phase 1 に戻るのではなくアーキテクチャを疑い、ユーザーと議論する。「修正のたびに別の場所で新症状」はアーキテクチャ問題のサイン。
6. **Red Flags**: 「とりあえず変えてみる」「複数変更をまとめて試す」「たぶん X だから直す」「調査より先に修正案を列挙」等 → 全て Phase 1 へ戻る。
7. **合理化への反論表**: 最低 6 行（「単純な問題だから」「緊急だから」「まず試してから調査」「テストは修正確認後」「複数同時修正が速い」「もう 1 回だけ修正」）。
8. **調査しても原因不明のとき**: 本当に環境・タイミング起因なら調査内容を記録し、リトライ／タイムアウト／ログ強化で対処。ただし「原因不明」の 95% は調査不足。
9. **補助テクニック（統合）**: 逆方向トレース（バグを呼び出し履歴を遡って発生源まで追う）／多層防御（根本修正後に複数層へバリデーション追加）／条件ベース待機（任意の sleep でなく条件ポーリングに置き換える）を各 5〜10 行で要約。

- [ ] **Step 3: 検証**

Run: `head -4 plugins/kata/skills/debug/SKILL.md && grep -c "superpowers" plugins/kata/skills/debug/SKILL.md; grep -oE "kata:[a-z-]+" plugins/kata/skills/debug/SKILL.md | sort -u`
Expected: `name: debug`、superpowers は 0 件、参照は `kata:tdd`・`kata:verify-done` のみ

- [ ] **Step 4: コミット**

```bash
git add plugins/kata/skills/debug
git commit -m "feat(kata): debug スキルを追加"
```

---

### Task 4: verify-done スキル

**Files:**
- Create: `plugins/kata/skills/verify-done/SKILL.md`

**Interfaces:**
- Produces: `kata:verify-done`（debug・execute・finish から参照される）

- [ ] **Step 1: 原典を読む**

Read: `/home/acrobatkame/workspace/superpowers/skills/verification-before-completion/SKILL.md`

- [ ] **Step 2: SKILL.md を書く（50〜100 行）**

frontmatter（完全文）:

```yaml
---
name: verify-done
description: Use when about to claim work is complete, fixed, or passing, before committing or reporting success - requires fresh verification evidence before any success claim
---
```

本文構成:

1. **鉄の掟**: `新鮮な検証の証拠なしに完了を主張しない`。このメッセージ内で検証コマンドを実行していないなら「通る」とは言えない。
2. **ゲート手順**: 主張の前に必ず (1) その主張を証明するコマンドを特定 → (2) 完全に実行 → (3) 出力全体と exit code を読む → (4) 出力が主張を裏付けるか確認 → (5) 証拠付きで主張。どれかを飛ばす＝検証でなく嘘。
3. **主張と必要な証拠の対応表**: テスト通過＝テストコマンド出力 0 failures（過去の実行や「通るはず」は不可）／ビルド成功＝exit 0（linter 通過では不十分）／バグ修正＝元の症状の再テスト／エージェント完了＝VCS diff の確認（エージェントの成功報告を信用しない）／要件充足＝プランと突き合わせたチェックリスト。
4. **Claude Code 特化**: 実動作の検証にはビルトイン `verify` スキルが利用可能なら使う。なければ対象フローを手で実行して観察する。
5. **Red Flags**: 「〜のはず」「たぶん」「Done!」等の先走った満足表現、検証なしのコミット・PR、部分チェックからの外挿。
6. **合理化への反論表**: 最低 5 行（「動くはず」「自信がある」「今回だけ」「linter は通った」「エージェントが成功と言った」「疲れた」）。

- [ ] **Step 3: 検証**

Run: `head -4 plugins/kata/skills/verify-done/SKILL.md && wc -l < plugins/kata/skills/verify-done/SKILL.md`
Expected: `name: verify-done`、行数 50〜110 程度

- [ ] **Step 4: コミット**

```bash
git add plugins/kata/skills/verify-done
git commit -m "feat(kata): verify-done スキルを追加"
```

---

### Task 5: design スキル

**Files:**
- Create: `plugins/kata/skills/design/SKILL.md`

**Interfaces:**
- Consumes: `kata:plan`（終端で必ず呼ぶ）
- Produces: `kata:design`

- [ ] **Step 1: 原典を読む**

Read: `/home/acrobatkame/workspace/superpowers/skills/brainstorming/SKILL.md`（ビジュアルコンパニオン節と `visual-companion.md`・`scripts/` は対象外）

- [ ] **Step 2: SKILL.md を書く**

frontmatter（完全文）:

```yaml
---
name: design
description: Use before any creative work - creating features, building components, adding functionality, or changing behavior. Explores intent, requirements and design through dialogue before implementation
---
```

本文構成:

1. **概要**: 対話でアイデアを設計と spec に育てる。プロジェクト文脈の把握→一問一答→設計提示→承認→spec 文書化。
2. **HARD-GATE**: 設計を提示しユーザーが承認するまで、実装スキルの起動・コード作成・スキャフォールドを一切行わない。どんなに単純に見えるプロジェクトでも適用。
3. **アンチパターン節**: 「単純すぎて設計不要」の反駁 — 単純なプロジェクトこそ未検証の思い込みが無駄工数を生む。設計は短くてよいが提示と承認は省略不可。
4. **チェックリスト**（TaskCreate が利用可能ならタスク化、なければ todo リスト）: プロジェクト文脈の探索→一問一答の明確化→2〜3 案の提示→設計のセクション提示→spec 文書化→セルフレビュー→ユーザーレビュー→`kata:plan` へ移行。
5. **プロセス詳細**:
   - 文脈探索: ファイル・docs・直近コミットを見る。複数の独立サブシステムを含む依頼はまず分解を提案。
   - 質問: 1 メッセージ 1 質問。AskUserQuestion ツールが利用可能なら選択式で提示（preview で構成比較も可）。なければ本文で選択肢を列挙。
   - 視覚提示: モックアップ・図解が言葉より伝わる場面では、Artifact ツールが利用可能なら HTML で提示。なければテキスト（ASCII 図）で代替。
   - 設計提示: セクションごとに複雑さに応じた分量で提示し、都度確認。アーキテクチャ・構成要素・データフロー・エラー処理・テストをカバー。
   - 分離と明確さ: 各ユニットは単一目的・明確なインターフェース・独立テスト可能に。
6. **spec 文書化**: `docs/kata/specs/YYYY-MM-DD-<topic>-design.md` に保存し、コミット。セルフレビュー（プレースホルダ走査／内部矛盾／スコープ／曖昧さ）を 1 回だけ実施して inline 修正。
7. **ユーザーレビューゲート**: spec のパスを伝えレビューを依頼。承認まで先へ進まない。
8. **終端**: 承認後は必ず `kata:plan` を起動する（他の実装スキルへ直接進まない）。EnterPlanMode を使う場面でも、先に本スキルを済ませる。
9. **主要原則**: 一問一答／選択式優先／YAGNI／必ず複数案／逐次承認。

- [ ] **Step 3: 検証**

Run: `head -4 plugins/kata/skills/design/SKILL.md && grep -oE "kata:[a-z-]+" plugins/kata/skills/design/SKILL.md | sort -u`
Expected: `name: design`、参照は `kata:plan` のみ

- [ ] **Step 4: コミット**

```bash
git add plugins/kata/skills/design
git commit -m "feat(kata): design スキルを追加"
```

---

### Task 6: plan スキル

**Files:**
- Create: `plugins/kata/skills/plan/SKILL.md`

**Interfaces:**
- Consumes: `kata:execute`（終端で執行方式を提示）
- Produces: `kata:plan`、プラン文書形式（ヘッダ＋Global Constraints＋タスク構造）— execute スキルはこの形式を前提にする

- [ ] **Step 1: 原典を読む**

Read: `/home/acrobatkame/workspace/superpowers/skills/writing-plans/SKILL.md`

- [ ] **Step 2: SKILL.md を書く**

frontmatter（完全文）:

```yaml
---
name: plan
description: Use when you have an approved design or spec for a multi-step task, before touching code - creates an implementation plan of bite-sized, independently verifiable tasks
---
```

本文構成:

1. **概要**: 「コードベースの文脈を持たない熟練エンジニア」が実装できる粒度で書く。触るファイル・コード・テスト・確認コマンドを全部書く。DRY・YAGNI・TDD・高頻度コミット。
2. **保存先**: `docs/kata/plans/YYYY-MM-DD-<feature-name>.md`。
3. **スコープチェック**: spec が複数の独立サブシステムを含むなら、プランを分割する（1 プラン＝単独で動作しテスト可能なソフトウェア）。
4. **ファイル構成の先行設計**: タスク定義の前に、作成・変更するファイルと各ファイルの責務を一覧化。1 ファイル 1 責務。
5. **タスクの適正サイズ**: タスク＝独自のテストサイクルを持つ最小単位。レビュアーが隣のタスクを承認しつつこのタスクだけ差し戻せる境界で切る。
6. **ステップ粒度**: 1 ステップ＝1 アクション（2〜5 分）。「失敗するテストを書く」「失敗を確認」「最小実装」「通過を確認」「コミット」。
7. **プランヘッダのテンプレート**（コードブロックで明示）: For agentic workers 行（`kata:execute` を必須サブスキルとして指定）／Goal／Architecture／Tech Stack／Global Constraints（spec の全域制約を正確な値で転記）。
8. **タスク構造のテンプレート**（コードブロックで明示）: Files（正確なパス）／Interfaces（Consumes: 先行タスクから使うもの、Produces: 後続タスクが依存する正確なシグネチャ）／チェックボックス付きステップ（テストコード・実装コード・実行コマンドと期待出力・コミットコマンド）。
9. **プレースホルダ禁止**: 「TBD」「後で実装」「適切にエラー処理」「Task N と同様」等はプランの失敗。コードを書くステップには必ず実際のコードを書く。
10. **セルフレビュー**: spec カバレッジ（各要件に対応タスクがあるか）／プレースホルダ走査／型・シグネチャの前後一貫性。見つけたら inline 修正。
11. **実行への引き継ぎ**: 保存後、`kata:execute` の起動を提案する（実行モードの選択は execute 側で行う）。

- [ ] **Step 3: 検証**

Run: `head -4 plugins/kata/skills/plan/SKILL.md && grep -oE "kata:[a-z-]+" plugins/kata/skills/plan/SKILL.md | sort -u`
Expected: `name: plan`、参照は `kata:execute` のみ（`kata:design` への言及があっても可）

- [ ] **Step 4: コミット**

```bash
git add plugins/kata/skills/plan
git commit -m "feat(kata): plan スキルを追加"
```

---

### Task 7: request-review スキル

**Files:**
- Create: `plugins/kata/skills/request-review/SKILL.md`
- Create: `plugins/kata/skills/request-review/references/code-reviewer-prompt.md`

**Interfaces:**
- Produces: `kata:request-review` と `references/code-reviewer-prompt.md`（execute の最終レビューがこのテンプレートを使う）

- [ ] **Step 1: 原典を読む**

Read: `/home/acrobatkame/workspace/superpowers/skills/requesting-code-review/SKILL.md` と `code-reviewer.md`

- [ ] **Step 2: SKILL.md を書く（50〜100 行）**

frontmatter（完全文）:

```yaml
---
name: request-review
description: Use when completing a task or major feature, or before merging - dispatches a reviewer subagent to verify the work against spec and plan
---
```

本文構成:

1. **概要**: レビュアーサブエージェントに「セッション履歴ではなく、精選した文脈」を渡してレビューさせる。早く・頻繁に。
2. **役割分担（Claude Code 特化）**: バグ・品質の検出はビルトイン `/code-review` が利用可能ならそれに委譲。本スキルの主眼は **spec・プラン適合性**（要求を満たすか、余計なものを作っていないか）。ビルトインがない環境では `references/code-reviewer-prompt.md` で両方をカバー。
3. **必須タイミング**: execute の各タスク後／大きな機能の完了後／マージ前。
4. **手順**: (1) `BASE_SHA`・`HEAD_SHA` を取得（複数コミットのタスクでは HEAD~1 でなく記録済み BASE を使う）→ (2) `git diff -U10 BASE..HEAD` をファイルに書き出し → (3) Agent ツール（general-purpose）で `references/code-reviewer-prompt.md` のテンプレートを埋めて dispatch → (4) フィードバック対応（Critical は即修正、Important は先へ進む前に修正、Minor は記録。レビュアーが誤っていれば根拠を示して反論）。
5. **Red Flags**: 「単純だからレビュー不要」／Critical 未対応のまま進む／正当な指摘への抗弁なし・盲従。

- [ ] **Step 3: references/code-reviewer-prompt.md を書く**

原典 `code-reviewer.md`（172 行）のエッセンスをテンプレート化。含める要素: プレースホルダ（`{DESCRIPTION}`・`{PLAN_OR_REQUIREMENTS}`・`{BASE_SHA}`・`{HEAD_SHA}`・`{DIFF_FILE}`）／レビュー観点（spec 適合＝不足と過剰の両方・コード品質・テストの実質性）／severity 定義（Critical/Important/Minor）／出力形式（Strengths・Issues・総合判定）。

- [ ] **Step 4: 検証**

Run: `head -4 plugins/kata/skills/request-review/SKILL.md && grep -c "{DESCRIPTION}" plugins/kata/skills/request-review/references/code-reviewer-prompt.md`
Expected: `name: request-review`、プレースホルダが存在（1 以上）

- [ ] **Step 5: コミット**

```bash
git add plugins/kata/skills/request-review
git commit -m "feat(kata): request-review スキルを追加"
```

---

### Task 8: execute スキル（統合スキル）

**Files:**
- Create: `plugins/kata/skills/execute/SKILL.md`
- Create: `plugins/kata/skills/execute/references/implementer-prompt.md`
- Create: `plugins/kata/skills/execute/references/task-reviewer-prompt.md`

**Interfaces:**
- Consumes: `kata:plan` のプラン形式、`kata:tdd`、`kata:request-review`（references/code-reviewer-prompt.md 含む）、`kata:verify-done`、`kata:finish`
- Produces: `kata:execute`

- [ ] **Step 1: 原典を読む**

Read: `/home/acrobatkame/workspace/superpowers/skills/executing-plans/SKILL.md`、`subagent-driven-development/SKILL.md`、`subagent-driven-development/implementer-prompt.md`、`subagent-driven-development/task-reviewer-prompt.md`、`using-git-worktrees/SKILL.md`

- [ ] **Step 2: SKILL.md を書く（3 原典の統合。300 行以内）**

frontmatter（完全文）:

```yaml
---
name: execute
description: Use when you have a written implementation plan to execute - sets up an isolated worktree, then executes tasks directly or via fresh subagents with per-task review
---
```

本文構成:

1. **概要**: プランを読み、批判的にレビューし、隔離された作業環境で全タスクを実行する。main/master 上で直接実装を始めない（明示的な同意がない限り）。
2. **Step 0 作業環境の分離**（原典 using-git-worktrees の統合）:
   - 既存分離の検出: `git rev-parse --git-dir` と `--git-common-dir` の比較（実コマンド付き）。サブモジュール誤判定のガード（`git rev-parse --show-superproject-working-tree`）。すでに worktree 内ならスキップ。
   - 分離の作成: EnterWorktree ツールが利用可能なら必ずそれを使う（ネイティブツールがあるのに `git worktree add` するのは phantom state を作る典型ミス）。なければ `git worktree add` フォールバック: `.worktrees/<branch>` を既定とし、**作成前に `git check-ignore` で ignore 済みか必ず確認**（未 ignore なら .gitignore へ追加してコミット）。
   - セットアップとベースライン: 依存インストール（package.json/Cargo.toml/pyproject.toml 等の自動検出）→テストを実行してクリーンな出発点を確認。失敗しているなら報告して指示を仰ぐ。
3. **Step 1 プラン読み込み**: プランを読み、疑問・懸念があれば実行前にまとめて 1 回で確認（タスク途中の逐次割り込みでなく）。Global Constraints を記録。TaskCreate が利用可能ならタスク登録、なければ todo リスト。
4. **Step 2 実行モード選択**（statement で判断基準を明示）:
   - **自走モード**: タスクが密結合／小規模プラン／サブエージェント不要な単純作業。
   - **サブエージェント駆動モード（推奨）**: タスクが概ね独立で、コンテキストを新鮮に保ちたいとき。
5. **自走モード**: タスクごとに in_progress → ステップを正確に実行（プランに逸脱したくなったら停止して確認）→ 検証コマンド実行 → completed。ブロッカー（依存欠落・テスト失敗・指示不明瞭）に当たったら推測せず停止して質問。
6. **サブエージェント駆動モード**:
   - 原則: タスクごとに新しい implementer サブエージェント＋タスクごとのレビュー＋最後にブランチ全体レビュー。タスク間でユーザーに「続けますか？」と聞かない（停止条件は BLOCKED・真の曖昧さ・全タスク完了のみ）。
   - dispatch 手順: タスク開始前に BASE コミットを記録 → タスク本文をファイルに抽出（`awk`/手動コピーでよい。プラン全文をサブエージェントに読ませない）→ Agent ツール（general-purpose）で `references/implementer-prompt.md` を埋めて起動。**実装サブエージェントの並列起動は禁止**（コンフリクトする）。
   - 実装者の報告ステータス処理: DONE→レビューへ／DONE_WITH_CONCERNS→懸念を読んでから／NEEDS_CONTEXT→文脈を足して再 dispatch（SendMessage が利用可能なら同一エージェントを継続）／BLOCKED→文脈不足なら補足、能力不足ならより強いモデル、タスク過大なら分割、プラン自体の誤りならユーザーへ。
   - タスクレビュー: `git diff -U10 BASE..HEAD` をファイルへ書き出し、`references/task-reviewer-prompt.md` を埋めてレビュアーを dispatch。spec 適合と品質の両判定が揃うまでタスク完了にしない。Critical/Important は修正サブエージェント → 再レビュー。Minor は台帳に記録。
   - 進捗台帳: コンパクション対策としてリポジトリルートの `.kata/progress.md`（git-ignore された作業ファイル）に「Task N: complete (commits X..Y)」を追記。再開時は台帳と `git log` を信じ、完了済みタスクを再 dispatch しない。
   - モデル選択: 機械的タスクは安価なモデル、統合・判断はセッション標準、最終ブランチレビューは最も能力の高いモデル。dispatch 時に明示。
7. **完了処理**: 全タスク後、ブランチ全体の最終レビュー（`kata:request-review` のテンプレートで dispatch）→ `kata:verify-done` で完了主張の検証 → `kata:finish` を起動。
8. **Red Flags**: main 直接実装／レビュー省略／未修正 Critical のまま次へ／実装サブエージェントの並列起動／プラン全文をサブエージェントへ／台帳が complete 済みのタスクの再 dispatch／ブロッカーの強行突破。

- [ ] **Step 3: references/implementer-prompt.md を書く**

原典 `implementer-prompt.md`（139 行）のエッセンスをテンプレート化。含める要素: プレースホルダ（`{TASK_CONTEXT}`＝プロジェクト内での位置 1 行、`{TASK_FILE}`＝タスク本文ファイルパス、`{INTERFACES}`＝先行タスクのインターフェース、`{REPORT_FILE}`＝報告書パス）／作業前に質問してよい（不明点があれば実装前に聞く）／TDD 遵守（`kata:tdd` 準拠。テストを先に書き失敗を確認）／コミットまで行う／セルフレビュー／報告契約（報告書ファイルに全文、返信は status＝DONE・DONE_WITH_CONCERNS・NEEDS_CONTEXT・BLOCKED のいずれか＋コミット一覧＋テスト結果 1 行＋懸念のみ）。

- [ ] **Step 4: references/task-reviewer-prompt.md を書く**

原典 `task-reviewer-prompt.md`（188 行）のエッセンスをテンプレート化。含める要素: プレースホルダ（`{TASK_FILE}`・`{REPORT_FILE}`・`{DIFF_FILE}`・`{GLOBAL_CONSTRAINTS}`）／二重判定＝spec 適合（要求の不足と過剰の両方を列挙）と品質（severity: Critical/Important/Minor）／diff から確認できない要件は「⚠️ Cannot verify from diff」として報告（コントローラーが解決する）／出力形式（spec 判定・Strengths・Issues・総合判定）。

- [ ] **Step 5: 検証**

Run: `head -4 plugins/kata/skills/execute/SKILL.md && ls plugins/kata/skills/execute/references/ && grep -oE "kata:[a-z-]+" plugins/kata/skills/execute/SKILL.md | sort -u && wc -l < plugins/kata/skills/execute/SKILL.md`
Expected: `name: execute`、references に 2 ファイル、参照は `kata:tdd`・`kata:request-review`・`kata:verify-done`・`kata:finish`（＋`kata:plan` 言及可）、300 行以内

- [ ] **Step 6: コミット**

```bash
git add plugins/kata/skills/execute
git commit -m "feat(kata): execute スキルを追加（実行・サブエージェント駆動・worktree 統合）"
```

---

### Task 9: finish スキル

**Files:**
- Create: `plugins/kata/skills/finish/SKILL.md`

**Interfaces:**
- Consumes: `kata:verify-done`
- Produces: `kata:finish`

- [ ] **Step 1: 原典を読む**

Read: `/home/acrobatkame/workspace/superpowers/skills/finishing-a-development-branch/SKILL.md`

- [ ] **Step 2: SKILL.md を書く（50〜100 行）**

frontmatter（完全文）:

```yaml
---
name: finish
description: Use when implementation is complete, verified and reviewed - presents structured options for merging, creating a PR, keeping or discarding the branch, then cleans up
---
```

本文構成:

1. **手順**: テスト確認 → 環境検出 → 選択肢提示 → 実行 → 後片付け。
2. **Step 1 テスト確認**: 全テスト通過を実行して確認（`kata:verify-done` 準拠）。失敗があれば選択肢を出さずに停止。
3. **Step 2 環境検出**: `git rev-parse --git-dir` と `--git-common-dir` の比較で通常リポ／worktree／detached HEAD を判定（実コマンド付き）。
4. **Step 3 選択肢提示**: AskUserQuestion が利用可能なら選択式で、なければ番号付きリストで、正確に 4 択（detached HEAD は merge を除く 3 択）: (1) ベースブランチへローカルマージ (2) push して PR 作成 (3) ブランチ維持 (4) 破棄。余計な説明を付けない。
5. **Step 4 実行**: マージ＝先にマージ成功とマージ後テストを確認してから片付け／PR＝`gh` CLI（`git push -u origin <branch>` → `gh pr create`）、worktree は PR 対応用に残す／破棄＝「discard」の入力確認必須、確認後に force delete。
6. **Step 5 後片付け**: 選択肢 (1)(4) のみ。自分（kata）が `.worktrees/` 配下に作った worktree だけ削除する（`cd` でメインリポに出てから `git worktree remove` → `git worktree prune`）。ExitWorktree 等のネイティブツールがある環境ではそれを使う。ハーネス管理の workspace は削除しない。
7. **Red Flags**: テスト失敗のまま進める／確認なしの破棄／worktree 内から remove 実行／自分が作っていない worktree の削除／ブランチ削除を worktree 削除より先に行う。

- [ ] **Step 3: 検証**

Run: `head -4 plugins/kata/skills/finish/SKILL.md && grep -c "gh pr create" plugins/kata/skills/finish/SKILL.md`
Expected: `name: finish`、`gh pr create` が 1 以上

- [ ] **Step 4: コミット**

```bash
git add plugins/kata/skills/finish
git commit -m "feat(kata): finish スキルを追加"
```

---

### Task 10: parallel スキル

**Files:**
- Create: `plugins/kata/skills/parallel/SKILL.md`

**Interfaces:**
- Produces: `kata:parallel`

- [ ] **Step 1: 原典を読む**

Read: `/home/acrobatkame/workspace/superpowers/skills/dispatching-parallel-agents/SKILL.md`

- [ ] **Step 2: SKILL.md を書く（50〜100 行）**

frontmatter（完全文）:

```yaml
---
name: parallel
description: Use when facing 2+ independent tasks with no shared state or ordering dependency - dispatches focused subagents to work concurrently
---
```

本文構成:

1. **原則**: 独立した問題領域ごとに 1 エージェント。セッション履歴を継承させず、必要な文脈だけを正確に構成して渡す。
2. **使う条件／使わない条件**: 独立（片方の修正が他方に影響しない）かつ共有状態なし → 使う。関連する失敗・全体把握が必要・探索段階 → 使わない。
3. **手順**: (1) 独立ドメインへの分割 → (2) 各エージェントへ「範囲・ゴール・制約・期待出力」を明記したプロンプト作成 → (3) **同一メッセージ内で複数 Agent ツールを呼んで並列起動**（1 メッセージ 1 呼び出しだと逐次になる）→ (4) 結果の統合（各サマリー確認・競合確認・全体テスト実行）。
4. **Claude Code 特化**: ファイル変更を伴う並列タスクは Agent ツールの `isolation: "worktree"` で分離する。読み取り専用調査なら不要。
5. **良いプロンプトの条件**: 焦点が 1 つ／自己完結（エラーメッセージ・テスト名を貼る）／出力形式を指定。Bad/Good の対比を 3 組程度。
6. **統合時の検証**: エージェントの成功報告を信用せず diff と全体テストで確認（`kata:verify-done` 準拠）。

- [ ] **Step 3: 検証**

Run: `head -4 plugins/kata/skills/parallel/SKILL.md && grep -c "isolation" plugins/kata/skills/parallel/SKILL.md`
Expected: `name: parallel`、`isolation` が 1 以上

- [ ] **Step 4: コミット**

```bash
git add plugins/kata/skills/parallel
git commit -m "feat(kata): parallel スキルを追加"
```

---

### Task 11: using-kata スキル（ディスパッチャー）

**Files:**
- Create: `plugins/kata/skills/using-kata/SKILL.md`

**Interfaces:**
- Consumes: 全 9 スキルの名前と一言説明（Task 2〜10 の成果）
- Produces: `kata:using-kata`

- [ ] **Step 1: 原典を読む**

Read: `/home/acrobatkame/workspace/superpowers/skills/using-superpowers/SKILL.md`（Platform Adaptation 節は対象外）

- [ ] **Step 2: SKILL.md を書く（50〜100 行）**

frontmatter（完全文）:

```yaml
---
name: using-kata
description: Use when starting any conversation or task - establishes how to find and use kata skills, requiring a skill check before any response or action
---
```

本文構成:

1. **サブエージェント除外**: 特定タスクの実行のために dispatch されたサブエージェントはこのスキルを無視する。
2. **ルール**: 該当する可能性が 1% でもあるスキルは、応答・行動（明確化の質問・コード探索を含む）の前に必ず起動する。合わなければ使わなくてよいが、確認は必須。
3. **スキル早見表**: 全 9 スキルの「name — 一言トリガー」一覧（design=何か作る前／plan=承認済み設計から／execute=プランを実行／tdd=実装コードを書く前／debug=バグ・失敗・予期しない挙動／verify-done=完了を主張する前／request-review=タスク・機能完了時／finish=実装完了後の統合判断／parallel=独立タスク 2 つ以上）。
4. **優先順位**: プロセススキル（design・debug）が先、実装系はその後。「作って」→ design から。「直して」→ debug から。EnterPlanMode の前に design。
5. **Red Flags 表**: 「ただの質問だから」「先にコードを見てから」「スキルは大げさ」「覚えているから読まなくていい」等の合理化 → 全て「スキルを確認・起動せよ」。
6. **ユーザー指示の優先**: CLAUDE.md・直接指示はスキルより優先。スキル省略はユーザーが明示したときのみ。

- [ ] **Step 3: 検証**

Run: `head -4 plugins/kata/skills/using-kata/SKILL.md && for s in design plan execute tdd debug verify-done request-review finish parallel; do grep -q "$s" plugins/kata/skills/using-kata/SKILL.md || echo "MISSING: $s"; done`
Expected: `name: using-kata`、MISSING 出力なし

- [ ] **Step 4: コミット**

```bash
git add plugins/kata/skills/using-kata
git commit -m "feat(kata): using-kata ディスパッチャースキルを追加"
```

---

### Task 12: README

**Files:**
- Modify: `README.md`（既存スタブを全置換）

**Interfaces:**
- Consumes: 全スキル名（Task 2〜11）、marketplace 名 `claude-plugins`（Task 1）

- [ ] **Step 1: README.md を書く**

含める節:

1. **概要**: 個人用 Claude Code プラグイン配布リポジトリ。収録: kata。
2. **kata とは**: 開発プロセス規律スキル集。スキル一覧表（短縮名／原典スキル名／一言説明）— 対応表は spec `docs/kata/specs/2026-07-09-kata-plugin-design.md` の収録スキル表と一致させる。
3. **導入手順**:
   ```
   /plugin marketplace add <このリポジトリの Git URL またはローカルパス>
   /plugin install kata
   ```
4. **ディスパッチャーの有効化（2 方式）**:
   - 基本: CLAUDE.md へ 1 行追記 — `タスク開始前に kata:using-kata スキルの指示に従うこと。` の例文を提示。
   - 任意: 自作 SessionStart フック。settings.json に書く例を提示し、「このプラグインはフックを同梱しない。以下は利用者が自分で書く設定であり、第三者コードの自動実行ではない」と明記:
     ```json
     {
       "hooks": {
         "SessionStart": [
           {
             "hooks": [
               {
                 "type": "command",
                 "command": "echo 'タスク開始前に kata:using-kata スキルの指示に従うこと。'"
               }
             ]
           }
         ]
       }
     }
     ```
5. **設計思想とサプライチェーン方針**: Markdown のみ・実行可能コードなし。理由の説明。
6. **クレジットとライセンス**: 本プラグインは [obra/superpowers](https://github.com/obra/superpowers)（Jesse Vincent, MIT License）のプロセス設計に基づく再構成である旨と、本リポジトリ自体も MIT である旨。

- [ ] **Step 2: 検証**

Run: `grep -c "obra/superpowers" README.md && grep -c "plugin install kata" README.md`
Expected: 両方 1 以上

- [ ] **Step 3: コミット**

```bash
git add README.md
git commit -m "docs: README に導入手順・スキル一覧・クレジットを記載"
```

---

### Task 13: 全体検証

**Files:**
- Modify: なし（検証のみ。問題があれば該当スキルを修正）

- [ ] **Step 1: 相互参照の整合チェック**

Run:
```bash
for ref in $(grep -rhoE "kata:[a-z-]+" plugins/kata/skills | sed 's/kata://' | sort -u); do
  [ -d "plugins/kata/skills/$ref" ] || echo "BROKEN REF: kata:$ref"
done; echo CHECK-DONE
```
Expected: `BROKEN REF` の出力なし、`CHECK-DONE` のみ

- [ ] **Step 2: superpowers 残存チェックと frontmatter 一括確認**

Run:
```bash
grep -rn "superpowers" plugins/ ; echo "---"
for f in plugins/kata/skills/*/SKILL.md; do head -3 "$f" | grep -H "name:" || echo "NO NAME: $f"; done
```
Expected: superpowers は 0 件（`---` の前に出力なし）、全 10 スキルに `name:` があり NO NAME なし

- [ ] **Step 3: 手動インストール確認（ユーザー協力）**

ユーザーに依頼: 別セッションで `/plugin marketplace add /home/acrobatkame/workspace/claude-plugins` → `/plugin install kata` を実行し、`/kata:using-kata` が呼び出せることを確認してもらう。スキル一覧に 10 スキルが表示されることも確認。

- [ ] **Step 4: 最終コミット（修正があった場合のみ）**

```bash
git add -A
git commit -m "fix(kata): 全体検証で見つかった不整合を修正"
```
