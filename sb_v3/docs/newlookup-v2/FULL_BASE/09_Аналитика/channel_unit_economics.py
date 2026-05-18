import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ─── Базовые данные продукта ───────────────────────────────────────────────
ARPU_NET = 103.07        # чистый доход с 1 пользователя в месяц
LTV_6M   = 618.0         # LTV за 6 месяцев
CHURN    = 0.15          # отток в месяц

# ─── Данные по каналам ────────────────────────────────────────────────────
channels = {

    # ── 1. РАССЫЛКИ В TELEGRAM-ЧАТЫ ──────────────────────────────────────
    "Спам в TG-чатах\n(10 акк.)": {
        "cost_setup":     50,    # номера + инструмент
        "cost_monthly":   50,    # ротация номеров
        "reach_monthly":  45000, # просмотров/мес (10 акк × 150 чатов × 30 дней)
        "ctr":            0.008, # 0.8% — спам, низкий CTR
        "conv_to_user":   0.25,  # 25% кликнувших запускают бота
        "ban_risk":       "Высокий",
        "color":          "#e74c3c",
        "category":       "Серый",
    },

    # ── 2. TELEGRAM STORIES ───────────────────────────────────────────────
    "Stories\n(микро-блогеры)": {
        "cost_setup":     0,
        "cost_monthly":   300,   # 10 блогеров × $30
        "reach_monthly":  80000, # 10 блогеров × 8,000 просмотров
        "ctr":            0.018, # 1.8%
        "conv_to_user":   0.30,
        "ban_risk":       "Низкий",
        "color":          "#2ecc71",
        "category":       "Белый",
    },

    # ── 3. КРУПНЫЕ ФОРУМЫ (Lolz, XSS, BHF) ──────────────────────────────
    "Крупные форумы\n(Lolz/XSS/BHF)": {
        "cost_setup":     200,   # закреп тем, аккаунты
        "cost_monthly":   100,   # поддержка тем
        "reach_monthly":  60000, # просмотры тем за месяц
        "ctr":            0.035, # 3.5% — целевая аудитория
        "conv_to_user":   0.45,  # 45% — уже знают что такое пробив
        "ban_risk":       "Средний",
        "color":          "#f39c12",
        "category":       "Серый",
    },

    # ── 4. МЕЛКИЕ ФОРУМЫ (Античат, региональные) ─────────────────────────
    "Мелкие форумы\n(Античат и др.)": {
        "cost_setup":     50,
        "cost_monthly":   30,
        "reach_monthly":  8000,  # маленькая аудитория
        "ctr":            0.025,
        "conv_to_user":   0.35,
        "ban_risk":       "Низкий",
        "color":          "#95a5a6",
        "category":       "Серый",
    },

    # ── 5. ПОСЕВЫ В TG-КАНАЛАХ ────────────────────────────────────────────
    "Посевы в\nTG-каналах": {
        "cost_setup":     0,
        "cost_monthly":   1500,  # 5 каналов × $300 средний пост
        "reach_monthly":  250000,
        "ctr":            0.012, # 1.2%
        "conv_to_user":   0.20,
        "ban_risk":       "Низкий",
        "color":          "#3498db",
        "category":       "Белый",
    },

    # ── 6. МАРКЕТОЛОГИ / ЗЕРКАЛА ─────────────────────────────────────────
    "Маркетологи\n+ зеркала": {
        "cost_setup":     500,   # посев для привлечения маркетологов
        "cost_monthly":   0,     # комиссия 7% — уже в себестоимости
        "reach_monthly":  500000,# 20 маркетологов × 25,000 охват
        "ctr":            0.020,
        "conv_to_user":   0.30,
        "ban_risk":       "Низкий",
        "color":          "#9b59b6",
        "category":       "Белый",
    },

    # ── 7. АРБИТРАЖ ТРАФИКА ───────────────────────────────────────────────
    "Арбитраж\n(PropellerAds)": {
        "cost_setup":     200,   # тест, лендинг
        "cost_monthly":   1000,  # бюджет на трафик
        "reach_monthly":  200000,
        "ctr":            0.006, # 0.6% — холодный трафик
        "conv_to_user":   0.15,
        "ban_risk":       "Средний",
        "color":          "#e67e22",
        "category":       "Серый",
    },

    # ── 8. YOUTUBE / TG БЛОГЕРЫ ──────────────────────────────────────────
    "YouTube/TG\nблогеры": {
        "cost_setup":     0,
        "cost_monthly":   800,   # 2 интеграции × $400
        "reach_monthly":  100000,
        "ctr":            0.025, # 2.5% — доверие к блогеру
        "conv_to_user":   0.35,
        "ban_risk":       "Низкий",
        "color":          "#1abc9c",
        "category":       "Белый",
    },

    # ── 9. ВИРУСНЫЙ КОНТЕНТ ───────────────────────────────────────────────
    "Вирусный\nконтент": {
        "cost_setup":     200,   # создание видео/скриншотов
        "cost_monthly":   100,   # поддержка, дистрибуция
        "reach_monthly":  300000,# если вирусится — огромный охват
        "ctr":            0.015,
        "conv_to_user":   0.25,
        "ban_risk":       "Низкий",
        "color":          "#27ae60",
        "category":       "Белый",
    },
}

