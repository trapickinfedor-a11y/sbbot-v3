from typing import Optional, List
"""
Database module — SQLite via aiosqlite
Tables: users, sb_accounts, usfull_accounts, searches, transactions, payments, settings
"""
import aiosqlite
import logging
from pathlib import Path
from datetime import datetime
import collections
import time

DB_PATH = Path(__file__).parent / "data" / "bot.db"
logger = logging.getLogger("sbbot.db")

# In-memory sliding-window rate tracking per API key
_api_rate_window: dict[int, collections.deque] = {}


async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT    DEFAULT '',
            full_name   TEXT    DEFAULT '',
            balance     REAL    DEFAULT 0.0,
            is_admin    INTEGER DEFAULT 0,
            is_banned   INTEGER DEFAULT 0,
            markup_pct          REAL    DEFAULT 0.0,
            daily_limit         INTEGER DEFAULT 0,    -- 0 = unlimited / inherit from plan
            total_spent         REAL    DEFAULT 0.0,
            searches            INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now')),
            last_seen   TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sb_accounts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT    UNIQUE,
            password    TEXT,
            proxy       TEXT    DEFAULT '',
            status      TEXT    DEFAULT 'unknown',
            balance_tok REAL    DEFAULT 0.0,
            init_tok    REAL    DEFAULT 0.0,
            searches    INTEGER DEFAULT 0,
            last_login  TEXT,
            last_check  TEXT,
            added_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS usfull_accounts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE,
            password    TEXT,
            api_key     TEXT    DEFAULT '',
            proxy       TEXT    DEFAULT '',
            status      TEXT    DEFAULT 'unknown',
            balance     REAL    DEFAULT 0.0,
            init_balance REAL   DEFAULT 0.0,
            searches    INTEGER DEFAULT 0,
            last_check  TEXT,
            added_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS searches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            search_type TEXT,
            source      TEXT    DEFAULT 'searchbug',
            query       TEXT,
            result_json TEXT,
            cost_user   REAL    DEFAULT 0.0,
            cost_sb     REAL    DEFAULT 0.0,
            status      TEXT    DEFAULT 'ok',
            created_at  TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            amount      REAL,
            type        TEXT,
            comment     TEXT    DEFAULT '',
            admin_id    INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            provider        TEXT    NOT NULL,
            invoice_id      TEXT    UNIQUE,
            amount          REAL    NOT NULL,
            currency        TEXT    DEFAULT 'USD',
            status          TEXT    DEFAULT 'pending',
            payload         TEXT,
            created_at      TEXT    DEFAULT (datetime('now')),
            confirmed_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS search_cache (
            cache_key   TEXT PRIMARY KEY,
            result_json TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            expires_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS guarantee_searches (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            search_id       TEXT,
            search_type     TEXT    NOT NULL,
            query           TEXT,
            cost_user       REAL    DEFAULT 0.0,
            status          TEXT    DEFAULT 'active',
            created_at      TEXT    DEFAULT (datetime('now')),
            expires_at      TEXT    DEFAULT (datetime('now', '+8 days')),
            current_phase   INTEGER DEFAULT 0,
            reminded_phase  INTEGER DEFAULT 0,
            last_reminder_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS admin_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id    INTEGER NOT NULL,
            action      TEXT    NOT NULL,
            target_type TEXT    DEFAULT '',
            target_id   TEXT    DEFAULT '',
            details     TEXT    DEFAULT '',
            ip_address  TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS webhook_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            provider    TEXT    NOT NULL,
            event_type  TEXT    NOT NULL,
            invoice_id  TEXT    DEFAULT '',
            user_id     INTEGER DEFAULT 0,
            payload_md5 TEXT    DEFAULT '',
            status_code INTEGER DEFAULT 0,
            error_msg   TEXT    DEFAULT '',
            processed   INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS rate_limits (
            user_id     INTEGER NOT NULL,
            action      TEXT    NOT NULL,
            count       INTEGER DEFAULT 1,
            window_start TEXT   DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, action)
        );

        CREATE TABLE IF NOT EXISTS user_alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            alert_type  TEXT    NOT NULL,
            message     TEXT    NOT NULL,
            is_read     INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_searches_user ON searches(user_id);
        CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
        CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
        CREATE INDEX IF NOT EXISTS idx_guarantee_user ON guarantee_searches(user_id);
        CREATE INDEX IF NOT EXISTS idx_guarantee_status ON guarantee_searches(status);
        CREATE INDEX IF NOT EXISTS idx_admin_logs_admin ON admin_logs(admin_id);
        CREATE INDEX IF NOT EXISTS idx_admin_logs_target ON admin_logs(target_type, target_id);
        CREATE INDEX IF NOT EXISTS idx_webhook_logs_invoice ON webhook_logs(invoice_id);
        CREATE INDEX IF NOT EXISTS idx_webhook_logs_created ON webhook_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_user_alerts_user ON user_alerts(user_id, is_read);

        -- Default prices (user-facing, USD)
        INSERT OR IGNORE INTO settings VALUES ('phone_price',           '2.0');
        INSERT OR IGNORE INTO settings VALUES ('address_price',         '2.0');
        INSERT OR IGNORE INTO settings VALUES ('number_address_price',  '2.0');
        INSERT OR IGNORE INTO settings VALUES ('background_price',      '3.0');
        INSERT OR IGNORE INTO settings VALUES ('phone_verify_price',    '0.1');
        INSERT OR IGNORE INTO settings VALUES ('address_verify_price',  '0.3');
        INSERT OR IGNORE INTO settings VALUES ('email_verify_price',    '0.1');
        INSERT OR IGNORE INTO settings VALUES ('emailrep_price',        '0.1');
        INSERT OR IGNORE INTO settings VALUES ('ssn_dob_price',         '1.0');
        INSERT OR IGNORE INTO settings VALUES ('driver_license_price',  '2.0');
        INSERT OR IGNORE INTO settings VALUES ('credit_report_price',   '5.0');
        INSERT OR IGNORE INTO settings VALUES ('credit_score_price',    '4.0');
        INSERT OR IGNORE INTO settings VALUES ('min_deposit',           '5.0');
        INSERT OR IGNORE INTO settings VALUES ('default_markup',        '0');
        INSERT OR IGNORE INTO settings VALUES ('admin_chat_id',         '');
        INSERT OR IGNORE INTO settings VALUES ('daily_limit_basic',     '10');
        INSERT OR IGNORE INTO settings VALUES ('daily_limit_pro',       '50');
        INSERT OR IGNORE INTO settings VALUES ('daily_limit_enterprise', '200');
        INSERT OR IGNORE INTO settings VALUES ('default_daily_limit',  '5');
        INSERT OR IGNORE INTO settings VALUES ('allow_pay_over_limit', '1');  -- 1=allow wallet override, 0=block
        INSERT OR IGNORE INTO settings VALUES ('cryptobot_token',       '');
        INSERT OR IGNORE INTO settings VALUES ('heleket_api_key',       '');
        INSERT OR IGNORE INTO settings VALUES ('heleket_merchant_id',   '');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_starter_cost',  '29.99');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_starter_daily',  '100');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_starter_rate',   '10');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_pro_cost',       '99.99');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_pro_daily',     '500');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_pro_rate',      '30');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_enterprise_cost', '299.99');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_enterprise_daily', '2000');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_enterprise_rate',  '60');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_unlimited_cost', '999.99');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_unlimited_daily', '999999');
        INSERT OR IGNORE INTO settings VALUES ('api_tier_unlimited_rate', '300');

        -- Migration: add daily_limit column to existing users table
        try:
            await db.execute("ALTER TABLE users ADD COLUMN daily_limit INTEGER DEFAULT 0")
        except Exception:
            pass  -- column already exists

        CREATE TABLE IF NOT EXISTS subscription_plans (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    UNIQUE NOT NULL,
            tier        TEXT    NOT NULL DEFAULT 'basic',
            daily_limit INTEGER NOT NULL DEFAULT 10,
            monthly_price REAL  NOT NULL DEFAULT 0.0,
            features    TEXT    DEFAULT '{}',
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            plan_id         INTEGER NOT NULL,
            status          TEXT    DEFAULT 'active',
            searches_today  INTEGER DEFAULT 0,
            total_searches  INTEGER DEFAULT 0,
            reset_at        TEXT,
            created_at      TEXT    DEFAULT (datetime('now')),
            expires_at      TEXT,
            FOREIGN KEY (plan_id) REFERENCES subscription_plans(id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS api_keys (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            api_key     TEXT    UNIQUE NOT NULL,
            label       TEXT    DEFAULT 'default',
            daily_limit INTEGER DEFAULT 100,
            searches_today INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now')),
            last_used   TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        -- Migration: add tier/rate_limit/total_requests to api_keys (idempotent)
        PRAGMA foreign_keys=off;
        ALTER TABLE api_keys ADD COLUMN tier TEXT DEFAULT 'starter';
        ALTER TABLE api_keys ADD COLUMN rate_limit INTEGER DEFAULT 10;
        ALTER TABLE api_keys ADD COLUMN total_requests INTEGER DEFAULT 0;
        PRAGMA foreign_keys=on;

        INSERT OR IGNORE INTO subscription_plans (name, tier, daily_limit, monthly_price, features) VALUES
            ('Basic', 'basic', 10, 9.99, '{"phone":true,"address":true}'),
            ('Pro', 'pro', 50, 29.99, '{"phone":true,"address":true,"ssn":true,"dl":true}'),
            ('Enterprise', 'enterprise', 200, 99.99, '{"phone":true,"address":true,"ssn":true,"dl":true,"cr":true,"cs":true}');
        """)
        await db.commit()
    logger.info("Database initialized")


# ── Users ──────────────────────────────────────────────────────────────────────

async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def upsert_user(user_id: int, username: str, full_name: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name,
                last_seen = datetime('now')
        """, (user_id, username or "", full_name or ""))
        await db.commit()
    return await get_user(user_id)


async def get_all_users() -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def set_admin(user_id: int, is_admin: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_admin=? WHERE user_id=?", (int(is_admin), user_id)
        )
        await db.commit()


async def set_banned(user_id: int, banned: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned=? WHERE user_id=?", (int(banned), user_id)
        )
        await db.commit()


async def set_user_markup(user_id: int, pct: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET markup_pct=? WHERE user_id=?", (pct, user_id)
        )
        await db.commit()


async def add_balance(user_id: int, amount: float, comment: str = "", admin_id: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id)
        )
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, comment, admin_id) VALUES (?,?,'deposit',?,?)",
            (user_id, amount, comment, admin_id)
        )
        await db.commit()


