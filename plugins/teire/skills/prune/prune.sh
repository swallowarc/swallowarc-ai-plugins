#!/usr/bin/env bash
# default ブランチ以外のローカルブランチと linked worktree を削除する。
#
#   prune.sh plan           削除対象を表示し、最後に plan id を出す（何も変更しない）
#   prune.sh apply <id>     plan id が現在の対象と一致するときだけ削除する
#
# ローカルブランチの内容は一切更新しない（fetch / pull / merge / checkout を行わない）。
# 未 push コミットの判定は、手元にある remote-tracking ref を基準にする。
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }

git rev-parse --git-dir >/dev/null 2>&1 || die "git リポジトリの中で実行してください"

# --- default ブランチの特定（ネットワークに出ない） ---
default=""
if ref=$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null); then
  default=${ref#origin/}
fi
if [ -z "$default" ]; then
  for b in main master; do
    if git show-ref -q --verify "refs/heads/$b"; then default=$b; break; fi
  done
fi
[ -n "$default" ] || die "default ブランチを特定できません（origin/HEAD も main / master もない）"
git show-ref -q --verify "refs/heads/$default" || die "default ブランチ '$default' がローカルにありません"

current_top=$(git rev-parse --show-toplevel)

# --- worktree 一覧を走査 ---
# 出力行: path<TAB>branch(空なら detached)<TAB>flags
wt_lines=()
main_path=""
path="" branch="" locked="" prunable=""
flush() {
  if [ -n "$path" ]; then
    if [ -z "$main_path" ]; then
      main_path=$path
    else
      wt_lines+=("$path"$'\t'"$branch"$'\t'"$locked$prunable")
    fi
  fi
  path="" branch="" locked="" prunable=""
}
while IFS= read -r line; do
  case "$line" in
    "worktree "*) flush; path=${line#worktree } ;;
    "branch refs/heads/"*) branch=${line#branch refs/heads/} ;;
    locked*) locked="locked," ;;
    prunable*) prunable="prunable," ;;
    "") flush ;;
  esac
done < <(git worktree list --porcelain)
flush

main_branch=$(git -C "$main_path" symbolic-ref -q --short HEAD 2>/dev/null || true)
current_branch=$(git symbolic-ref -q --short HEAD 2>/dev/null || true)

plan_lines=()
skip_lines=()
wt_remove=()      # 削除する worktree のパス
wt_prunable=0
keep_branches=" $default "   # 削除しないブランチ（空白区切り）

for entry in ${wt_lines[@]+"${wt_lines[@]}"}; do
  IFS=$'\t' read -r p b f <<<"$entry"
  label=${b:-"(detached)"}
  if [[ "$f" == *prunable* ]]; then
    wt_prunable=1
    plan_lines+=("worktree  $p  [$label]  ディレクトリ消失（prune）")
    continue
  fi
  if [ "$p" = "$current_top" ]; then
    skip_lines+=("worktree  $p  [$label]  現在いる worktree のため残す")
    [ -n "$b" ] && keep_branches+="$b "
    continue
  fi
  if [[ "$f" == *locked* ]]; then
    skip_lines+=("worktree  $p  [$label]  locked のため残す")
    [ -n "$b" ] && keep_branches+="$b "
    continue
  fi
  dirty=$(git -C "$p" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  note=""
  [ "$dirty" != "0" ] && note="  ⚠ 未コミット変更 ${dirty} 件"
  if [ -z "$b" ]; then
    unpushed=$(git -C "$p" rev-list --count HEAD --not --remotes "refs/heads/$default" 2>/dev/null || echo "?")
    [ "$unpushed" != "0" ] && note+="  ⚠ detached HEAD に未 push コミット ${unpushed} 件"
  fi
  wt_remove+=("$p")
  plan_lines+=("worktree  $p  [$label]$note")
done

[ -n "$main_branch" ] && [ "$main_branch" != "$default" ] && {
  skip_lines+=("branch    $main_branch  メイン worktree でチェックアウト中のため残す")
  keep_branches+="$main_branch "
}
[ -n "$current_branch" ] && keep_branches+="$current_branch "

br_remove=()
while IFS= read -r b; do
  [[ "$keep_branches" == *" $b "* ]] && continue
  unpushed=$(git rev-list --count "refs/heads/$b" --not --remotes "refs/heads/$default")
  note=""
  [ "$unpushed" != "0" ] && note="  ⚠ 未 push コミット ${unpushed} 件"
  up=$(git for-each-ref --format='%(upstream:short)' "refs/heads/$b")
  [ -z "$up" ] && note+="  (upstream なし)"
  br_remove+=("$b")
  plan_lines+=("branch    $b$note")
done < <(git for-each-ref --format='%(refname:short)' refs/heads/)

plan_id=$(printf '%s\n' "$default" ${plan_lines[@]+"${plan_lines[@]}"} | git hash-object --stdin | cut -c1-12)

mode=${1:-plan}
case "$mode" in
  plan)
    echo "default ブランチ: ${default}（削除しない・更新しない）"
    echo
    if [ ${#plan_lines[@]} -eq 0 ]; then
      echo "削除対象はありません。"
    else
      echo "削除対象:"
      printf '  %s\n' "${plan_lines[@]}"
    fi
    if [ ${#skip_lines[@]} -gt 0 ]; then
      echo
      echo "残すもの:"
      printf '  %s\n' "${skip_lines[@]}"
    fi
    echo
    echo "plan id: $plan_id"
    ;;
  apply)
    [ -n "${2:-}" ] || die "apply には plan id が必要です（先に plan を実行）"
    [ "$2" = "$plan_id" ] || die "plan id が一致しません（対象が変わった）。plan をやり直してください"
    [ ${#plan_lines[@]} -gt 0 ] || { echo "削除対象はありません。"; exit 0; }
    fail=0
    for p in ${wt_remove[@]+"${wt_remove[@]}"}; do
      if git worktree remove --force "$p"; then echo "removed worktree: $p"
      else echo "FAILED worktree: $p" >&2; fail=1; fi
    done
    git worktree prune
    [ "$wt_prunable" = 1 ] && echo "pruned stale worktree entries"
    for b in ${br_remove[@]+"${br_remove[@]}"}; do
      if sha=$(git rev-parse --short "refs/heads/$b") && git branch -D -q "$b"; then
        echo "deleted branch: $b (was $sha)"
      else echo "FAILED branch: $b" >&2; fail=1; fi
    done
    exit $fail
    ;;
  *) die "usage: prune.sh plan | prune.sh apply <plan-id>" ;;
esac
