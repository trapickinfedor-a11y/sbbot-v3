#!/usr/bin/env python3
"""
NewLookup — Модель роста до 100,000 пользователей
Юнит-экономика + Стратегия + Графики
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ─────────────────────────────────────────────
# ЦВЕТА
# ─────────────────────────────────────────────
DARK_BG   = '#0d1117'
CARD_BG   = '#161b22'
ACCENT1   = '#58a6ff'   # синий
ACCENT2   = '#3fb950'   # зелёный
ACCENT3   = '#f78166'   # красный/оранжевый
ACCENT4   = '#d2a8ff'   # фиолетовый
ACCENT5   = '#ffa657'   # жёлтый
TEXT_COLOR = '#e6edf3'
GRID_COLOR = '#21262d'

plt.rcParams.update({
    'text.color': TEXT_COLOR, 'axes.labelcolor': TEXT_COLOR,
    'xtick.color': TEXT_COLOR, 'ytick.color': TEXT_COLOR,
    'axes.facecolor': CARD_BG, 'figure.facecolor': DARK_BG,
    'axes.edgecolor': GRID_COLOR, 'grid.color': GRID_COLOR,
    'font.family': 'DejaVu Sans', 'font.size': 10,
})

# ─────────────────────────────────────────────
# ЮНИТ-ЭКОНОМИКА (из реального кода проекта)
# ─────────────────────────────────────────────
AOV              = 42.26    # средний чек ($)
ORDERS_PER_MONTH = 4.5      # заказов на пользователя в месяц
ARPU_GROSS       = AOV * ORDERS_PER_MONTH  # $190.19
GROSS_MARGIN     = 0.601    # 60.1%
ARPU_NET         = 103.07   # чистый ARPU после всех комиссий
LTV_6M           = ARPU_NET * 6
CAC_BLENDED      = 3.50     # средний CAC

# ─────────────────────────────────────────────
# СЦЕНАРИИ РОСТА ДО 100k ПОЛЬЗОВАТЕЛЕЙ
# ─────────────────────────────────────────────
def simulate(scenario, months=36):
    """
    Симуляция роста по сценарию.
    Ключевые каналы:
      1. Органика (SEO, сарафан)
      2. Зеркальные боты (Mirror Bots)
      3. Маркетологи (Marketers)
      4. Рефералы (4% комиссия)
    """
    cfg = {
        'conservative': {
            'start': 50,
            'churn': 0.20,
            'organic_rate': 0.06,       # % от текущей базы в месяц
            'mirror_new_per_month': 2,  # новых зеркал в месяц
            'users_per_mirror': 15,     # пользователей с 1 зеркала в месяц
            'mkt_new_per_month': 2,     # новых маркетологов в месяц
            'users_per_mkt': 10,        # пользователей от 1 маркетолога в месяц
            'ref_rate': 0.05,           # % пользователей, приглашающих рефералов
            'refs_per_user': 0.3,       # рефералов от 1 пользователя в месяц
        },
        'base': {
            'start': 100,
            'churn': 0.15,
            'organic_rate': 0.10,
            'mirror_new_per_month': 5,
            'users_per_mirror': 22,
            'mkt_new_per_month': 5,
            'users_per_mkt': 15,
            'ref_rate': 0.08,
            'refs_per_user': 0.5,
        },
        'aggressive': {
            'start': 200,
            'churn': 0.12,
            'organic_rate': 0.15,
            'mirror_new_per_month': 10,
            'users_per_mirror': 30,
            'mkt_new_per_month': 10,
            'users_per_mkt': 22,
            'ref_rate': 0.12,
            'refs_per_user': 0.8,
        },
    }
    p = cfg[scenario]

    data = []
    users = p['start']
    mirrors = 0
    marketers = 0
    cumulative_rev = 0
    cumulative_profit = 0
    reached_100k = None

    for m in range(1, months + 1):
        mirrors    += p['mirror_new_per_month']
        marketers  += p['mkt_new_per_month']

        # Новые пользователи по каналам
        organic_new  = int(users * p['organic_rate'])
        mirror_new   = int(mirrors * p['users_per_mirror'])
        mkt_new      = int(marketers * p['users_per_mkt'])
        ref_new      = int(users * p['ref_rate'] * p['refs_per_user'])
        total_new    = organic_new + mirror_new + mkt_new + ref_new

        # Отток
        churned = int(users * p['churn'])
        users   = max(1, users + total_new - churned)

        if users >= 100_000 and reached_100k is None:
            reached_100k = m

        # Финансы
        gross_rev    = users * ARPU_GROSS
        cogs         = gross_rev * (1 - GROSS_MARGIN)
        payment_fee  = gross_rev * 0.03
        ref_fee      = gross_rev * 0.04 * 0.30
        mkt_fee      = gross_rev * 0.07 * 0.25
        infra        = 140 + min(users // 500 * 80, 1200)
        total_costs  = cogs + payment_fee + ref_fee + mkt_fee + infra
        net_profit   = gross_rev - total_costs
        cumulative_rev    += gross_rev
        cumulative_profit += net_profit

        data.append({
            'm': m, 'users': users, 'mirrors': mirrors, 'marketers': marketers,
            'new_organic': organic_new, 'new_mirror': mirror_new,
            'new_mkt': mkt_new, 'new_ref': ref_new, 'total_new': total_new,
            'churned': churned, 'mrr': gross_rev, 'net_profit': net_profit,
            'cum_rev': cumulative_rev, 'cum_profit': cumulative_profit,
        })

    return data, reached_100k

cons_data,  cons_100k  = simulate('conservative')
base_data,  base_100k  = simulate('base')
aggr_data,  aggr_100k  = simulate('aggressive')

months_x = [d['m'] for d in base_data]

print(f"Консервативный: 100k пользователей — месяц {cons_100k}")
print(f"Базовый:        100k пользователей — месяц {base_100k}")
print(f"Агрессивный:    100k пользователей — месяц {aggr_100k}")

# ─────────────────────────────────────────────
# ГРАФИКИ
# ─────────────────────────────────────────────
fig = plt.figure(figsize=(22, 30))
fig.patch.set_facecolor(DARK_BG)

# ── 1. Рост пользователей ──
ax1 = fig.add_subplot(4, 2, 1)
for data, color, label, m100k in [
    (cons_data, ACCENT3, 'Conservative', cons_100k),
    (base_data, ACCENT1, 'Base',         base_100k),
    (aggr_data, ACCENT2, 'Aggressive',   aggr_100k),
]:
    ux = [d['users'] for d in data]
    ax1.fill_between(months_x, ux, alpha=0.12, color=color)
    ax1.plot(months_x, ux, color=color, lw=2.5, label=label)
    if m100k:
        ax1.axvline(x=m100k, color=color, ls=':', lw=1.5, alpha=0.8)
        ax1.annotate(f'M{m100k}', xy=(m100k, 100000), color=color,
                     fontsize=8, ha='left', va='bottom')

ax1.axhline(y=100000, color='white', ls='--', lw=1.5, alpha=0.6, label='100k target')
ax1.set_title('User Growth — 3 Scenarios', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax1.set_xlabel('Month'); ax1.set_ylabel('Active Users')
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
ax1.legend(facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9)
ax1.grid(True, alpha=0.3)

# ── 2. MRR при 100k пользователях ──
ax2 = fig.add_subplot(4, 2, 2)
for data, color, label in [
    (cons_data, ACCENT3, 'Conservative'),
    (base_data, ACCENT1, 'Base'),
    (aggr_data, ACCENT2, 'Aggressive'),
]:
    ax2.fill_between(months_x, [d['mrr'] for d in data], alpha=0.12, color=color)
    ax2.plot(months_x, [d['mrr'] for d in data], color=color, lw=2.5, label=label)

ax2.set_title('MRR Growth — 3 Scenarios', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax2.set_xlabel('Month'); ax2.set_ylabel('MRR ($)')
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000000:.1f}M' if x >= 1e6 else f'${x/1000:.0f}k'))
ax2.legend(facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9)
ax2.grid(True, alpha=0.3)

# ── 3. Разбивка новых пользователей по каналам (Base, стек) ──
ax3 = fig.add_subplot(4, 2, 3)
org  = [d['new_organic'] for d in base_data]
mir  = [d['new_mirror']  for d in base_data]
mkt  = [d['new_mkt']     for d in base_data]
ref  = [d['new_ref']     for d in base_data]
ax3.stackplot(months_x, org, ref, mir, mkt,
              labels=['Organic', 'Referral', 'Mirror Bots', 'Marketers'],
              colors=[ACCENT1, ACCENT4, ACCENT5, ACCENT2], alpha=0.85)
ax3.set_title('New Users by Channel — Base Scenario', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax3.set_xlabel('Month'); ax3.set_ylabel('New Users / Month')
ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
ax3.legend(facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9, loc='upper left')
ax3.grid(True, alpha=0.3)

# ── 4. Mirror Bots и Marketers (Base) ──
ax4 = fig.add_subplot(4, 2, 4)
ax4_twin = ax4.twinx()
ax4.plot(months_x, [d['mirrors'] for d in base_data], color=ACCENT1, lw=2.5, marker='o', ms=3, label='Mirror Bots')
ax4_twin.plot(months_x, [d['marketers'] for d in base_data], color=ACCENT5, lw=2.5, marker='s', ms=3, label='Marketers')
ax4.set_title('Mirror Bots & Marketers Growth (Base)', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax4.set_xlabel('Month')
ax4.set_ylabel('Mirror Bots', color=ACCENT1)
ax4_twin.set_ylabel('Marketers', color=ACCENT5)
ax4_twin.tick_params(axis='y', colors=ACCENT5)
ax4.tick_params(axis='y', colors=ACCENT1)
lines1, labels1 = ax4.get_legend_handles_labels()
lines2, labels2 = ax4_twin.get_legend_handles_labels()
ax4.legend(lines1 + lines2, labels1 + labels2, facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9)
ax4.grid(True, alpha=0.3)

# ── 5. Чистая прибыль по месяцам (Base) ──
ax5 = fig.add_subplot(4, 2, 5)
profits = [d['net_profit'] for d in base_data]
bar_colors = [ACCENT2 if p >= 0 else ACCENT3 for p in profits]
ax5.bar(months_x, profits, color=bar_colors, alpha=0.85)
ax5.axhline(y=0, color=TEXT_COLOR, lw=0.8, alpha=0.5)
ax5.set_title('Monthly Net Profit — Base Scenario', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax5.set_xlabel('Month'); ax5.set_ylabel('Net Profit ($)')
ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000000:.1f}M' if abs(x) >= 1e6 else f'${x/1000:.0f}k'))
ax5.grid(True, alpha=0.3, axis='y')

# ── 6. Накопленная прибыль ──
ax6 = fig.add_subplot(4, 2, 6)
for data, color, label in [
    (cons_data, ACCENT3, 'Conservative'),
    (base_data, ACCENT1, 'Base'),
    (aggr_data, ACCENT2, 'Aggressive'),
]:
    ax6.fill_between(months_x, [d['cum_profit'] for d in data], alpha=0.12, color=color)
    ax6.plot(months_x, [d['cum_profit'] for d in data], color=color, lw=2.5, label=label)
ax6.axhline(y=0, color=TEXT_COLOR, lw=0.8, alpha=0.5)
ax6.set_title('Cumulative Net Profit (36 months)', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax6.set_xlabel('Month'); ax6.set_ylabel('Cumulative Profit ($)')
ax6.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000000:.0f}M'))
ax6.legend(facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9)
ax6.grid(True, alpha=0.3)

# ── 7. Юнит-экономика таблица ──
ax7 = fig.add_subplot(4, 2, 7)
ax7.axis('off')
ax7.set_title('Unit Economics — Key Metrics', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)

rows = [
    ("МЕТРИКА", "ЗНАЧЕНИЕ", "КОММЕНТАРИЙ"),
    ("AOV (средний чек)", "$42.26", "Взвешенный по всем категориям"),
    ("ARPU Gross (мес)", "$190.19", "4.5 заказа × $42.26"),
    ("ARPU Net (мес)", "$103.07", "После себестоимости и комиссий"),
    ("Gross Margin", "60.1%", "Средняя по всем услугам"),
    ("LTV (6 мес)", "$618", "ARPU Net × 6 мес"),
    ("CAC (blended)", "$3.50", "Органика + реф + маркетолог"),
    ("LTV / CAC", "176x", "Отличный показатель"),
    ("Payback Period", "< 1 мес", "Мгновенная окупаемость"),
    ("Breakeven", "2 пользователя", "$140 fixed / $103 ARPU"),
    ("Реф. комиссия", "4% от заказа", "Рефереру при каждом заказе"),
    ("Маркетолог", "7% от заказа", "Маркетологу при каждом заказе"),
    ("Платёжная комиссия", "3% (Crypto)", "CryptoPay / Cryptomus"),
    ("Churn (base)", "15%/мес", "Цель — снизить до 8-10%"),
    ("При 100k users MRR", "~$19M/мес", "ARPU Gross × 100,000"),
    ("При 100k users Profit", "~$10.3M/мес", "ARPU Net × 100,000"),
]

y = 0.98
for i, row in enumerate(rows):
    if i == 0:
        for text, x_pos in zip(row, [0.01, 0.45, 0.68]):
            ax7.text(x_pos, y, text, transform=ax7.transAxes,
                     color=ACCENT1, fontsize=9, fontweight='bold', va='top')
        y -= 0.04
        continue
    for j, (text, x_pos) in enumerate(zip(row, [0.01, 0.45, 0.68])):
        color = TEXT_COLOR if j == 0 else (ACCENT2 if j == 1 else '#8b949e')
        ax7.text(x_pos, y, text, transform=ax7.transAxes,
                 color=color, fontsize=8.5, va='top')
    y -= 0.058

# ── 8. Roadmap ──
ax8 = fig.add_subplot(4, 2, 8)
ax8.axis('off')
ax8.set_title('Roadmap to 100,000 Users', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)

phases = [
    ("ФАЗА 1 (M1-3): Запуск", [
        "Старт: 100 пользователей",
        "5-10 зеркальных ботов",
        "10-15 маркетологов",
        "Настроить реф-систему и рассылки",
        "Цель: 500 активных пользователей",
    ], ACCENT3),
    ("ФАЗА 2 (M4-9): Рост", [
        "30+ зеркальных ботов",
        "50+ маркетологов",
        "Запустить Announcements-рассылки",
        "Снизить churn до 12%",
        "Цель: 5,000 активных пользователей",
    ], ACCENT5),
    ("ФАЗА 3 (M10-18): Масштаб", [
        "100+ зеркальных ботов",
        "150+ маркетологов",
        "Автоматизация воркеров",
        "Программа лояльности",
        "Цель: 30,000 активных пользователей",
    ], ACCENT1),
    ("ФАЗА 4 (M19-24+): 100k", [
        "200+ зеркальных ботов",
        "300+ маркетологов",
        "Новые категории услуг",
        "Гео-экспансия (EU, Asia)",
        "Цель: 100,000 пользователей",
    ], ACCENT2),
]

y = 0.97
for title, actions, color in phases:
    ax8.text(0.01, y, f"▶ {title}", transform=ax8.transAxes,
             color=color, fontsize=9.5, fontweight='bold', va='top')
    y -= 0.045
    for action in actions:
        ax8.text(0.04, y, f"• {action}", transform=ax8.transAxes,
                 color='#8b949e', fontsize=8.5, va='top')
        y -= 0.038
    y -= 0.012

plt.suptitle('NewLookup — Growth Model to 100,000 Users | Unit Economics + Strategy',
             color=TEXT_COLOR, fontsize=14, fontweight='bold', y=0.999)
plt.tight_layout(rect=[0, 0, 1, 0.999])
plt.savefig('/home/ubuntu/users_100k_charts.png', dpi=150, bbox_inches='tight',
            facecolor=DARK_BG, edgecolor='none')
plt.close()
print("Charts saved!")

# ─────────────────────────────────────────────
# ТАБЛИЦА ПО МЕСЯЦАМ (BASE)
# ─────────────────────────────────────────────
print("\n=== BASE SCENARIO — Monthly Table (36 months) ===")
print(f"{'M':>3} | {'Users':>7} | {'Mirrors':>7} | {'Mktrs':>5} | {'New/mo':>7} | {'Churn':>6} | {'MRR':>10} | {'Profit':>9}")
print("-" * 80)
for d in base_data:
    flag = " ← 100k!" if d['users'] >= 100000 and (d['m'] == 1 or base_data[d['m']-2]['users'] < 100000) else ""
    print(f"M{d['m']:>2} | {d['users']:>7,} | {d['mirrors']:>7} | {d['marketers']:>5} | {d['total_new']:>7,} | {d['churned']:>6,} | ${d['mrr']:>9,.0f} | ${d['net_profit']:>8,.0f}{flag}")

# Итоги
print("\n=== SUMMARY ===")
for name, data, m100k in [
    ('Conservative', cons_data, cons_100k),
    ('Base',         base_data, base_100k),
    ('Aggressive',   aggr_data, aggr_100k),
]:
    final = data[-1]
    print(f"\n{name}:")
    print(f"  100k users: Month {m100k if m100k else 'NOT REACHED in 36 months'}")
    print(f"  Final users (M36): {final['users']:,}")
    print(f"  Final MRR (M36):   ${final['mrr']:,.0f}")
    print(f"  Total Revenue:     ${final['cum_rev']:,.0f}")
    print(f"  Total Profit:      ${final['cum_profit']:,.0f}")
    print(f"  Mirrors at M36:    {final['mirrors']}")
    print(f"  Marketers at M36:  {final['marketers']}")
