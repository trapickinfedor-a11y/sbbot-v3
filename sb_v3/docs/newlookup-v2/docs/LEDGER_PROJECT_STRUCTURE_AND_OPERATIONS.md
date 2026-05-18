# Ledger Project Structure And Operations

## Goal
`ledger` is the financial source of truth.

`balance`, `pending_balance`, `withdrawable_balance`, `total_earned`, `total_withdrawn` are now projection fields that must be derived from `transactions`, not treated as independent finance state.

## Core Structure
- `shared/database/models.py`
  Main financial entities and the canonical `Transaction` ledger table.
- `shared/services/ledger_service.py`
  All write-side financial mutations. New money movement must enter here or through a service that calls it.
- `shared/services/ledger_projection_service.py`
  Read-side projections from ledger into account balances and payout views.
- `shared/services/ledger_reconciliation_service.py`
  Drift detection between ledger-derived expectations and stored projection fields.
- `shared/tasks/auto_complete.py`
  Scheduled settlement of matured ledger entries.
- `web_panel/api/deposits.py`
  Admin ledger explorer, manual reconciliation trigger, projection diagnostics API.
- `web_panel/templates/deposits.html`
  Finance/ops dashboard for ledger events and reconciliation.

## Financial Source Of Truth Rules
1. Never change `user.balance`, `worker.balance`, `marketer.balance`, `owner.balance`, `seller.pending_balance`, `seller.withdrawable_balance` directly in feature code.
2. Create or transition ledger entries first.
3. Let `LedgerService` resync projections through `LedgerProjectionService`.
4. If a feature only needs to read available funds, prefer projection reads over trusting stale model fields.
5. `seller.deposit_balance` is no longer a finance source of truth. It is legacy/non-ledger data and must not be used to authorize withdrawals.

## Write Paths
- Buyer funds: `LedgerService.credit_user_balance()`, `debit_user_balance()`, `refund_user_transaction()`
- Seller escrow: `create_seller_hold()`, `settle_seller_hold()`, `dispute_seller_hold()`, `fail_seller_hold()`
- Seller instant credits outside hold flow: `credit_seller_balance()`
- Worker payouts: `credit_worker_balance()`, `reserve_worker_withdrawal()`, `finalize_worker_withdrawal()`, `release_worker_withdrawal_reservation()`
- Marketer payouts: `credit_marketer_balance()`, `reserve_marketer_withdrawal()`, `finalize_marketer_withdrawal()`, `release_marketer_withdrawal_reservation()`
- Owner payouts: `credit_owner_balance()`, `reserve_owner_withdrawal()`, `finalize_owner_withdrawal()`, `release_owner_withdrawal_reservation()`

## Read Paths
- User balance projection: `LedgerProjectionService.get_user_balance()`
- Seller payout projection: `LedgerProjectionService.get_seller_projection()`
- Worker projection: `LedgerProjectionService.get_worker_projection()`
- Marketer projection: `LedgerProjectionService.get_marketer_projection()`
- Owner projection: `LedgerProjectionService.get_owner_projection()`

## Reconciliation
- Automatic periodic job is started from `web_panel/main.py`
- Manual trigger:
  `POST /api/deposits/reconciliation/run`
- Dashboard:
  `/deposits`

What reconciliation checks:
- `user.balance`
- `seller.pending_balance`
- `seller.withdrawable_balance`
- `seller.total_earned`
- `worker.balance`, `worker.total_earned`, `worker.total_withdrawn`
- `marketer.balance`, `marketer.total_earned`, `marketer.total_withdrawn`
- `owner.balance`, `owner.total_earned`, `owner.total_withdrawn`

## Admin / Ops Diagnostics
- Ledger event explorer:
  `/deposits`
- Projection lookup API:
  `GET /api/deposits/projection?account_type=<type>&account_id=<id>`
- Manual reconciliation:
  `POST /api/deposits/reconciliation/run`
- Seller disputes board:
  `/seller-crm`
- Worker performance summary:
  `GET /api/workers/stats`

Recommended ops flow:
1. Open `/deposits`
2. Filter by `account_type`, `account_id`, `status`, `type`, or search by idempotency key
3. Inspect related entity and status transitions
4. Run reconciliation
5. If projection drift exists, investigate duplicated retries, manual DB edits, or legacy code path writes

## Seller / Worker Withdrawals
New seller and worker withdrawal requests now live in the main DB:
- Seller: `SellerWithdrawal`
- Worker: `WorkerWithdrawal`

Compatibility routes still exist:
- `/api/seller-crm/withdrawal-tasks`
- `/api/worker-crm/withdrawal-tasks`

These routes are now compatibility aliases over main DB withdrawal records. Seller admin UI should use `/withdrawals`; legacy `/withdrawal-tasks` stays only for compatibility.

## tasks DB Scope
`tasks DB` should no longer be used as the primary financial store.

Keep it only for non-financial background/task workloads until those are migrated separately.

Runtime scope now:
- `WorkerReminderTask` and similar background reminders
- no seller/worker payout requests

## Dynamic Escrow Hold
Seller escrow maturity is no longer fixed.

Policy:
- New seller (`total_orders < ESCROW_NEW_SELLER_SALES_THRESHOLD`) uses `ESCROW_HOLD_NEW_SELLER_HOURS`
- Top seller (`likes/dislikes` reputation score >= `ESCROW_TOP_SELLER_SCORE_X10 / 10`) uses `ESCROW_HOLD_TOP_SELLER_HOURS`
- Everyone else uses `ESCROW_HOLD_STANDARD_HOURS`

Relevant settings live in `SystemSetting`.
- Risky buyer (`trust_score <= BUYER_TRUST_SCORE_RISK_THRESHOLD`) escalates hold to `ESCROW_HOLD_RISKY_BUYER_HOURS`.

## Seller Mini App Business Surface
- Seller workspace now includes:
  analytics summary, finance summary/export, vacation mode, upload templates, listings view, and bulk repricing.
- Key routes:
  `GET /api/seller-mini-app/listings`,
  `POST /api/seller-mini-app/listings/bulk-price`,
  `GET /api/seller-mini-app/templates`,
  `POST /api/seller-mini-app/templates`,
  `DELETE /api/seller-mini-app/templates/{template_id}`
- Vacation mode is operational, not cosmetic:
  buyer-facing seller-bank availability and menu counts must exclude sellers with `is_on_vacation = true`.

## Worker Privacy
Worker order views in `support_bot/handlers/work_orders.py` must not expose raw buyer PII.

Allowed worker-side display:
- service/category/state/quantity
- non-sensitive field presence metadata

Blocked from worker-side display:
- name
- address
- SSN/DOB/DL
- phone/email
- other raw buyer identifiers

## Adding New Financial Features
Checklist:
1. Define transaction type, relation type, and idempotency key shape.
2. Write through `LedgerService`.
3. Read through `LedgerProjectionService` if the feature needs current balances.
4. Add reconciliation-safe tests.
5. Add race/idempotency tests for retries or repeated approval clicks.
6. Expose an admin diagnostic path if operators will need to inspect the flow manually.

## Testing Priorities
- Idempotent repeat calls
- Reserve/finalize/release sequences
- Drift correction through projection resync
- Approval/reject double-submit safety
- Hold maturity and release timing
- Admin compatibility routes over main DB withdrawals

## Legacy / Future Cleanup
- Remove remaining legacy docs that still describe tasks DB as finance source
- Expand browser/E2E coverage for admin payout workflows
- Add bulk export and account drill-down shortcuts from the ledger dashboard
