# kata

開発プロセスに規律を与えるスキル集。
[obra/superpowers](https://github.com/obra/superpowers)（Jesse Vincent, MIT License）のプロセス設計のエッセンスを、Claude Code 専用、日本語、Markdown のみ（実行可能コードなし）で再構成したものである。
原典そのものの再配布ではない。

## インストール

```
/plugin marketplace add swallowarc/swallowarc-ai-plugins
/plugin install kata@swallowarc-ai-plugins
```

収録スキルは `/kata:<スキル名>` で呼び出す（例：`/kata:design`）。

## 収録スキル

| スキル | 原典（superpowers） | 説明 |
| --- | --- | --- |
| `design` | brainstorming | 対話で要件→設計→spec 文書化。実装前の必須ゲート |
| `plan` | writing-plans | spec から実装プランを作成 |
| `execute` | executing-plans + subagent-driven-development + using-git-worktrees | プランの実行。worktree 分離と実行モード（自走／サブエージェント駆動〔直列・wave 並列〕）を内包 |
| `tdd` | test-driven-development | RED→GREEN→REFACTOR の強制 |
| `debug` | systematic-debugging | 4 フェーズの根本原因調査。修正提案前の必須ゲート |
| `verify-done` | verification-before-completion | 完了宣言前の検証実行を義務化 |
| `request-review` | requesting-code-review | spec とプランへの適合性のコードレビュー依頼 |
| `finish` | finishing-a-development-branch | 完了後のマージ、PR 作成、クリーンアップの構造化 |
| `parallel` | dispatching-parallel-agents | プランなしの独立タスクの並列サブエージェント分配 |
| `using-kata` | using-superpowers | 入口。タスク開始前のスキル該当チェックを義務付けるディスパッチャー |

基本フローは `design` → `plan` → `execute` → `finish`。
実装中は `tdd`、`request-review`、`verify-done` が横断ゲートとして入る。
バグ対応は `debug` から始める。

## ディスパッチャー（using-kata）の有効化

スキルの自動発動を安定させるには、以下のいずれかを設定する。

1. **基本の CLAUDE.md 方式（コード実行ゼロ）**：CLAUDE.md に 1 行追記する。

   ```
   タスク開始前に kata:using-kata スキルの指示に従うこと。
   ```

2. **任意の SessionStart フック方式（発動の強制力が高い）**：kata プラグインはフックを同梱しない。
   以下は利用者が自分の settings.json に書く設定であり、第三者コードの自動実行ではない。

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
