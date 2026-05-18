# Shared Services

[[MOC]] > Shared Services

**78 файлов** | Общий слой: модели, сервисы, утилиты, middleware

---

## shared/__init__.py — 1 строка
## shared/brute_bank_group_key.py — 9 строк
**Функции:** `make_brute_group_key(bank_code: str, attributes: Optional...)`

## shared/catalog.py — 59 строк
**Функции:** `get_bank_types_for_category(session, ...)`, `get_bank_by_id_from_catalog(bank_id)`, `get_bank_name_by_id(session, bank_id)`
**Cross-imports:** `shared.database.models.BankItem`, `shared.catalog_banks.BANK_CATALOG`

## shared/catalog_banks.py — 82 строки
## shared/cc_catalog.py — 137 строк
**Функции:** `get_cc_categories(session)`, `get_cc_types_for_category(session, cat)`, `get_cc_items_for_category(...)`, `get_cc_item_name(session, cc_code)`
**Cross-imports:** `shared.database.models.CCCategory`, `CCItem`, `SellerCCItem`, `Seller`

---

## shared/config/

### env_utils.py — 79 строк
**Классы:** `StartupValidationError(RuntimeError)`
**Функции:** `parse_int_env(name, default)`, `parse_float_env(name, default)`, `parse_int_list_env(name)`, `validate_startup_env(...)`

### settings.py — 39 строк
**Классы:** `GlobalSettings`
**Функции:** `is_sqlite(self)`, `nocodb_enabled(self)`

---

## shared/database/

### models.py — 2804 строки → см. [[DB Models]]

### session.py — 2300 строк
**Функции:** `init_db()`, `_run_post_create_migrations()`, `get_session()`
**Cross-imports:** `shared.database.models.Base`, `ProductCatalogManager`, `MenuCategoryService`, `PricingConfigService`
**TODO:** 38 заглушек

### task_models.py — 35 строк
**Классы:** `TaskBase(DeclarativeBase)`, `WorkerReminderTask(TaskBase)`

### tasks_session.py — 55 строк
**Функции:** `_resolve_tasks_database_url()`, `init_tasks_db()`, `get_tasks_session()`

### migrations/ — 3 файла
- `add_bank_requests.py` — 71 строка (`upgrade()`, `downgrade()`)
- `sync_mini_app_v2.py` — 233 строки
- `v24_001_additions.py` — 291 строка

---

## shared/middlewares/

### error_logging.py — 72 строки
**Классы:** `GlobalErrorLoggingMiddleware(BaseMiddleware)`
**Функции:** `_event_user_id(event)`, `__init__(self, source)`, `__call__(...)`

---

## shared/security/internal_api.py — 31 строка
**Функции:** `get_internal_api_token()`, `build_internal_api_headers()`, `verify_internal_api_request(...)`

---

## shared/nocodb/

### client.py — 138 строк
**Классы:** `NocoDBClient`
**Функции (8):** `__init__`, `_url(path)`, `list_records(...)`, `create_record(...)`, `create_records_bulk(...)`, `update_record(...)`, `delete_record(...)`, `test_connection()`
**API:** `{base_url}/api/v2{path}`

---

## shared/services/ (40+ сервисов)

### ledger_service.py — 1072 строки
**Классы:** `LedgerService`
**Функции (43):** `money(value)`, `_has_account_transactions(...)`, `_bootstrap_user_if_needed(...)`, `_bootstrap_seller_if_needed(...)`, `_bootstrap_worker_if_needed(...)`, `_bootstrap_marketer_if_needed(...)`, `_bootstrap_owner_if_needed(...)`, `_sync_projection(...)`, `build_idempotency_key(*parts)`, `get_transaction(...)`, `create_entry(...)`, `_lock_user(...)`, `_lock_seller(...)`, `_lock_worker(...)`, `_lock_marketer(...)`, `_lock_owner(...)`, `credit_user_balance(...)`, `debit_user_balance(...)`, `refund_user_transaction(...)`, `mark_transaction_completed(...)`, `mark_transaction_disputed(...)`, `mark_transaction_failed(...)`, `create_seller_hold(...)`, `settle_seller_hold(...)`, `dispute_seller_hold(...)`, `fail_seller_hold(...)`, `credit_worker_balance(...)`, `credit_marketer_balance(...)`, `credit_owner_balance(...)`, `credit_seller_balance(...)`
**Cross-imports:** `shared.database.models.(...)`, `LedgerProjectionService`

