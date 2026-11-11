#!/bin/sh
# Claude Code status line: directory, git branch, model, effort,
# context window (bar, percent, tokens), session cost, rate limits.
# Reads the status line JSON on stdin. Any figure the JSON lacks is left out.

input=$(cat)

eval "$(printf '%s' "$input" | jq -r '@sh "
current_dir=\(.workspace.current_dir // "")
model_name=\(.model.display_name // "")
effort_level=\(.effort.level // "")
used=\(.context_window.used_percentage // "")
tokens=\(.context_window.total_input_tokens // "")
window=\(.context_window.context_window_size // "")
cost=\(.cost.total_cost_usd // "")
five=\(.rate_limits.five_hour.used_percentage // "")
seven=\(.rate_limits.seven_day.used_percentage // "")
"')"

esc=$(printf '\033')
reset="${esc}[0m"
dim="${esc}[2m"
sep=" │ "

# Green under 60, yellow from 60, red from 80.
level_color() {
  if [ "$1" -ge 80 ]; then
    printf '31'
  elif [ "$1" -ge 60 ]; then
    printf '33'
  else
    printf '32'
  fi
}

# 84000 -> 84.0k, 1000000 -> 1.0M
compact() {
  awk -v n="$1" 'BEGIN {
    if (n >= 1000000) printf "%.1fM", n / 1000000
    else if (n >= 1000) printf "%.1fk", n / 1000
    else printf "%d", n
  }'
}

dir_name=$(basename "$current_dir")
out="${esc}[92m📁 ${dir_name}${reset}"

if git -C "$current_dir" rev-parse --git-dir > /dev/null 2>&1; then
  branch=$(git -C "$current_dir" --no-optional-locks rev-parse --abbrev-ref HEAD 2> /dev/null)
  [ -n "$branch" ] && out="${out}${sep}${esc}[35m⎇ ${branch}${reset}"
fi

out="${out}${sep}${esc}[34m🤖 ${model_name}${reset}"
[ -n "$effort_level" ] && out="${out} ${esc}[36m(${effort_level})${reset}"

if [ -n "$used" ]; then
  used_int=$(printf '%.0f' "$used")
  color=$(level_color "$used_int")
  filled=$(((used_int + 5) / 10))
  [ "$filled" -gt 10 ] && filled=10
  bar_on=$(printf '%*s' "$filled" '' | sed 's/ /█/g')
  bar_off=$(printf '%*s' "$((10 - filled))" '' | sed 's/ /░/g')
  out="${out}${sep}${esc}[${color}m${bar_on}${reset}${dim}${bar_off}${reset} ${esc}[${color}m${used_int}%${reset}"

  if [ -n "$tokens" ] && [ -n "$window" ]; then
    out="${out} ${dim}$(compact "$tokens")/$(compact "$window")${reset}"
  fi
fi

if [ -n "$cost" ]; then
  out="${out}${sep}${dim}\$$(printf '%.2f' "$cost")${reset}"
fi

limits=""

for pair in "5h:$five" "7d:$seven"; do
  label=${pair%%:*}
  value=${pair#*:}
  [ -z "$value" ] && continue
  value_int=$(printf '%.0f' "$value")
  [ -n "$limits" ] && limits="${limits} ${dim}·${reset} "
  limits="${limits}${dim}${label}${reset} ${esc}[$(level_color "$value_int")m${value_int}%${reset}"
done

[ -n "$limits" ] && out="${out}${sep}${limits}"

printf '%s\n' "$out"
