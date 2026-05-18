#!/usr/bin/env python3
"""
NewLookup — Полная юнит-экономика и модель роста до $100k MRR
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from decimal import Decimal

# ─────────────────────────────────────────────
# 1. ПРАЙС-ЛИСТ (из prices.py на сервере)
# ─────────────────────────────────────────────
SERVICES = {
    # Lookups
    "SSN/DOB Lookup":       {"price": 2.80,  "cost": 0.80,  "category": "Lookup",    "avg_qty": 3},
    "Credit Score Lookup":  {"price": 2.00,  "cost": 0.50,  "category": "Lookup",    "avg_qty": 2},
    "DL Lookup":            {"price": 7.00,  "cost": 2.00,  "category": "Lookup",    "avg_qty": 1},
    "MVR Lookup":           {"price": 11.00, "cost": 3.50,  "category": "Lookup",    "avg_qty": 1},
    "Full MVR":             {"price": 22.00, "cost": 7.00,  "category": "Lookup",    "avg_qty": 1},
    "BG Check":             {"price": 2.00,  "cost": 0.60,  "category": "Lookup",    "avg_qty": 2},
    "Phone/Name Lookup":    {"price": 1.50,  "cost": 0.40,  "category": "Lookup",    "avg_qty": 4},
    "MMN Lookup":           {"price": 9.00,  "cost": 2.50,  "category": "Lookup",    "avg_qty": 1},
    "EIN Lookup":           {"price": 11.00, "cost": 3.00,  "category": "Lookup",    "avg_qty": 1},
    # Credit Reports
    "CR TransUnion":        {"price": 4.99,  "cost": 1.50,  "category": "CR",        "avg_qty": 1},
    "CR Experian":          {"price": 5.99,  "cost": 1.80,  "category": "CR",        "avg_qty": 1},
    "CR LexisNexis":        {"price": 9.00,  "cost": 2.80,  "category": "CR",        "avg_qty": 1},
    "CR WalletHub":         {"price": 8.00,  "cost": 2.50,  "category": "CR",        "avg_qty": 1},
    # FULLZ Personal
    "FULLZ Personal Base":  {"price": 9.00,  "cost": 3.00,  "category": "FULLZ",     "avg_qty": 2},
    "FULLZ +CR+DL":         {"price": 26.00, "cost": 8.00,  "category": "FULLZ",     "avg_qty": 1},
    "FULLZ +CR+DL+MVR":     {"price": 38.00, "cost": 12.00, "category": "FULLZ",     "avg_qty": 1},
    # FULLZ Business
    "FULLZ Biz Base":       {"price": 15.00, "cost": 5.00,  "category": "FULLZ Biz", "avg_qty": 1},
    "FULLZ Biz +CR+DL":     {"price": 34.00, "cost": 11.00, "category": "FULLZ Biz", "avg_qty": 1},
    # Banks VCC
    "Bank VCC Chime":       {"price": 85.00, "cost": 40.00, "category": "Bank VCC",  "avg_qty": 1},
    "Bank VCC PayPal":      {"price": 89.00, "cost": 42.00, "category": "Bank VCC",  "avg_qty": 1},
    "Bank VCC Varo":        {"price": 120.00,"cost": 55.00, "category": "Bank VCC",  "avg_qty": 1},
    "Bank VCC Blockchain":  {"price": 170.00,"cost": 75.00, "category": "Bank VCC",  "avg_qty": 1},
    # Banks Personal
    "Bank Chase":           {"price": 99.00, "cost": 45.00, "category": "Bank Pers", "avg_qty": 1},
    "Bank Wells Fargo":     {"price": 259.00,"cost": 110.00,"category": "Bank Pers", "avg_qty": 1},
    "Bank BOA":             {"price": 100.00,"cost": 45.00, "category": "Bank Pers", "avg_qty": 1},
    "Bank PNC":             {"price": 140.00,"cost": 60.00, "category": "Bank Pers", "avg_qty": 1},
    # Banks Business
    "Bank Biz Chase":       {"price": 199.00,"cost": 85.00, "category": "Bank Biz",  "avg_qty": 1},
    "Bank Biz Wells":       {"price": 395.00,"cost": 160.00,"category": "Bank Biz",  "avg_qty": 1},
    "Bank Biz Capital One": {"price": 250.00,"cost": 100.00,"category": "Bank Biz",  "avg_qty": 1},
    # Crypto Banks
    "Bank CashApp":         {"price": 160.00,"cost": 65.00, "category": "Bank Crypto","avg_qty": 1},
    "Bank Coinbase":        {"price": 140.00,"cost": 58.00, "category": "Bank Crypto","avg_qty": 1},
    # eSIM
    "eSIM Verizon 1mo":     {"price": 20.00, "cost": 8.00,  "category": "eSIM",      "avg_qty": 2},
    "eSIM AT&T 1mo":        {"price": 35.00, "cost": 12.00, "category": "eSIM",      "avg_qty": 1},
    "eSIM T-Mobile 1mo":    {"price": 35.00, "cost": 12.00, "category": "eSIM",      "avg_qty": 1},
    "eSIM Data 5GB":        {"price": 25.00, "cost": 9.00,  "category": "eSIM",      "avg_qty": 2},
    "eSIM Data 10GB":       {"price": 40.00, "cost": 14.00, "category": "eSIM",      "avg_qty": 1},
    # Add Info
    "Add Info Phone+Addr":  {"price": 80.00, "cost": 30.00, "category": "Add Info",  "avg_qty": 1},
    "Add Info Phone Only":  {"price": 40.00, "cost": 15.00, "category": "Add Info",  "avg_qty": 1},
    "Unfreeze TU":          {"price": 20.00, "cost": 7.00,  "category": "Add Info",  "avg_qty": 1},
    "Unfreeze Experian":    {"price": 25.00, "cost": 9.00,  "category": "Add Info",  "avg_qty": 1},
    # Education (estimated)
    "Education Sub 1mo":    {"price": 29.00, "cost": 5.00,  "category": "Education", "avg_qty": 1},
    "Education Sub 3mo":    {"price": 69.00, "cost": 10.00, "category": "Education", "avg_qty": 1},
    "Education Manual":     {"price": 19.00, "cost": 3.00,  "category": "Education", "avg_qty": 1},
}

# ─────────────────────────────────────────────
# 2. СИСТЕМНЫЕ КОМИССИИ
# ─────────────────────────────────────────────
PAYMENT_FEE = 0.03        # 3% платёжная комиссия (CryptoPay)
REFERRAL_PERCENT = 0.04   # 4% рефереру
MARKETER_PERCENT = 0.07   # 7% маркетологу
MARKETER_USER_BONUS = 0.03 # 3% бонус пользователю от маркетолога

# ─────────────────────────────────────────────
# 3. ИНФРАСТРУКТУРНЫЕ ЗАТРАТЫ ($/мес)
# ─────────────────────────────────────────────
INFRA_COSTS = {
    "VPS сервер (24GB RAM, 6 CPU, 217GB)": 80,
    "Домен + SSL":                          5,
    "Telegram Bot API (бесплатно)":         0,
    "CryptoPay / Cryptomus (% от оборота)": 0,  # включено в PAYMENT_FEE
    "Резервный сервер (backup)":            30,
    "Мониторинг (Grafana/UptimeRobot)":     10,
    "CDN / защита от DDoS":                 15,
}
FIXED_COSTS_MONTHLY = sum(INFRA_COSTS.values())  # $140/мес

# ─────────────────────────────────────────────
# 4. РАСЧЁТ МАРЖИ ПО КАТЕГОРИЯМ
# ─────────────────────────────────────────────
categories = {}
for name, s in SERVICES.items():
    cat = s["category"]
    margin = (s["price"] - s["cost"]) / s["price"] * 100
    if cat not in categories:
        categories[cat] = {"prices": [], "costs": [], "margins": []}
    categories[cat]["prices"].append(s["price"])
    categories[cat]["costs"].append(s["cost"])
    categories[cat]["margins"].append(margin)

cat_summary = {}
for cat, data in categories.items():
    avg_price = np.mean(data["prices"])
    avg_cost = np.mean(data["costs"])
    avg_margin = np.mean(data["margins"])
    cat_summary[cat] = {
        "avg_price": avg_price,
        "avg_cost": avg_cost,
        "avg_margin": avg_margin,
        "gross_margin_pct": (avg_price - avg_cost) / avg_price * 100
    }

# ─────────────────────────────────────────────
# 5. ТИПИЧНЫЙ ПОЛЬЗОВАТЕЛЬ (ARPU, LTV, CAC)
# ─────────────────────────────────────────────
# Распределение заказов по категориям (% от всех заказов)
ORDER_MIX = {
    "Lookup":     0.40,  # 40% — самые дешёвые, самые частые
    "CR":         0.15,  # 15%
    "FULLZ":      0.12,  # 12%
    "FULLZ Biz":  0.05,  # 5%
    "Bank VCC":   0.08,  # 8%
    "Bank Pers":  0.06,  # 6%
    "Bank Biz":   0.03,  # 3%
    "Bank Crypto":0.03,  # 3%
    "eSIM":       0.04,  # 4%
    "Add Info":   0.02,  # 2%
    "Education":  0.02,  # 2%
}

# Средний чек по категориям (взвешенный)
avg_order_value = sum(
    ORDER_MIX.get(cat, 0) * cat_summary[cat]["avg_price"]
    for cat in cat_summary
)
avg_order_cost = sum(
    ORDER_MIX.get(cat, 0) * cat_summary[cat]["avg_cost"]
    for cat in cat_summary
)
avg_gross_margin_pct = (avg_order_value - avg_order_cost) / avg_order_value

print(f"Средний чек (AOV): ${avg_order_value:.2f}")
print(f"Средняя себестоимость: ${avg_order_cost:.2f}")
print(f"Валовая маржа: {avg_gross_margin_pct*100:.1f}%")

# Метрики пользователя
ORDERS_PER_USER_PER_MONTH = 4.5     # среднее кол-во заказов в месяц
USER_LIFETIME_MONTHS = 6            # средняя жизнь пользователя
CHURN_RATE_MONTHLY = 0.18           # 18% отток в месяц
REFERRAL_TRAFFIC_PCT = 0.30         # 30% приходят по реф-ссылке
MARKETER_TRAFFIC_PCT = 0.25         # 25% приходят через маркетологов

# ARPU (Monthly)
arpu_gross = avg_order_value * ORDERS_PER_USER_PER_MONTH
arpu_net = avg_order_cost * ORDERS_PER_USER_PER_MONTH  # себестоимость
arpu_platform = arpu_gross - arpu_net  # платформенная маржа до комиссий

# Комиссии с ARPU
payment_fee_per_user = arpu_gross * PAYMENT_FEE
referral_fee_per_user = arpu_gross * REFERRAL_PERCENT * REFERRAL_TRAFFIC_PCT
marketer_fee_per_user = arpu_gross * MARKETER_PERCENT * MARKETER_TRAFFIC_PCT

arpu_clean = arpu_platform - payment_fee_per_user - referral_fee_per_user - marketer_fee_per_user

# LTV
ltv = arpu_clean * USER_LIFETIME_MONTHS

# CAC (стоимость привлечения)
# Каналы: органика (Telegram), маркетологи, реф-ссылки
CAC_ORGANIC = 0         # бесплатно (Telegram, сарафан)
CAC_MARKETER = 8        # маркетолог получает 7% с первых $115 = ~$8
CAC_REFERRAL = 5        # реферер получает 4% с первых $125 = ~$5
CAC_BLENDED = (
    CAC_ORGANIC * 0.45 +
    CAC_MARKETER * MARKETER_TRAFFIC_PCT +
    CAC_REFERRAL * REFERRAL_TRAFFIC_PCT
)

ltv_cac_ratio = ltv / CAC_BLENDED if CAC_BLENDED > 0 else float('inf')

print(f"\n--- МЕТРИКИ ПОЛЬЗОВАТЕЛЯ ---")
print(f"ARPU (gross): ${arpu_gross:.2f}/мес")
print(f"ARPU (net после всех комиссий): ${arpu_clean:.2f}/мес")
print(f"LTV: ${ltv:.2f}")
print(f"CAC (blended): ${CAC_BLENDED:.2f}")
print(f"LTV/CAC: {ltv_cac_ratio:.1f}x")
print(f"Payback period: {CAC_BLENDED/arpu_clean:.1f} мес")

# ─────────────────────────────────────────────
# 6. ТОЧКА БЕЗУБЫТОЧНОСТИ
# ─────────────────────────────────────────────
breakeven_users = FIXED_COSTS_MONTHLY / arpu_clean
print(f"\n--- ТОЧКА БЕЗУБЫТОЧНОСТИ ---")
print(f"Фиксированные затраты: ${FIXED_COSTS_MONTHLY}/мес")
print(f"Нужно активных пользователей: {breakeven_users:.0f}")

# ─────────────────────────────────────────────
# 7. МОДЕЛЬ РОСТА ДО $100K MRR (24 месяца)
# ─────────────────────────────────────────────
# Сценарий: органический рост + маркетологи + реф-система
months = 24
users_start = 50
growth_rates = [
    # М1-3: запуск, медленный рост
    0.25, 0.30, 0.35,
    # М4-6: маркетологи подключились
    0.40, 0.45, 0.45,
    # М7-12: активный рост
    0.40, 0.38, 0.35, 0.32, 0.30, 0.28,
    # М13-18: масштабирование
    0.25, 0.23, 0.22, 0.20, 0.20, 0.18,
    # М19-24: стабилизация
    0.17, 0.16, 0.15, 0.14, 0.13, 0.12,
]

monthly_data = []
active_users = users_start
cumulative_revenue = 0

for m in range(months):
    growth = growth_rates[m] if m < len(growth_rates) else 0.10
    new_users = int(active_users * growth)
    churned = int(active_users * CHURN_RATE_MONTHLY)
    active_users = active_users + new_users - churned

    gross_revenue = active_users * arpu_gross
    cogs = active_users * arpu_net
    payment_fees = gross_revenue * PAYMENT_FEE
    ref_fees = gross_revenue * REFERRAL_PERCENT * REFERRAL_TRAFFIC_PCT
    mkt_fees = gross_revenue * MARKETER_PERCENT * MARKETER_TRAFFIC_PCT
    net_revenue = gross_revenue - cogs - payment_fees - ref_fees - mkt_fees
    profit = net_revenue - FIXED_COSTS_MONTHLY

    # Инфра масштабируется
    extra_infra = 0
    if active_users > 500:
        extra_infra = 80   # доп сервер
    if active_users > 2000:
        extra_infra = 200  # кластер
    if active_users > 5000:
        extra_infra = 400  # enterprise

    total_costs = FIXED_COSTS_MONTHLY + extra_infra + cogs + payment_fees + ref_fees + mkt_fees
    actual_profit = gross_revenue - total_costs
    cumulative_revenue += gross_revenue

    monthly_data.append({
        "month": m + 1,
        "active_users": active_users,
        "new_users": new_users,
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "total_costs": total_costs,
        "profit": actual_profit,
        "cumulative_revenue": cumulative_revenue,
        "mrr": gross_revenue,
        "extra_infra": extra_infra,
    })

# ─────────────────────────────────────────────
# 8. ГРАФИКИ
# ─────────────────────────────────────────────
fig = plt.figure(figsize=(20, 24))
fig.patch.set_facecolor('#0d1117')

# Цветовая схема
DARK_BG = '#0d1117'
CARD_BG = '#161b22'
ACCENT1 = '#58a6ff'
ACCENT2 = '#3fb950'
ACCENT3 = '#f78166'
ACCENT4 = '#d2a8ff'
ACCENT5 = '#ffa657'
TEXT_COLOR = '#e6edf3'
GRID_COLOR = '#21262d'

plt.rcParams.update({
    'text.color': TEXT_COLOR,
    'axes.labelcolor': TEXT_COLOR,
    'xtick.color': TEXT_COLOR,
    'ytick.color': TEXT_COLOR,
    'axes.facecolor': CARD_BG,
    'figure.facecolor': DARK_BG,
    'axes.edgecolor': GRID_COLOR,
    'grid.color': GRID_COLOR,
    'font.family': 'DejaVu Sans',
    'font.size': 11,
})

months_list = [d["month"] for d in monthly_data]
mrr_list = [d["mrr"] for d in monthly_data]
users_list = [d["active_users"] for d in monthly_data]
profit_list = [d["profit"] for d in monthly_data]
costs_list = [d["total_costs"] for d in monthly_data]

# --- PLOT 1: MRR Growth ---
ax1 = fig.add_subplot(4, 2, 1)
ax1.fill_between(months_list, mrr_list, alpha=0.3, color=ACCENT1)
ax1.plot(months_list, mrr_list, color=ACCENT1, linewidth=2.5, marker='o', markersize=4)
ax1.axhline(y=100000, color=ACCENT3, linestyle='--', linewidth=1.5, label='$100k target')
# Mark $100k crossing
for i, d in enumerate(monthly_data):
    if d["mrr"] >= 100000:
        ax1.axvline(x=d["month"], color=ACCENT3, linestyle=':', alpha=0.7)
        ax1.annotate(f'M{d["month"]}: $100k!', xy=(d["month"], 100000),
                    xytext=(d["month"]-3, 115000), color=ACCENT3, fontsize=9,
                    arrowprops=dict(arrowstyle='->', color=ACCENT3))
        break
ax1.set_title('MRR Growth (Gross)', color=TEXT_COLOR, fontsize=13, fontweight='bold', pad=10)
ax1.set_xlabel('Month')
ax1.set_ylabel('MRR ($)')
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000:.0f}k'))
ax1.legend(facecolor=CARD_BG, edgecolor=GRID_COLOR)
ax1.grid(True, alpha=0.3)

# --- PLOT 2: Active Users ---
ax2 = fig.add_subplot(4, 2, 2)
ax2.fill_between(months_list, users_list, alpha=0.3, color=ACCENT2)
ax2.plot(months_list, users_list, color=ACCENT2, linewidth=2.5, marker='o', markersize=4)
ax2.set_title('Active Users Growth', color=TEXT_COLOR, fontsize=13, fontweight='bold', pad=10)
ax2.set_xlabel('Month')
ax2.set_ylabel('Active Users')
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.1f}k' if x >= 1000 else f'{x:.0f}'))
ax2.grid(True, alpha=0.3)

# --- PLOT 3: Revenue vs Costs vs Profit ---
ax3 = fig.add_subplot(4, 2, 3)
ax3.fill_between(months_list, mrr_list, alpha=0.2, color=ACCENT1, label='Gross Revenue')
ax3.fill_between(months_list, costs_list, alpha=0.2, color=ACCENT3, label='Total Costs')
ax3.plot(months_list, mrr_list, color=ACCENT1, linewidth=2)
ax3.plot(months_list, costs_list, color=ACCENT3, linewidth=2)
ax3.plot(months_list, profit_list, color=ACCENT2, linewidth=2.5, linestyle='--', label='Net Profit')
ax3.axhline(y=0, color=TEXT_COLOR, linestyle='-', linewidth=0.5, alpha=0.5)
ax3.set_title('Revenue vs Costs vs Profit', color=TEXT_COLOR, fontsize=13, fontweight='bold', pad=10)
ax3.set_xlabel('Month')
ax3.set_ylabel('$')
ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000:.0f}k'))
ax3.legend(facecolor=CARD_BG, edgecolor=GRID_COLOR)
ax3.grid(True, alpha=0.3)

# --- PLOT 4: Margin by Category ---
ax4 = fig.add_subplot(4, 2, 4)
cats = list(cat_summary.keys())
margins = [cat_summary[c]["gross_margin_pct"] for c in cats]
colors_bar = [ACCENT1, ACCENT2, ACCENT3, ACCENT4, ACCENT5,
              '#79c0ff', '#56d364', '#ff7b72', '#bc8cff', '#ffb347', '#63e6be']
bars = ax4.barh(cats, margins, color=colors_bar[:len(cats)], alpha=0.85)
for bar, val in zip(bars, margins):
    ax4.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
             f'{val:.0f}%', va='center', color=TEXT_COLOR, fontsize=9)
ax4.set_title('Gross Margin by Category', color=TEXT_COLOR, fontsize=13, fontweight='bold', pad=10)
ax4.set_xlabel('Gross Margin %')
ax4.set_xlim(0, 85)
ax4.grid(True, alpha=0.3, axis='x')

# --- PLOT 5: Revenue Mix (Pie) ---
ax5 = fig.add_subplot(4, 2, 5)
mix_labels = list(ORDER_MIX.keys())
mix_values = list(ORDER_MIX.values())
wedge_colors = [ACCENT1, ACCENT2, ACCENT3, ACCENT4, ACCENT5,
                '#79c0ff', '#56d364', '#ff7b72', '#bc8cff', '#ffb347', '#63e6be']
wedges, texts, autotexts = ax5.pie(
    mix_values, labels=mix_labels, autopct='%1.0f%%',
    colors=wedge_colors[:len(mix_labels)],
    textprops={'color': TEXT_COLOR, 'fontsize': 9},
    pctdistance=0.8
)
for at in autotexts:
    at.set_fontsize(8)
ax5.set_title('Order Mix by Category', color=TEXT_COLOR, fontsize=13, fontweight='bold', pad=10)

# --- PLOT 6: Unit Economics Summary ---
ax6 = fig.add_subplot(4, 2, 6)
ax6.axis('off')
metrics = [
    ("AOV (Average Order Value)", f"${avg_order_value:.2f}"),
    ("ARPU Gross (monthly)", f"${arpu_gross:.2f}"),
    ("ARPU Net (after all fees)", f"${arpu_clean:.2f}"),
    ("Gross Margin", f"{avg_gross_margin_pct*100:.1f}%"),
    ("LTV (6 months)", f"${ltv:.2f}"),
    ("CAC (blended)", f"${CAC_BLENDED:.2f}"),
    ("LTV/CAC Ratio", f"{ltv_cac_ratio:.1f}x"),
    ("Payback Period", f"{CAC_BLENDED/arpu_clean:.1f} months"),
    ("Breakeven (users)", f"{breakeven_users:.0f} active users"),
    ("Fixed Costs", f"${FIXED_COSTS_MONTHLY}/mo"),
    ("Payment Fee", f"{PAYMENT_FEE*100:.0f}% (CryptoPay)"),
    ("Referral Commission", f"{REFERRAL_PERCENT*100:.0f}% to referrer"),
    ("Marketer Commission", f"{MARKETER_PERCENT*100:.0f}% to marketer"),
    ("Monthly Churn Rate", f"{CHURN_RATE_MONTHLY*100:.0f}%"),
    ("User Lifetime", f"{USER_LIFETIME_MONTHS} months"),
]
y_pos = 0.97
ax6.set_title('Unit Economics Summary', color=TEXT_COLOR, fontsize=13, fontweight='bold', pad=10)
for i, (label, value) in enumerate(metrics):
    color = ACCENT2 if i % 2 == 0 else ACCENT1
    ax6.text(0.02, y_pos, label, transform=ax6.transAxes,
             color='#8b949e', fontsize=9.5, va='top')
    ax6.text(0.75, y_pos, value, transform=ax6.transAxes,
             color=color, fontsize=9.5, va='top', fontweight='bold')
    y_pos -= 0.063

# --- PLOT 7: Cumulative Revenue ---
ax7 = fig.add_subplot(4, 2, 7)
cum_rev = [d["cumulative_revenue"] for d in monthly_data]
cum_profit = []
cp = 0
for d in monthly_data:
    cp += d["profit"]
    cum_profit.append(cp)
ax7.fill_between(months_list, cum_rev, alpha=0.2, color=ACCENT1)
ax7.plot(months_list, cum_rev, color=ACCENT1, linewidth=2.5, label='Cumulative Revenue')
ax7.fill_between(months_list, [max(0, p) for p in cum_profit], alpha=0.2, color=ACCENT2)
ax7.plot(months_list, cum_profit, color=ACCENT2, linewidth=2.5, linestyle='--', label='Cumulative Profit')
ax7.axhline(y=0, color=TEXT_COLOR, linewidth=0.5, alpha=0.5)
ax7.set_title('Cumulative Revenue & Profit (24 months)', color=TEXT_COLOR, fontsize=13, fontweight='bold', pad=10)
ax7.set_xlabel('Month')
ax7.set_ylabel('$')
ax7.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000:.0f}k'))
ax7.legend(facecolor=CARD_BG, edgecolor=GRID_COLOR)
ax7.grid(True, alpha=0.3)

# --- PLOT 8: Monthly Breakdown Table (last 6 months) ---
ax8 = fig.add_subplot(4, 2, 8)
ax8.axis('off')
ax8.set_title('Growth Milestones', color=TEXT_COLOR, fontsize=13, fontweight='bold', pad=10)

# Find key milestones
milestones = []
targets = [1000, 5000, 10000, 25000, 50000, 100000]
found = set()
for d in monthly_data:
    for t in targets:
        if d["mrr"] >= t and t not in found:
            found.add(t)
            milestones.append((f"M{d['month']}", f"${t/1000:.0f}k MRR", f"{d['active_users']:,} users", f"${d['profit']:,.0f}/mo profit"))

col_labels = ['Month', 'MRR Target', 'Users', 'Monthly Profit']
table_data = milestones[:6]
if table_data:
    table = ax8.table(
        cellText=table_data,
        colLabels=col_labels,
        cellLoc='center',
        loc='center',
        bbox=[0, 0.1, 1, 0.85]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (row, col), cell in table.get_celld().items():
        cell.set_facecolor(CARD_BG if row > 0 else '#21262d')
        cell.set_edgecolor(GRID_COLOR)
        cell.set_text_props(color=TEXT_COLOR if row > 0 else ACCENT1)

plt.suptitle('NewLookup — Unit Economics & Growth Model to $100k MRR',
             color=TEXT_COLOR, fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout(rect=[0, 0, 1, 0.995])
plt.savefig('/home/ubuntu/unit_economics_charts.png', dpi=150, bbox_inches='tight',
            facecolor=DARK_BG, edgecolor='none')
plt.close()
print("\nCharts saved!")

# ─────────────────────────────────────────────
# 9. ВЫВОД ПОЛНОЙ ТАБЛИЦЫ ПО МЕСЯЦАМ
# ─────────────────────────────────────────────
print("\n{'='*80}")
print(f"{'Мес':>4} | {'Пользователи':>12} | {'MRR (Gross)':>12} | {'Затраты':>10} | {'Прибыль':>10} | {'Кум. Прибыль':>12}")
print("-"*70)
cp = 0
for d in monthly_data:
    cp += d["profit"]
    print(f"M{d['month']:>2}  | {d['active_users']:>12,} | ${d['mrr']:>11,.0f} | ${d['total_costs']:>9,.0f} | ${d['profit']:>9,.0f} | ${cp:>11,.0f}")

print(f"\n{'='*70}")
print(f"ИТОГО за 24 месяца:")
print(f"  Суммарная выручка: ${monthly_data[-1]['cumulative_revenue']:,.0f}")
print(f"  Финальный MRR: ${monthly_data[-1]['mrr']:,.0f}")
print(f"  Финальные активные пользователи: {monthly_data[-1]['active_users']:,}")
