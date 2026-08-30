#!/usr/bin/env bash
# 日常清理 —— 只读诊断。不做任何修改，安全重复运行。
set -uo pipefail

hr() { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }

# 追溯进程祖先链，用来区分「cmux 树下的活进程」和「launchd 收养的孤儿」
trace() {
  local p=$1 out=""
  while [ -n "$p" ] && [ "$p" != "0" ]; do
    local info; info=$(ps -o ppid=,comm= -p "$p" 2>/dev/null) || break
    [ -z "$info" ] && break
    local comm; comm=$(echo "$info" | awk '{$1="";print $0}' | xargs basename 2>/dev/null)
    out="$out <- $p:$comm"
    p=$(echo "$info" | awk '{print $1}')
  done
  echo "$out"
}

hr "系统概况"
uptime
sysctl vm.swapusage
memory_pressure -Q 2>/dev/null | tail -1

hr "磁盘"
df -h / /System/Volumes/Data 2>/dev/null | grep -v '^map'

hr "监听端口"
lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {print $1, $2, $9}' | sort -u

# 常驻服务与系统组件 —— 这些 PPID=1 是正常的，不是清理目标
NOISE='/System/|/usr/libexec/|/usr/sbin/|com\.apple|/usr/local/munki|/Library/Input Methods|/Applications/'
NOISE="$NOISE"'|ssh-agent|gpg-agent|keyboxd|cloudphotod|colima|limactl|\.colima/|cmux'

none_or() { local out; out=$(cat); [ -n "$out" ] && echo "$out" || echo "  无"; }

hr "孤儿进程（PPID=1，已排除常驻服务）"
ps -Ao pid,ppid,etime,rss,user,command \
  | awk -v u="$USER" '$2==1 && $5==u' \
  | grep -vE "$NOISE" | cut -c1-150 | none_or

hr "长跑的 dev 进程（>1 天，可能是遗留 debug）"
ps -Ao pid,ppid,etime,command \
  | grep -E '^[[:space:]]*[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+-' \
  | grep -iE 'make |uv run|npm |pnpm |yarn |node |port-forward|vite|next|nodemon|webpack|worker' \
  | grep -v grep | grep -vE "$NOISE" | cut -c1-150 | none_or

hr "supervisor 嫌疑（循环重启脚本，杀子进程前必须先处理）"
ps -Ao pid,ppid,etime,command \
  | grep -iE '\-pf\.sh|dev-.*\.sh|watch.*\.sh|forever|pm2' \
  | grep -v grep | grep -vE "$NOISE" | cut -c1-150 | none_or

hr "祖先链抽样（确认哪些在 cmux 下、哪些是孤儿）"
{ for pid in $(ps -Ao pid,command | grep -iE 'port-forward|uv run|make dev|npm run' \
               | grep -v grep | awk '{print $1}' | head -8); do
    echo "  $pid:$(trace "$pid")"
  done; } | none_or

hr "Docker"
if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  docker system df
  echo "--- 容器 ---"
  docker ps -a --format '  {{.Names}}\t{{.Status}}'
  echo "--- 悬空卷（具名的通常是数据库数据，别乱删）---"
  docker volume ls -qf dangling=true | head -40
else
  echo "  Docker 未运行"
fi

hr "Colima"
if command -v colima >/dev/null; then
  colima status 2>&1 | grep -iE 'running|stopped|runtime' | head -3
  du -sh ~/.colima 2>/dev/null
  ps -Ao rss,comm | grep -i 'Virtualization.VirtualMachine' | grep -v grep \
    | awk '{printf "  VM RSS: %.0f MB\n", $1/1024}'
else
  echo "  未安装"
fi

hr "缓存大户（Top 20）"
du -sx -m ~/.cache/* ~/Library/Caches/* ~/Library/pnpm ~/.npm 2>/dev/null \
  | sort -rn | head -20 | awk '{printf "  %6d MB  %s\n", $1, $2}'

hr "缓存锁占用检查（有占用就别清）"
LOCKS=("$HOME/.cache/uv/.lock" "$HOME/Library/pnpm/store/v3/.pnpm-store.lock" "$HOME/.npm/_locks")
for lock in "${LOCKS[@]}"; do
  [ -e "$lock" ] || continue
  if lsof "$lock" >/dev/null 2>&1; then
    echo "  ⚠ 被占用，跳过: $lock"
    lsof "$lock" 2>/dev/null | tail -1 | awk '{print "    -> "$1" (pid "$2")"}'
  else
    echo "  ✓ 空闲: $lock"
  fi
done

hr "家目录大户（Top 15）"
du -sx -m ~/* ~/.[!.]* 2>/dev/null | sort -rn | head -15 \
  | awk '{printf "  %6d MB  %s\n", $1, $2}'

printf '\n\033[1m诊断完成。动手前请对照 SKILL.md 的「绝不动的东西」和 Common Mistakes。\033[0m\n'