async def deduct_balance(user_id: int, amount: float, comment: str = "") -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT balance FROM users WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row or row[0] < amount:
                return False
        await db.execute(
            "UPDATE users SET balance=balance-?, total_spent=total_spent+?, searches=searches+1 WHERE user_id=?",
            (amount, amount, user_id)
        )
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, comment) VALUES (?,?,'charge',?)",
            (user_id, -amount, comment)
        )
        await db.commit()
        return True


# ── Settings ───────────────────────────────────────────────────────────────────

async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else ""


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, value))
        await db.commit()


async def get_all_settings() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key, value FROM settings") as cur:
            return {r[0]: r[1] for r in await cur.fetchall()}


# ── SearchBug Accounts ─────────────────────────────────────────────────────────

async def get_sb_accounts() -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sb_accounts ORDER BY id") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def upsert_sb_account(email: str, password: str, proxy: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO sb_accounts (email, password, proxy)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                password = excluded.password,
                proxy    = excluded.proxy
        """, (email, password, proxy))
        await db.commit()


async def delete_sb_account(email: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sb_accounts WHERE email=?", (email,))
        await db.commit()


async def update_sb_account_status(
    email: str, status: str, balance: float = 0.0, init_tok: float = 0.0
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE sb_accounts
            SET status=?, balance_tok=?, last_check=datetime('now'),
                init_tok = CASE WHEN init_tok=0 THEN ? ELSE init_tok END
            WHERE email=?
        """, (status, balance, init_tok, email))
        await db.commit()


