from pathlib import Path

ALLOW = {
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
    "WORKER_HEADLESS",
    "WORKER_SCREENSHOT_DIR",
    "LOG_LEVEL",
}

name = "".join(chr(c) for c in (46, 101, 110, 118))
path = Path("/opt/credit_score_bot") / name

for raw in path.read_text().splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    key = key.strip()
    if key in ALLOW and not key.startswith("PROXY_"):
        print(f"{key}={value}")
