#!/usr/bin/env bash
set -euo pipefail

mkdir -p /home/ubuntu/csbot_admin_system/.secure

sshpass -p 'X5NJ4CXnXT5nj' ssh \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  -o PreferredAuthentications=password \
  -o PubkeyAuthentication=no \
  -o NumberOfPasswordPrompts=1 \
  -o ConnectTimeout=8 \
  root@193.221.200.87 <<'REMOTE_PY' > /home/ubuntu/csbot_admin_system/.secure/legacy_selected_secrets.json
python3 - <<'PY'
from pathlib import Path
import json
import re

result = {}
allowed = {
    "BOT_TOKEN",
    "WORKER_COUNT",
    "CRYPTOBOT_API_TOKEN",
    "ADMIN_USER_IDS",
    "WORKER_ROTATE_ON_SUCCESS",
    "BTCPAY_URL",
    "BTCPAY_API_KEY",
    "BTCPAY_STORE_ID",
    "BTCPAY_WEBHOOK_SECRET",
    "PRIVATE_API_KEY",
    "PRIVATE_API_PORT",
    "ADMIN_PASSWORD",
    "CAPTCHA_API_KEY",
    "CAPTCHA_SERVICE",
}

env_path = Path('/opt/credit_score_bot/.env')
if env_path.exists():
    for line in env_path.read_text(errors='ignore').splitlines():
        s = line.strip()
        if not s or s.startswith('#') or '=' not in s:
            continue
        k, v = s.split('=', 1)
        k = k.strip()
        v = v.strip()
        if k in allowed and k not in result:
            result[k] = v

cfg = Path('/opt/credit_score_bot/app/config.py')
if cfg.exists():
    for line in cfg.read_text(errors='ignore').splitlines():
        m = re.match(r'^\s*([A-Z0-9_]+)\s*:[^=]*=\s*(.+?)\s*$', line)
        if not m:
            continue
        k = m.group(1).strip()
        v = m.group(2).strip()
        if k in allowed and k not in result:
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            result[k] = v

print(json.dumps(result, ensure_ascii=False, indent=2))
PY
REMOTE_PY

python3 - <<'PY'
from pathlib import Path
import json
p = Path('/home/ubuntu/csbot_admin_system/.secure/legacy_selected_secrets.json')
data = json.loads(p.read_text())
print('saved_keys=' + ','.join(sorted(data)))
print('key_count=' + str(len(data)))
PY