async def increment_sb_searches(email: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sb_accounts SET searches=searches+1 WHERE email=?", (email,)
        )
        await db.commit()


# ── Usfull Accounts ────────────────────────────────────────────────────────────

async def get_usfull_accounts() -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM usfull_accounts ORDER BY id") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def upsert_usfull_account(username: str, password: str, api_key: str = "", proxy: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO usfull_accounts (username, password, api_key, proxy)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password = excluded.password,
                api_key  = excluded.api_key,
                proxy    = excluded.proxy
        """, (username, password, api_key, proxy))
        await db.commit()


async def update_usfull_account_status(username: str, status: str, balance: float = 0.0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE usfull_accounts
            SET status=?, balance=?, last_check=datetime('now'),
                init_balance = CASE WHEN init_balance=0 THEN ? ELSE init_balance END
            WHERE username=?
        """, (status, balance, balance, username))
        await db.commit()


async def update_usfull_api_key(username: str, api_key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE usfull_accounts SET api_key=? WHERE username=?", (api_key, username)
        )
        await db.commit()


async def increment_usfull_searches(username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE usfull_accounts SET searches=searches+1 WHERE username=?", (username,)
        )
        await db.commit()


# ── Searches history ───────────────────────────────────────────────────────────

async def save_search(
    user_id: int, search_type: str, query: str,
    result_json: str, cost_user: float, cost_sb: float,
    status: str = "ok", source: str = "searchbug"
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO searches (user_id, search_type, source, query, result_json, cost_user, cost_sb, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, search_type, source, query, result_json, cost_user, cost_sb, status))
        await db.commit()


