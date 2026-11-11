---
name: install
description: ユーザーが /statusline:install と明示的に呼んだとき、またはこのプラグインのステータスラインの導入や更新を依頼したときに使う。同梱の statusline.sh をユーザーの Claude Code 設定に導入する
---

# install（ステータスラインの導入）

## 概要

このスキルと同じディレクトリにある `statusline.sh` を、ユーザーの Claude Code のステータスラインとして導入する。
プラグインのインストール先はバージョンごとに変わるので、スクリプトは `~/.claude/` に複製して、設定からはその複製を参照する。

## 手順

1. `jq` が使えることを確かめる（`command -v jq`）。
   なければ導入できないので、`jq` のインストールが必要だと伝えて止める。
2. `~/.claude/statusline.sh` がすでにあるか確かめる。
   あって内容が同梱のものと違う場合は、上書きしてよいかをユーザーに確認する。
   同じ内容なら複製は省く。
3. このスキルのディレクトリにある `statusline.sh` を `~/.claude/statusline.sh` に複製し、実行権限を付ける（`chmod +x`）。
4. `~/.claude/settings.json` の `statusLine` を確かめる。
   すでに別のコマンドが設定されている場合は、置き換えてよいかをユーザーに確認する。
5. `statusLine` を次の値にする。
   ほかのキーは変えない。

   ```json
   "statusLine": {
     "type": "command",
     "command": "~/.claude/statusline.sh"
   }
   ```

6. 次のサンプル入力で動作を確かめ、出力をユーザーに見せる。

   ```sh
   echo '{"workspace":{"current_dir":"/tmp"},"model":{"display_name":"Model"},"effort":{"level":"high"},"context_window":{"used_percentage":42,"total_input_tokens":84000,"context_window_size":200000},"cost":{"total_cost_usd":1.23},"rate_limits":{"five_hour":{"used_percentage":64},"seven_day":{"used_percentage":91}}}' | ~/.claude/statusline.sh
   ```

## 守ること

- `settings.json` はユーザーの設定なので、`statusLine` 以外を書き換えない。
- 既存のスクリプトや設定を、確認なしに上書きしない。
- 導入後に表示が出ない場合は、`jq` の有無と `~/.claude/statusline.sh` の実行権限を先に確かめる。