### seller_upload_pipeline_service.py — 1363 строки
**Классы:** `SellerUploadPipelineService`
**Функции (39):** `_slugify(value)`, `_build_market_bank_code(...)`, `parse_price(value)`, `parse_log_details(raw_text)`, `_infer_card_brand(number, item_name)`, `parse_cc_line_flexible(...)`, `_sample_presence_flags(...)`, `parse_logs_bulk_text(raw_text)`, `parse_selfreg_ba_bulk_text(raw_text)`, `parse_brute_universal_text(raw_text, default_price)`, `parse_text_mapping(raw_text)`, `normalize_nfc_payload(...)`, `normalize_otp_payload(...)`, `normalize_selfreg_cc_payload(...)`, `parse_enroll_zip(zip_bytes, price)`, `inspect_enroll_archive(zip_bytes)`, `parse_selfreg_ba_zip(...)`, `inspect_selfreg_ba_archive(...)`, ...
**Cross-imports:** `BruteBankGroup`, `BruteBankItem`, `SellerBank`, `NocoDBService`, `SellerUploadBatchService`

### seller_order_delivery_service.py — 619 строк
**Классы:** `SellerOrderPolicy`
**Функции (25):** `_sync_bank_stock_flags(bank)`, `format_seller_order_window_label(minutes)`, `get_seller_order_v24_windows(session)`, `get_seller_dynamic_hold_hours(session)`, `get_seller_order_policy(order, bank)`, `is_seller_order_data_revealed(order)`, `get_seller_order_result_text(order)`, `mark_seller_order_data_revealed(...)`, `release_seller_order_reservation(...)`, `build_buyer_order_actions_keyboard(...)`, `mark_seller_order_completed(...)`, `notify_buyer_order_completed(...)`, `confirm_seller_order(...)`, `request_seller_order_return(...)`, `save_seller_order_rating(...)`, `auto_confirm_expired_orders(session)`
**Cross-imports:** `MirrorBot`, `Seller`, `SellerBank`, `SellerOrder`, `SellerOrderDispute`, `SystemSetting`, `User`, `bot_pool`, `guarantee_policy_service`, `LedgerService`, `NocoDBService`, `AdminNotificationService`

### seller_deposit_service.py — 575 строк
**Классы:** `SellerDepositService`
**Функции (17):** `normalize_payment_status(...)`, `package_amount(package_code)`, `package_categories(package_code)`, `seller_is_active(seller)`, `allowed_categories(seller)`, `has_upload_access(seller, item_type)`, `activate_seller_access(...)`, `create_btcpay_invoice(...)`, `sync_invoice_status(...)`, `process_paid_invoice(...)`, `ban_seller(...)`, `request_exit(...)`, `_notify_seller_payment_success(...)`, `_notify_seller_banned(...)`
**Cross-imports:** `shared.database.models.(...)`, `admin_audit_service`, `AdminNotificationService`, `AuditEventService`, `BTCPayService`, `NotificationService`, `NocoDBService`

### admin_notification_service.py — 568 строк
**Классы:** `AdminNotificationService`
**Функции (22):** `init(cls, bot)`, `_get_bot(cls)`, `_send_to_admins(...)`, `notify_admin_action(...)`, `notify_new_order(...)`, `notify_order_taken(...)`, `notify_order_completed(...)`, `notify_order_cancelled(...)`, `notify_bulk_order_completed(...)`, `notify_bulk_item_completed(...)`, `notify_addinfo_set(...)`, `notify_payment_success(...)`, `notify_payment_expired(...)`, `notify_balance_update(...)`, `notify_new_user(...)`, `notify_user_banned(...)`, `notify_new_support_ticket(...)`, `notify_new_complaint(...)`, `notify_files_sent(...)`, `notify_product_purchased(...)`, `notify_dispute(...)`, `notify_new_dispute(...)`

### ledger_reconciliation_service.py — 376 строк
**Классы:** `ReconciliationIssue`, `LedgerReconciliationService`
**Функции (9):** `as_payload(self)`, `_sum_transactions(...)`, `_add_issue(...)`, `reconcile_users(session)`, `reconcile_sellers(session)`, `reconcile_workers(session)`, `reconcile_marketers(session)`, `reconcile_owners(session)`, `run_full_reconciliation(...)`

### coupon_service.py — 340 строк
**Классы:** `CouponApplication`, `CouponService`
**Функции (11):** `_money(value)`, `applied(self)`, `normalize_code(code)`, `get_coupon_by_code(session, code)`, `assign_coupon_to_user(...)`, `activate_coupon(...)`, `clear_user_coupon(...)`, `calculate_discount(...)`, `record_redemption(...)`, `_validate_coupon_availability(...)`, `_validate_coupon_scope(...)`

