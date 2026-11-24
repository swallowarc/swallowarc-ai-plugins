---
name: prune
description: ユーザーが /teire:prune と明示的に呼んだとき、または default ブランチ以外のローカルブランチや worktree を一括で掃除するよう依頼したときに使う。削除対象を一覧で示して確認を取ってから、同梱の prune.sh で削除する
model: haiku
---

# prune（ローカルブランチと worktree の掃除）

## 概要

default ブランチ以外のローカルブランチと linked worktree を削除する。
判定と削除はこのスキルと同じディレクトリにある `prune.sh` が行う。
自分で `git branch -D` や `git worktree remove` を組み立てない。

ローカルブランチの内容は一切更新しない。
`git fetch`・`git pull`・`git merge`・`git rebase`・`git reset`・`git checkout`／`git switch` は実行しない。default ブランチも古いままでよい。

## 手順

1. 対象リポジトリのルートで `bash <このスキルのディレクトリ>/prune.sh plan` を実行する。
   何も変更しないコマンドである。
2. 出力をそのまま（省略・要約せず）ユーザーに見せる。
   `⚠` の付いた行（未コミット変更、未 push コミット）があれば、その件数を本文で繰り返し、削除すると戻せないことを明記する。
   「削除対象はありません。」なら、そこで終える。
3. 削除してよいかを確認する。
   AskUserQuestion が使えるなら、質問文に削除対象の件数と `⚠` の件数を入れる（ダイアログの外の本文が読まれない環境があるため）。
   明確な同意がなければ削除しない。
4. 同意が得られたら、plan の出力にあった plan id を渡して `bash <このスキルのディレクトリ>/prune.sh apply <plan id>` を実行する。
   plan id が一致しないと拒否される。拒否されたら手順 1 からやり直し、新しい一覧で再度確認する。
5. apply の出力をそのまま報告する。
   `deleted branch: <name> (was <sha>)` の sha は、誤って消したときに `git branch <name> <sha>` で戻すための手がかりなので省かない。
   `FAILED` があれば、その行と原因を報告する。自分で強制的に再試行しない。

## スクリプトが残すもの

- default ブランチ（`origin/HEAD`、なければ main／master）
- いま作業している worktree と、そのブランチ
- メイン worktree でチェックアウト中のブランチ（切り替えないため削除できない）
- locked の worktree と、そのブランチ

残したものは plan の「残すもの」に出る。
これらを消すために lock の解除やブランチの切り替えを提案・実行しない。必要ならユーザーが自分で行う。

## Red Flags

- plan の出力を見せずに apply する
- `⚠` の件数を伝えずに確認を取る
- 削除前に fetch や pull で「最新化」する
- スクリプトを使わず git コマンドを手で組み立てて削除する
- 失敗した削除を `--force` などで勝手にやり直す