async def get_user_searches(user_id: int, limit: int = 50) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM searches WHERE user_id=? ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*), COALESCE(SUM(balance),0) FROM users"
        ) as cur:
            users_row = await cur.fetchone()
        async with db.execute(
            "SELECT COUNT(*) FROM searches WHERE status='ok'"
        ) as cur:
            searches_row = await cur.fetchone()
        async with db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='deposit'"
        ) as cur:
            deposits_row = await cur.fetchone()
        async with db.execute(
            "SELECT COALESCE(SUM(cost_user),0) FROM searches WHERE status='ok'"
        ) as cur:
            revenue_row = await cur.fetchone()
        async with db.execute(
            "SELECT COUNT(*) FROM sb_accounts WHERE status IN ('active','low_balance')"
        ) as cur:
            sb_active = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM sb_accounts") as cur:
            sb_total = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM usfull_accounts WHERE status IN ('active','low_balance')"
        ) as cur:
            uf_active = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM usfull_accounts") as cur:
            uf_total = (await cur.fetchone())[0]

        # Revenue by source
        async with db.execute(
            "SELECT COALESCE(SUM(cost_user),0) FROM searches WHERE status='ok' AND source IN ('enformion','searchbug')"
        ) as cur:
            rev_enf = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COALESCE(SUM(cost_user),0) FROM searches WHERE status='ok' AND source='usfull'"
        ) as cur:
            rev_uf = (await cur.fetchone())[0]

        # Revenue by search_type
        async with db.execute(
            "SELECT search_type, COALESCE(SUM(cost_user),0), COUNT(*) "
            "FROM searches WHERE status='ok' GROUP BY search_type"
        ) as cur:
            by_type = [{"type": r[0], "revenue": r[1], "count": r[2]} for r in await cur.fetchall()]

        # Today's stats
        async with db.execute(
            "SELECT COALESCE(SUM(cost_user),0), COUNT(*) FROM searches "
            "WHERE status='ok' AND date(created_at)=date('now')"
        ) as cur:
            today_row = await cur.fetchone()
        async with db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions "
            "WHERE type='deposit' AND date(created_at)=date('now')"
        ) as cur:
            today_dep = (await cur.fetchone())[0]

        # Active sessions
        async with db.execute(
            "SELECT COUNT(DISTINCT user_id) FROM searches "
            "WHERE date(last_seen)=date('now') OR date(created_at)=date('now')"
        ) as cur:
            active_users_today = (await cur.fetchone())[0]

        return {
            "users":              users_row[0],
            "total_balance":      round(users_row[1], 2),
            "searches":           searches_row[0],
            "total_deposits":     round(deposits_row[0], 2),
            "total_revenue":      round(revenue_row[0], 2),
            "profit":             round(revenue_row[0] - deposits_row[0], 2),
            "sb_active":          sb_active,
            "sb_total":           sb_total,
            "uf_active":          uf_active,
            "uf_total":           uf_total,
            "rev_enf":            round(rev_enf, 2),
            "rev_uf":             round(rev_uf, 2),
            "by_type":           by_type,
            "today_revenue":     round(today_row[0], 2),
            "today_searches":    today_row[1],
            "today_deposits":    round(today_dep, 2),
            "active_users_today": active_users_today,
        }


# ── Payments ───────────────────────────────────────────────────────────────────

