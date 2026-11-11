# statusline

Claude Code のステータスライン用スクリプトと、その導入スキルを収録したプラグイン。

## インストール

```
/plugin marketplace add swallowarc/swallowarc-ai-plugins
/plugin install statusline@swallowarc-ai-plugins
```

インストールしただけではステータスラインは変わらない。
続けて導入スキルを実行する。

```
/statusline:install
```

## 表示内容

```
📁 my-project │ ⎇ main │ 🤖 Model (high) │ ████░░░░░░ 42% 84.0k/200.0k │ $1.23 │ 5h 64% · 7d 91%
```

左から順に次を表示する。

- 作業ディレクトリ名
- git ブランチ（git リポジトリ内のときだけ）
- モデル名と effort
- コンテキスト使用率のバーと割合、使用トークン数とウィンドウサイズ
- セッションの費用（USD）
- 5 時間と 7 日のレート制限の使用率

使用率は 60% 未満が緑、60% 以上が黄、80% 以上が赤になる。
入力に含まれない項目は、区切りごと省略する。
レート制限はサブスクリプション利用時にだけ出る。

## 収録スキル

### install

同梱の `statusline.sh` を `~/.claude/statusline.sh` に複製し、`~/.claude/settings.json` の `statusLine` をそのスクリプトに向ける。
既存のスクリプトや設定がある場合は、上書きの前に確認する。

```
/statusline:install
```

スクリプトを更新したときは、プラグインを更新してから同じスキルをもう一度実行する。

## 前提

- `jq` が必要である。
- POSIX シェル（`sh`）と `awk`、`sed`、`git` を使う。
- 端末の幅が狭いと、右側の項目から切れる。

## 手動での導入

スキルを使わない場合は、`skills/install/statusline.sh` を任意の場所に置いて実行権限を付け、`~/.claude/settings.json` に次を書く。

```json
"statusLine": {
  "type": "command",
  "command": "~/.claude/statusline.sh"
}
```
