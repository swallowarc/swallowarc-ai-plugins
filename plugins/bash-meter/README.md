# bash-meter

Bash の実行時間と失敗を、トランスクリプトに表示する mod。
スキルではなく、Claude Code の表示を変える hooks モジュールである。

## インストール

```
/plugin marketplace add swallowarc/swallowarc-ai-plugins
/plugin install bash-meter@swallowarc-ai-plugins
```

インストールすると、そのセッションから有効になる。
設定やコマンドはない。

## 表示内容

Claude Code は連続するツール呼び出しを 1 行にまとめて表示する。
bash-meter は、そのまとめ行の下に Bash の計測結果を出す。

```
Listed 1 directory, ran 3 shell commands
⏱ 4 bash · 4.2s · slowest 3.1s (sleep 3; echo slow)
✗ exit 2 · 46ms · ls /nonexistent-path
```

- 1 行目は、まとまり内の Bash の件数と合計時間である。
  2 件以上あり、最長が 1 秒以上のときは、いちばん遅いコマンドも出す。
- 2 行目以降は、失敗したコマンドごとの終了コード、時間、コマンドである。

詳細表示（ctrl+o）のように Bash が 1 件ずつ並ぶ画面では、各行の右横に時間を出す。
失敗時は `✗ exit N · 時間`、バックグラウンド実行は `→ background` になる。

## 計測の仕様と制約

- 時間は、エンジンが報告するコマンド本体の実行時間である。
  権限チェックとフックの時間は含まない。
- エンジンの値が取れなかった呼び出しでは、呼び出し全体の時間を出す。
  この場合は権限チェックとフックの時間を含むので、長めの数字になる。
- Bash の結果に終了コードの項目はないので、エラー文中の `Exit code N` から読み取る。
  読み取れない失敗は `failed` と表示する。
- バックグラウンド実行のコマンドは、完了までの時間を計測しない。
- サブエージェント内の Bash も計測するが、その行が画面に出ない場合は表示されない。

## 前提

mod の API は early access であり、Claude Code のバージョンによって変わる。
作成時のバージョンは 2.1.322 で、それより古いバージョンや大きく離れたバージョンでは動かない可能性がある。
読み込みに失敗した場合は、`claude --debug` のログに理由が出る。
