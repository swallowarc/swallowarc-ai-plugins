#!/usr/bin/env bash
# 停止中のコンテナと、稼働中のコンテナが使っていない Docker イメージを削除する。
#
#   docker-prune.sh plan        削除対象を表示し、最後に plan id を出す（何も変更しない）
#   docker-prune.sh apply <id>  plan id が現在の対象と一致するときだけ削除する
#
# 削除は plan に出した ID を 1 件ずつ docker rm / docker rmi で行い、-f は付けない。
# plan と apply の間に起動したコンテナやそのイメージは、Docker 側が削除を拒否する。
# ボリューム・ネットワーク・ビルドキャッシュには触れない。
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "docker コマンドが見つかりません"
docker info >/dev/null 2>&1 || die "Docker デーモンに接続できません（Docker Desktop 等が起動しているか確認してください）"

context=$(docker context show 2>/dev/null || echo "?")
if [ -n "${DOCKER_HOST:-}" ]; then
  endpoint=$DOCKER_HOST
else
  endpoint=$(docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null || echo "?")
fi

# 内部の区切り。tab は read で空フィールドが詰まるので使わない
sep=$'\x1f'

# --- コンテナの分類 ---
# created / exited / dead を停止中として削除し、それ以外（running / paused / restarting など）は残す。
ct_remove=()    # 削除するコンテナ: id<SEP>name
ct_lines=()
keep_lines=()
keep_ids=()
while IFS=$sep read -r id state name image status; do
  [ -n "$id" ] || continue
  case "$state" in
    created|exited|dead)
      ct_remove+=("$id$sep$name")
      ct_lines+=("container  ${id:0:12}  $name  ($image)  $status")
      ;;
    *)
      keep_ids+=("$id")
      keep_lines+=("container  ${id:0:12}  $name  ($image)  $status")
      ;;
  esac
done < <(docker ps -a --no-trunc --format "{{.ID}}$sep{{.State}}$sep{{.Names}}$sep{{.Image}}$sep{{.Status}}")

# 残すコンテナが使っているイメージ ID（空白区切り）
in_use=" "
if [ ${#keep_ids[@]} -gt 0 ]; then
  while IFS= read -r img; do
    in_use+="$img "
  done < <(docker inspect --format '{{.Image}}' "${keep_ids[@]}")
fi

# --- イメージの分類 ---
# 同じ ID に複数のタグが付く場合は 1 行にまとめる。出力行: id<SEP>ref,ref,...<SEP>size
im_remove=()
im_lines=()
im_keep=0
while IFS=$sep read -r id refs size; do
  [ -n "$id" ] || continue
  if [[ "$in_use" == *" $id "* ]]; then
    im_keep=$((im_keep + 1))
    continue
  fi
  short=${id#sha256:}
  im_remove+=("$id$sep$refs")
  im_lines+=("image      ${short:0:12}  ${refs:-<none>}  $size")
done < <(
  docker images -a --no-trunc --format "{{.ID}}$sep{{.Repository}}$sep{{.Tag}}$sep{{.Size}}" |
    awk -F'\037' '
      {
        if (!($1 in seen)) { seen[$1] = 1; order[++n] = $1; size[$1] = $4; refs[$1] = "" }
        if ($2 != "<none>" && $3 != "<none>") {
          r = $2 ":" $3
          refs[$1] = (refs[$1] == "" ? r : refs[$1] "," r)
        }
      }
      END { for (i = 1; i <= n; i++) printf "%s\037%s\037%s\n", order[i], refs[order[i]], size[order[i]] }
    '
)
if command -v shasum >/dev/null 2>&1; then hasher=shasum; else hasher=sha1sum; fi
plan_id=$(printf '%s\n' "$endpoint" ${ct_remove[@]+"${ct_remove[@]}"} ${im_remove[@]+"${im_remove[@]}"} |
  $hasher | cut -c1-12)

total=$(( ${#ct_remove[@]} + ${#im_remove[@]} ))

mode=${1:-plan}
case "$mode" in
  plan)
    echo "Docker context: ${context}（${endpoint}）"
    echo
    if [ "$total" -eq 0 ]; then
      echo "削除対象はありません。"
    else
      echo "削除対象: コンテナ ${#ct_remove[@]} 件、イメージ ${#im_remove[@]} 件"
      [ ${#ct_lines[@]} -gt 0 ] && printf '  %s\n' "${ct_lines[@]}"
      [ ${#im_lines[@]} -gt 0 ] && printf '  %s\n' "${im_lines[@]}"
    fi
    if [ ${#keep_lines[@]} -gt 0 ] || [ "$im_keep" -gt 0 ]; then
      echo
      echo "残すもの（稼働中のコンテナと、その使用イメージ ${im_keep} 件）:"
      [ ${#keep_lines[@]} -gt 0 ] && printf '  %s\n' "${keep_lines[@]}"
    fi
    echo
    echo "plan id: $plan_id"
    ;;
  apply)
    [ -n "${2:-}" ] || die "apply には plan id が必要です（先に plan を実行）"
    [ "$2" = "$plan_id" ] || die "plan id が一致しません（対象が変わった）。plan をやり直してください"
    [ "$total" -gt 0 ] || { echo "削除対象はありません。"; exit 0; }
    fail=0
    for entry in ${ct_remove[@]+"${ct_remove[@]}"}; do
      IFS=$sep read -r id name <<<"$entry"
      if out=$(docker rm "$id" 2>&1); then echo "removed container: $name (${id:0:12})"
      else echo "FAILED container: $name (${id:0:12}): $out" >&2; fail=1; fi
    done
    for entry in ${im_remove[@]+"${im_remove[@]}"}; do
      IFS=$sep read -r id refs <<<"$entry"
      short=${id#sha256:}; short=${short:0:12}
      out=""
      ok=1
      # タグを外していき、最後のタグが外れた時点でイメージ本体も消える。
      # タグのないイメージ（と、タグを外しても残ったもの）は ID で消す。
      if [ -n "$refs" ]; then
        IFS=',' read -r -a ref_arr <<<"$refs"
        out=$(docker rmi "${ref_arr[@]}" 2>&1) || ok=0
      fi
      if [ "$ok" = 1 ] && docker image inspect "$id" >/dev/null 2>&1; then
        out=$(docker rmi "$id" 2>&1) || ok=0
      fi
      if [ "$ok" = 1 ]; then echo "removed image: ${refs:-<none>} ($short)"
      else echo "FAILED image: ${refs:-<none>} ($short): $out" >&2; fail=1; fi
    done
    exit $fail
    ;;
  *) die "usage: docker-prune.sh plan | docker-prune.sh apply <plan-id>" ;;
esac