async def create_payment(
    user_id: int, provider: str, invoice_id: str,
    amount: float, currency: str = "USD", payload: str = ""
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO payments (user_id, provider, invoice_id, amount, currency, payload)
            VALUES (?,?,?,?,?,?)
        """, (user_id, provider, invoice_id, amount, currency, payload))
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as cur:
            row = await cur.fetchone()
            return row[0]


async def get_payment_by_invoice(invoice_id: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE invoice_id=?", (invoice_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def confirm_payment(invoice_id: str) -> Optional[dict]:
    """Mark payment as confirmed and credit user balance."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE invoice_id=?", (invoice_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        if row["status"] == "confirmed":
            return dict(row)
        await db.execute(
            "UPDATE payments SET status='confirmed', confirmed_at=datetime('now') WHERE invoice_id=?",
            (invoice_id,)
        )
        await db.execute(
            "UPDATE users SET balance=balance+? WHERE user_id=?",
            (row["amount"], row["user_id"])
        )
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, comment) VALUES (?,?,'deposit',?)",
            (row["user_id"], row["amount"], f"Payment via {row['provider']}")
        )
        await db.commit()
        return dict(row)


async def get_user_payments(user_id: int, limit: int = 10) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ── Search Cache ──────────────────────────────────────────────────────────────

async def get_cached(cache_key: str) -> Optional[dict]:
    """Get cached search result if not expired."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM search_cache WHERE cache_key=? AND expires_at > datetime('now')",
            (cache_key,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                import json
                return json.loads(row["result_json"])
            return None


async def set_cache(cache_key: str, result: dict, ttl_hours: int = 24):
    """Cache a search result."""
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO search_cache (cache_key, result_json, expires_at)
            VALUES (?, ?, datetime('now', '+' || ? || ' hours'))
        """, (cache_key, json.dumps(result), ttl_hours))
        await db.commit()


async def clear_expired_cache():
    """Remove expired cache entries."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM search_cache WHERE expires_at <= datetime('now')")
        await db.commit()


# ── Guarantee searches ──────────────────────────────────────────────────────

async def create_guarantee(
    user_id: int,
    search_type: str,
    query: str,
    cost_user: float = 0.0,
    search_id: str = "",
) -> int:
    """Create a new guarantee entry for a search. Expires in 8 days."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO guarantee_searches (user_id, search_id, search_type, query, cost_user, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (user_id, search_id or "", search_type, query, cost_user))
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as cur:
            row = await cur.fetchone()
            return row[0]


async def get_guarantee(guarantee_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guarantee_searches WHERE id=?", (guarantee_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_active_guarantees(user_id: int) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM guarantee_searches
            WHERE user_id=? AND status='active' AND expires_at > datetime('now')
            ORDER BY created_at DESC
        """, (user_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def update_guarantee_phase(guarantee_id: int, phase: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE guarantee_searches
            SET current_phase=?, reminded_phase=?, last_reminder_at=datetime('now')
            WHERE id=?
        """, (phase, phase, guarantee_id))
        await db.commit()


async def expire_guarantee(guarantee_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE guarantee_searches SET status='expired' WHERE id=?",
            (guarantee_id,)
        )
        await db.commit()


async def get_guarantee_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM guarantee_searches WHERE user_id=? AND status='active'",
            (user_id,)
        ) as cur:
            active = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM guarantee_searches WHERE user_id=? AND status='expired'",
            (user_id,)
        ) as cur:
            expired = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM guarantee_searches WHERE user_id=?",
            (user_id,)
        ) as cur:
            total = (await cur.fetchone())[0]
        return {"total": total, "active": active, "expired": expired}


# ── Notifications ───────────────────────────────────────────────────────────

async def create_notification(
    user_id: int,
    kind: str,
    title: str,
    body: str,
    metadata: dict = None,
) -> int:
    """Create an in-app notification."""
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO notifications (user_id, kind, title, body, metadata_json)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id, kind, title, body,
            json.dumps(metadata or {}, ensure_ascii=False)
        ))
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as cur:
            row = await cur.fetchone()
            return row[0]


async def get_user_notifications(user_id: int, limit: int = 20,
                                  unread_only: bool = False) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        where = "AND status='unread'" if unread_only else ""
        async with db.execute(f"""
            SELECT * FROM notifications
            WHERE user_id=? {where}
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def mark_notification_read(notification_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE notifications SET status='read', read_at=datetime('now')
            WHERE id=?
        """, (notification_id,))
        await db.commit()


