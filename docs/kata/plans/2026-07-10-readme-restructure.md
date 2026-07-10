# README.md 2 部構成再編 実装計画

> **For agentic workers:** 本プランの実行には `kata:execute` が必須のサブスキルである。タスクは `- [ ]` のチェックボックスで進捗を追跡する。

**Goal:** README.md を「利用ガイド → 開発ガイド → ライセンス」の 2 部構成に再編し、承認済み spec（`docs/kata/specs/2026-07-10-readme-restructure-design.md`）が定める文言修正 4 点を適用する。

**Architecture:** README.md 1 ファイルの全置換で実現する。新しい本文はこのプランに完全な形で埋め込み済みであり、実装者は Step 1 の内容をそのまま書き込めばよい。ドキュメントのみの変更のためテストコードは書かず、TDD のテストサイクルの代わりに spec の検証方針 3 点（見出し構成・内部アンカーリンク・言及パスの実在）をコマンドで確認するステップを置く。

**Tech Stack:** Markdown（GitHub Flavored）、git、grep/ls（検証用）

## Global Constraints

- 変更は spec に列挙された内容に限る。全面書き直しはしない（spec「作業範囲は並べ替え＋文言修正」）
- README のみの変更のため **plugin.json の `version` 更新は不要**（バージョン更新ルールの対象はスキル変更のみ）
- CONTRIBUTING.md の新設、SKILL.md・marketplace.json・フックスクリプトの変更は行わない
- 想定読者は GitHub でこのリポジトリを見つけた第三者を含む。個人環境依存の記述（`/Users/acrobat.kame/...`）を残さない
- ライセンス関連の記述（MIT、obra/superpowers 由来の明示）は内容を変えずに維持する

---

### Task 1: README.md を 2 部構成へ書き換える

**Files:**
- Modify: `README.md`（全置換）

**Interfaces:**
- Consumes: なし（依存タスクなし）
- Produces: なし（後続タスクなし。成果物は README.md 本文のみ）

- [ ] **Step 1: README.md を以下の内容で全置換する**

以下が新しい README.md の全文である。省略箇所はない。

````markdown
# swallowarc-ai-plugins