### menu_category_service.py — 327 строк
**Классы:** `MenuCategoryService`
**Функции (6):** `ensure_defaults(session)`, `get_label(category, language)`, `list_categories(...)`, `get_keyboard_payload(...)`, `_iter_labels(category)`, `resolve_route_by_text(...)`

### nocodb_service.py — 310 строк
**Классы:** `NocoDBService`
**Функции (17):** `_to_iso(value)`, `_serialize(value)`, `_compact(payload)`, `enabled(cls)`, `_table_id(cls, table_key)`, `_client(cls)`, `_append_record(...)`, `_schedule(...)`, `log_order_message(...)`, `log_moderator_action(...)`, `log_seller_buyer_chat(...)`, `log_support_ticket(...)`, `log_financial_operation(...)`, `log_file_operation(...)`, `log_error(...)`, `log_seller_upload(...)`, `log_event(...)`

### notification_service.py — 268 строк
**Классы:** `NotificationService`
**Функции (8):** `_normalize_role(cls, role)`, `_token_for_role(cls, role)`, `_channel_name(cls, role)`, `_get_bot(cls, role)`, `_resolve_chat_id(cls, role, user_id)`, `_role_chat_ids(cls, role)`, `send(...)`, `broadcast(...)`

### moderation_pricing_service.py — 268 строк
**Классы:** `ModerationMarkupRule`
**Функции (33):** `normalize_base_price(value)`, `suggest_markup_for_bank(bank)`, `suggest_markup_for_cc(item)`, `suggest_markup_for_brute(item)`, `suggest_markup_for_nfc/otp/selfreg_cc/check/enroll/selfreg_ba/document/fullz/logs(item)`, `compute_final_price(...)`, `get_markup_rule(rule_code)`, `_apply_rule(...)`, `apply_base_price(...)`, `apply_bank_markup(...)`, `apply_cc_markup(...)`, `apply_brute_markup(...)`, ...

### ledger_projection_service.py — 248 строк
**Классы:** `LedgerProjectionService`
**Функции (12):** `_money(value)`, `_sum_transactions(...)`, `get_user_balance(session, user_id)`, `sync_user_projection(session, user_id)`, `get_seller/worker/marketer/owner_projection(session, id)`, `sync_seller/worker/marketer/owner_projection(session, id)`

### marketer_monitoring_service.py — 259 строк
**Функции (6):** `get_or_create_marketer_stats_row(...)`, `_send_marketer_registration_milestone(...)`, `record_marketer_registration(...)`, `evaluate_marketer_withdrawal_risk(...)`, `build_marketer_withdrawal_block_reason(...)`, `notify_marketer_withdrawal_blocked(...)`

### seller_dispute_service.py — 218 строк
**Классы:** `SellerDisputeService`
**Функции (9):** `_get_setting_int(...)`, `get_seller_response_hours(session)`, `open_dispute(...)`, `mark_seller_responded(...)`, `request_appeal(...)`, `review_appeal(...)`, `resolve_for_buyer(...)`, `resolve_for_seller(...)`, `auto_resolve_expired_disputes(session)`

### log_channel_service.py — 212 строк
**Классы:** `LogChannelService`
**Функции (5):** `_get_bot(cls)`, `_resolve_routes(cls, event_type)`, `_event_emoji(cls, ...)`, `_format_message(cls, ...)`, `send(...)`

### bin_lookup_service.py — 201 строк
**Классы:** `BinInfo`, `BinLookupService`
**Функции (5):** `_get_lock()`, `_evict_stale()`, `lookup(bin_prefix)`, `_fetch(bin6)`, `enrich_parsed(parsed)`

### bot_owner_service.py — 173 строк
**Функции (5):** `get_min_withdrawal_amount(session)`, `get_or_create_owner(session, ...)`, `get_owner_stats(...)`, `_agg(start, end)`, `get_owner_month_topups_chart(...)`

### product_catalog_service.py — 172 строк
**Классы:** `ProductCatalogManager`
**Функции (6):** `ensure_defaults(session)`, `list_services(...)`, `get_service(session, code)`, `get_categories_payload(session, ...)`, `format_service_label(code)`, `compute_age_days(created_at)`