async def mark_all_notifications_read(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE notifications SET status='read', read_at=datetime('now')
            WHERE user_id=? AND status='unread'
        """, (user_id,))
        await db.commit()


async def get_unread_notification_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND status='unread'",
            (user_id,)
        ) as cur:
            return (await cur.fetchone())[0]


# ── Admin logs ────────────────────────────────────────────────────────────────

async def log_admin_action(admin_id: int, action: str, target_type: str = "",
                            target_id: str = "", details: str = "", ip: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO admin_logs (admin_id, action, target_type, target_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (admin_id, action, target_type, target_id, details, ip))
        await db.commit()


async def get_admin_logs(limit: int = 100, admin_id: Optional[int] = None) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?"
        args = [limit]
        if admin_id:
            query = "SELECT * FROM admin_logs WHERE admin_id=? ORDER BY created_at DESC LIMIT ?"
            args = [admin_id, limit]
        async with db.execute(query, args) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ── Webhook logs ─────────────────────────────────────────────────────────────

async def log_webhook(provider: str, event_type: str, invoice_id: str = "",
                      user_id: int = 0, payload_md5: str = "", status_code: int = 0,
                      error_msg: str = "", processed: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO webhook_logs (provider, event_type, invoice_id, user_id,
                                      payload_md5, status_code, error_msg, processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (provider, event_type, invoice_id, user_id, payload_md5, status_code, error_msg, processed))
        await db.commit()


async def get_webhook_logs(limit: int = 100, provider: str = "") -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM webhook_logs ORDER BY created_at DESC LIMIT ?"
        args = [limit]
        if provider:
            query = "SELECT * FROM webhook_logs WHERE provider=? ORDER BY created_at DESC LIMIT ?"
            args = [provider, limit]
        async with db.execute(query, args) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ── Rate limiting ────────────────────────────────────────────────────────────

async def check_rate_limit(user_id: int, action: str, max_count: int = 10,
                            window_seconds: int = 60) -> bool:
    """
    Check if user is within rate limit. Returns True if allowed, False if exceeded.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT count, window_start FROM rate_limits
            WHERE user_id=? AND action=?
        """, (user_id, action)) as cur:
            row = await cur.fetchone()

        if not row:
            await db.execute("""
                INSERT INTO rate_limits (user_id, action, count, window_start)
                VALUES (?, ?, 1, datetime('now'))
            """, (user_id, action))
            await db.commit()
            return True

        count, window_start_str = row
        # Check if window expired via SQL
        async with db.execute("""
            SELECT (julianday('now') - julianday(?)) * 86400 > ?
        """, (window_start_str, window_seconds)) as cur:
            expired = await cur.fetchone()
            is_expired = expired and expired[0] > 0

        if is_expired:
            await db.execute("""
                UPDATE rate_limits SET count=1, window_start=datetime('now')
                WHERE user_id=? AND action=?
            """, (user_id, action))
            await db.commit()
            return True

        if count >= max_count:
            return False

        await db.execute("""
            UPDATE rate_limits SET count=count+1
            WHERE user_id=? AND action=?
        """, (user_id, action))
        await db.commit()
        return True


async def get_rate_limit_remaining(user_id: int, action: str, max_count: int = 10,
                                     window_seconds: int = 60) -> tuple[int, int]:
    """
    Returns (remaining, seconds_until_reset).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT count, window_start FROM rate_limits WHERE user_id=? AND action=?
        """, (user_id, action)) as cur:
            row = await cur.fetchone()

        if not row:
            return max_count, 0

        count, window_start_str = row
        async with db.execute("""
            SELECT (julianday('now') - julianday(?)) * 86400
        """, (window_start_str,)) as cur:
            elapsed = await cur.fetchone()
            elapsed_val = elapsed[0] if elapsed else 0

        if elapsed_val >= window_seconds:
            return max_count, 0

        remaining = max(0, max_count - count)
        reset_in = int(window_seconds - elapsed_val)
        return remaining, reset_in


# ── Per-user daily search limits ──────────────────────────────────────────────

async def get_user_daily_limit(user_id: int) -> int:
    """Get daily search limit for user. Returns per-user override or default."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT daily_limit FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
    if row and row["daily_limit"] > 0:
        return row["daily_limit"]
    # Fall back to default
    default = await get_setting("default_daily_limit")
    return int(default) if default else 5


async def set_user_daily_limit(user_id: int, limit_val: int) -> None:
    """Set per-user daily limit override. 0 = inherit from plan/default."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET daily_limit=? WHERE user_id=?",
            (limit_val, user_id)
        )
        await db.commit()


async def get_daily_search_count(user_id: int) -> int:
    """Count searches by user today (since midnight)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT COUNT(*) FROM searches
            WHERE user_id=? AND date(created_at) = date('now')
        """, (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def check_daily_limit(user_id: int) -> tuple[bool, int, int]:
    """
    Returns (allowed, remaining, limit).
    - allowed=True + remaining=-1 → unlimited (no limit)
    - allowed=True + remaining>=0 → within limit
    - allowed=False → limit exceeded
    """
    limit = await get_user_daily_limit(user_id)
    if limit == 0:
        return True, -1, -1
    used = await get_daily_search_count(user_id)
    remaining = limit - used
    return remaining >= 0, remaining, limit


async def get_daily_limit_reset_seconds() -> int:
    """Seconds until midnight UTC (when daily counters reset)."""
    import time
    now = time.time()
    midnight = 86400 - (now % 86400)
    return int(midnight)


async def increment_daily_usage(user_id: int) -> None:
    """
    Increment per-user daily usage counter.
    No-op if user has no per-user limit override (counter based on searches table).
    """
    pass  # Counter is derived from searches table — no separate counter needed


# ── User alerts ───────────────────────────────────────────────────────────────

async def create_user_alert(user_id: int, alert_type: str, message: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_alerts (user_id, alert_type, message)
            VALUES (?, ?, ?)
        """, (user_id, alert_type, message))
        await db.commit()


