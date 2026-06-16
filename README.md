# swallowarc-ai-plugins

AI エージェント向けプラグイン管理・配布リポジトリ。
Claude Code の[プラグインマーケットプレイス](https://code.claude.com/docs/en/plugin-marketplaces)として機能する。

スキルは単一プラグイン **`swallowarc`** に集約し、`/swallowarc:<skill-name>` で呼び出す。
新しいスキルが必要になったら、このプラグインに追加していく。

## リポジトリ構成

```
.
├── .claude-plugin/
│   └── marketplace.json              # マーケットプレイス定義（配布プラグイン一覧）
└── plugins/
    └── swallowarc/                   # スキル集約プラグイン（呼び出し名前空間 = swallowarc）
        ├── .claude-plugin/
        │   └── plugin.json           # プラグイン manifest（name: swallowarc）
        └── skills/
            └── book-summary-html/
                └── SKILL.md          # スキル本体 → /swallowarc:book-summary-html
```

> **名前空間の注意:** スキルの呼び出し名 `/<prefix>:<skill>` の `<prefix>` は **プラグイン名（plugin.json の `name`）** で決まる。
> `/swallowarc:...` で呼ぶため、プラグイン名は `swallowarc` にしている（マーケットプレイス名 `swallowarc-ai-plugins` とは別物）。

## 利用方法（Claude Code）

このマーケットプレイスを追加する:

```
/plugin marketplace add swallowarc/swallowarc-ai-plugins
```

> ローカルで試す場合: `/plugin marketplace add /Users/acrobat.kame/IdeaProjects/swallowarc-ai-plugins`

プラグインをインストールする:

```
/plugin install swallowarc@swallowarc-ai-plugins
```

インストール後、収録スキルは `/swallowarc:<skill-name>` で呼び出せる（例: `/swallowarc:book-summary-html`）。

更新・削除:

```
/plugin marketplace update swallowarc-ai-plugins
/plugin marketplace remove swallowarc-ai-plugins
```

## 収録スキル（plugin: swallowarc）

| スキル | 呼び出し | 説明 |
| --- | --- | --- |
| `book-summary-html` | `/swallowarc:book-summary-html` | 本の要点をまとめた HTML サマリーサイト（書誌情報つき index ＋ 章/部ページ）を生成する。元情報は基本 Web リサーチ（WebSearch / WebFetch）で集め、PDF など本文ファイルがある場合のみ引数で渡してそれを主ソースにする。 |
| `infographic-prompt` | `/swallowarc:infographic-prompt` | 概念・文書・本の要点を「手描きホワイトボード解説風の1枚絵インフォグラフィック」にするための画像生成プロンプトを作る。Nano Banana Pro（Gemini 3 Pro Image）や GPT Image 2 などの画像モデル向け。 |

## バージョン更新ルール（必須）

スキルを**追加・更新したら、必ず `plugin.json` の `version` をインクリメントすること。**
`plugin.json` は `plugins/swallowarc/.claude-plugin/plugin.json` にある（Semantic Versioning）。

> **なぜ必須か:** バージョンを上げないと、利用側で `/plugin marketplace update` を実行しても**変更が取り込み対象にならず**、古いスキルのまま使われてしまう。「任意」ではなく必須。

| 変更内容 | 上げるバージョン | 例 |
| --- | --- | --- |
| スキルの**追加**（新しい SKILL.md／新ディレクトリ） | **マイナー** をインクリメント | `0.2.1` → `0.3.0` |
| 既存スキルの**更新のみ**（中身の修正・補助ファイル変更） | **パッチ** をインクリメント | `0.2.1` → `0.2.2` |

複数の変更が混在する場合は、より大きい方（追加が含まれればマイナー）を優先する。

## 新しいスキルの追加手順

1. `plugins/swallowarc/skills/<skill-name>/SKILL.md` を作成する。
   - frontmatter に `name` と `description` を記述（`description` は三人称で "Use when ..." 始まり、トリガー条件のみを書く）。
2. 必要なら同ディレクトリに `references/`・`assets/`・`templates/` などの補助ファイルを置く。
3. **README.md の「収録スキル」表を更新する**（追加したスキルを 1 行追記）。
4. **`plugin.json` の `version` を更新する**（上記「バージョン更新ルール」に従う。追加=マイナー）。
5. このリポジトリを push し、利用側で `/plugin marketplace update swallowarc-ai-plugins` を実行する。
   - 追加したスキルは `/swallowarc:<skill-name>` で利用可能になる。

## 自動化（Claude Code フック）

`.claude/settings.json` に `PostToolUse` フックを設定済み。
スキルの `SKILL.md`（`plugins/swallowarc/skills/*/SKILL.md`）を Write/Edit すると、
**「README.md の最新化」と「plugin.json のバージョン更新（追加=マイナー／更新のみ=パッチ）」をリマインド**する。
作業の取りこぼしを防ぐためのもので、フック自体はファイルを書き換えない（リマインドのみ）。

構成:

- `.claude/settings.json` … フックの宣言（イベント `PostToolUse` ／ matcher `Write|Edit`）のみ。
- `.claude/hooks/skill-changed.sh` … 実際の判定・リマインド文を出力するスクリプト本体。
  `${CLAUDE_PROJECT_DIR}` 経由で参照される（stdin に渡る JSON の `file_path` を見て、SKILL.md のときだけリマインドを返す）。

> フックは Markdown では宣言できない（スキル/コマンドと違い自動ロードされない）。
> イベント・matcher の宣言は settings.json の JSON に書く必要があり、ロジックだけを外部スクリプトに切り出している。
