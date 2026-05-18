'use strict';

/* ─────────────────────────────────────────────
   Seller Hub — Mini App JS
   ───────────────────────────────────────────── */

const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }

// ── State ──────────────────────────────────────
const S = {
    seller: null,
    conversations: [],
    activeConvId: null,
    orders: [],
    orderFilter: 'active',
    batches: [],
    listings: [],
    templates: [],
    activeBatchId: null,
    uploadTab: 'bank',
    mainTab: 'chats',
    previews: { 
        bank: null, 
        brute: null,
        cc: null,
        nfc: null,
        otp: null,
        enroll: null,
        selfreg_cc: null,
        checks: null,
    },
    pollTimer: null,
};

// ── DOM helpers ────────────────────────────────
const $ = id => document.getElementById(id);
const q = sel => document.querySelector(sel);
const qa = sel => document.querySelectorAll(sel);

// ── Toast ──────────────────────────────────────
function toast(msg, type = 'info', ms = 3000) {
    const c = $('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    c.appendChild(el);
    setTimeout(() => el.style.opacity = '0', ms - 400);
    setTimeout(() => el.remove(), ms);
}

// ── API ────────────────────────────────────────
function getHeaders(extra = {}) {
    const h = { ...extra };
    const initData = tg?.initData || '';
    if (initData) { h['X-Telegram-Init-Data'] = initData; }
    else {
        const p = new URLSearchParams(window.location.search);
        const dev = p.get('dev_tg_id');
        if (dev) h['X-Dev-Seller-Telegram-Id'] = dev;
    }
    return h;
}

async function api(path, opts = {}) {
    const headers = getHeaders(opts.headers || {});
    const res = await fetch(path, { ...opts, headers });
    if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

async function apiBlob(path) {
    const res = await fetch(path, { headers: getHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.blob();
}

// ── Formatters ─────────────────────────────────
function fmtTime(v) {
    if (!v) return '';
    const d = new Date(v);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function fmtMoney(v) {
    if (v == null) return '$0.00';
    return '$' + parseFloat(v).toFixed(2);
}
function fmtStatus(s) {
    const map = {
        approved: 'Approved', in_progress: 'In Progress', completed: 'Completed',
        disputed: 'Disputed', pending_admin: 'Pending', cancelled: 'Cancelled', rejected: 'Rejected',
    };
    return map[s] || s;
}
function statusIcon(s) {
    const m = { approved: '🟡', in_progress: '🔵', completed: '✅', disputed: '🔴', pending_admin: '⏳', cancelled: '⛔', rejected: '❌' };
    return m[s] || '📦';
}

// ── Navigation ─────────────────────────────────
function setTab(tab) {
    S.mainTab = tab;
    qa('.tab-section').forEach(s => s.classList.add('hidden'));
    const sec = $(`tab-${tab}`);
    if (sec) sec.classList.remove('hidden');
    qa('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    if (tab === 'orders'    && !S.orders.length)      loadOrders(S.orderFilter);
    if (tab === 'uploads'   && !S.batches.length)     loadBatches();
    if (tab === 'analytics')                          loadAnalytics();
    if (tab === 'finance')                            loadFinance();
    if (tab === 'settings')                           loadSettings();
}

// ── Role visibility ────────────────────────────
function applyRoles() {
    const s = S.seller || {};
    const canChat   = !s.is_helper || ['support_helper', 'manager_helper'].includes(s.actor_role);
    const canUpload = !s.is_helper || ['upload_helper', 'manager_helper'].includes(s.actor_role);
    const chatBtn   = q('.nav-btn[data-tab="chats"]');
    const uplBtn    = q('.nav-btn[data-tab="uploads"]');
    if (chatBtn)  chatBtn.classList.toggle('hidden', !canChat);
    if (uplBtn)   uplBtn.classList.toggle('hidden', !canUpload);
    if (!canChat   && S.mainTab === 'chats')   setTab(canUpload ? 'uploads' : 'analytics');
    if (!canUpload && S.mainTab === 'uploads') setTab(canChat   ? 'chats'   : 'analytics');
}

// ── CHATS ──────────────────────────────────────
async function loadConversations() {
    try {
        const data = await api('/api/seller-mini-app/conversations');
        S.conversations = data;
        renderConversations();
        // Update badge
        const unread = data.reduce((a, c) => a + (c.unread_count || 0), 0);
        updateBadge('nb-chats', unread);
        updateBadge('notif-badge', unread);
    } catch (e) { /* silent on poll */ }
}

function renderConversations() {
    const el = $('conversation-list');
    const q = $('chat-search')?.value?.toLowerCase() || '';
    const list = q ? S.conversations.filter(c =>
        (c.product_label || '').toLowerCase().includes(q) ||
        (c.buyer_label || '').toLowerCase().includes(q)
    ) : S.conversations;

    if (!list.length) {
        el.innerHTML = `<div class="empty-state">No buyer chats yet.</div>`;
        return;
    }
    el.innerHTML = '';
    list.forEach(c => {
        const btn = document.createElement('button');
        btn.className = `conv-item ${S.activeConvId === c.id ? 'active' : ''}`;
        btn.style.cssText = 'all:unset;display:block;width:100%;cursor:pointer';
        btn.innerHTML = `
            <div class="conv-top">
                <span class="conv-name">${esc(c.product_label || c.buyer_label || 'Buyer chat')}</span>
                <span class="conv-time">${fmtTime(c.latest_message_at)}</span>
            </div>
            <div class="conv-prev">${esc(c.latest_message || '—')}</div>
            ${c.unread_count ? `<div class="conv-badge">${c.unread_count}</div>` : ''}
        `;
        btn.onclick = () => openConversation(c.id);
        el.appendChild(btn);
    });
}

async function openConversation(id) {
    S.activeConvId = id;
    renderConversations();
    try {
        const data = await api(`/api/seller-mini-app/messages?conversation_id=${id}`);
        renderMessages(data);
        mobileChatOpen();
    } catch (e) { toast(e.message, 'error'); }
}

function renderMessages(payload) {
    const conv = payload.conversation || {};
    $('chat-name').textContent = conv.buyer_label || 'Buyer chat';
    const status = conv.latest_order_status || '';
    $('chat-order-status').textContent = status ? `Order #${conv.latest_order_id} · ${fmtStatus(status)}` : '';
    const chip = $('chat-status-chip');
    chip.className = `status-chip ${status}`;
    chip.textContent = fmtStatus(status);

    const ml = $('message-list');
    ml.innerHTML = '';
    (payload.messages || []).forEach(m => {
        const d = document.createElement('div');
        d.className = `msg ${m.sender_type}`;
        const files = Array.isArray(m.files) && m.files.length
            ? `<div class="msg-file">📎 File attached</div>` : '';
        d.innerHTML = `
            <div class="msg-meta">${m.sender_type.toUpperCase()} · ${fmtTime(m.created_at)}</div>
            <div>${esc(m.message_text || '')}</div>${files}
        `;
        ml.appendChild(d);
    });
    ml.scrollTop = ml.scrollHeight;
    $('chat-view').classList.remove('hidden');
    $('chat-placeholder').classList.add('hidden');
}

async function sendMessage(e) {
    e.preventDefault();
    if (!S.activeConvId) return;
    const text = $('message-input').value.trim();
    const file = $('file-input').files[0];
    if (!text && !file) return;

    const fd = new FormData();
    fd.append('conversation_id', S.activeConvId);
    if (text) fd.append('message_text', text);
    if (file) fd.append('file', file);

    try {
        await fetch('/api/seller-mini-app/send', {
            method: 'POST', body: fd, headers: getHeaders(),
        });
        $('message-input').value = '';
        $('file-input').value = '';
        $('file-preview').classList.add('hidden');
        $('message-input').style.height = 'auto';
        await openConversation(S.activeConvId);
    } catch (err) { toast(err.message, 'error'); }
}

// Mobile chat
function mobileChatOpen() {
    if (window.innerWidth > 640) return;
    $('chat-sidebar').classList.add('mobile-hide');
    $('chat-main').classList.add('mobile-show');
}
function mobileChatBack() {
    $('chat-sidebar').classList.remove('mobile-hide');
    $('chat-main').classList.remove('mobile-show');
}

// ── ORDERS ─────────────────────────────────────
async function loadOrders(filter = 'active') {
    S.orderFilter = filter;
    const el = $('order-list');
    el.innerHTML = `<div class="empty-state">Loading…</div>`;
    try {
        const data = await api(`/api/seller-mini-app/orders?status_filter=${filter}`);
        S.orders = data;
        renderOrders();
    } catch (e) { el.innerHTML = `<div class="empty-state">${esc(e.message)}</div>`; }
}

function renderOrders() {
    const el = $('order-list');
    if (!S.orders.length) {
        el.innerHTML = `<div class="empty-state">No orders found.</div>`;
        updateBadge('nb-orders', 0);
        return;
    }
    const active = S.orders.filter(o => ['approved', 'in_progress'].includes(o.status)).length;
    const disputed = S.orders.filter(o => o.status === 'disputed').length;
    const chipsEl = $('order-stats-chips');
    if (chipsEl) {
        chipsEl.innerHTML = '';
        if (active) {
            const chip = document.createElement('span');
            chip.className = 'stat-chip active-cnt';
            chip.textContent = `⚡ ${active} active`;
            chipsEl.appendChild(chip);
        }
        if (disputed) {
            const chip = document.createElement('span');
            chip.className = 'stat-chip';
            chip.style.cssText = 'color:var(--danger);border-color:rgba(255,107,107,0.3);background:rgba(255,107,107,0.1)';
            chip.textContent = `⚠️ ${disputed} disputed`;
            chipsEl.appendChild(chip);
        }
    }
    updateBadge('nb-orders', active + disputed);
    el.innerHTML = '';
    S.orders.forEach(o => {
        const d = document.createElement('div');
        d.className = `order-card st-${o.status}`;
        d.innerHTML = `
            <div class="order-icon">${statusIcon(o.status)}</div>
            <div class="order-body">
                <div class="order-title">${esc(o.bank_name || o.product_label || `Order #${o.id}`)}</div>
                <div class="order-meta">
                    <span>${esc(o.product_type || '')} ${esc(o.product_subtype || '')}</span>
                    <span>×${o.quantity || 1}</span>
                    <span class="status-chip ${o.status}">${fmtStatus(o.status)}</span>
                </div>
            </div>
            <div class="order-right">
                <div class="order-price">${fmtMoney(o.price_for_seller)}</div>
                <div class="order-date">${fmtTime(o.created_at)}</div>
            </div>
        `;
        el.appendChild(d);
    });
}

// ── UPLOADS ────────────────────────────────────
function setUploadTab(tab) {
    S.uploadTab = tab;
    qa('.upload-tab').forEach(b => b.classList.toggle('active', b.dataset.upload === tab));
    qa('.upload-pane').forEach(p => p.classList.add('hidden'));
    $(`upload-${tab}`)?.classList.remove('hidden');
    if (tab === 'batches') loadBatches();
    if (tab === 'listings') { loadListings(); loadTemplates(); }
}

async function loadBatches() {
    try {
        const data = await api('/api/seller-mini-app/uploads/batches');
        S.batches = data;
        renderBatchList();
    } catch (e) { /* silent */ }
}

function renderBatchList() {
    const el = $('batch-list');
    if (!S.batches.length) { el.innerHTML = `<div class="empty-state">No batches yet.</div>`; return; }
    el.innerHTML = '';
    S.batches.forEach(b => {
        const btn = document.createElement('button');
        btn.className = `batch-item ${S.activeBatchId === b.id ? 'active' : ''}`;
        btn.style.cssText = 'all:unset;display:block;width:100%;cursor:pointer';
        const chip = b.moderation_status === 'approved' ? '✅' : b.moderation_status === 'rejected' ? '❌' : '⏳';
        btn.innerHTML = `<strong>#${b.id} ${esc(b.title || b.item_type)}</strong><br>${chip} ${esc(b.moderation_status)} · ${b.total_items} items`;
        btn.onclick = () => openBatch(b.id);
        el.appendChild(btn);
    });
}

async function openBatch(id) {
    S.activeBatchId = id;
    renderBatchList();
    try {
        const data = await api(`/api/seller-mini-app/uploads/batches/${id}`);
        const b = data.batch;
        const items = data.items || [];
        
        // Batch info
        const chip = b.moderation_status === 'approved' ? '✅' : b.moderation_status === 'rejected' ? '❌' : '⏳';
        $('batch-info').innerHTML = `
            <div class="batch-info-card">
                <div class="batch-info-header">
                    <strong>#${b.id} ${esc(b.title || b.item_type)}</strong>
                    <span class="status-chip ${b.moderation_status}">${chip} ${esc(b.moderation_status)}</span>
                </div>
                <div class="batch-info-grid">
                    <div class="batch-info-item">
                        <span class="label">Type</span>
                        <span class="value">${esc(b.item_type)}</span>
                    </div>
                    <div class="batch-info-item">
                        <span class="label">Mode</span>
                        <span class="value">${esc(b.upload_mode)}</span>
                    </div>
                    <div class="batch-info-item">
                        <span class="label">Created</span>
                        <span class="value">${fmtTime(b.created_at)}</span>
                    </div>
                </div>
                <div class="batch-stats">
                    <div class="stat-item">
                        <span class="stat-label">Total</span>
                        <span class="stat-value">${b.total_items}</span>
                    </div>
                    <div class="stat-item approved">
                        <span class="stat-label">Approved</span>
                        <span class="stat-value">${b.approved_items || 0}</span>
                    </div>
                    <div class="stat-item pending">
                        <span class="stat-label">Pending</span>
                        <span class="stat-value">${b.pending_items || 0}</span>
                    </div>
                    <div class="stat-item rejected">
                        <span class="stat-label">Rejected</span>
                        <span class="stat-value">${b.rejected_items || 0}</span>
                    </div>
                </div>
                ${b.moderation_comment ? `<div class="moderator-note">⚠️ <strong>Moderator note:</strong> ${esc(b.moderation_comment)}</div>` : ''}
            </div>
        `;
        
        // Items list
        $('batch-item-count').textContent = `${items.length} item${items.length !== 1 ? 's' : ''}`;
        if (!items.length) {
            $('batch-items-list').innerHTML = `<div class="empty-state">No items in this batch</div>`;
        } else {
            $('batch-items-list').innerHTML = '';
            items.forEach(it => {
                const itemChip = it.status === 'approved' ? '✅' : it.status === 'rejected' ? '❌' : '⏳';
                const itemEl = document.createElement('div');
                itemEl.className = `batch-item-card item-${it.status}`;
                itemEl.innerHTML = `
                    <div class="item-left">
                        <span class="item-status">${itemChip}</span>
                        <div class="item-details">
                            <div class="item-name">${esc(it.bank_name || it.login || it.item_name || `Item #${it.id}`)}</div>
                            <div class="item-meta">
                                <span class="item-type">${esc(it.category || it.product_type || '')}</span>
                                <span class="item-price">$${parseFloat(it.seller_price || 0).toFixed(2)}</span>
                                <span class="item-stock">×${it.stock_count || 1}</span>
                            </div>
                        </div>
                    </div>
                    <div class="item-reason ${it.rejection_reason ? '' : 'hidden'}">
                        <span class="reason-label">❌ ${esc(it.rejection_reason || '')}</span>
                    </div>
                `;
                $('batch-items-list').appendChild(itemEl);
            });
        }
    } catch (e) { 
        $('batch-info').innerHTML = `<div class="empty-state">Error: ${esc(e.message)}</div>`;
        $('batch-items-list').innerHTML = '';
    }
}

// Bank upload preview
async function previewBank() {
    const form = $('bank-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    payload.has_chat = fd.has('has_chat');
    payload.number_access_available = fd.has('number_access_available');
    payload.number_change_allowed = fd.has('number_change_allowed');
    payload.auto_unpublish_enabled = fd.has('auto_unpublish_enabled');
    payload.adaptive_report_enabled = fd.has('adaptive_report_enabled');
    ['seller_price', 'stock_count', 'rental_days', 'listing_duration_days'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        const res = await api('/api/seller-mini-app/uploads/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'bank', payload }),
        });
        S.previews.bank = res;
        $('upload-preview').textContent = JSON.stringify(res, null, 2);
    } catch (e) { toast(e.message, 'error'); }
}

async function submitBank(e) {
    e.preventDefault();
    const form = $('bank-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    payload.has_chat = fd.has('has_chat');
    payload.number_access_available = fd.has('number_access_available');
    payload.number_change_allowed = fd.has('number_change_allowed');
    payload.auto_unpublish_enabled = fd.has('auto_unpublish_enabled');
    payload.adaptive_report_enabled = fd.has('adaptive_report_enabled');
    ['seller_price', 'stock_count', 'rental_days', 'listing_duration_days'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        await api('/api/seller-mini-app/uploads/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'bank', payload }),
        });
        toast('Bank submitted for moderation!', 'success');
        form.reset();
        $('upload-preview').textContent = 'Click Preview to check details before submitting.';
        await loadBatches();
    } catch (e) { toast(e.message, 'error'); }
}

// Brute upload preview
async function previewBrute() {
    const form = $('brute-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    const bulkFile = $('brute-bulk-file').files[0];
    if (bulkFile) {
        try {
            const parseForm = new FormData();
            parseForm.append('file', bulkFile);
            const parsed = await fetch('/api/seller-mini-app/uploads/parse-file', {
                method: 'POST', body: parseForm, headers: getHeaders(),
            }).then(r => r.json());
            payload.parsed_rows = parsed.rows || [];
        } catch (e) { toast('Failed to parse file: ' + e.message, 'error'); return; }
    }
    try {
        const res = await api('/api/seller-mini-app/uploads/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'brute', payload }),
        });
        S.previews.brute = res;
        $('brute-preview-box').textContent = JSON.stringify(res, null, 2);
    } catch (e) { toast(e.message, 'error'); }
}

async function submitBrute(e) {
    e.preventDefault();
    const form = $('brute-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    try {
        await api('/api/seller-mini-app/uploads/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'brute', payload }),
        });
        toast('Brute batch submitted!', 'success');
        form.reset();
        $('brute-preview-box').textContent = 'Click Preview to see parsed items.';
        await loadBatches();
    } catch (e) { toast(e.message, 'error'); }
}

// CC Upload
async function previewCC() {
    const form = $('cc-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    payload.is_non_vbv = fd.has('is_non_vbv');
    // Extra data
    const extraData = {
        phone: payload.extra_phone || null,
        email: payload.extra_email || null,
        ssn: payload.extra_ssn || null,
        dob: payload.extra_dob || null,
        dl: payload.extra_dl || null,
        info: payload.extra_info || null,
        ref: payload.extra_ref || null,
    };
    payload.extra_data = extraData;
    // Clean up
    delete payload.extra_phone; delete payload.extra_email; delete payload.extra_ssn;
    delete payload.extra_dob; delete payload.extra_dl; delete payload.extra_info; delete payload.extra_ref;
    ['seller_price', 'stock_count', 'seller_price_non_vbv'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        const res = await api('/api/seller-mini-app/uploads/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'cc', payload }),
        });
        S.previews.cc = res;
        $('cc-preview-box').textContent = JSON.stringify(res, null, 2);
    } catch (e) { toast(e.message, 'error'); }
}

async function submitCC(e) {
    e.preventDefault();
    const form = $('cc-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    payload.is_non_vbv = fd.has('is_non_vbv');
    const extraData = {
        phone: payload.extra_phone || null,
        email: payload.extra_email || null,
        ssn: payload.extra_ssn || null,
        dob: payload.extra_dob || null,
        dl: payload.extra_dl || null,
        info: payload.extra_info || null,
        ref: payload.extra_ref || null,
    };
    payload.extra_data = extraData;
    delete payload.extra_phone; delete payload.extra_email; delete payload.extra_ssn;
    delete payload.extra_dob; delete payload.extra_dl; delete payload.extra_info; delete payload.extra_ref;
    ['seller_price', 'stock_count', 'seller_price_non_vbv'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        await api('/api/seller-mini-app/uploads/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'cc', payload }),
        });
        toast('CC items submitted for moderation!', 'success');
        form.reset();
        $('cc-preview-box').textContent = 'Click Preview to check details before submitting.';
        await loadBatches();
    } catch (e) { toast(e.message, 'error'); }
}

// NFC Upload
async function previewNFC() {
    const form = $('nfc-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    ['balance', 'seller_price', 'stock_count'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        const res = await api('/api/seller-mini-app/uploads/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'nfc', payload }),
        });
        S.previews.nfc = res;
        $('nfc-preview-box').textContent = JSON.stringify(res, null, 2);
    } catch (e) { toast(e.message, 'error'); }
}

async function submitNFC(e) {
    e.preventDefault();
    const form = $('nfc-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    ['balance', 'seller_price', 'stock_count'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        await api('/api/seller-mini-app/uploads/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'nfc', payload }),
        });
        toast('NFC item submitted!', 'success');
        form.reset();
        $('nfc-preview-box').textContent = 'Click Preview to check details before submitting.';
        await loadBatches();
    } catch (e) { toast(e.message, 'error'); }
}

// OTP Upload
async function previewOTP() {
    const form = $('otp-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    ['balance', 'seller_price', 'stock_count'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        const res = await api('/api/seller-mini-app/uploads/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'otp', payload }),
        });
        S.previews.otp = res;
        $('otp-preview-box').textContent = JSON.stringify(res, null, 2);
    } catch (e) { toast(e.message, 'error'); }
}

async function submitOTP(e) {
    e.preventDefault();
    const form = $('otp-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    ['balance', 'seller_price', 'stock_count'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        await api('/api/seller-mini-app/uploads/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'otp', payload }),
        });
        toast('OTP item submitted!', 'success');
        form.reset();
        $('otp-preview-box').textContent = 'Click Preview to check details before submitting.';
        await loadBatches();
    } catch (e) { toast(e.message, 'error'); }
}

// Enroll Upload
async function previewEnroll() {
    const form = $('enroll-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    payload.has_ssn = fd.has('has_ssn');
    payload.has_dob = fd.has('has_dob');
    payload.has_name = fd.has('has_name');
    payload.has_address = fd.has('has_address');
    payload.has_email = fd.has('has_email');
    payload.has_security_qa = fd.has('has_security_qa');
    payload.has_docs = fd.has('has_docs');
    ['balance', 'seller_price', 'stock_count'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        const res = await api('/api/seller-mini-app/uploads/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'enroll', payload }),
        });
        S.previews.enroll = res;
        $('enroll-preview-box').textContent = JSON.stringify(res, null, 2);
    } catch (e) { toast(e.message, 'error'); }
}

async function submitEnroll(e) {
    e.preventDefault();
    const form = $('enroll-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    payload.has_ssn = fd.has('has_ssn');
    payload.has_dob = fd.has('has_dob');
    payload.has_name = fd.has('has_name');
    payload.has_address = fd.has('has_address');
    payload.has_email = fd.has('has_email');
    payload.has_security_qa = fd.has('has_security_qa');
    payload.has_docs = fd.has('has_docs');
    ['balance', 'seller_price', 'stock_count'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        await api('/api/seller-mini-app/uploads/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'enroll', payload }),
        });
        toast('Enroll item submitted!', 'success');
        form.reset();
        $('enroll-preview-box').textContent = 'Click Preview to check details before submitting.';
        await loadBatches();
    } catch (e) { toast(e.message, 'error'); }
}

// Selfreg CC Upload
async function previewSelfregCC() {
    const form = $('selfreg-cc-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    payload.has_ssn = fd.has('has_ssn');
    payload.has_docs = fd.has('has_docs');
    ['seller_price', 'stock_count'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        const res = await api('/api/seller-mini-app/uploads/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'selfreg_cc', payload }),
        });
        S.previews.selfreg_cc = res;
        $('selfreg-cc-preview-box').textContent = JSON.stringify(res, null, 2);
    } catch (e) { toast(e.message, 'error'); }
}

async function submitSelfregCC(e) {
    e.preventDefault();
    const form = $('selfreg-cc-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    payload.has_ssn = fd.has('has_ssn');
    payload.has_docs = fd.has('has_docs');
    ['seller_price', 'stock_count'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        await api('/api/seller-mini-app/uploads/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'selfreg_cc', payload }),
        });
        toast('Selfreg CC item submitted!', 'success');
        form.reset();
        $('selfreg-cc-preview-box').textContent = 'Click Preview to check details before submitting.';
        await loadBatches();
    } catch (e) { toast(e.message, 'error'); }
}

// Checks Upload
async function previewChecks() {
    const form = $('checks-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    ['amount', 'seller_price', 'stock_count'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        const res = await api('/api/seller-mini-app/uploads/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'checks', payload }),
        });
        S.previews.checks = res;
        $('checks-preview-box').textContent = JSON.stringify(res, null, 2);
    } catch (e) { toast(e.message, 'error'); }
}

async function submitChecks(e) {
    e.preventDefault();
    const form = $('checks-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    ['amount', 'seller_price', 'stock_count'].forEach(k => {
        if (payload[k]) payload[k] = parseFloat(payload[k]) || 0;
    });
    try {
        await api('/api/seller-mini-app/uploads/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_type: 'checks', payload }),
        });
        toast('Check item submitted!', 'success');
        form.reset();
        $('checks-preview-box').textContent = 'Click Preview to check details before submitting.';
        await loadBatches();
    } catch (e) { toast(e.message, 'error'); }
}

// Listings
async function loadListings() {
    try {
        const data = await api('/api/seller-mini-app/listings');
        S.listings = data;
        renderListings();
    } catch (e) { $('listing-list').innerHTML = `<div class="empty-state">${esc(e.message)}</div>`; }
}

function renderListings() {
    const el = $('listing-list');
    if (!S.listings.length) { el.innerHTML = `<div class="empty-state">No active listings.</div>`; return; }
    el.innerHTML = '';
    S.listings.forEach(l => {
        const d = document.createElement('div');
        d.className = 'listing-item';
        const mod = l.moderation_status || 'pending';
        const chip = mod === 'approved' ? '✅' : mod === 'rejected' ? '❌' : '⏳';
        d.innerHTML = `
            <input type="checkbox" class="listing-cb" data-id="${l.id}">
            <div class="listing-info">
                <div class="listing-name">${esc(l.bank_name || l.title || `Listing #${l.id}`)}</div>
                <div class="listing-meta">${esc(l.category || '')} · ${esc(l.product_type || '')} · ${chip} ${mod}</div>
            </div>
            <div class="listing-price">${fmtMoney(l.seller_price)}</div>
        `;
        el.appendChild(d);
    });
}

async function bulkReprice() {
    const mode  = $('bulk-price-mode').value;
    const value = parseFloat($('bulk-price-value').value);
    if (isNaN(value)) { toast('Enter a valid number', 'error'); return; }
    const ids = [...qa('.listing-cb:checked')].map(cb => parseInt(cb.dataset.id));
    if (!ids.length) { toast('Select at least one listing', 'error'); return; }
    try {
        await api('/api/seller-mini-app/listings/bulk-price', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ listing_ids: ids, mode, value }),
        });
        toast('Prices updated — listings sent to moderation', 'success');
        await loadListings();
    } catch (e) { toast(e.message, 'error'); }
}

// Templates
async function loadTemplates() {
    try {
        const data = await api('/api/seller-mini-app/templates');
        S.templates = data;
        renderTemplates();
    } catch (e) { /* silent */ }
}

function renderTemplates() {
    const el = $('template-list');
    if (!S.templates.length) { el.innerHTML = `<div class="empty-state">No saved templates.</div>`; return; }
    el.innerHTML = '';
    S.templates.forEach(t => {
        const row = document.createElement('div');
        row.className = 'template-row';
        row.innerHTML = `
            <span>${esc(t.name || t.item_type)}</span>
            <button class="btn-secondary btn-sm" data-tid="${t.id}" data-ttype="${t.item_type}">Load</button>
            <button class="btn-danger btn-sm" data-del="${t.id}">✕</button>
        `;
        el.appendChild(row);
    });
    el.querySelectorAll('[data-del]').forEach(b => {
        b.onclick = () => deleteTemplate(parseInt(b.dataset.del));
    });
    el.querySelectorAll('[data-tid]').forEach(b => {
        b.onclick = () => loadTemplate(S.templates.find(t => t.id === parseInt(b.dataset.tid)));
    });
}

async function saveTemplate(type) {
    const form = $(type === 'bank' ? 'bank-upload-form' : 'brute-upload-form');
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    const name = prompt('Template name:');
    if (!name) return;
    try {
        await api('/api/seller-mini-app/templates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, item_type: type, payload }),
        });
        toast('Template saved!', 'success');
        await loadTemplates();
    } catch (e) { toast(e.message, 'error'); }
}

async function deleteTemplate(id) {
    try {
        await api(`/api/seller-mini-app/templates/${id}`, { method: 'DELETE' });
        toast('Template deleted', 'info');
        await loadTemplates();
    } catch (e) { toast(e.message, 'error'); }
}

function loadTemplate(t) {
    if (!t) return;
    const form = $(t.item_type === 'bank' ? 'bank-upload-form' : 'brute-upload-form');
    if (!form) return;
    const p = t.payload || {};
    Object.keys(p).forEach(k => {
        const el = form.elements[k];
        if (!el) return;
        if (el.type === 'checkbox') el.checked = !!p[k];
        else el.value = p[k];
    });
    toast('Template loaded!', 'success');
}

// ── ANALYTICS ──────────────────────────────────
async function loadAnalytics() {
    try {
        const [summary, funnel] = await Promise.all([
            api('/api/seller-mini-app/analytics/summary'),
            api('/api/seller-mini-app/analytics/funnel'),
        ]);
        renderAnalyticsSummary(summary);
        renderFunnel(funnel);
        renderTopProducts(summary.top_products || []);
        loadAbandonedCarts();
    } catch (e) { /* silent */ }
}

function renderAnalyticsSummary(d) {
    const el = $('analytics-summary');
    if (!d) { el.innerHTML = ''; return; }
    const cards = [
        { label: 'Orders (30d)',    value: d.orders_30d ?? d.total_orders ?? '—',                          cls: '' },
        { label: 'Revenue (30d)',   value: fmtMoney(d.revenue_30d ?? d.total_revenue),                     cls: 'green' },
        { label: 'Avg order value', value: fmtMoney(d.avg_order_value),                                    cls: 'amber' },
        { label: 'Conversion',      value: d.conversion_rate ? `${d.conversion_rate}%` : '—',              cls: 'purple' },
        { label: 'Active listings', value: d.active_listings ?? '—',                                       cls: '' },
        { label: 'Items sold',      value: d.items_sold ?? '—',                                            cls: 'green' },
        { label: 'Disputes',        value: d.disputes ?? '—',                                              cls: d.disputes > 0 ? 'amber' : '' },
        { label: 'Completion rate', value: d.completion_rate ? `${d.completion_rate}%` : '—',              cls: '' },
    ];
    el.innerHTML = cards.map(c => `
        <div class="stat-card ${c.cls}">
            <div class="stat-value">${c.value}</div>
            <div class="stat-label">${c.label}</div>
        </div>
    `).join('');
}

function renderFunnel(d) {
    const el = $('funnel-view');
    if (!d || !d.steps || !d.steps.length) {
        el.innerHTML = `<div class="empty-state">No funnel data yet.</div>`;
        return;
    }
    const max = Math.max(...d.steps.map(s => s.count || 0), 1);
    el.innerHTML = d.steps.map(s => {
        const pct = Math.max(Math.round((s.count / max) * 100), 6);
        return `
            <div class="funnel-row">
                <div class="funnel-label">${esc(s.label)}</div>
                <div class="funnel-bar-wrap">
                    <div class="funnel-bar" style="width:${pct}%">${s.count}</div>
                </div>
            </div>`;
    }).join('');
}

function renderTopProducts(products) {
    const el = $('top-products-view');
    if (!products || !products.length) { el.innerHTML = `<div class="empty-state">No data yet.</div>`; return; }
    el.innerHTML = products.slice(0, 8).map((p, i) => `
        <div class="top-prod-item">
            <div class="top-prod-rank">${i + 1}</div>
            <div class="top-prod-name">${esc(p.bank_name || p.name || `Item #${p.id}`)}</div>
            <div class="top-prod-val">${fmtMoney(p.revenue || p.gross_sales)}</div>
        </div>
    `).join('');
}

async function loadAbandonedCarts() {
    try {
        const data = await api('/api/seller-mini-app/analytics/abandoned-carts');
        const el = $('abandoned-carts-view');
        if (!data || !data.length) { el.textContent = 'No abandoned cart data.'; return; }
        el.textContent = data.map(c =>
            `${esc(c.bank_name || 'Item')} — ${c.count} abandoned`
        ).join('\n');
    } catch (e) { /* silent */ }
}

// ── FINANCE ────────────────────────────────────
async function loadFinance() {
    try {
        const d = await api('/api/seller-mini-app/finance/summary');
        renderFinance(d);
    } catch (e) { /* silent */ }
}

function renderFinance(d) {
    const el = $('finance-summary');
    if (!d) { el.innerHTML = ''; return; }
    el.innerHTML = `
        <div class="balance-card">
            <div class="bal-label">Withdrawable Balance</div>
            <div class="bal-value">${fmtMoney(d.withdrawable_balance)}</div>
            <div class="bal-sub">Pending: ${fmtMoney(d.pending_balance)}</div>
        </div>
        <div class="fin-row">
            <div class="fin-pill">
                <div class="fin-pill-label">Total earned</div>
                <div class="fin-pill-val positive">${fmtMoney(d.total_earned)}</div>
            </div>
            <div class="fin-pill">
                <div class="fin-pill-label">Total withdrawn</div>
                <div class="fin-pill-val">${fmtMoney(d.total_withdrawn)}</div>
            </div>
        </div>
        <div class="fin-row">
            <div class="fin-pill">
                <div class="fin-pill-label">Deposit</div>
                <div class="fin-pill-val">${fmtMoney(d.deposit_balance)}</div>
            </div>
            <div class="fin-pill">
                <div class="fin-pill-label">Markup</div>
                <div class="fin-pill-val">${d.markup_percent ?? '—'}%</div>
            </div>
        </div>
    `;
}

async function exportCSV() {
    try {
        const blob = await apiBlob('/api/seller-mini-app/finance/export.csv');
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href = url; a.download = 'seller_finance.csv'; a.click();
        URL.revokeObjectURL(url);
    } catch (e) { toast(e.message, 'error'); }
}

async function requestWithdrawal(e) {
    e.preventDefault();
    const amount = parseFloat($('withdraw-amount').value);
    const req    = $('withdraw-requisites').value.trim();
    if (!amount || amount <= 0) { toast('Enter a valid amount', 'error'); return; }
    if (!req) { toast('Enter payment requisites', 'error'); return; }
    try {
        await api('/api/seller-mini-app/finance/withdraw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, requisites: req }),
        });
        toast('Withdrawal request submitted!', 'success');
        $('withdraw-amount').value    = '';
        $('withdraw-requisites').value = '';
        await loadFinance();
    } catch (err) { toast(err.message, 'error'); }
}

// ── SETTINGS ───────────────────────────────────
async function loadSettings() {
    try {
        const d = await api('/api/seller-mini-app/me');
        S.seller = d;
        renderProfile(d);
        $('vacation-toggle').checked = !!d.vacation_mode;
        if (d.vacation_ends_at) $('vacation-ends-at').value = d.vacation_ends_at.slice(0, 16);
        $('auto-payout-toggle').checked = !!d.auto_payout;
        if (d.quiet_hours_from) $('quiet-from').value = d.quiet_hours_from;
        if (d.quiet_hours_to)   $('quiet-to').value   = d.quiet_hours_to;
    } catch (e) { /* silent */ }
}

function renderProfile(d) {
    const el = $('profile-info');
    if (!d) return;
    const items = [
        { label: 'Name',         val: d.display_name || d.username || '—' },
        { label: 'Type',         val: d.seller_type || '—' },
        { label: 'Markup',       val: `${d.markup_percent ?? '—'}%` },
        { label: 'Orders',       val: d.total_orders ?? '—' },
        { label: 'Earned',       val: fmtMoney(d.total_earned) },
        { label: 'Registered',   val: d.created_at ? new Date(d.created_at).toLocaleDateString() : '—' },
    ];
    el.innerHTML = items.map(i => `
        <div class="prof-item">
            <div class="prof-label">${i.label}</div>
            <div class="prof-val"  title="${esc(String(i.val))}">${esc(String(i.val))}</div>
        </div>
    `).join('');
}

async function saveVacation() {
    const on  = $('vacation-toggle').checked;
    const end = $('vacation-ends-at').value;
    try {
        await api('/api/seller-mini-app/settings/vacation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ vacation_mode: on, vacation_ends_at: end || null }),
        });
        toast(on ? 'Vacation mode enabled' : 'Vacation mode disabled', 'success');
        $('settings-summary').textContent = on ? `Vacation until ${end || 'manual off'}` : 'Vacation off';
        updateStatusDot(on ? 'vacation' : 'online');
    } catch (e) { toast(e.message, 'error'); }
}

async function saveAutoPayout() {
    const on = $('auto-payout-toggle').checked;
    try {
        await api('/api/seller-mini-app/settings/auto-payout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ auto_payout: on }),
        });
        toast('Auto-payout ' + (on ? 'enabled' : 'disabled'), 'success');
    } catch (e) { toast(e.message, 'error'); }
}

async function saveQuietHours() {
    const from = $('quiet-from').value;
    const to   = $('quiet-to').value;
    if (!from || !to) { toast('Set both from and to times', 'error'); return; }
    try {
        await api('/api/seller-mini-app/settings/quiet-hours', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quiet_hours_from: from, quiet_hours_to: to }),
        });
        toast('Quiet hours saved!', 'success');
    } catch (e) { toast(e.message, 'error'); }
}

function updateStatusDot(mode) {
    const dot = $('status-dot');
    dot.className = 'status-dot ' + (mode || '');
}

// ── Utilities ──────────────────────────────────
function esc(s) {
    return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function updateBadge(id, count) {
    const el = $(id);
    if (!el) return;
    if (count > 0) { el.textContent = count > 99 ? '99+' : count; el.classList.remove('hidden'); }
    else el.classList.add('hidden');
}

// ── Polling ────────────────────────────────────
function startPolling() {
    S.pollTimer = setInterval(() => {
        if (S.mainTab === 'chats') {
            loadConversations();
            if (S.activeConvId) openConversation(S.activeConvId).catch(() => {});
        }
        if (S.mainTab === 'orders') loadOrders(S.orderFilter);
    }, 5000);
}

// ── Init ───────────────────────────────────────
async function init() {
    // Load seller info
    try {
        const me = await api('/api/seller-mini-app/me');
        S.seller = me;
        const name = me.display_name || me.username || 'Seller';
        $('seller-name').textContent = name;
        $('seller-avatar').textContent = name[0]?.toUpperCase() || 'S';
        $('seller-role').textContent = me.is_helper ? `Helper · ${me.actor_role || ''}` : 'Seller';
        updateStatusDot(me.vacation_mode ? 'vacation' : 'online');
        applyRoles();
        renderProfile(me);
    } catch (e) {
        $('seller-name').textContent = 'Seller';
    }

    // Initialize i18n
    if (typeof initI18n === 'function') {
        initI18n();
        const savedLang = getSavedLanguage();
        const langSelector = $('language-selector');
        if (langSelector) langSelector.value = savedLang;
    }

    // Load first tab
    await loadConversations();
    startPolling();

    // ── Event: bottom nav ──
    qa('.nav-btn').forEach(b => b.onclick = () => setTab(b.dataset.tab));

    // ── Event: upload tabs ──
    qa('.upload-tab').forEach(b => b.onclick = () => setUploadTab(b.dataset.upload));

    // ── Event: order filters ──
    qa('.filter-chip').forEach(b => {
        b.onclick = () => {
            qa('.filter-chip').forEach(x => x.classList.remove('active'));
            b.classList.add('active');
            loadOrders(b.dataset.filter);
        };
    });

    // ── Event: chat search ──
    $('chat-search')?.addEventListener('input', () => renderConversations());

    // ── Event: send message ──
    $('send-form')?.addEventListener('submit', sendMessage);

    // ── Event: file input ──
    $('file-input')?.addEventListener('change', () => {
        const f = $('file-input').files[0];
        if (f) {
            $('file-preview-name').textContent = f.name;
            $('file-preview').classList.remove('hidden');
        }
    });
    $('file-clear-btn')?.addEventListener('click', () => {
        $('file-input').value = '';
        $('file-preview').classList.add('hidden');
    });

    // ── Event: back button (mobile) ──
    $('chat-back-btn')?.addEventListener('click', mobileChatBack);

    // ── Event: auto-resize textarea ──
    $('message-input')?.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 130) + 'px';
    });

    // ── Events: bank form ──
    $('bank-preview-btn')?.addEventListener('click', previewBank);
    $('bank-upload-form')?.addEventListener('submit', submitBank);
    $('bank-number-access')?.addEventListener('change', function () {
        $('bank-number-access-fields')?.classList.toggle('hidden', !this.checked);
    });
    $('bank-auto-unpublish')?.addEventListener('change', function () {
        $('bank-auto-unpublish-fields')?.classList.toggle('hidden', !this.checked);
    });

    // ── Events: brute form ──
    $('brute-preview-btn')?.addEventListener('click', previewBrute);
    $('brute-upload-form')?.addEventListener('submit', submitBrute);
    // Mode selector for brute upload
    qa('#brute-mode-ctrl .mode-btn').forEach(btn => {
        btn.onclick = () => {
            qa('#brute-mode-ctrl .mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const mode = btn.dataset.mode;
            $('brute-upload-mode').value = mode;
            $('brute-single-fields').classList.toggle('hidden', mode !== 'single');
            $('brute-bulk-fields').classList.toggle('hidden', mode !== 'bulk');
        };
    });
    // Drag-drop brute bulk file
    $('brute-bulk-file')?.addEventListener('change', function () {
        const f = this.files[0];
        if (f) {
            const uploadText = q('.file-upload-zone .upload-text');
            if (uploadText) uploadText.textContent = `📄 ${f.name}`;
        }
    });

    // ── Events: CC form ──
    $('cc-preview-btn')?.addEventListener('click', previewCC);
    $('cc-upload-form')?.addEventListener('submit', submitCC);
    $('cc-non-vbv')?.addEventListener('change', function () {
        $('cc-non-vbv-fields')?.classList.toggle('hidden', !this.checked);
    });

    // ── Events: NFC form ──
    $('nfc-preview-btn')?.addEventListener('click', previewNFC);
    $('nfc-upload-form')?.addEventListener('submit', submitNFC);

    // ── Events: OTP form ──
    $('otp-preview-btn')?.addEventListener('click', previewOTP);
    $('otp-upload-form')?.addEventListener('submit', submitOTP);

    // ── Events: Enroll form ──
    $('enroll-preview-btn')?.addEventListener('click', previewEnroll);
    $('enroll-upload-form')?.addEventListener('submit', submitEnroll);

    // ── Events: Selfreg CC form ──
    $('selfreg-cc-preview-btn')?.addEventListener('click', previewSelfregCC);
    $('selfreg-cc-upload-form')?.addEventListener('submit', submitSelfregCC);

    // ── Events: Checks form ──
    $('checks-preview-btn')?.addEventListener('click', previewChecks);
    $('checks-upload-form')?.addEventListener('submit', submitChecks);

    // ── Events: listings ──
    $('apply-bulk-price-btn')?.addEventListener('click', bulkReprice);

    // ── Events: templates ──
    $('save-bank-template-btn')?.addEventListener('click', () => saveTemplate('bank'));
    $('save-brute-template-btn')?.addEventListener('click', () => saveTemplate('brute'));

    // ── Events: finance ──
    $('finance-export-btn')?.addEventListener('click', exportCSV);
    $('withdraw-form')?.addEventListener('submit', requestWithdrawal);

    // ── Events: settings ──
    $('save-settings-btn')?.addEventListener('click', saveVacation);
    $('save-auto-payout-btn')?.addEventListener('click', saveAutoPayout);
    $('save-quiet-hours-btn')?.addEventListener('click', saveQuietHours);
}

// ═══════════════════════════════════════
// ADD BANK MODAL FUNCTION
// ═══════════════════════════════════════
function openAddBankModal(context) {
    const bankName = prompt(
        'Enter the bank name to add:\n\n' +
        'Examples:\n' +
        '• Chase\n' +
        '• Bank of America\n' +
        '• Wells Fargo\n' +
        '• Capital One\n' +
        '• Citi\n' +
        '• US Bank\n\n' +
        'The bank will be sent for moderation and approval.'
    );
    
    if (bankName && bankName.trim()) {
        const trimmedBankName = bankName.trim();
        
        // Send request to add bank
        api('/api/seller-mini-app/request-bank', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                bank_name: trimmedBankName,
                context: context, // 'otp' or 'checks'
                request_type: 'new_bank'
            })
        })
        .then(data => {
            if (data.success) {
                toast(`✅ Bank "${trimmedBankName}" submitted for moderation`, 'success', 4000);
            } else {
                toast(`⚠️ ${data.error || 'Failed to submit bank'}`, 'error', 4000);
            }
        })
        .catch(err => {
            toast(`❌ Error: ${err.message}`, 'error', 4000);
        });
    }
}

document.addEventListener('DOMContentLoaded', init);
