#!/usr/bin/env bash
# PostToolUse フック: スキルの SKILL.md を Write/Edit したら、
# README.md の最新化と plugin.json のバージョン更新をリマインドする。
#
# 入力: stdin に Claude Code から PostToolUse の JSON が渡る
#       （.tool_input.file_path に編集対象パスが入る）
# 出力: 対象が SKILL.md のときだけ hookSpecificOutput.additionalContext を
#       stdout に JSON で返す。それ以外は無音（何も出力しない）。
# 注意: フック自体はファイルを書き換えない。リマインドのみ。
set -euo pipefail

file_path=$(jq -r '.tool_input.file_path // empty')

case "$file_path" in
  */plugins/*/skills/*/SKILL.md)
    plugin_name=$(printf '%s' "$file_path" | sed -E 's#.*/plugins/([^/]+)/skills/.*#\1#')
    jq -n --arg p "$plugin_name" '{
      hookSpecificOutput: {
        hookEventName: "PostToolUse",
        additionalContext: "スキル(SKILL.md)を変更しました。作業完了前に必ず: 1) README.md の収録スキル表を実態に合わせて最新化する、2) plugins/\($p)/.claude-plugin/plugin.json の version を更新する（新規スキル追加=マイナー、既存スキルの更新のみ=パッチ をインクリメント。バージョンを上げないと利用側 /plugin marketplace update に取り込まれません）。"
      }
    }'
    ;;
esac
