#!/usr/bin/env python3
"""
NewLookup — Модель роста до $100k MRR (3 сценария)
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ─────────────────────────────────────────────
# БАЗОВЫЕ ПАРАМЕТРЫ (из реального кода)
# ─────────────────────────────────────────────
AOV = 42.26                  # средний чек
ORDERS_PER_USER_MONTH = 4.5  # заказов в месяц на пользователя
ARPU_GROSS = AOV * ORDERS_PER_USER_MONTH  # $190.19
ARPU_NET = 103.07            # после всех комиссий и себестоимости
GROSS_MARGIN = 0.601         # 60.1%

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
    'text.color': TEXT_COLOR, 'axes.labelcolor': TEXT_COLOR,
    'xtick.color': TEXT_COLOR, 'ytick.color': TEXT_COLOR,
    'axes.facecolor': CARD_BG, 'figure.facecolor': DARK_BG,
    'axes.edgecolor': GRID_COLOR, 'grid.color': GRID_COLOR,
    'font.family': 'DejaVu Sans', 'font.size': 10,
})

# ─────────────────────────────────────────────
# 3 СЦЕНАРИЯ РОСТА
# ─────────────────────────────────────────────
def simulate(scenario):
    """
    Симуляция роста по сценарию.
    scenario = 'conservative' | 'base' | 'aggressive'
    """
    params = {
        'conservative': {
            'start_users': 30,
            'churn': 0.22,
            # Количество новых зеркальных ботов в месяц
            'mirror_bots_per_month': [0,0,1,1,1,1,2,2,2,2,2,2,3,3,3,3,3,3,4,4,4,4,4,4],
            'users_per_mirror': 15,    # пользователей с одного зеркала в месяц
            'marketers_per_month': [0,0,0,1,1,1,2,2,2,3,3,3,4,4,4,5,5,5,6,6,6,7,7,7],
            'users_per_marketer': 8,   # пользователей от одного маркетолога в месяц
            'organic_growth': 0.08,    # органический рост в месяц
            'infra_scale': {500: 80, 1000: 160, 2000: 280, 5000: 450},
        },
        'base': {
            'start_users': 50,
            'churn': 0.18,
            'mirror_bots_per_month': [0,1,2,2,3,3,4,4,5,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12],
            'users_per_mirror': 20,
            'marketers_per_month': [0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12],
            'users_per_marketer': 12,
            'organic_growth': 0.12,
            'infra_scale': {500: 80, 1000: 160, 2000: 280, 5000: 450},
        },
        'aggressive': {
            'start_users': 80,
            'churn': 0.15,
            'mirror_bots_per_month': [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24],
            'users_per_mirror': 28,
            'marketers_per_month': [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24],
            'users_per_marketer': 18,
            'organic_growth': 0.18,
            'infra_scale': {500: 80, 1000: 160, 2000: 280, 5000: 450},
        },
    }
    p = params[scenario]
    FIXED_BASE = 140  # базовые инфра затраты

    months = 24
    data = []
    active_users = p['start_users']
    total_mirrors = 0
    total_marketers = 0
    cumulative_rev = 0
    cumulative_profit = 0

    for m in range(months):
        # Новые зеркала и маркетологи в этом месяце
        new_mirrors = p['mirror_bots_per_month'][m] if m < len(p['mirror_bots_per_month']) else p['mirror_bots_per_month'][-1]
        new_marketers = p['marketers_per_month'][m] if m < len(p['marketers_per_month']) else p['marketers_per_month'][-1]
        total_mirrors += new_mirrors
        total_marketers += new_marketers

        # Новые пользователи из разных каналов
        organic_new = int(active_users * p['organic_growth'])
        mirror_new = total_mirrors * p['users_per_mirror']
        marketer_new = total_marketers * p['users_per_marketer']
        total_new = organic_new + mirror_new + marketer_new

        # Отток
        churned = int(active_users * p['churn'])
        active_users = max(1, active_users + total_new - churned)

        # Финансы
        gross_rev = active_users * ARPU_GROSS
        cogs = active_users * ARPU_GROSS * (1 - GROSS_MARGIN)
        payment_fee = gross_rev * 0.03
        ref_fee = gross_rev * 0.04 * 0.30
        mkt_fee = gross_rev * 0.07 * 0.25

        # Инфра масштабирование
        extra_infra = 0
        for threshold, cost in sorted(p['infra_scale'].items()):
            if active_users >= threshold:
                extra_infra = cost

        total_costs = FIXED_BASE + extra_infra + cogs + payment_fee + ref_fee + mkt_fee
        net_profit = gross_rev - total_costs
        cumulative_rev += gross_rev
        cumulative_profit += net_profit

        data.append({
            'month': m + 1,
            'users': active_users,
            'mirrors': total_mirrors,
            'marketers': total_marketers,
            'new_users': total_new,
            'mrr': gross_rev,
            'net_profit': net_profit,
            'cumulative_rev': cumulative_rev,
            'cumulative_profit': cumulative_profit,
            'total_costs': total_costs,
        })

    return data

conservative = simulate('conservative')
base = simulate('base')
aggressive = simulate('aggressive')

# ─────────────────────────────────────────────
# НАЙТИ МЕСЯЦ ДОСТИЖЕНИЯ $100k
# ─────────────────────────────────────────────
def find_100k(data):
    for d in data:
        if d['mrr'] >= 100000:
            return d['month']
    return None

m100_cons = find_100k(conservative)
m100_base = find_100k(base)
m100_agg = find_100k(aggressive)

print(f"Консервативный: $100k MRR в месяц {m100_cons}")
print(f"Базовый: $100k MRR в месяц {m100_base}")
print(f"Агрессивный: $100k MRR в месяц {m100_agg}")

# ─────────────────────────────────────────────
# ГРАФИКИ
# ─────────────────────────────────────────────
fig = plt.figure(figsize=(22, 28))
fig.patch.set_facecolor(DARK_BG)

months_x = list(range(1, 25))

# ── PLOT 1: MRR 3 сценария ──
ax1 = fig.add_subplot(4, 2, 1)
ax1.fill_between(months_x, [d['mrr'] for d in conservative], alpha=0.15, color=ACCENT3)
ax1.fill_between(months_x, [d['mrr'] for d in base], alpha=0.15, color=ACCENT1)
ax1.fill_between(months_x, [d['mrr'] for d in aggressive], alpha=0.15, color=ACCENT2)
ax1.plot(months_x, [d['mrr'] for d in conservative], color=ACCENT3, lw=2, label='Conservative')
ax1.plot(months_x, [d['mrr'] for d in base], color=ACCENT1, lw=2.5, label='Base')
ax1.plot(months_x, [d['mrr'] for d in aggressive], color=ACCENT2, lw=2.5, label='Aggressive')
ax1.axhline(y=100000, color='white', ls='--', lw=1.5, alpha=0.6, label='$100k target')
if m100_cons: ax1.axvline(x=m100_cons, color=ACCENT3, ls=':', lw=1.5, alpha=0.8)
if m100_base: ax1.axvline(x=m100_base, color=ACCENT1, ls=':', lw=1.5, alpha=0.8)
if m100_agg:  ax1.axvline(x=m100_agg,  color=ACCENT2, ls=':', lw=1.5, alpha=0.8)
ax1.set_title('MRR Growth — 3 Scenarios', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax1.set_xlabel('Month'); ax1.set_ylabel('MRR ($)')
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000:.0f}k'))
ax1.legend(facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9)
ax1.grid(True, alpha=0.3)

# ── PLOT 2: Users Growth ──
ax2 = fig.add_subplot(4, 2, 2)
ax2.fill_between(months_x, [d['users'] for d in conservative], alpha=0.15, color=ACCENT3)
ax2.fill_between(months_x, [d['users'] for d in base], alpha=0.15, color=ACCENT1)
ax2.fill_between(months_x, [d['users'] for d in aggressive], alpha=0.15, color=ACCENT2)
ax2.plot(months_x, [d['users'] for d in conservative], color=ACCENT3, lw=2, label='Conservative')
ax2.plot(months_x, [d['users'] for d in base], color=ACCENT1, lw=2.5, label='Base')
ax2.plot(months_x, [d['users'] for d in aggressive], color=ACCENT2, lw=2.5, label='Aggressive')
ax2.set_title('Active Users Growth', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax2.set_xlabel('Month'); ax2.set_ylabel('Users')
ax2.legend(facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9)
ax2.grid(True, alpha=0.3)

# ── PLOT 3: Net Profit (Base scenario) ──
ax3 = fig.add_subplot(4, 2, 3)
profits = [d['net_profit'] for d in base]
colors_profit = [ACCENT2 if p >= 0 else ACCENT3 for p in profits]
ax3.bar(months_x, profits, color=colors_profit, alpha=0.8)
ax3.axhline(y=0, color=TEXT_COLOR, lw=0.8, alpha=0.5)
ax3.set_title('Monthly Net Profit — Base Scenario', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax3.set_xlabel('Month'); ax3.set_ylabel('Profit ($)')
ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000:.0f}k'))
ax3.grid(True, alpha=0.3, axis='y')

# ── PLOT 4: Revenue Breakdown (Base, M12) ──
ax4 = fig.add_subplot(4, 2, 4)
m12 = base[11]
breakdown_labels = ['Gross\nRevenue', 'COGS\n(Workers)', 'Payment\nFees (3%)', 'Referral\nFees (4%)', 'Marketer\nFees (7%)', 'Infra\nCosts', 'Net\nProfit']
cogs_val = m12['mrr'] * (1 - GROSS_MARGIN)
pay_fee = m12['mrr'] * 0.03
ref_fee = m12['mrr'] * 0.04 * 0.30
mkt_fee = m12['mrr'] * 0.07 * 0.25
infra = m12['total_costs'] - cogs_val - pay_fee - ref_fee - mkt_fee
breakdown_values = [m12['mrr'], -cogs_val, -pay_fee, -ref_fee, -mkt_fee, -infra, m12['net_profit']]
bar_colors = [ACCENT1, ACCENT3, ACCENT5, ACCENT4, ACCENT4, ACCENT3, ACCENT2]
bars = ax4.bar(breakdown_labels, breakdown_values, color=bar_colors, alpha=0.85)
for bar, val in zip(bars, breakdown_values):
    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (500 if val >= 0 else -1500),
             f'${abs(val)/1000:.1f}k', ha='center', color=TEXT_COLOR, fontsize=8, fontweight='bold')
ax4.axhline(y=0, color=TEXT_COLOR, lw=0.8, alpha=0.5)
ax4.set_title('Revenue Waterfall — Month 12 (Base)', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax4.set_ylabel('$')
ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000:.0f}k'))
ax4.grid(True, alpha=0.3, axis='y')

# ── PLOT 5: Mirror Bots & Marketers Growth ──
ax5 = fig.add_subplot(4, 2, 5)
ax5_twin = ax5.twinx()
ax5.plot(months_x, [d['mirrors'] for d in base], color=ACCENT1, lw=2.5, marker='o', ms=4, label='Mirror Bots')
ax5_twin.plot(months_x, [d['marketers'] for d in base], color=ACCENT5, lw=2.5, marker='s', ms=4, label='Marketers')
ax5.set_title('Mirror Bots & Marketers (Base)', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax5.set_xlabel('Month')
ax5.set_ylabel('Mirror Bots', color=ACCENT1)
ax5_twin.set_ylabel('Marketers', color=ACCENT5)
ax5_twin.tick_params(axis='y', colors=ACCENT5)
ax5.tick_params(axis='y', colors=ACCENT1)
lines1, labels1 = ax5.get_legend_handles_labels()
lines2, labels2 = ax5_twin.get_legend_handles_labels()
ax5.legend(lines1 + lines2, labels1 + labels2, facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9)
ax5.grid(True, alpha=0.3)

# ── PLOT 6: Cumulative Profit ──
ax6 = fig.add_subplot(4, 2, 6)
ax6.fill_between(months_x, [d['cumulative_profit'] for d in conservative], alpha=0.15, color=ACCENT3)
ax6.fill_between(months_x, [d['cumulative_profit'] for d in base], alpha=0.15, color=ACCENT1)
ax6.fill_between(months_x, [d['cumulative_profit'] for d in aggressive], alpha=0.15, color=ACCENT2)
ax6.plot(months_x, [d['cumulative_profit'] for d in conservative], color=ACCENT3, lw=2, label='Conservative')
ax6.plot(months_x, [d['cumulative_profit'] for d in base], color=ACCENT1, lw=2.5, label='Base')
ax6.plot(months_x, [d['cumulative_profit'] for d in aggressive], color=ACCENT2, lw=2.5, label='Aggressive')
ax6.axhline(y=0, color=TEXT_COLOR, lw=0.8, alpha=0.5)
ax6.set_title('Cumulative Net Profit (24 months)', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)
ax6.set_xlabel('Month'); ax6.set_ylabel('Cumulative Profit ($)')
ax6.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000:.0f}k'))
ax6.legend(facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9)
ax6.grid(True, alpha=0.3)

# ── PLOT 7: Unit Economics Card ──
ax7 = fig.add_subplot(4, 2, 7)
ax7.axis('off')
ax7.set_facecolor(CARD_BG)
ax7.set_title('Unit Economics — Key Metrics', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)

metrics = [
    ("МЕТРИКА", "ЗНАЧЕНИЕ", "КОММЕНТАРИЙ"),
    ("AOV (средний чек)", "$42.26", "Взвешенный по mix заказов"),
    ("ARPU Gross (мес)", "$190.19", "4.5 заказа × $42.26"),
    ("ARPU Net (мес)", "$103.07", "После всех комиссий"),
    ("Gross Margin", "60.1%", "Среднее по всем категориям"),
    ("LTV (6 мес)", "$618", "ARPU Net × 6 мес"),
    ("CAC Blended", "$3.50", "Органика + реф + маркетолог"),
    ("LTV/CAC", "176x", "Отличный показатель"),
    ("Payback Period", "<1 мес", "Мгновенная окупаемость"),
    ("Breakeven", "2 пользователя", "$140 fixed / $103 ARPU"),
    ("Referral Fee", "4% от заказа", "Рефереру при каждом заказе"),
    ("Marketer Fee", "7% от заказа", "Маркетологу при каждом заказе"),
    ("Payment Fee", "3% (CryptoPay)", "Комиссия платёжной системы"),
    ("Churn (base)", "18%/мес", "Нужно снижать до 10-12%"),
    ("Server Cost", "$140-450/мес", "Зависит от кол-ва пользователей"),
]

y = 0.98
for i, row in enumerate(metrics):
    if i == 0:
        for j, (text, x_pos) in enumerate(zip(row, [0.01, 0.45, 0.72])):
            ax7.text(x_pos, y, text, transform=ax7.transAxes,
                    color=ACCENT1, fontsize=9, fontweight='bold', va='top')
        y -= 0.04
        ax7.axhline(y=y + 0.005, color=GRID_COLOR, lw=1, xmin=0, xmax=1)
        continue
    bg_color = '#1c2128' if i % 2 == 0 else CARD_BG
    for j, (text, x_pos) in enumerate(zip(row, [0.01, 0.45, 0.72])):
        color = TEXT_COLOR if j == 0 else (ACCENT2 if j == 1 else '#8b949e')
        ax7.text(x_pos, y, text, transform=ax7.transAxes,
                color=color, fontsize=8.5, va='top')
    y -= 0.062

# ── PLOT 8: Roadmap to $100k ──
ax8 = fig.add_subplot(4, 2, 8)
ax8.axis('off')
ax8.set_facecolor(CARD_BG)
ax8.set_title('Roadmap to $100k MRR', color=TEXT_COLOR, fontsize=12, fontweight='bold', pad=8)

roadmap = [
    ("ФАЗА 1 (M1-3)", "Запуск", [
        "Запустить 3-5 зеркальных ботов",
        "Подключить 5-10 маркетологов",
        "Настроить реф-систему",
        "Цель: 100 активных пользователей",
    ], ACCENT3),
    ("ФАЗА 2 (M4-8)", "Рост", [
        "20+ зеркальных ботов",
        "30+ маркетологов",
        "Запустить рассылки через Announcements",
        "Цель: 500 активных пользователей",
    ], ACCENT5),
    ("ФАЗА 3 (M9-16)", "Масштаб", [
        "50+ зеркальных ботов",
        "100+ маркетологов",
        "Автоматизация воркеров",
        "Цель: 1500 активных пользователей",
    ], ACCENT1),
    ("ФАЗА 4 (M17-24)", "$100k MRR", [
        "100+ зеркальных ботов",
        "200+ маркетологов",
        "Новые категории товаров",
        "Цель: $100k MRR",
    ], ACCENT2),
]

y = 0.97
for phase_name, phase_title, actions, color in roadmap:
    ax8.text(0.01, y, f"▶ {phase_name}: {phase_title}", transform=ax8.transAxes,
            color=color, fontsize=9.5, fontweight='bold', va='top')
    y -= 0.045
    for action in actions:
        ax8.text(0.04, y, f"• {action}", transform=ax8.transAxes,
                color='#8b949e', fontsize=8.5, va='top')
        y -= 0.038
    y -= 0.015

plt.suptitle('NewLookup — Growth Model to $100k MRR | 3 Scenarios',
             color=TEXT_COLOR, fontsize=15, fontweight='bold', y=0.998)
plt.tight_layout(rect=[0, 0, 1, 0.998])
plt.savefig('/home/ubuntu/growth_model_charts.png', dpi=150, bbox_inches='tight',
            facecolor=DARK_BG, edgecolor='none')
plt.close()
print("Growth model charts saved!")

# ─────────────────────────────────────────────
# ВЫВОД ТАБЛИЦЫ ПО МЕСЯЦАМ (BASE SCENARIO)
# ─────────────────────────────────────────────
print("\n=== BASE SCENARIO — Monthly Table ===")
print(f"{'M':>3} | {'Users':>6} | {'Mirrors':>7} | {'Mktrs':>5} | {'MRR':>10} | {'Costs':>9} | {'Profit':>9} | {'Cum.Profit':>11}")
print("-"*75)
for d in base:
    print(f"M{d['month']:>2} | {d['users']:>6,} | {d['mirrors']:>7} | {d['marketers']:>5} | ${d['mrr']:>9,.0f} | ${d['total_costs']:>8,.0f} | ${d['net_profit']:>8,.0f} | ${d['cumulative_profit']:>10,.0f}")

# Финальные итоги
print(f"\n=== RESULTS ===")
for scenario_name, data in [('Conservative', conservative), ('Base', base), ('Aggressive', aggressive)]:
    m100 = find_100k(data)
    final = data[-1]
    print(f"\n{scenario_name}:")
    print(f"  $100k MRR reached: Month {m100 if m100 else 'NOT REACHED in 24 months'}")
    print(f"  Final MRR (M24): ${final['mrr']:,.0f}")
    print(f"  Final Users (M24): {final['users']:,}")
    print(f"  Total Revenue (24mo): ${final['cumulative_rev']:,.0f}")
    print(f"  Total Profit (24mo): ${final['cumulative_profit']:,.0f}")
