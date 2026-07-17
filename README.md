# swallowarc-ai-plugins

AI エージェント向けプラグインの管理と配布のためのリポジトリ。
Claude Code の[プラグインマーケットプレイス](https://code.claude.com/docs/en/plugin-marketplaces)として機能する。

## 配布プラグイン

使い方の詳細は各プラグインの README に書いてある。

| プラグイン | 説明 | ドキュメント |
| --- | --- | --- |
| `shoroku` | 書籍の要約作成に特化したスキル集。本の要点まとめサイトの生成と、手描き風説明画像のプロンプト生成を収録する（旧称 swallowarc） | [plugins/shoroku](plugins/shoroku/README.md) |
| `kata` | 開発プロセスに規律を与えるスキル集。設計→プラン→実行のワークフローと、TDD やデバッグなどの横断ゲートを提供する | [plugins/kata](plugins/kata/README.md) |
| `buntai` | 日本語の文体規範のスキル集。k16shikano 氏公開の文章規範を収録する | [plugins/buntai](plugins/buntai/README.md) |

## インストール

このマーケットプレイスを追加する。

```
/plugin marketplace add swallowarc/swallowarc-ai-plugins
```

ローカルで試す場合は、リポジトリをクローンしたローカルパスを指定する。

必要なプラグインだけをインストールする。

```
/plugin install shoroku@swallowarc-ai-plugins
/plugin install kata@swallowarc-ai-plugins
/plugin install buntai@swallowarc-ai-plugins
```

インストール後、収録スキルは `/<プラグイン名>:<スキル名>` で呼び出せる（例：`/kata:design`、`/shoroku:book-summary-html`）。

## 更新と削除

```
/plugin marketplace update swallowarc-ai-plugins
/plugin marketplace remove swallowarc-ai-plugins
```

## 開発

リポジトリ構成、スキルの追加手順、バージョン更新ルールは [CONTRIBUTING.md](CONTRIBUTING.md) に書いてある。

## ライセンス

本リポジトリは MIT License（`LICENSE` 参照）。
由来を持つプラグインが 2 つある。
kata は [obra/superpowers](https://github.com/obra/superpowers)（Jesse Vincent, MIT License）のプロセス設計に基づく再構成であり、原典そのものの再配布ではない。
buntai の収録スキル本文は k16shikano 氏の著作であり、原典のライセンスは Unlicense である。
詳細は各プラグインの README を参照。
