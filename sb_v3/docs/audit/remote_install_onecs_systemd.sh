#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=/opt/csbot_admin_system/app
LOG_DIR=/opt/csbot_admin_system/logs
UNIT_PATH=/etc/systemd/system/onecs.service
START_SCRIPT=$APP_ROOT/start-onecs.sh

mkdir -p "$LOG_DIR"

PID=$(ss -ltnp '( sport = :3111 )' | awk 'match($0,/pid=[0-9]+/){print substr($0,RSTART+4,RLENGTH-4)}' | head -n1)
if [[ -z "${PID:-}" ]]; then
  echo 'NO_PID_FOR_3111'
  exit 1
fi

python3 - "$PID" "$START_SCRIPT" "$UNIT_PATH" "$APP_ROOT" "$LOG_DIR" <<'PY'
import sys
from pathlib import Path

pid, start_script_path, unit_path, app_root, log_dir = sys.argv[1:6]
raw_items = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
keep = {}
for item in raw_items:
    if not item or b'=' not in item:
        continue
    k, v = item.split(b'=', 1)
    key = k.decode('utf-8', 'ignore')
    value = v.decode('utf-8', 'ignore')
    if key in {
        'DATABASE_URL', 'JWT_SECRET', 'VITE_APP_ID', 'OAUTH_SERVER_URL',
        'OWNER_OPEN_ID', 'OWNER_NAME', 'BUILT_IN_FORGE_API_URL',
        'BUILT_IN_FORGE_API_KEY', 'VITE_FRONTEND_FORGE_API_URL',
        'VITE_FRONTEND_FORGE_API_KEY', 'ADMIN_PASSWORD', 'ADMIN_USER_IDS',
        'BOT_TOKEN', 'CAPTCHA_SERVICE', 'PRIVATE_API_KEY', 'PRIVATE_API_PORT',
        'PROXY_HOST', 'PROXY_PASSWORD', 'PROXY_PORT', 'PROXY_USERNAME',
        'WORKER_COUNT', 'WORKER_ROTATE_ON_SUCCESS', 'VITE_ANALYTICS_ENDPOINT',
        'VITE_ANALYTICS_WEBSITE_ID', 'VITE_APP_LOGO', 'VITE_APP_TITLE',
        'VITE_OAUTH_PORTAL_URL'
    }:
        keep[key] = value

keep['NODE_ENV'] = 'production'
keep['PORT'] = '3111'

start_lines = [
    '#!/usr/bin/env bash',
    'set -euo pipefail',
    f'cd {app_root}',
]
for key in sorted(keep):
    start_lines.append(f'export {key}={keep[key]!r}')
start_lines.append('exec /usr/bin/env node dist/index.js')
Path(start_script_path).write_text('\n'.join(start_lines) + '\n', encoding='utf-8')

unit_lines = [
    '[Unit]',
    'Description=ONE CS Admin System',
    'After=network.target',
    'Wants=network-online.target',
    '',
    '[Service]',
    'Type=simple',
    'User=root',
    f'WorkingDirectory={app_root}',
    f'ExecStart={start_script_path}',
    'Restart=always',
    'RestartSec=5',
    f'StandardOutput=append:{log_dir}/onecs-systemd.log',
    f'StandardError=append:{log_dir}/onecs-systemd-error.log',
    '',
    '[Install]',
    'WantedBy=multi-user.target',
    '',
]
Path(unit_path).write_text('\n'.join(unit_lines), encoding='utf-8')
print(f'prepared {start_script_path} and {unit_path} with {len(keep)} env vars')
PY

chmod +x "$START_SCRIPT"
systemctl daemon-reload
systemctl enable onecs.service

if systemctl is-active --quiet onecs.service; then
  systemctl restart onecs.service
else
  systemctl start onecs.service
fi

sleep 5
systemctl status onecs.service --no-pager -l || true
ss -ltnp '( sport = :3111 )' || true
curl -sS -I --max-time 15 http://127.0.0.1:3111/ | sed -n '1,12p'
