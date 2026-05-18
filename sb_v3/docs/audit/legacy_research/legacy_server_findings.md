# Legacy server findings for ONE CS

## Summary

I connected to the remote server `193.221.200.87` and searched the main system locations for legacy bot code, archives, and candidate project directories. The only clearly relevant artifact found on the server was `/root/credit_score_bot_v3.zip`.

After pulling and unpacking the archive locally into `legacy_research/extracted/credit_score_bot/`, I verified that it contains a **Python Telegram credit score bot prototype**, not a full ONE CS platform and not the current TypeScript admin system.

## What was found on the server

| Item | Path | Finding |
|---|---|---|
| Legacy archive | `/root/credit_score_bot_v3.zip` | Present and readable |
| Hostname | `lovely-east.yeezyhost.net` | Server reachable |
| Other obvious ONE CS directories | `/root`, `/home`, `/opt`, `/var/www`, `/srv` | No clearly named unpacked ONE CS project found during targeted search |

## Legacy archive structure

The archive contains a Python bot with these main areas:

| Area | Purpose |
|---|---|
| `app/handlers/` | Telegram bot handlers for form flow, bulk flow, SSN retry flow |
| `app/services/` | Worker pool, batch processor, retry manager |
| `cs_module/workers/cs_worker.py` | Main browser automation worker |
| `cs_module/bot_interface/models.py` | Request/result data contracts |
| `cs_module/core/queue.py` | Queue and worker-pool orchestration |
| `cs_module/proxy/manager.py` | Proxy rotation |
| `cs_module/fingerprint/rotator.py` | Fingerprint rotation |
| `cs_module/antidetect/human.py` | Anti-detection behaviour |
| `cs_module/test_local.py` | Local extraction test for score retrieval from PDF |

## What the legacy code actually does

The legacy archive implements a **credit-score retrieval pipeline** centered on `universal-credit.com`, with optional fallback through SSN flow.

The old result contract in `cs_module/bot_interface/models.py` contains:

| Field | Meaning |
|---|---|
| `status` | `pending`, `running`, `waiting_ssn`, `success`, `failed`, `cancelled` |
| `credit_score` | Integer result |
| `source` | Source website |
| `pdf_path` | Downloaded PDF path |
| `worker_id` | Worker identifier |
| `proxy_ip` | Proxy used |
| `duration_seconds` | Processing duration |
| `needs_ssn` | Whether user input is needed to continue |

The old user-facing summary is limited to a simple success/failure message. It does **not** include the richer ONE CS card format requested now.

## Score extraction logic found

The clearest concrete extraction logic appears in `cs_module/test_local.py`.

The legacy implementation searches extracted PDF text with patterns such as:

- `credit score`
- `fico score`
- `score value`
- `your score is`

It then parses a **3-digit score** and accepts it only if it is in the range **300 to 850**.

## Important gap: no separate 1–10 data quality algorithm found

I searched the archive contents for terms related to:

- `quality`
- `data quality`
- `quality score`
- `1-10`
- `1 to 10`
- pricing, subscriptions, API key issuance, BTCPay, Crypto Bot

The result is clear: the recovered archive contains **credit-score retrieval logic only**. I did **not** find a standalone legacy implementation of:

| Missing from recovered archive | Status |
|---|---|
| Data quality scoring on a 1–10 scale | Not found |
| ONE CS 1–20 credit score normalization | Not found |
| Crypto payment integration | Not found |
| API key auto-issuance after payment | Not found |
| Multi-language onboarding | Not found |
| Rich admin controls for broadcast/force stop/content/pricing | Not found in this archive |

## Comparison with the current TypeScript project

The current project already contains infrastructure for a larger platform than the recovered archive:

| Current project capability | Status in current repo |
|---|---|
| Admin panel sections | Present |
| DB schema for subscriptions and payment providers (`btcpay`, `cryptobot`, `manual`) | Present |
| Telegram endpoint schema | Present |
| Bulk job schemas | Present |
| Imported lead parser with `credit score: ###` parsing | Present |
| Separate 1–10 data quality algorithm | Not present yet |
| Full Telegram user bot flow | Not implemented yet |

The current parser integration point is `shared/importedLeadFormat.ts`. It currently extracts legacy raw `credit score: ###` values and computes only a `completenessScore` from `0` to `1`, which is **not** the requested 1–10 data quality score.

## Practical conclusion

The remote server search was successful in one important sense: it recovered a **useful legacy credit-score bot archive**. However, that archive does **not** contain the full historical ONE CS business logic that we still need.

So the current situation is:

| Topic | Conclusion |
|---|---|
| Legacy credit-score retrieval flow | Recovered |
| Legacy worker/proxy/SSN queue design | Recovered |
| Legacy 300–850 score extraction | Recovered |
| Legacy 1–10 data quality logic | Not recovered |
| Legacy ONE CS 1–20 score mapping | Not recovered |
| Payment/API/subscription lifecycle | Not recovered in this archive |

## Recommended next implementation path

The archive is still valuable and can be reused as a behavioural reference for:

1. job lifecycle states;
2. worker queue and batch progress flow;
3. SSN wait/resume behaviour;
4. result metadata such as duration, source, worker, and failure reason.

The missing parts now need to be defined or reconstructed in the current TypeScript system:

| Priority | Next step |
|---|---|
| 1 | Define the new ONE CS mapping from raw `300–850` credit score to product score `1–20` |
| 2 | Define the new `dataQualityScore` formula on a `1–10` scale |
| 3 | Add both fields to shared result models, bot cards, CSV/TXT exports, and admin analytics |
| 4 | Reuse legacy state ideas (`waiting_ssn`, worker duration, source, retry flow) in the TypeScript job model |
| 5 | Implement Telegram flow, payment confirmation, and API key issuance in the current stack |

## Local paths saved for follow-up

| Purpose | Path |
|---|---|
| Pulled archive | `/home/ubuntu/csbot_admin_system/legacy_research/credit_score_bot_v3.zip` |
| Extracted legacy code | `/home/ubuntu/csbot_admin_system/legacy_research/extracted/credit_score_bot/` |
| Findings report | `/home/ubuntu/csbot_admin_system/legacy_research/legacy_server_findings.md` |
