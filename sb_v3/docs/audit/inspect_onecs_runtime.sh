#!/usr/bin/env bash
set -euo pipefail

echo '== HOST =='
hostname

echo '== DATE =='
date

echo '== SS 3111 =='
ss -ltnp '( sport = :3111 )' || true

PID=$(ss -ltnp '( sport = :3111 )' | awk 'match($0,/pid=[0-9]+/){print substr($0,RSTART+4,RLENGTH-4)}' | head -n1)
echo "PID=${PID:-}"
if [[ -z "${PID:-}" ]]; then
  echo 'NO_PID_FOR_3111'
  exit 1
fi

PARENT_PID=$(ps -o ppid= -p "$PID" | tr -d ' ')
GRANDPARENT_PID=$(ps -o ppid= -p "$PARENT_PID" | tr -d ' ')

echo '== PROCESS =='
ps -fp "$PID"

echo '== PARENT =='
ps -fp "$PARENT_PID" || true

echo '== GRANDPARENT =='
ps -fp "$GRANDPARENT_PID" || true

echo '== PSTREE =='
pstree -ap "$GRANDPARENT_PID" || pstree -ap "$PARENT_PID" || pstree -ap "$PID" || true

echo '== CWD =='
readlink -f "/proc/$PID/cwd"

echo '== CMDLINE =='
tr '\0' ' ' < "/proc/$PID/cmdline"
echo

echo '== SELECTED ENV =='
tr '\0' '\n' < "/proc/$PID/environ" | grep -E '^(PORT|NODE_ENV|DATABASE_URL|JWT_SECRET|BOT_TOKEN|ADMIN_|PROXY_|PRIVATE_|WORKER_|VITE_|OWNER_|OAUTH_)' | sort || true