AI エージェント向けプラグイン管理・配布リポジトリ。
Claude Code の[プラグインマーケットプレイス](https://code.claude.com/docs/en/plugin-marketplaces)として機能する。

配布プラグインは 2 つ:

- **`swallowarc`** — 個人用の汎用スキル集。`/swallowarc:<skill-name>` で呼び出す。
- **`kata`** — 開発プロセスに規律を与えるスキル集（設計→プラン→実行のワークフローと横断ゲート）。`/kata:<skill-name>` で呼び出す。

## 利用ガイド

### インストール

このマーケットプレイスを追加する:

```
/plugin marketplace add swallowarc/swallowarc-ai-plugins
```

> ローカルで試す場合: `/plugin marketplace add <リポジトリをクローンしたローカルパス>`

プラグインをインストールする（必要なものだけでよい）:

```
/plugin install swallowarc@swallowarc-ai-plugins
/plugin install kata@swallowarc-ai-plugins
```

インストール後、収録スキルは `/swallowarc:<skill-name>`・`/kata:<skill-name>` で呼び出せる（例: `/swallowarc:book-summary-html`、`/kata:design`）。

### 収録スキル（swallowarc）

| スキル | 呼び出し | 説明 |
| --- | --- | --- |
| `book-summary-html` | `/swallowarc:book-summary-html` | 本の要点をまとめた HTML サマリーサイト（書誌情報つき index ＋ 章/部ページ）を生成する。元情報は Web リサーチで集め、PDF など本文ファイルがあれば引数で渡してそれを主ソースにできる（モード等の詳細はスキル本体を参照）。 |
| `infographic-prompt` | `/swallowarc:infographic-prompt` | 概念・文書・本の要点を「手描きホワイトボード解説風の1枚絵インフォグラフィック」にするための画像生成プロンプトを作る。Nano Banana Pro（Gemini 3 Pro Image）や GPT Image 2 などの画像モデル向け。 |

### 収録スキル（kata）

開発プロセスに規律を与えるスキル集。[obra/superpowers](https://github.com/obra/superpowers)（Jesse Vincent, MIT License）のプロセス設計のエッセンスを、Claude Code 専用・日本語・**Markdown のみ（実行可能コードなし）** で再構成したもの。

| スキル | 原典（superpowers） | 説明 |
| --- | --- | --- |
| `design` | brainstorming | 対話で要件→設計→spec 文書化。実装前の必須ゲート |
| `plan` | writing-plans | spec から実装プランを作成 |
| `execute` | executing-plans + subagent-driven-development + using-git-worktrees | プランの実行。worktree 分離と実行モード（自走／サブエージェント駆動）を内包 |
| `tdd` | test-driven-development | RED→GREEN→REFACTOR の強制 |
| `debug` | systematic-debugging | 4 フェーズの根本原因調査。修正提案前の必須ゲート |
| `verify-done` | verification-before-completion | 完了宣言前の検証実行を義務化 |
| `request-review` | requesting-code-review | spec・プラン適合性のコードレビュー依頼 |
| `finish` | finishing-a-development-branch | 完了後のマージ/PR/クリーンアップの構造化 |
| `parallel` | dispatching-parallel-agents | 独立タスクの並列サブエージェント分配 |
| `using-kata` | using-superpowers | 入口。タスク開始前のスキル該当チェックを義務付けるディスパッチャー |

基本フロー: `design` → `plan` → `execute` →（実装中に `tdd`・`request-review`・`verify-done`）→ `finish`。バグ対応は `debug` から。

### ディスパッチャー（using-kata）の有効化

スキルの自動発動を安定させるには、以下のいずれかを設定する。

1. **基本: CLAUDE.md 方式（コード実行ゼロ）** — CLAUDE.md に 1 行追記する:

   ```
   タスク開始前に kata:using-kata スキルの指示に従うこと。
   ```

2. **任意: 自作 SessionStart フック方式（発動の強制力が高い）** — kata プラグインはフックを**同梱しない**。以下は利用者が自分の settings.json に書く設定であり、第三者コードの自動実行ではない:

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

### 更新・削除

```
/plugin marketplace update swallowarc-ai-plugins
/plugin marketplace remove swallowarc-ai-plugins
```

## 開発ガイド

### リポジトリ構成

```
.
├── .claude-plugin/
│   └── marketplace.json              # マーケットプレイス定義（配布プラグイン一覧）
└── plugins/
    ├── swallowarc/                   # 汎用スキル集約プラグイン（呼び出し名前空間 = swallowarc）
    └── kata/                         # 開発プロセス規律プラグイン（呼び出し名前空間 = kata）
```

新しい単発スキルは `swallowarc` プラグインに追加していく（開発プロセス系は `kata`）。

> **名前空間の注意:** スキルの呼び出し名 `/<prefix>:<skill>` の `<prefix>` は **プラグイン名（plugin.json の `name`）** で決まる。
> `/swallowarc:...` で呼ぶため、プラグイン名は `swallowarc` にしている（マーケットプレイス名 `swallowarc-ai-plugins` とは別物）。

### 新しいスキルの追加手順

1. `plugins/<plugin-name>/skills/<skill-name>/SKILL.md` を作成する（汎用スキルは `swallowarc`、開発プロセス系は `kata`）。
   - frontmatter に `name` と `description` を記述（`description` は日本語で「〜のときに使う」形式で始め、トリガー条件のみを書く）。
2. 必要なら同ディレクトリに `references/`・`assets/`・`templates/` などの補助ファイルを置く。
3. **README.md の「収録スキル」表を更新する**（追加したスキルを 1 行追記）。
4. **該当プラグインの `plugin.json` の `version` を更新する**（[バージョン更新ルール（必須）](#バージョン更新ルール必須)に従う。追加=マイナー）。
5. このリポジトリを push し、利用側で `/plugin marketplace update swallowarc-ai-plugins` を実行する。
   - 追加したスキルは `/<plugin-name>:<skill-name>` で利用可能になる。

### バージョン更新ルール（必須）

スキルを**追加・更新したら、必ず該当プラグインの `plugin.json` の `version` をインクリメントすること。**
`plugin.json` は `plugins/<plugin-name>/.claude-plugin/plugin.json` にある（Semantic Versioning）。

> **なぜ必須か:** バージョンを上げないと、利用側で `/plugin marketplace update` を実行しても**変更が取り込み対象にならず**、古いスキルのまま使われてしまう。「任意」ではなく必須。

| 変更内容 | 上げるバージョン | 例 |
| --- | --- | --- |
| スキルの**追加**（新しい SKILL.md／新ディレクトリ） | **マイナー** をインクリメント | `0.2.1` → `0.3.0` |
| 既存スキルの**更新のみ**（中身の修正・補助ファイル変更） | **パッチ** をインクリメント | `0.2.1` → `0.2.2` |

複数の変更が混在する場合は、より大きい方（追加が含まれればマイナー）を優先する。

### 自動化（Claude Code フック）

`.claude/settings.json` に `PostToolUse` フックを設定済み。
スキルの `SKILL.md`（`plugins/*/skills/*/SKILL.md`）を Write/Edit すると、
**「README.md の最新化」と「plugin.json のバージョン更新（追加=マイナー／更新のみ=パッチ）」をリマインド**する。
作業の取りこぼしを防ぐためのもので、フック自体はファイルを書き換えない（リマインドのみ）。

構成:

- `.claude/settings.json` … フックの宣言（イベント `PostToolUse` ／ matcher `Write|Edit`）のみ。
- `.claude/hooks/skill-changed.sh` … 実際の判定・リマインド文を出力するスクリプト本体。
  `${CLAUDE_PROJECT_DIR}` 経由で参照される（stdin に渡る JSON の `file_path` を見て、SKILL.md のときだけリマインドを返す）。

> フックは Markdown では宣言できない（スキル/コマンドと違い自動ロードされない）。
> イベント・matcher の宣言は settings.json の JSON に書く必要があり、ロジックだけを外部スクリプトに切り出している。

## ライセンス

本リポジトリは MIT License（`LICENSE` 参照）。
kata プラグインは [obra/superpowers](https://github.com/obra/superpowers)（Copyright Jesse Vincent, MIT License）のプロセス設計に基づく再構成であり、原典そのものの再配布ではない。
````

- [ ] **Step 2: 見出し構成を検証する**

Run: `grep -E '^#{1,3} ' README.md`
Expected: 次の見出しがこの順で出力される（それ以外の見出しがないこと）。

```
# swallowarc-ai-plugins
## 利用ガイド
### インストール
### 収録スキル（swallowarc）
### 収録スキル（kata）
### ディスパッチャー（using-kata）の有効化
### 更新・削除
## 開発ガイド
### リポジトリ構成
### 新しいスキルの追加手順
### バージョン更新ルール（必須）
### 自動化（Claude Code フック）
## ライセンス
```

- [ ] **Step 3: 内部アンカーリンクを検証する**

Run: `grep -n 'バージョン更新ルール（必須）' README.md`
Expected: 見出し行 `### バージョン更新ルール（必須）` と、追加手順ステップ 4 のリンク `[バージョン更新ルール（必須）](#バージョン更新ルール必須)` の 2 箇所がヒットする。
GitHub のアンカー生成規則（約物を除去し空白をハイフン化）により、見出し `### バージョン更新ルール（必須）` のアンカーは `#バージョン更新ルール必須` になるため、リンク先表記と一致していることを目視確認する。

- [ ] **Step 4: 言及パスの実在を確認する**

Run: `ls .claude/settings.json .claude/hooks/skill-changed.sh .claude-plugin/marketplace.json plugins/swallowarc plugins/kata LICENSE`
Expected: すべてのパスがエラーなく列挙される（`No such file or directory` が出ないこと）。

- [ ] **Step 5: stale 記述・個人パスが残っていないことを確認する**

Run: `grep -n -e 'docs/kata/specs' -e '/Users/acrobat.kame' -e '新しい単発スキルはここに追加' README.md || echo CLEAN`
Expected: `CLEAN`（削除・汎用化・移動の対象とした 3 つの記述が README に残っていない）。

- [ ] **Step 6: コミットする**

```bash
git add README.md
git commit -m "docs: README を利用ガイド→開発ガイドの2部構成に再編"
```
