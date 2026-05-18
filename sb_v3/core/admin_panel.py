"""
SBBot v3 — Admin Panel (FastAPI)
Run: uvicorn admin_panel:app --host 0.0.0.0 --port 3111
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure core modules are importable
_core = Path(__file__).parent
if str(_core) not in sys.path:
    sys.path.insert(0, str(_core))

import logging
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sbbot.admin")

ADMIN_IDS = set(int(x) for x in os.environ.get("ADMIN_USER_IDS", "").split(",") if x.strip())


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    logger.info(f"[Admin] Started on :3111. Allowed IDs: {ADMIN_IDS or 'ALL'}")
    yield
    logger.info("[Admin] Shutdown")


app = FastAPI(title="SBBot Admin", lifespan=lifespan)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _admin_id(request: Request) -> int | None:
    try:
        return int(request.query_params.get("admin_id", "0") or "0")
    except ValueError:
        return None


def _require_admin(request: Request):
    aid = _admin_id(request)
    if aid is None:
        return JSONResponse({"error": "admin_id required"}, status_code=401)
    if ADMIN_IDS and aid not in ADMIN_IDS:
        return JSONResponse({"error": "not authorized"}, status_code=403)
    return None  # OK


# ── HTML base template ───────────────────────────────────────────────────────

_BASE = """<!doctype html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SBBot Admin — %(title)s</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#0f1117;color:#e2e8f0;min-height:100vh}
header{background:#1a1f2e;border-bottom:1px solid #2d3748;padding:.75rem 1.5rem;display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap}
header a{color:#60a5fa;text-decoration:none;font-size:.9rem}
header a:hover{text-decoration:underline}
header .brand{font-weight:700;color:#f1f5f9;font-size:1.1rem}
header .right{margin-left:auto;font-size:.8rem;color:#94a3b8}
main{padding:1.5rem;max-width:1400px;margin:0 auto}
h1{font-size:1.4rem;margin-bottom:1.25rem;color:#f1f5f9;border-bottom:1px solid #2d3748;padding-bottom:.5rem}
h2{font-size:1.1rem;color:#cbd5e1;margin:.75rem 0 .5rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.75rem;margin-bottom:1.5rem}
.card{background:#1e2433;border:1px solid #2d3748;border-radius:8px;padding:1rem}
.card .label{font-size:.75rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em}
.card .value{font-size:1.6rem;font-weight:700;margin:.25rem 0}
.card .sub{font-size:.75rem;color:#60a5fa}
table{width:100%%;border-collapse:collapse;font-size:.85rem;margin:.5rem 0}
th{text-align:left;padding:.5rem .75rem;background:#1e2433;color:#94a3b8;border-bottom:1px solid #2d3748;white-space:nowrap}
td{padding:.45rem .75rem;border-bottom:1px solid #1e2433}
tr:hover td{background:#1e2433}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:999px;font-size:.7rem;font-weight:600}
.badge-ok{background:#052e16;color:#4ade80}
.badge-err{background:#3f0a0a;color:#f87171}
.badge-warn{background:#2d1f00;color:#fbbf24}
.badge-info{background:#0c2040;color:#60a5fa}
.btn{display:inline-block;padding:.25rem .75rem;border-radius:5px;font-size:.8rem;cursor:pointer;text-decoration:none;border:none}
.btn-sm{padding:.15rem .5rem;font-size:.75rem}
.btn-danger{background:#7f1d1d;color:#fca5a5}
.btn-danger:hover{background:#991b1b}
.btn-primary{background:#1d4ed8;color:#bfdbfe}
.btn-primary:hover{background:#1e40af}
.btn-success{background:#14532d;color:#86efac}
.btn-success:hover{background:#166534}
input,select,textarea{background:#1e2433;border:1px solid #2d3748;color:#e2e8f0;padding:.4rem .6rem;border-radius:5px;font-size:.85rem;width:100%%}
input:focus,select:focus{outline:none;border-color:#60a5fa}
form{margin:.5rem 0}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin:.5rem 0}
.form-group{margin-bottom:.5rem}
.form-group label{display:block;font-size:.75rem;color:#94a3b8;margin-bottom:.25rem}
.empty{color:#475569;font-size:.85rem;text-align:center;padding:2rem}
</style>
</head><body>
<header>
  <span class="brand">⚙️ SBBot Admin</span>
  <a href="/">Статистика</a>
  <a href="/accounts">Аккаунты</a>
  <a href="/users">Пользователи</a>
  <a href="/prices">Цены</a>
  <a href="/logs">Логи</a>
  <a href="/settings">Настройки</a>
  <span class="right">?admin_id=YOUR_ID</span>
</header>
<main>
%(body)s
</main></body></html>
"""


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(_BASE % {"title": title, "body": body})


# ── Stats ────────────────────────────────────────────────────────────────────

@app.get("/")
async def index(request: Request):
    err = _require_admin(request)
    if err: return err
    stats = await db.get_stats()
    by_type = stats.get("by_type", [])
    type_rows = "".join(
        f"<tr><td>{r['type']}</td><td>{r['count']}</td><td>${r['revenue']:.2f}</td></tr>"
        for r in sorted(by_type, key=lambda x: x["revenue"], reverse=True)
    ) or "<tr><td colspan=3 class=empty>нет данных</td></tr>"
    body = f"""
<h1>📊 Статистика системы</h1>
<div class="grid">
  <div class="card"><div class="label">Пользователей</div><div class="value">{stats['users']}</div></div>
  <div class="card"><div class="label">Баланс кошельков</div><div class="value">${stats['total_balance']:.2f}</div></div>
  <div class="card"><div class="label">Поисков (всего)</div><div class="value">{stats['searches']}</div></div>
  <div class="card"><div class="label">Выручка (всего)</div><div class="value">${stats['total_revenue']:.2f}</div></div>
  <div class="card"><div class="label">Депозиты (всего)</div><div class="value">${stats['total_deposits']:.2f}</div></div>
  <div class="card"><div class="label">Прибыль</div><div class="value">${stats['profit']:.2f}</div></div>
</div>
<h2>Сегодня</h2>
<div class="grid">
  <div class="card"><div class="label">Выручка</div><div class="value">${stats.get('today_revenue',0):.2f}</div></div>
  <div class="card"><div class="label">Депозиты</div><div class="value">${stats.get('today_deposits',0):.2f}</div></div>
  <div class="card"><div class="label">Поисков</div><div class="value">{stats.get('today_searches',0)}</div></div>
  <div class="card"><div class="label">Активных юзеров</div><div class="value">{stats.get('active_users_today',0)}</div></div>
</div>
<h2>Выручка по источникам</h2>
<div class="grid">
  <div class="card"><div class="label">Enformion</div><div class="value">${stats.get('rev_enf',0):.2f}</div><div class="sub">sb: {stats.get('sb_active',0)}/{stats.get('sb_total',0)}</div></div>
  <div class="card"><div class="label">Usfull.pro</div><div class="value">${stats.get('rev_uf',0):.2f}</div><div class="sub">uf: {stats.get('uf_active',0)}/{stats.get('uf_total',0)}</div></div>
</div>
<h2>Поиски по типам</h2>
<table><tr><th>Тип</th><th>Запросов</th><th>Выручка</th></tr>{type_rows}</table>
"""
    return _page("Статистика", body)


# ── Accounts ────────────────────────────────────────────────────────────────

@app.get("/accounts")
async def accounts_page(request: Request):
    err = _require_admin(request)
    if err: return err
    aid = int(request.query_params.get("admin_id", "0"))
    sb_accounts = await db.get_sb_accounts()
    uf_accounts = await db.get_usfull_accounts()
    sb_rows = ""
    for a in sb_accounts:
        badge = "badge-ok" if a.get("status") == "active" else "badge-warn" if a.get("status") == "low_balance" else "badge-err"
        init = a.get("init_tok", 1) or 1
        pct = int(a.get("balance_tok", 0) / init * 100)
        sb_rows += f"""<tr>
  <td>{a.get('email') or ''}</td>
  <td><span class="badge {badge}">{a.get('status','unknown')}</span></td>
  <td>${a.get('balance_tok',0):.2f}</td>
  <td>{a.get('init_tok',0):.0f}</td>
  <td>{pct}%%</td>
  <td>{a.get('searches',0)}</td>
  <td>{a.get('proxy','—') or '—'}</td>
</tr>"""
    uf_rows = ""
    for a in uf_accounts:
        badge = "badge-ok" if a.get("status") == "active" else "badge-warn" if a.get("status") == "low_balance" else "badge-err"
        uf_rows += f"""<tr>
  <td>{a.get('username') or ''}</td>
  <td><span class="badge {badge}">{a.get('status','unknown')}</span></td>
  <td>${a.get('balance',0):.2f}</td>
  <td>${a.get('init_balance',0):.2f}</td>
  <td>{a.get('searches',0)}</td>
  <td>{a.get('proxy','—') or '—'}</td>
</tr>"""
    body = f"""
<h1>🔑 Управление аккаунтами</h1>
<h2>Enformion ({len(sb_accounts)})</h2>
<form method="post" action="/accounts/add_sb?admin_id={aid}">
  <div class="form-row">
    <div class="form-group"><label>Email</label><input name="email" placeholder="user@domain.com" required></div>
    <div class="form-group"><label>Password</label><input name="password" placeholder="password" required></div>
    <div class="form-group"><label>Proxy (опционально)</label><input name="proxy" placeholder="socks5://host:port"></div>
  </div>
  <button type="submit" class="btn btn-success btn-sm">+ Добавить</button>
</form>
<table><tr><th>Email</th><th>Статус</th><th>Баланс</th><th>Начальный</th><th>%</th><th>Поисков</th><th>Proxy</th></tr>
{sb_rows or '<tr><td colspan=7 class=empty>Нет аккаунтов</td></tr>'}</table>
<h2>Usfull.pro ({len(uf_accounts)})</h2>
<form method="post" action="/accounts/add_uf?admin_id={aid}">
  <div class="form-row">
    <div class="form-group"><label>Username</label><input name="username" placeholder="user" required></div>
    <div class="form-group"><label>API Key</label><input name="api_key" placeholder="api_key_here" required></div>
    <div class="form-group"><label>Proxy (опционально)</label><input name="proxy" placeholder="socks5://host:port"></div>
  </div>
  <button type="submit" class="btn btn-success btn-sm">+ Добавить</button>
</form>
<table><tr><th>Username</th><th>Статус</th><th>Баланс</th><th>Начальный</th><th>Поисков</th><th>Proxy</th></tr>
{uf_rows or '<tr><td colspan=6 class=empty>Нет аккаунтов</td></tr>'}</table>
"""
    return _page("Аккаунты", body)


@app.post("/accounts/add_sb")
async def add_sb(
    admin_id: int = Query(...),
    email: str = Form(...),
    password: str = Form(...),
    proxy: str = Form(""),
):
    if ADMIN_IDS and admin_id not in ADMIN_IDS:
        return JSONResponse({"error": "not authorized"}, status_code=403)
    await db.upsert_sb_account(email, password, proxy)
    await db.log_admin_action(admin_id, "add_sb_account", "sb_accounts", email, f"proxy={proxy}")
    return RedirectResponse(url="/accounts?admin_id=" + str(admin_id), status_code=303)


@app.post("/accounts/add_uf")
async def add_uf(
    admin_id: int = Query(...),
    username: str = Form(...),
    api_key: str = Form(...),
    proxy: str = Form(""),
):
    if ADMIN_IDS and admin_id not in ADMIN_IDS:
        return JSONResponse({"error": "not authorized"}, status_code=403)
    await db.upsert_usfull_account(username, "", api_key, proxy)
    await db.log_admin_action(admin_id, "add_uf_account", "usfull_accounts", username)
    return RedirectResponse(url="/accounts?admin_id=" + str(admin_id), status_code=303)


# ── Users ──────────────────────────────────────────────────────────────────

@app.get("/users")
async def users_page(request: Request):
    err = _require_admin(request)
    if err: return err
    aid = int(request.query_params.get("admin_id", "0"))
    users = await db.get_all_users()
    rows = ""
    for u in users[:100]:
        banned = '<span class="badge badge-err">BAN</span>' if u.get("is_banned") else ""
        admin = '<span class="badge badge-info">ADMIN</span>' if u.get("is_admin") else ""
        rows += f"""<tr>
  <td>{u.get('user_id','')}</td>
  <td>{u.get('username','') or '—'}</td>
  <td>{u.get('full_name','') or '—'}</td>
  <td>${u.get('balance',0):.2f}</td>
  <td>{u.get('searches',0)}</td>
  <td>{banned} {admin}</td>
  <td>{u.get('markup_pct',0)}%</td>
  <td>{u.get('daily_limit','') or '—'}</td>
  <td>{str(u.get('created_at',''))[:10]}</td>
  <td>
    <form method="post" action="/users/ban?admin_id={aid}" style="display:inline">
      <input type="hidden" name="user_id" value="{u['user_id']}">
      <input type="hidden" name="ban" value="{'0' if u.get('is_banned') else '1'}">
      <button type="submit" class="btn btn-sm {'btn-success' if u.get('is_banned') else 'btn-danger'}">
        {'Разбанить' if u.get('is_banned') else 'Забанить'}
      </button>
    </form>
  </td>
</tr>"""
    body = f"""
<h1>👥 Пользователи ({len(users)} всего)</h1>
<table><tr><th>ID</th><th>Username</th><th>Имя</th><th>Баланс</th><th>Поисков</th><th>Статус</th><th>Markup</th><th>Лимит</th><th>Создан</th><th>Действие</th></tr>
{rows or '<tr><td colspan=10 class=empty>Нет пользователей</td></tr>'}</table>
"""
    return _page("Пользователи", body)


@app.post("/users/ban")
async def ban_user(
    admin_id: int = Query(...),
    user_id: int = Form(...),
    ban: str = Form("1"),
):
    if ADMIN_IDS and admin_id not in ADMIN_IDS:
        return JSONResponse({"error": "not authorized"}, status_code=403)
    await db.set_banned(user_id, ban == "1")
    await db.log_admin_action(admin_id, "ban_user" if ban == "1" else "unban_user", "user", str(user_id))
    return RedirectResponse(url="/users?admin_id=" + str(admin_id), status_code=303)


# ── Prices ─────────────────────────────────────────────────────────────────

@app.get("/prices")
async def prices_page(request: Request):
    err = _require_admin(request)
    if err: return err
    aid = int(request.query_params.get("admin_id", "0"))
    settings = await db.get_all_settings()
    price_keys = [
        "phone_price", "address_price", "background_price",
        "ssn_dob_price", "driver_license_price",
        "credit_report_price", "credit_score_price",
        "phone_verify_price", "address_verify_price",
        "email_verify_price", "emailrep_price",
    ]
    rows = ""
    for k in price_keys:
        val = settings.get(k, "")
        rows += f"""<tr>
  <td>{k}</td>
  <td>
    <form method="post" action="/prices/set?admin_id={aid}" style="display:flex;gap:.5rem;align-items:center">
      <input type="hidden" name="key" value="{k}">
      <input name="value" value="{val}" style="width:80px">
      <button type="submit" class="btn btn-sm btn-primary">💾</button>
    </form>
  </td>
</tr>"""
    body = f"""
<h1>💰 Цены</h1>
<table><tr><th>Ключ</th><th>$</th></tr>{rows}</table>
<h2>Общие настройки</h2>
<table>
  <tr><td>min_deposit</td><td>{settings.get('min_deposit','')}</td></tr>
  <tr><td>default_markup</td><td>{settings.get('default_markup','')}%</td></tr>
  <tr><td>allow_pay_over_limit</td><td>{settings.get('allow_pay_over_limit','')}</td></tr>
  <tr><td>daily_limit_basic/pro/enterprise</td><td>{settings.get('daily_limit_basic','')} / {settings.get('daily_limit_pro','')} / {settings.get('daily_limit_enterprise','')}</td></tr>
</table>
"""
    return _page("Цены", body)


@app.post("/prices/set")
async def set_price(
    admin_id: int = Query(...),
    key: str = Form(...),
    value: str = Form(...),
):
    if ADMIN_IDS and admin_id not in ADMIN_IDS:
        return JSONResponse({"error": "not authorized"}, status_code=403)
    await db.set_setting(key, value)
    await db.log_admin_action(admin_id, "set_price", "settings", key, value)
    return RedirectResponse(url="/prices?admin_id=" + str(admin_id), status_code=303)


# ── Logs ─────────────────────────────────────────────────────────────────

@app.get("/logs")
async def logs_page(request: Request):
    err = _require_admin(request)
    if err: return err
    admin_logs = await db.get_admin_logs(limit=100)
    wh_logs = await db.get_webhook_logs(limit=50)
    a_rows = "".join(
        f"<tr><td>{str(l.get('created_at',''))[:19]}</td><td>{l.get('admin_id','')}</td>"
        f"<td>{l.get('action','')}</td><td>{l.get('target_type','')}</td>"
        f"<td>{str(l.get('details',''))[:50]}</td></tr>"
        for l in admin_logs
    ) or "<tr><td colspan=5 class=empty>Нет логов</td></tr>"
    w_rows = "".join(
        f"<tr><td>{str(l.get('created_at',''))[:19]}</td><td>{l.get('provider','')}</td>"
        f"<td><span class=\"badge {'badge-ok' if l.get('processed') else 'badge-warn'}\">{l.get('event_type','')}</span></td>"
        f"<td>{str(l.get('invoice_id',''))[:30]}</td><td>{l.get('status_code','')}</td>"
        f"<td>{str(l.get('error_msg',''))[:40]}</td></tr>"
        for l in wh_logs
    ) or "<tr><td colspan=6 class=empty>Нет логов</td></tr>"
    body = f"""
<h1>📋 Логи</h1>
<h2>Админские действия ({len(admin_logs)})</h2>
<table><tr><th>Время</th><th>Admin</th><th>Действие</th><th>Объект</th><th>Детали</th></tr>{a_rows}</table>
<h2>Webhook ({len(wh_logs)})</h2>
<table><tr><th>Время</th><th>Провайдер</th><th>Событие</th><th>Invoice</th><th>Status</th><th>Ошибка</th></tr>{w_rows}</table>
"""
    return _page("Логи", body)


# ── Settings ───────────────────────────────────────────────────────────────

@app.get("/settings")
async def settings_page(request: Request):
    err = _require_admin(request)
    if err: return err
    aid = int(request.query_params.get("admin_id", "0"))
    settings = await db.get_all_settings()
    rows = "".join(f"""<tr>
  <td>{k}</td>
  <td>
    <form method="post" action="/settings/set?admin_id={aid}" style="display:flex;gap:.5rem">
      <input name="key" value="{k}" type="hidden">
      <input name="value" value="{v}" style="flex:1;min-width:200px">
      <button type="submit" class="btn btn-sm btn-primary">💾</button>
    </form>
  </td>
</tr>""" for k, v in sorted(settings.items()))
    body = f"""<h1>⚙️ Настройки ({len(settings)} ключей)</h1>
<table><tr><th>Ключ</th><th>Значение</th></tr>{rows}</table>"""
    return _page("Настройки", body)


@app.post("/settings/set")
async def set_setting(
    admin_id: int = Query(...),
    key: str = Form(...),
    value: str = Form(...),
):
    if ADMIN_IDS and admin_id not in ADMIN_IDS:
        return JSONResponse({"error": "not authorized"}, status_code=403)
    await db.set_setting(key, value)
    return RedirectResponse(url="/settings?admin_id=" + str(admin_id), status_code=303)


# ── JSON API ───────────────────────────────────────────────────────────────

@app.get("/api/enf_status")
async def enf_status():
    try:
        from sb_engine import pool as enf_pool
        return enf_pool.status_report()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/uf_status")
async def uf_status():
    try:
        from usfull_engine import usfull_engine as uf_engine
        return uf_engine.get_pool_status()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/stats")
async def stats_json(request: Request):
    err = _require_admin(request)
    if err: return err
    return await db.get_stats()