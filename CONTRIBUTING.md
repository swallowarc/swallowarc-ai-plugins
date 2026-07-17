# 開発ガイド

このリポジトリのプラグインとスキルを追加、更新するときの手順とルール。
プラグインの利用方法は [README.md](README.md) と各プラグインの README に書いてある。

## リポジトリ構成

```
.
├── .claude-plugin/
│   └── marketplace.json              # マーケットプレイス定義（配布プラグイン一覧）
└── plugins/
    ├── shoroku/                      # 書籍要約プラグイン（呼び出し名前空間 = shoroku）
    ├── kata/                         # 開発プロセス規律プラグイン（呼び出し名前空間 = kata）
    └── buntai/                       # 日本語文体規範プラグイン（呼び出し名前空間 = buntai）
```

新しいスキルは主題が合う既存プラグインに追加する（書籍要約系は `shoroku`、開発プロセス系は `kata`）。
合うプラグインがなければ、主題が名前に表れる新しいプラグインを作る。

スキルの呼び出し名 `/<prefix>:<skill>` の `<prefix>` は、マーケットプレイス名ではなく**プラグイン名（plugin.json の `name`）**で決まる（マーケットプレイス名 `swallowarc-ai-plugins` とは別物）。

## 新しいスキルの追加手順

1. `plugins/<plugin-name>/skills/<skill-name>/SKILL.md` を作成する。
   frontmatter に `name` と `description` を記述する（`description` は日本語で「〜のときに使う」形式で始め、トリガー条件のみを書く）。
2. 必要なら同ディレクトリに `references/`、`assets/`、`templates/` などの補助ファイルを置く。
3. **該当プラグインの README.md の収録スキルの説明を更新する**（利用者向けドキュメントは各プラグインの README に置く）。
4. **該当プラグインの `plugin.json` の `version` を更新する**（下記のバージョン更新ルールに従う。追加はマイナー）。
5. このリポジトリを push し、利用側で `/plugin marketplace update swallowarc-ai-plugins` を実行する。
   追加したスキルは `/<plugin-name>:<skill-name>` で利用可能になる。

新しいプラグインを追加するときは、上記に加えて次を行う。

- `plugins/<plugin-name>/.claude-plugin/plugin.json` と `plugins/<plugin-name>/README.md` を作成する
- `.claude-plugin/marketplace.json` の `plugins` にエントリを追加する
- ルート README.md の配布プラグイン表に 1 行追記する

## プラグインの改名と削除

プラグイン名は利用者の設定（`enabledPlugins`）に入る安定識別子なので、改名は破壊的変更である。
改名または削除をしたら、`.claude-plugin/marketplace.json` の `renames` に「旧名→新名」（削除は `null`）を追記する。
Claude Code v2.1.193 以降の利用者は、起動時に設定が自動で書き換わり移行される。
`renames` は履歴なので追記のみとし、既存エントリの書き換えや削除はしない（改名の連鎖は追える）。
編集後は `claude plugin validate .` で循環や宙ぶらりんの参照がないことを検証する。

## バージョン更新ルール（必須）

スキルを**追加、更新したら、必ず該当プラグインの `plugin.json` の `version` をインクリメントすること。**
`plugin.json` は `plugins/<plugin-name>/.claude-plugin/plugin.json` にある（Semantic Versioning）。

バージョンを上げないと、利用側で `/plugin marketplace update` を実行しても**変更が取り込み対象にならず**、古いスキルのまま使われてしまう。
「任意」ではなく必須である。

| 変更内容 | 上げるバージョン | 例 |
| --- | --- | --- |
| スキルの**追加**（新しい SKILL.md、新ディレクトリ） | **マイナー** をインクリメント | `0.2.1` → `0.3.0` |
| 既存スキルの**更新のみ**（中身の修正、補助ファイルや README の変更） | **パッチ** をインクリメント | `0.2.1` → `0.2.2` |

複数の変更が混在する場合は、より大きい方（追加が含まれればマイナー）を優先する。

## 自動化（Claude Code フック）

`.claude/settings.json` に `PostToolUse` フックを設定済み。
スキルの `SKILL.md`（`plugins/*/skills/*/SKILL.md`）を Write/Edit すると、**「README の最新化」と「plugin.json のバージョン更新」をリマインド**する。
作業の取りこぼしを防ぐためのもので、フック自体はファイルを書き換えない（リマインドのみ）。

構成は次の 2 ファイルからなる。

- `.claude/settings.json`：フックの宣言（イベント `PostToolUse`、matcher `Write|Edit`）のみ
- `.claude/hooks/skill-changed.sh`：実際の判定とリマインド文を出力するスクリプト本体。
  `${CLAUDE_PROJECT_DIR}` 経由で参照される（stdin に渡る JSON の `file_path` を見て、SKILL.md のときだけリマインドを返す）

フックは Markdown では宣言できない（スキルやコマンドと違い自動ロードされない）。
イベントと matcher の宣言は settings.json の JSON に書く必要があり、ロジックだけを外部スクリプトに切り出している。