async def get_user_alerts(user_id: int, limit: int = 20,
                           unread_only: bool = False) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM user_alerts WHERE user_id=?"
        if unread_only:
            query += " AND is_read=0"
        query += " ORDER BY created_at DESC LIMIT ?"
        async with db.execute(query, (user_id, limit)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def mark_user_alert_read(alert_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE user_alerts SET is_read=1 WHERE id=?", (alert_id,))
        await db.commit()


# ── User search helpers ──────────────────────────────────────────────────────

async def find_user(query: str) -> Optional[dict]:
    """Search user by user_id or username (partial match)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        try:
            uid = int(query)
            async with db.execute("SELECT * FROM users WHERE user_id=?", (uid,)) as cur:
                row = await cur.fetchone()
                if row:
                    return dict(row)
        except ValueError:
            pass
        # Try username match
        async with db.execute(
            "SELECT * FROM users WHERE username LIKE ? LIMIT 5",
            (f"%{query}%",)
        ) as cur:
            rows = await cur.fetchall()
            if rows:
                return [dict(r) for r in rows]
    return None


# ── Subscriptions ───────────────────────────────────────────────────────────

async def get_subscription(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT s.*, p.name as plan_name, p.tier, p.daily_limit, p.features
            FROM subscriptions s JOIN subscription_plans p ON s.plan_id = p.id
            WHERE s.user_id=? AND s.status='active'
        """, (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def check_subscription_limit(user_id: int) -> tuple[bool, int, int]:
    """
    Returns (allowed, remaining, daily_limit).
    - allowed=True + remaining=-1 → unlimited (no per-user limit set)
    - allowed=True + remaining>=0 → within limit
    - allowed=False → limit exceeded

    Priority: per-user daily_limit override > subscription plan daily_limit > default
    """
    # 1. Check per-user override first
    user = await get_user(user_id)
    user_daily = user.get("daily_limit", 0) if user else 0
    if user_daily > 0:
        used = await get_daily_search_count(user_id)
        remaining = user_daily - used
        return remaining >= 0, remaining, user_daily

    # 2. Check subscription plan
    sub = await get_subscription(user_id)
    if sub:
        today = datetime.now().strftime("%Y-%m-%d")
        if sub.get("reset_at", "")[:10] != today:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE subscriptions SET searches_today=0, reset_at=datetime('now','start of day') WHERE user_id=?",
                    (user_id,)
                )
                await db.commit()
            sub["searches_today"] = 0
        remaining = sub["daily_limit"] - sub["searches_today"]
        return remaining > 0, remaining, sub["daily_limit"]

    # 3. Fall back to global default
    default = int(await get_setting("default_daily_limit") or "5")
    used = await get_daily_search_count(user_id)
    remaining = default - used
    return remaining >= 0, remaining, default


async def increment_subscription_usage(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET searches_today=searches_today+1, total_searches=total_searches+1 WHERE user_id=? AND status='active'",
            (user_id,)
        )
        await db.commit()


async def create_subscription(user_id: int, plan_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO subscriptions (user_id, plan_id, status, reset_at, expires_at)
            VALUES (?, ?, 'active', datetime('now','start of day'), datetime('now','+30 days'))
        """, (user_id, plan_id))
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as cur:
            return (await cur.fetchone())[0]


async def cancel_subscription(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET status='cancelled' WHERE user_id=?",
            (user_id,)
        )
        await db.commit()


async def get_all_subscription_plans() -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM subscription_plans WHERE is_active=1") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_api_key(key: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM api_keys WHERE api_key=? AND (last_used IS NULL OR datetime(last_used) > datetime('now','-1 hour'))", (key,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def increment_api_key_usage(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE api_keys SET searches_today=searches_today+1, last_used=datetime('now') WHERE api_key=?",
            (key,)
        )
        await db.commit()


# ── API Keys ──────────────────────────────────────────────────────────────────

async def create_api_key(user_id: int, label: str = "default") -> Optional[dict]:
    import secrets
    key = "sk_" + secrets.token_urlsafe(32)
    tier = "starter"
    async with aiosqlite.connect(DB_PATH) as db:
        # Get default daily/rate from starter settings
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT value FROM settings WHERE key='api_tier_starter_daily'") as cur:
            row = await cur.fetchone()
            daily = int(row[0]) if row else 100
        async with db.execute("SELECT value FROM settings WHERE key='api_tier_starter_rate'") as cur:
            row = await cur.fetchone()
            rate = int(row[0]) if row else 10
        await db.execute("""
            INSERT INTO api_keys (user_id, api_key, label, tier, daily_limit, rate_limit)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, key, label, tier, daily, rate))
        await db.commit()
    return await get_api_key_by_key(key)


async def get_api_key_by_key(key: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM api_keys WHERE api_key=?", (key,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_api_keys_for_user(user_id: int) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, user_id, api_key, label, tier, daily_limit, rate_limit,
                   searches_today, total_requests, created_at, last_used
            FROM api_keys WHERE user_id=?
        """, (user_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def revoke_api_key(key_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM api_keys WHERE id=? AND user_id=?", (key_id, user_id))
        await db.commit()
        return cur.rowcount > 0


async def check_api_rate_limit(key_id: int) -> tuple[bool, int, int]:
    """
    Sliding window rate limiting per API key.
    Returns (allowed, remaining, limit_per_minute).
    """
    global _api_rate_window
    now = time.time()
    window = 60.0

    if key_id not in _api_rate_window:
        _api_rate_window[key_id] = collections.deque()

    dq = _api_rate_window[key_id]
    # Clean old entries
    cutoff = now - window
    while dq and dq[0] < cutoff:
        dq.popleft()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT rate_limit, daily_limit, searches_today FROM api_keys WHERE id=?",
            (key_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, 0, 0
            rate_limit = row['rate_limit']
            daily_limit = row['daily_limit']
            searches_today = row['searches_today']


    if len(dq) >= rate_limit:
        return False, 0, rate_limit
    dq.append(now)
    remaining_daily = max(0, daily_limit - searches_today)
    return True, remaining_daily, rate_limit


async def increment_api_usage(key_id: int, count: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE api_keys
            SET searches_today = searches_today + ?,
                total_requests = total_requests + ?,
                last_used = datetime('now')
            WHERE id=?
        """, (count, count, key_id))
        await db.commit()


async def reset_api_daily_counters():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE api_keys SET searches_today = 0")
        await db.commit()


async def get_api_tier_settings(tier: str) -> dict:
    prefix = f"api_tier_{tier}"
    async with aiosqlite.connect(DB_PATH) as db:
        rows = {}
        async with db.execute(
            "SELECT key, value FROM settings WHERE key LIKE ?", (f"{prefix}%",)) as cur:
            for row in await cur.fetchall():
                k = row[0].replace(f"{prefix}_", "")
                try:
                    rows[k] = float(row[1])
                except ValueError:
                    rows[k] = row[1]
        return rows


async def update_api_key_tier(key_id: int, user_id: int, tier: str):
    tier_settings = await get_api_tier_settings(tier)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE api_keys
            SET tier=?, daily_limit=?, rate_limit=?
            WHERE id=? AND user_id=?
        """, (
            tier,
            int(tier_settings.get('daily', 100)),
            int(tier_settings.get('rate', 10)),
            key_id, user_id
        ))
        await db.commit()