### seller_helper_service.py — 168 строк
**Классы:** `SellerHelperService`
**Функции (8):** `list_helpers(...)`, `get_helper(...)`, `get_pending_invite(...)`, `create_invite(...)`, `accept_invite(...)`, `change_status(...)`, `change_role(...)`, `log_action(...)`

### reputation_service.py — 165 строк
**Функции (5):** `recalculate_seller_score(session, seller)`, `_apply_platform_fee(seller, score)`, `get_seller_badge(score)`, `recalculate_buyer_trust_score(session, ...)`, `recalculate_all_seller_scores(session)`

### btcpay_service.py — 162 строк
**Классы:** `BTCPayConfigurationError`, `BTCPayInvoice`, `BTCPayService`
**Функции (11):** `_base_url()`, `_store_id()`, `_api_key()`, `_headers()`, `is_configured()`, `create_invoice(...)`, `fetch_invoice(invoice_id)`, `is_paid_status(status)`, `parse_webhook_invoice_id(payload)`, `verify_webhook_signature(...)`, `decode_webhook_body(raw_body)`
**API:** `{base_url}/api/v1/stores/{store_id}/invoices`

### admin_audit_service.py — 160 строк
**Функции (1):** `log_admin_action(...)`
**Cross-imports:** `Admin`, `AdminAuditLog`, `AuditEventService`, `LogChannelService`, `NocoDBService`

### pdf_watermark.py — 143 строк
**Функции (4):** `_encode_user_id_binary(user_id)`, `decode_user_id_from_text(text)`, `generate_watermarked_pdf(...)`, `render_pdf_pages_as_images(pdf_bytes)`

### seller_upload_batch_service.py — 137 строк
**Классы:** `SellerUploadBatchService`
**Функции (3):** `create_batch(...)`, `recalc_batch_status(session, batch_id)`, `list_batches(session, seller_id)`

### bulk_discount_service.py — 131 строк
**Функции (7):** `ensure_defaults(session)`, `get_tiers(session, category)`, `get_all_tiers(session)`, `get_discount_percent(...)`, `get_discount_decimal(...)`, `upsert_tier(...)`, `delete_tier(session, tier_id)`

### worker_score_service.py — 132 строки
**Функции (2):** `recalculate_worker_score(session, worker)`, `get_worker_dashboard(session, worker)`

### pricing_config_service.py — 117 строк
**Классы:** `PricingConfigService`
**Функции (6):** `ensure_defaults(session)`, `list_all(session)`, `get_row(session, key)`, `get_value(session, key, default)`, `deserialize(row)`, `upsert(...)`

### worker_earnings_service.py — 114 строк
**Функции (4):** `calculate_order_income_for_worker(order, ...)`, `get_worker_score_multiplier(worker)`, `calculate_worker_earnings_from_order(...)`, `credit_worker_on_order_complete(...)`

### notification_log_service.py — 103 строки
**Функции (3):** `_write_log(...)`, `fire_log(...)`, `log_async(...)`

### order_notification_service.py — 99 строк
**Классы:** `OrderNotificationService`
**Функции (3):** `_post_with_retry(url, order_data)`, `notify_new_order(order_data)`, `send_order_to_channel(order_data)`
**API:** `{base_url}/api/notifications/new-order`

### ui_translation_service.py — 99 строк
**Классы:** `UiTranslator`
**Функции (3):** `get(self, key, default, ...)`, `get_ui_text(...)`, `upsert_ui_translation(...)`

### system_settings_service.py — 98 строк
**Классы:** `SystemSettingsService`
**Функции (7):** `seed_defaults(session)`, `get(session, key, default)`, `get_int(...)`, `get_float(...)`, `get_bool(...)`, `set(session, key, value)`, `list_all(session)`

### seller_conversation_service.py — 83 строки
**Функции (2):** `get_or_create_conversation(...)`, `get_conversation_from_order(...)`

### seller_actor_service.py — 82 строки
**Классы:** `SellerActorContext`
**Функции (11):** `is_owner`, `is_helper`, `actor_telegram_id`, `actor_label`, `role`, `can_upload`, `can_support`, `can_manage_helpers`, `can_manage_finance`, `can_view_profile`, `resolve_seller_actor(session, telegram_id)`

### guarantee_policy_service.py — 83 строки
**Классы:** `GuaranteePolicy`
**Функции (4):** `format_guarantee_window(minutes)`, `get_seller_guarantee_policy(...)`, `get_product_guarantee_policy(...)`, `is_guarantee_active(guarantee_until, ...)`

