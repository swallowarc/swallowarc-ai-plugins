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
| `book-summary-html` | `/swallowarc:book-summary-html` | 本の読書メモ素材（mindmap・memo・本文）から、要点をまとめた HTML サマリーサイト（書誌情報つき index ＋ 章/部ページ）を生成する。 |

## 新しいスキルの追加手順

1. `plugins/swallowarc/skills/<skill-name>/SKILL.md` を作成する。
   - frontmatter に `name` と `description` を記述（`description` は三人称で "Use when ..." 始まり、トリガー条件のみを書く）。
2. 必要なら同ディレクトリに `references/`・`assets/`・`templates/` などの補助ファイルを置く。
3. `plugin.json` の `version` を更新する（任意。省略時は git commit SHA がバージョンになる）。
4. このリポジトリを push し、利用側で `/plugin marketplace update swallowarc-ai-plugins` を実行する。
   - 追加したスキルは `/swallowarc:<skill-name>` で利用可能になる。
