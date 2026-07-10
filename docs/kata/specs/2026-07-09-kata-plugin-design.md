# kata プラグイン設計書

日付: 2026-07-09
ステータス: 承認待ち

## 背景と目的

[obra/superpowers](https://github.com/obra/superpowers)（MIT License, Jesse Vincent）は開発プロセスに規律を与える優れたスキル集だが、職場ではサプライチェーンアタック懸念（外部マーケットプレイス経由のインストール、SessionStart フックによるスクリプト自動実行）により利用が禁止されている。

本プラグイン **kata** は、superpowers のうち利用頻度の高いスキルのエッセンス（プロセス構造、チェックリスト、ゲート、レッドフラグ対策）を自分の言葉で再構成したものである。**実行可能コード（hooks、Node サーバ、シェルスクリプト）を一切含まず Markdown のみ**で構成することで、懸念の根拠となる「自動実行されるコード」を構造的に排除する。

また、原典がハーネス非依存（Codex / Pi / Antigravity / Cursor 対応）に書かれているのに対し、本プラグインは **Claude Code 専用**として、ネイティブツール・ビルトインスキルを明示的に活用する（後述）。

### 方針の決定事項

| 項目 | 決定 |
|---|---|
| 作成方法 | エッセンス抽出して書き直し（コピーではない） |
| 記述言語 | frontmatter の description は英語、本文は日本語 |
| プラグイン名 | kata（呼び出しは `/kata:<skill-name>`） |
| 配置先 | 新リポジトリ `claude-plugins`（swallowarc-ai-plugins とは別） |
| スキル構成 | 原典 1:1 ではなく統合を実施（下記） |
| スキル名 | 手動呼び出し向けに短縮名を採用（下記） |
| 対応ハーネス | Claude Code 専用（マルチプラットフォーム対応はしない） |

### 原典からの構成変更（統合）

- **subagent-driven-development → execute に統合。** 両者は「プランを実行する」同一目的で、違いは実行主体だけ。スキル冒頭で実行モード（自走／サブエージェント駆動）を選択する構成にし、タスクループ（実装→レビュー→コミット）の共通構造を一本化する。サブエージェント用プロンプトは references/ に置く。
- **using-git-worktrees → execute に統合。** 実質「プラン実行前の準備手順」であるため、実行スキルの冒頭ステップとする。トレードオフ：プラン実行と無関係に作業分離だけしたい場面では自動発動しなくなる。
- **verify-done、parallel、finish は独立維持。** それぞれ発動タイミングが独自（完了主張の直前／独立タスクの並列化／作業の締め）で、プラン実行以外の文脈でも横断的に発火する必要があるため。
- 分離（split）が必要なスキルはない。収録対象はいずれも単一責務。

## 収録スキル（10個）

自動発動は description で判定されるため、短縮名による発動精度への影響はない。

### コアスキル（原典のプロセス構造を維持した丁寧な再構成）

| スキル | 原典との対応 | 役割 |
|---|---|---|
| design | brainstorming | 対話で要件→設計→spec 文書化。実装前の必須ゲート |
| plan | writing-plans | spec から実装プランを作成 |
| execute | executing-plans + subagent-driven-development + using-git-worktrees | プランの実行。冒頭で worktree 分離と実行モード（自走／サブエージェント駆動）を選択 |
| tdd | test-driven-development | RED→GREEN→REFACTOR の強制 |
| debug | systematic-debugging | 4フェーズの根本原因調査。修正提案前の必須ゲート |

### 補助スキル（要点のみの簡約版、各 50〜100 行目安）

| スキル | 原典との対応 | 役割 | 収録理由 |
|---|---|---|---|
| verify-done | verification-before-completion | 完了宣言前の検証コマンド実行を義務化 | debug が参照。横断的に発火 |
| request-review | requesting-code-review | spec・プラン適合性のコードレビュー依頼 | execute（サブエージェント駆動モード）が参照 |
| finish | finishing-a-development-branch | 完了後のマージ/PR/クリーンアップの構造化 | execute の終端から参照。プランなし作業でも使う |
| parallel | dispatching-parallel-agents | 独立タスクの並列分配 | 単独で有用（ユーザー選定） |

### ディスパッチャー

| スキル | 役割 |
|---|---|
| using-kata | 入口。タスク開始前にスキル該当チェックを義務付ける |

## Claude Code 特化の設計

原典にないネイティブツール・ビルトインスキルの活用を各スキルに明記する。職場と自宅で Claude Code のバージョンが異なる可能性があるため、ツール・ビルトインスキルへの依存はすべて**「あれば使う、なければフォールバック」の二段構え**で記述する（原典と同じパターン）。

### ネイティブツールの活用

| スキル | 特化内容 |
|---|---|
| design | 質問提示は AskUserQuestion ツール（選択式・一問一答、preview で構成比較）。モックアップ等の視覚提示は Artifact ツール（原典ビジュアルコンパニオンの Node サーバ不要な代替）。EnterPlanMode の前に design を済ませる旨を明記 |
| 全スキル | チェックリストは TaskCreate / TaskUpdate でタスク化（原典の「todo を作れ」の明文化） |
| execute | worktree 分離は EnterWorktree ツール優先、なければ `git worktree` コマンド。サブエージェント駆動モードは Agent ツール（1メッセージ並列起動、`isolation: "worktree"`、SendMessage による同一エージェント継続） |
| parallel | Agent ツールの並列起動規約＋ファイル変更を伴う場合の worktree isolation |
| finish | PR 作成は `gh` CLI を標準手順に |

### ビルトインスキルへの委譲

| kata スキル | 委譲先 | 役割分担 |
|---|---|---|
| request-review | ビルトイン `/code-review` | バグ・品質検出はビルトインに委譲。kata はビルトインが見ない「spec・プラン適合性」のレビューに特化（レビュアーサブエージェント）。ビルトインがない環境では references/ のレビュアープロンプトで全部をカバー |
| verify-done | ビルトイン `verify` | 実動作の検証手段として利用可能なら使う。なければ検証コマンドの手動実行 |

## スキル間フロー

相互参照はすべて `kata:<skill-name>` 形式で記述する。

```
design（設計・spec 作成）
  → plan（実装プラン作成）
    → execute（実行）
      ├─ 準備: worktree で作業分離（スキル内ステップ）
      ├─ モード選択: 自走 ／ サブエージェント駆動（スキル内分岐）
      ├─ 実装中: tdd（TDD 強制）
      ├─ 実装中: request-review（タスクごとのレビュー）
      ├─ 完了前: verify-done（検証）
      └─ 完了後: finish（マージ/PR）

独立系:
  debug（バグ・テスト失敗・予期しない挙動に遭遇したとき）
  parallel（独立タスクが 2 つ以上あるとき）
```

## 再構成の粒度

- **コアスキル**: 原典のプロセス構造（フェーズ、チェックリスト、ゲート、dot 形式のフロー図、レッドフラグ表＝「こう考え始めたら暴走のサイン」の一覧）を維持しつつ、本文は日本語で書き直す。原典が持つ説得構造（HARD-GATE、Anti-Pattern 節、rationalization 対策の文言）は構造ごと残す。ここを削ると規律スキルとしての効果が大きく落ちる。
- **補助スキル**: 要点のみの簡約版。
- **references/**: 以下のみ再構成して同梱する。
  - execute: `references/implementer-prompt.md`、`references/task-reviewer-prompt.md`（サブエージェント駆動モード用）
  - tdd: `references/testing-anti-patterns.md`
  - request-review: `references/code-reviewer-prompt.md`
  - 原典のその他の参照ファイル（デバッグ手法の個別解説等）は SKILL.md 本文に要点を統合する。
- **非収録**: brainstorming のビジュアルコンパニオン（Artifact ツールで代替）、原典の hooks・scripts 一式、writing-skills、receiving-code-review、using-superpowers の Platform Adaptation 節。
- **spec/プラン保存先**: 原典の `docs/superpowers/specs/` に代えて `docs/kata/specs/`、プランは `docs/kata/plans/` とする。

## リポジトリ構成

```
~/workspace/claude-plugins/
├── .claude-plugin/
│   └── marketplace.json          # マーケットプレイス定義（swallowarc-ai-plugins と同形式）
├── README.md                     # 導入手順・スキル一覧・原典クレジット・自作フック手順
├── LICENSE                       # MIT
├── docs/kata/specs/              # 本設計書もここに置く
└── plugins/
    └── kata/
        └── skills/
            ├── using-kata/SKILL.md
            ├── design/SKILL.md
            ├── plan/SKILL.md
            ├── execute/
            │   ├── SKILL.md
            │   └── references/
            │       ├── implementer-prompt.md
            │       └── task-reviewer-prompt.md
            ├── tdd/
            │   ├── SKILL.md
            │   └── references/testing-anti-patterns.md
            ├── debug/SKILL.md
            ├── verify-done/SKILL.md
            ├── request-review/
            │   ├── SKILL.md
            │   └── references/code-reviewer-prompt.md
            ├── finish/SKILL.md
            └── parallel/SKILL.md
```

リポジトリ名は `claude-plugins` であり、将来 kata 以外のプラグインを追加できる構成とする。

## 導入と運用

- 導入: `/plugin marketplace add <Git URL またはローカルパス>` → `/plugin install kata`。職場ではローカルパス指定（clone 済みディレクトリ）でも導入できる。
- ディスパッチャー（using-kata）の発動方法は 2 段階で README に記載する。
  1. **基本: CLAUDE.md 方式。**「タスク開始前に kata:using-kata に従う」の1行を CLAUDE.md に追記する。コード実行ゼロ。
  2. **任意: 自作 SessionStart フック方式。** 利用者が自分の settings.json に書く手順のみを README に記載する（プラグインにはフックを同梱しない）。発動の強制力が高い。自作の1行であり第三者コードの自動実行ではないため、サプライチェーン懸念とは別物である旨を明記する。

## ライセンスと帰属

エッセンス抽出の書き直しでも、原典のプロセス設計に依拠する以上は派生物と解釈される余地がある。原典は MIT License なので、README に原典（obra/superpowers, Jesse Vincent, MIT License）へのクレジットを明記することで完全にクリーンにする。これは「superpowers そのものの再配布ではない」ことの説明にもなる。

## 既知のリスク

- 書き直しにより、原典が実戦で調整してきた細かい文言の効きが落ちる可能性がある。使いながら調整する前提とする。
- 統合した execute は原典 3 スキル分の責務を持つため肥大しやすい。references/ への分離で本文を抑える。
- 短縮名により原典との対応が一目で分からなくなる。設計書・README の対応表で補う。
- ビルトインスキル（/code-review、verify）やネイティブツール（AskUserQuestion、EnterWorktree 等）は環境・バージョンによって存在しない可能性がある。フォールバック記述で吸収する。
- 職場ポリシーが「内容の如何を問わず superpowers 由来物は不可」という趣旨の場合、この方針でも解決しない。導入前に職場での確認が必要。

## テスト・検証方針

- 各 SKILL.md が Claude Code のスキル形式（frontmatter に name / description）として妥当であることを確認する。
- `/plugin marketplace add`（ローカルパス）→ `/plugin install kata` で導入し、`/kata:design` 等の呼び出しと自動発動（description マッチ）を実際のセッションで確認する。
- スキル間の相互参照（`kata:<skill-name>`）に参照切れがないことを確認する。