# ─── Расчёт юнит-экономики ────────────────────────────────────────────────
results = {}
for name, d in channels.items():
    clicks        = d["reach_monthly"] * d["ctr"]
    new_users_mo  = clicks * d["conv_to_user"]
    total_cost_mo = d["cost_monthly"] + (d["cost_setup"] / 3)  # setup амортизируем за 3 мес
    cac           = total_cost_mo / new_users_mo if new_users_mo > 0 else 9999
    ltv_cac       = LTV_6M / cac if cac > 0 else 0
    revenue_mo    = new_users_mo * ARPU_NET
    roi           = ((revenue_mo - total_cost_mo) / total_cost_mo * 100) if total_cost_mo > 0 else 9999
    results[name] = {
        "clicks":        round(clicks),
        "new_users":     round(new_users_mo),
        "cac":           round(cac, 2),
        "ltv_cac":       round(ltv_cac, 1),
        "revenue_mo":    round(revenue_mo),
        "cost_mo":       round(total_cost_mo),
        "roi":           round(roi),
        "color":         d["color"],
        "ban_risk":      d["ban_risk"],
        "category":      d["category"],
    }

# ─── Вывод таблицы ────────────────────────────────────────────────────────
print(f"{'Канал':<30} {'Польз/мес':>10} {'CAC $':>8} {'LTV/CAC':>8} {'ROI %':>8} {'Риск':<10}")
print("-" * 80)
for name, r in results.items():
    n = name.replace('\n', ' ')
    print(f"{n:<30} {r['new_users']:>10,} {r['cac']:>8.2f} {r['ltv_cac']:>8.1f}x {r['roi']:>8}% {r['ban_risk']:<10}")

