# teire

ローカル開発環境の手入れ（保守）のスキル集。

## インストール

```
/plugin marketplace add swallowarc/swallowarc-ai-plugins
/plugin install teire@swallowarc-ai-plugins
```

収録スキルは `/teire:<スキル名>` で呼び出す。

## 収録スキル

### branch-prune

default ブランチ以外のローカルブランチと linked worktree を一括で削除する。

```
/teire:branch-prune
```

削除対象を一覧で示し、確認を取ってから削除する。
未コミット変更のある worktree や未 push コミットのあるブランチも削除対象に含め、一覧に `⚠` 付きで件数を出す。
削除は `git branch -D` と `git worktree remove --force` で行うため、確認後は戻せない（ブランチは報告される sha から `git branch <name> <sha>` で復元できる）。

ローカルブランチは一切更新しない。
fetch・pull・checkout を行わないので、default ブランチも手元の状態のまま残る。
未 push の判定は、手元にある remote-tracking ref を基準にする。

次のものは削除しない。

- default ブランチ（`origin/HEAD`、なければ main／master）
- 実行中の worktree とそのブランチ
- メイン worktree でチェックアウト中のブランチ
- locked の worktree とそのブランチ

スキルは `model: haiku` で動く。
削除対象の判定は同梱の `branch-prune.sh` が行い、モデルは結果の提示と確認だけを担う。

スクリプトは単体でも使える。

```
bash skills/branch-prune/branch-prune.sh plan            # 対象の表示と plan id の発行（変更なし）
bash skills/branch-prune/branch-prune.sh apply <plan id> # plan id が一致するときだけ削除
```

### docker-prune

停止中の Docker コンテナと、稼働中のコンテナが使っていない Docker イメージを一括で削除する。

```
/teire:docker-prune
```

削除対象を一覧で示し、確認を取ってから削除する。
停止中のコンテナ（created／exited／dead）はすべて消え、それらだけが使っていたイメージも未使用として消える。
コンテナ内に書き込まれたデータは戻せず、消したイメージは再 pull か再ビルドが必要になる。
対象の Docker デーモンは現在の context で決まるため、一覧の先頭に context 名と接続先を出す。

削除は一覧に出した ID を `docker rm`／`docker rmi` で 1 件ずつ行い、`-f` は付けない。
一覧のあとに起動したコンテナやそのイメージは、Docker 側が削除を拒否して `FAILED` になる。

次のものは削除しない。

- 稼働中・一時停止中・再起動中のコンテナと、それらが使っているイメージ
- ボリューム（停止中コンテナの匿名ボリュームも残る）、ネットワーク、ビルドキャッシュ

スキルは `model: haiku` で動く。

```
bash skills/docker-prune/docker-prune.sh plan            # 対象の表示と plan id の発行（変更なし）
bash skills/docker-prune/docker-prune.sh apply <plan id> # plan id が一致するときだけ削除
```

## 前提

- `bash` を使う。
- branch-prune は `git`、docker-prune は `docker` を使う。