### menu_count_cache_service.py — 78 строк
**Классы:** `MenuCountCacheService`
**Функции (7):** `from_url(url, ...)` (×2), `_get_redis(cls)`, `_cache_key(cls, name)`, `get_counts(cls, name)`, `set_counts(cls, name, payload)`, `warm_all_counts(cls, session)`

### product_audit_service.py — 78 строк
**Функции (1):** `log_product_action(...)`

### audit_event_service.py — 62 строки
**Классы:** `AuditEventService`
**Функции (1):** `log(...)`

### admin_catalog_access.py — 60 строк
**Функции (3):** `normalize_uploader_catalog_codes(value)`, `get_admin_allowed_catalogs(admin)`, `sync_admin_allowed_catalogs(admin, catalog_codes)`

### bot_pool.py — 61 строка
**Функции (6):** `get_bot(token)`, `close_bot(token)`, `close_all()`, `get_seller_bot()`, `get_support_bot()`, `get_mirror_bot_instance(token)`

### runtime_pricing_service.py — 61 строка
**Классы:** `RuntimePricingService`
**Функции (3):** `get_service_price(...)`, `get_pair(...)`, `get_config(...)`

### seller_finance_service.py — 53 строки
**Классы:** `SellerFinanceService`
**Функции (8):** `_money(value)`, `pending_balance(seller)`, `withdrawable_balance(seller)`, `credit_pending(seller, amount)`, `reverse_pending(seller, amount)`, `settle_pending(seller, amount)`, `can_withdraw(seller, amount)`, `apply_withdrawal(seller, amount)`

### worker_order_service.py — 49 строк
**Классы:** `WorkerOrderService`
**Функции (2):** `ensure_from_order(session, order)`, `ensure_by_order_id(session, order_id)`

### worker_reminder_task_service.py — 71 строка
**Классы:** `WorkerReminderTaskService`
**Функции (2):** `schedule(...)`, `cancel_for_order(session, order_id)`

### dispute_auto_resolve_service.py — 37 строк
**Функции (2):** `run_dispute_auto_resolve_watcher(...)`, `_process_expired_disputes(session_maker)`

### marketer_activity_log.py — 32 строки
**Функции (1):** `log_marketer_activity(...)`

### bot_owner_stats.py — 30 строк
**Функции (1):** `record_owner_spent(...)`

### seller_inventory_service.py — 29 строк
**Функции (1):** `auto_unpublish_expired_seller_items(session)`

---

## shared/tasks/

### auto_complete.py — 796 строк
**Классы:** `Celery` (mock)
**Функции (25):** `check_auto_complete_orders`, `_async_check_auto_complete`, `process_matured_ledger_transactions`, `process_expired_seller_disputes`, `_release_escrow_for_order(session, order)`, `_pay_marketer_commission(session, order)`, `check_worker_violation_limits`, `check_abandoned_carts`, `recalculate_all_worker_scores`, `send_smart_notifications`, `check_sla_breaches`, `recalculate_all_seller_scores_task`

---

## shared/utils/

### chat_filter.py — 146 строк
**Функции (4):** `filter_message(text)`, `is_message_blocked(text)`, `check_violations(text)`, `filter_and_log(...)`

### chat_render.py — 184 строки
**Функции (7):** `_escape_markdown(text)`, `_escape_html(text)`, `get_chat_messages(...)`, `get_chat_messages_by_order(...)`, `build_chat_text(...)`, `buyer_chat_keyboard(...)`, `seller_chat_keyboard(...)`

### seller_card_renderers.py — 277 строк
**Функции (15):** `_bool_badge(value)`, `_flag(country_code)`, `_money(value)`, `render_cc_description(item)`, `render_brute_description(item)`, `render_bank_description(bank)`, `render_nfc_description(item)`, `render_otp_description(item)`, `render_enroll_description(item)`, `render_selfreg_ba_description(item)`, `render_logs_description(item)`, `render_selfreg_cc_description(item)`, `render_check_description(item)`, `render_document_description(item)`, `render_fullz_description(item)`

### seller_product_meta.py — 51 строка
**Функции (5):** `bank_type_label(product_type)`, `bank_subtype_label(product_subtype)`, `cc_subtype_label(product_subtype)`, `bank_item_badge(...)`, `cc_item_badge(...)`

### telegram_auth.py — 40 строк
**Функции (1):** `validate_telegram_init_data(...)`

---

## Зависимости

Используется всеми компонентами: [[Seller Bot]], [[Support Bot]], [[Web Panel]], [[Mini App]]