# ─── Графики ──────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(18, 14))
fig.patch.set_facecolor('#0d1117')
for ax in axes.flat:
    ax.set_facecolor('#161b22')
    ax.tick_params(colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.title.set_color('white')
    for spine in ax.spines.values():
        spine.set_edgecolor('#30363d')

names  = list(results.keys())
colors = [r["color"] for r in results.values()]

# ── График 1: Новых пользователей в месяц ────────────────────────────────
ax1 = axes[0, 0]
users = [r["new_users"] for r in results.values()]
bars = ax1.barh(names, users, color=colors, edgecolor='#30363d')
ax1.set_title("Новых пользователей / месяц", fontsize=13, fontweight='bold', pad=10)
ax1.set_xlabel("Пользователей", color='white')
for bar, val in zip(bars, users):
    ax1.text(bar.get_width() + 20, bar.get_y() + bar.get_height()/2,
             f'{val:,}', va='center', color='white', fontsize=9)
ax1.tick_params(axis='y', labelsize=8)

# ── График 2: CAC по каналам ─────────────────────────────────────────────
ax2 = axes[0, 1]
cacs = [r["cac"] for r in results.values()]
bars2 = ax2.barh(names, cacs, color=colors, edgecolor='#30363d')
ax2.set_title("CAC (стоимость привлечения) $", fontsize=13, fontweight='bold', pad=10)
ax2.set_xlabel("CAC, $", color='white')
ax2.axvline(x=3.50, color='#f1c40f', linestyle='--', linewidth=1.5, label='Текущий CAC $3.50')
ax2.legend(facecolor='#161b22', labelcolor='white', fontsize=9)
for bar, val in zip(bars2, cacs):
    ax2.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
             f'${val:.2f}', va='center', color='white', fontsize=9)
ax2.tick_params(axis='y', labelsize=8)

# ── График 3: ROI по каналам ─────────────────────────────────────────────
ax3 = axes[1, 0]
rois = [min(r["roi"], 9999) for r in results.values()]
bar_colors = ['#2ecc71' if r > 0 else '#e74c3c' for r in rois]
bars3 = ax3.barh(names, rois, color=bar_colors, edgecolor='#30363d')
ax3.set_title("ROI по каналу (%)", fontsize=13, fontweight='bold', pad=10)
ax3.set_xlabel("ROI %", color='white')
ax3.axvline(x=0, color='white', linewidth=0.8)
for bar, val in zip(bars3, rois):
    label = f'{val:,}%' if val < 9999 else '∞'
    ax3.text(bar.get_width() + 50, bar.get_y() + bar.get_height()/2,
             label, va='center', color='white', fontsize=9)
ax3.tick_params(axis='y', labelsize=8)

# ── График 4: Матрица CAC vs Объём ───────────────────────────────────────
ax4 = axes[1, 1]
ax4.set_title("Матрица: Объём vs CAC", fontsize=13, fontweight='bold', pad=10)
ax4.set_xlabel("Новых пользователей / мес", color='white')
ax4.set_ylabel("CAC ($)", color='white')
ax4.set_facecolor('#161b22')

for name, r in results.items():
    x = r["new_users"]
    y = min(r["cac"], 50)
    ax4.scatter(x, y, color=r["color"], s=200, zorder=5, edgecolors='white', linewidth=0.5)
    label = name.replace('\n', ' ')
    ax4.annotate(label, (x, y), textcoords="offset points", xytext=(8, 4),
                 color='white', fontsize=7.5)

ax4.axhline(y=10, color='#f1c40f', linestyle='--', linewidth=1, alpha=0.7, label='CAC $10 (хороший)')
ax4.axhline(y=3.5, color='#2ecc71', linestyle='--', linewidth=1, alpha=0.7, label='CAC $3.5 (отличный)')
ax4.legend(facecolor='#161b22', labelcolor='white', fontsize=8)
ax4.set_xlim(0, max(users) * 1.15)
ax4.set_ylim(0, 55)

# Зоны
ax4.fill_between([0, max(users)*1.15], 0, 10, alpha=0.08, color='#2ecc71', label='Зона отличного CAC')
ax4.fill_between([0, max(users)*1.15], 10, 30, alpha=0.05, color='#f39c12')
ax4.fill_between([0, max(users)*1.15], 30, 55, alpha=0.05, color='#e74c3c')

plt.suptitle("NewLookup — Юнит-экономика по каналам привлечения",
             fontsize=16, fontweight='bold', color='white', y=1.01)
plt.tight_layout()
plt.savefig('/home/ubuntu/channel_economics_charts.png', dpi=150, bbox_inches='tight',
            facecolor='#0d1117')
print("\nCharts saved!")
