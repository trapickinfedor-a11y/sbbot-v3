/* ═══════════════════════════════════════════════════════
   AnalyticsTab — Monthly analytics with navigation
   Obsidian Glass design — dark glassmorphism

   Features:
   • Month navigation (← April March February →)
   • Period presets: 7D / 30D / 3M / Month
   • CSV export per period
   • KPI grid: orders, revenue, avg, conversion, disputes, completion
   • Conversion funnel
   • Top products bar chart
   • Abandoned carts
   • Revenue by product type breakdown
   • Period comparison: this month vs last month (month / 30d presets)
   ═══════════════════════════════════════════════════════ */

import { useState, useEffect, useCallback } from "react";
import { cn, fmtMoney } from "@/lib/utils";
import { api, type AnalyticsSummary, type FunnelStep, type FunnelTopProduct, type FunnelResponse } from "@/lib/api";
import {
  MOCK_ANALYTICS,
  MOCK_FUNNEL,
  MOCK_TOP_PRODUCTS,
  MOCK_ABANDONED,
} from "@/lib/mockData";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import {
  BarChart2, TrendingUp, ShoppingCart, Package,
  AlertTriangle, CheckCircle, ChevronLeft, ChevronRight,
  Download, RefreshCw,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, LineChart, Line, CartesianGrid,
} from "recharts";

/* ─── Month helpers ───────────────────────────────────── */

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function getMonthKey(year: number, month: number) {
  return `${year}-${String(month + 1).padStart(2, "0")}`;
}

function getMonthRange(year: number, month: number) {
  const from = new Date(year, month, 1);
  const to   = new Date(year, month + 1, 0);
  return {
    date_from: from.toISOString().split("T")[0],
    date_to:   to.toISOString().split("T")[0],
  };
}

type PeriodPreset = "7d" | "30d" | "3m" | "month";

/* ─── Mock comparison data ────────────────────────────── */

const MOCK_REVENUE_COMPARISON = {
  last_30_days: 2180,
  prev_30_days: 1950,
  trend_pct: 11.8,
};

/* ─── Main component ──────────────────────────────────── */

export default function AnalyticsTab() {
  const { isDemoMode } = useApp();

  const now = new Date();
  const [selectedYear,  setSelectedYear]  = useState(now.getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth());
  const [preset, setPreset] = useState<PeriodPreset>("month");

  const [summary,     setSummary]     = useState<AnalyticsSummary | null>(null);
  const [funnel,      setFunnel]      = useState<FunnelStep[]>([]);
  const [funnelData,  setFunnelData]  = useState<FunnelResponse | null>(null);
  const [topProducts, setTopProducts] = useState<FunnelTopProduct[]>([]);
  const [abandoned,   setAbandoned]   = useState<{ product_name: string; price: number; abandoned_at: string }[]>([]);
  const [dailyData,   setDailyData]   = useState<{ day: number; revenue: number; orders: number }[]>([]);
  const [loading,     setLoading]     = useState(false);
  const [exporting,   setExporting]   = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (isDemoMode) {
        await new Promise((r) => setTimeout(r, 250));
        setSummary(MOCK_ANALYTICS);
        setFunnel(MOCK_FUNNEL);
        setFunnelData({
          funnel: MOCK_FUNNEL,
          revenue: MOCK_REVENUE_COMPARISON,
        });
        setTopProducts(MOCK_TOP_PRODUCTS);
        setAbandoned(MOCK_ABANDONED.items);
        setDailyData([]);
      } else {
        const range = (() => {
          if (preset === "7d") {
            const to = new Date(); const from = new Date(); from.setDate(from.getDate() - 7);
            return { date_from: from.toISOString().split("T")[0], date_to: to.toISOString().split("T")[0] };
          } else if (preset === "30d") {
            const to = new Date(); const from = new Date(); from.setDate(from.getDate() - 30);
            return { date_from: from.toISOString().split("T")[0], date_to: to.toISOString().split("T")[0] };
          } else if (preset === "3m") {
            const to = new Date(); const from = new Date(); from.setMonth(from.getMonth() - 3);
            return { date_from: from.toISOString().split("T")[0], date_to: to.toISOString().split("T")[0] };
          } else {
            return getMonthRange(selectedYear, selectedMonth);
          }
        })();
        const [s, f, a] = await Promise.all([
          api.analyticsSummary(range.date_from, range.date_to),
          api.analyticsFunnel(range.date_from, range.date_to),
          api.abandonedCarts(range.date_from, range.date_to),
        ]);
        setSummary(s);
        setFunnel(f.funnel ?? []);
        setFunnelData(f);
        setTopProducts(f.top_products ?? []);
        setAbandoned(a.items ?? []);
        setDailyData([]);
      }
    } catch (e) {
      toast.error((e as Error).message ?? "Failed to load analytics");
      setSummary(null);
      setFunnel([]);
      setFunnelData(null);
      setTopProducts([]);
      setAbandoned([]);
      setDailyData([]);
    } finally {
      setLoading(false);
    }
  }, [isDemoMode, selectedYear, selectedMonth, preset]);

  useEffect(() => { load(); }, [load]);

  const prevMonth = () => {
    if (selectedMonth === 0) { setSelectedYear((y) => y - 1); setSelectedMonth(11); }
    else setSelectedMonth((m) => m - 1);
    setPreset("month");
  };

  const nextMonth = () => {
    const isCurrentMonth = selectedYear === now.getFullYear() && selectedMonth === now.getMonth();
    if (isCurrentMonth) return;
    if (selectedMonth === 11) { setSelectedYear((y) => y + 1); setSelectedMonth(0); }
    else setSelectedMonth((m) => m + 1);
    setPreset("month");
  };

  const isCurrentMonth = selectedYear === now.getFullYear() && selectedMonth === now.getMonth();

  const applyPreset = (p: PeriodPreset) => {
    setPreset(p);
    if (p === "month") {
      setSelectedYear(now.getFullYear()); setSelectedMonth(now.getMonth());
    }
  };

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      if (isDemoMode) {
        const rows = [
          ["Month", "Orders", "Gross Sales", "Net Earned", "Completion %"],
          [
            `${MONTH_NAMES[selectedMonth]} ${selectedYear}`,
            summary?.total_orders ?? 0,
            summary?.gross_sales?.toFixed(2) ?? "0",
            summary?.net_earned?.toFixed(2) ?? "0",
            summary?.completion_rate ?? 0,
          ],
        ];
        const csv = rows.map((r) => r.join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement("a");
        a.href     = url;
        a.download = `analytics_${getMonthKey(selectedYear, selectedMonth)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success("CSV exported (Demo mode)");
      } else {
        const range = getMonthRange(selectedYear, selectedMonth);
        await api.exportAnalyticsCSV(range.date_from, range.date_to);
        toast.success("CSV download started");
      }
    } catch {
      toast.error("Export failed");
    } finally {
      setExporting(false);
    }
  };

  /* Whether the period comparison block should be visible */
  const showComparison = (preset === "month" || preset === "30d") && !!funnelData?.revenue;

  return (
    <div className="flex flex-col gap-4 pb-4">
      {/* ── Month navigator ── */}
      <div className="px-4 pt-4">
        <div className="glass-card p-3">
          {/* Month row */}
          <div className="flex items-center justify-between mb-3">
            <button onClick={prevMonth}
              className="w-8 h-8 rounded-xl bg-white/[0.05] flex items-center justify-center hover:bg-white/[0.10] transition-colors">
              <ChevronLeft className="w-4 h-4 text-zinc-400" />
            </button>
            <div className="text-center">
              <div className="text-[15px] font-bold text-white">
                {MONTH_NAMES[selectedMonth]} {selectedYear}
              </div>
              {isCurrentMonth && (
                <div className="text-[10px] text-blue-400 font-medium mt-0.5">Current month</div>
              )}
            </div>
            <button onClick={nextMonth} disabled={isCurrentMonth}
              className={cn(
                "w-8 h-8 rounded-xl flex items-center justify-center transition-colors",
                isCurrentMonth ? "opacity-30 cursor-not-allowed" : "bg-white/[0.05] hover:bg-white/[0.10]"
              )}>
              <ChevronRight className="w-4 h-4 text-zinc-400" />
            </button>
          </div>

          {/* Month quick-select strip */}
          <div className="flex gap-1 overflow-x-auto pb-1 scrollbar-hide">
            {SHORT_MONTHS.map((m, i) => {
              const isSelected = i === selectedMonth && selectedYear === now.getFullYear();
              const isFuture = selectedYear === now.getFullYear() && i > now.getMonth();
              return (
                <button key={m}
                  disabled={isFuture}
                  onClick={() => { setSelectedMonth(i); setSelectedYear(now.getFullYear()); setPreset("month"); }}
                  className={cn(
                    "flex-shrink-0 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all",
                    isSelected ? "bg-blue-500 text-white" : isFuture ? "text-zinc-700 cursor-not-allowed" : "text-zinc-500 hover:text-white hover:bg-white/[0.08]"
                  )}
                >{m}</button>
              );
            })}
          </div>

          {/* Period presets — 7D / 30D / 3M / Month */}
          <div className="flex gap-1.5 mt-3 pt-3 border-t border-white/[0.06]">
            {(["7d", "30d", "3m", "month"] as const).map((p) => {
              const labels: Record<PeriodPreset, string> = { "7d": "7D", "30d": "30D", "3m": "3M", "month": "Month" };
              return (
                <button
                  key={p}
                  onClick={() => applyPreset(p)}
                  className={cn(
                    "flex-1 py-1.5 rounded-lg text-[11px] font-semibold border transition-all",
                    preset === p
                      ? "bg-blue-500 border-blue-500 text-white shadow-[0_0_8px_oklch(0.62_0.22_258/0.4)]"
                      : "bg-white/[0.04] border-white/[0.07] text-zinc-500 hover:text-white hover:border-white/[0.15]"
                  )}
                >
                  {labels[p]}
                </button>
              );
            })}
          </div>

          {/* Actions row */}
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/[0.06]">
            <button onClick={load} disabled={loading}
              className="flex items-center gap-1.5 text-[12px] text-zinc-500 hover:text-blue-400 transition-colors">
              <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
              Refresh
            </button>
            <button onClick={handleExportCSV} disabled={exporting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-400 text-[12px] font-medium hover:bg-blue-500/25 transition-colors disabled:opacity-50">
              <Download className="w-3.5 h-3.5" />
              {exporting ? "Exporting…" : "Export CSV"}
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
        </div>
      ) : !summary ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-600 px-4">
          <BarChart2 className="w-12 h-12 opacity-30" />
          <span className="text-sm font-medium">No data for this period</span>
          <span className="text-[12px] text-center max-w-[220px]">No orders were completed in the selected period. Try a different date range.</span>
        </div>
      ) : (
        <>
          {/* ── KPI Grid ── */}
          {summary && (
            <div className="px-4">
              <div className="grid grid-cols-2 gap-2.5">
                <KpiCard label="Orders"      value={String(summary.total_orders ?? "—")}                         icon={Package}       color="blue"   />
                <KpiCard label="Net Earned"  value={fmtMoney(summary.net_earned)}                                icon={TrendingUp}    color="green"  />
                <KpiCard label="Gross Sales" value={fmtMoney(summary.gross_sales)}                               icon={ShoppingCart}  color="cyan"   />
                <KpiCard label="Completion"  value={summary.completion_rate ? `${summary.completion_rate}%` : "—"} icon={CheckCircle} color="green"  />
                <KpiCard label="Listings"    value={String(summary.active_listings ?? "—")}                      icon={BarChart2}     color="purple" />
                <KpiCard label="Rating"      value={summary.rating != null ? String(summary.rating) : "—"}       icon={AlertTriangle} color="amber"  />
              </div>
            </div>
          )}

          {/* ── Period comparison: this month vs last month ── */}
          {showComparison && funnelData?.revenue && (
            <div className="px-4">
              <PeriodComparison
                revenue={funnelData.revenue}
                preset={preset}
                monthName={MONTH_NAMES[selectedMonth]}
              />
            </div>
          )}

          {/* ── Daily revenue sparkline ── */}
          {dailyData.length > 0 && (
            <div className="px-4">
              <div className="glass-card p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
                    Daily Revenue
                  </h3>
                  <span className="text-[11px] text-zinc-600">{MONTH_NAMES[selectedMonth]}</span>
                </div>
                <div className="h-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={dailyData} margin={{ top: 4, right: 4, bottom: 0, left: -28 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="oklch(1 0 0 / 0.04)" />
                      <XAxis
                        dataKey="day"
                        tick={{ fill: "oklch(0.55 0.015 260)", fontSize: 9 }}
                        tickLine={false}
                        axisLine={false}
                        interval={4}
                      />
                      <YAxis
                        tick={{ fill: "oklch(0.55 0.015 260)", fontSize: 9 }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => `$${v}`}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "oklch(0.13 0.014 260)",
                          border: "1px solid oklch(1 0 0 / 0.08)",
                          borderRadius: "10px",
                          color: "oklch(0.94 0.008 260)",
                          fontSize: "12px",
                        }}
                        formatter={(v: number) => [`$${v}`, "Revenue"]}
                        labelFormatter={(l) => `Day ${l}`}
                      />
                      <Line
                        type="monotone"
                        dataKey="revenue"
                        stroke="oklch(0.62 0.22 258)"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4, fill: "oklch(0.62 0.22 258)" }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* ── Conversion funnel ── */}
          {funnel.length > 0 && (
            <div className="px-4">
              <div className="glass-card p-4">
                <h3 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-3">
                  Conversion Funnel
                </h3>
                <div className="flex flex-col gap-2">
                  {funnel.map((step, i) => {
                    const maxCount = funnel[0]?.value ?? 1;
                    const pct = Math.round((step.value / maxCount) * 100);
                    return (
                      <div key={i} className="flex flex-col gap-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-zinc-400">{step.stage}</span>
                          <span className="text-white font-semibold tabular">{step.value.toLocaleString()}</span>
                        </div>
                        <div className="h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${pct}%`,
                              background: `oklch(${0.62 - i * 0.04} ${0.22 - i * 0.02} 258)`,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ── Top Products ── */}
          {topProducts.length > 0 && (
            <div className="px-4">
              <div className="glass-card p-4">
                <h3 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-3">
                  Top Products
                </h3>
                <div className="h-36">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={topProducts.slice(0, 5)} margin={{ top: 4, right: 4, bottom: 0, left: -28 }}>
                      <XAxis
                        dataKey="name"
                        tick={{ fill: "oklch(0.55 0.015 260)", fontSize: 9 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        tick={{ fill: "oklch(0.55 0.015 260)", fontSize: 9 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "oklch(0.13 0.014 260)",
                          border: "1px solid oklch(1 0 0 / 0.08)",
                          borderRadius: "10px",
                          color: "oklch(0.94 0.008 260)",
                          fontSize: "12px",
                        }}
                        formatter={(v: number) => [v, "Sales"]}
                      />
                      <Bar dataKey="sales" radius={[4, 4, 0, 0]}>
                        {topProducts.slice(0, 5).map((_, i) => (
                          <Cell
                            key={i}
                            fill={["oklch(0.62 0.22 258)", "oklch(0.65 0.20 258)", "oklch(0.68 0.18 258)", "oklch(0.70 0.16 258)", "oklch(0.72 0.14 258)"][i]}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="mt-3 flex flex-col gap-1.5">
                  {topProducts.slice(0, 5).map((p, i) => (
                    <div key={i} className="flex items-center justify-between gap-2 py-1.5 border-b border-white/[0.05] last:border-0">
                      <div className="flex items-center gap-2.5">
                        <span className="text-[11px] text-zinc-600 w-4 tabular font-mono">{i + 1}</span>
                        <span className="text-[13px] text-white">{p.name}</span>
                        {p.category && <span className="text-[10px] text-zinc-600">{p.category}</span>}
                      </div>
                      <span className="text-[12px] text-blue-400 tabular font-medium">{p.sales} orders</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Abandoned Carts ── */}
          {abandoned.length > 0 && (
            <div className="px-4">
              <div className="glass-card p-4">
                <h3 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-3">
                  Abandoned Carts
                </h3>
                <div className="flex flex-col gap-1.5">
                  {abandoned.map((a, i) => (
                    <div key={i} className="flex items-center justify-between gap-2 py-1.5 border-b border-white/[0.05] last:border-0">
                      <span className="text-[13px] text-white">{a.product_name || "Item"}</span>
                      <span className="text-[12px] text-amber-400 tabular">{fmtMoney(a.price)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Revenue by type ── */}
          {summary && (
            <div className="px-4 pb-2">
              <div className="glass-card p-4">
                <h3 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-3">
                  Summary · {MONTH_NAMES[selectedMonth]} {selectedYear}
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  <SummaryRow label="Total Orders"   value={String(summary.total_orders ?? "—")} />
                  <SummaryRow label="Gross Sales"    value={fmtMoney(summary.gross_sales)} />
                  <SummaryRow label="Net Earned"     value={fmtMoney(summary.net_earned)} />
                  <SummaryRow label="Completion"     value={`${summary.completion_rate ?? "—"}%`} />
                  <SummaryRow label="Active Listings" value={String(summary.active_listings ?? "—")} />
                  <SummaryRow label="Likes / Dislikes" value={`${summary.likes} / ${summary.dislikes}`} />
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ─── Period Comparison block ─────────────────────────── */

function PeriodComparison({
  revenue,
  preset,
  monthName,
}: {
  revenue: { last_30_days: number; prev_30_days: number; trend_pct: number };
  preset: PeriodPreset;
  monthName: string;
}) {
  const isPositive = revenue.trend_pct >= 0;
  const absPct = Math.abs(revenue.trend_pct).toFixed(1);

  const thisPeriodLabel  = preset === "month" ? monthName      : "Last 30 days";
  const prevPeriodLabel  = preset === "month" ? "Previous month" : "Prior 30 days";

  return (
    <div className="glass-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
          Month Comparison
        </h3>
        {/* Trend chip */}
        <span
          className={cn(
            "inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[11px] font-semibold tabular",
            isPositive
              ? "bg-emerald-500/15 text-emerald-400"
              : "bg-red-500/15 text-red-400"
          )}
        >
          {isPositive ? "↑" : "↓"} {isPositive ? "+" : ""}{absPct}%
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* This period */}
        <div className="flex flex-col gap-1 p-3 rounded-xl bg-white/[0.04] border border-white/[0.06]">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wide font-medium">
            {thisPeriodLabel}
          </span>
          <span className="text-[18px] font-bold text-white tabular leading-none">
            {fmtMoney(revenue.last_30_days)}
          </span>
          <span className="text-[10px] text-zinc-600">This period</span>
        </div>

        {/* Last period */}
        <div className="flex flex-col gap-1 p-3 rounded-xl bg-white/[0.04] border border-white/[0.06]">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wide font-medium">
            {prevPeriodLabel}
          </span>
          <span className="text-[18px] font-bold text-zinc-400 tabular leading-none">
            {fmtMoney(revenue.prev_30_days)}
          </span>
          <span className="text-[10px] text-zinc-600">Last period</span>
        </div>
      </div>

      {/* Delta bar */}
      <div className="mt-3 flex items-center gap-2">
        <div className="flex-1 h-1 bg-white/[0.05] rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-700",
              isPositive ? "bg-emerald-500" : "bg-red-500"
            )}
            style={{
              width: `${Math.min(Math.abs(revenue.trend_pct) * 2, 100)}%`,
            }}
          />
        </div>
        <span className="text-[10px] text-zinc-600 tabular">
          {isPositive ? "+" : ""}{fmtMoney(revenue.last_30_days - revenue.prev_30_days)} vs prior
        </span>
      </div>
    </div>
  );
}

/* ─── KPI Card ────────────────────────────────────────── */

type KpiColor = "blue" | "green" | "cyan" | "purple" | "amber" | "muted";

function KpiCard({ label, value, icon: Icon, color }: {
  label: string; value: string;
  icon: React.ComponentType<{ className?: string }>;
  color: KpiColor;
}) {
  const colorMap: Record<KpiColor, { text: string; bg: string; icon: string }> = {
    blue:   { text: "text-blue-400",    bg: "bg-blue-500/10",    icon: "text-blue-400" },
    green:  { text: "text-emerald-400", bg: "bg-emerald-500/10", icon: "text-emerald-400" },
    cyan:   { text: "text-cyan-400",    bg: "bg-cyan-500/10",    icon: "text-cyan-400" },
    purple: { text: "text-violet-400",  bg: "bg-violet-500/10",  icon: "text-violet-400" },
    amber:  { text: "text-amber-400",   bg: "bg-amber-500/10",   icon: "text-amber-400" },
    muted:  { text: "text-zinc-400",    bg: "bg-white/[0.04]",   icon: "text-zinc-500" },
  };
  const c = colorMap[color];
  return (
    <div className="glass-card p-3.5 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-zinc-500 uppercase tracking-wide font-medium">{label}</span>
        <div className={cn("w-7 h-7 rounded-lg flex items-center justify-center", c.bg)}>
          <Icon className={cn("w-3.5 h-3.5", c.icon)} />
        </div>
      </div>
      <span className={cn("text-[22px] font-bold tabular leading-none", c.text)}>{value}</span>
    </div>
  );
}

/* ─── Summary row ─────────────────────────────────────── */

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] text-zinc-600 uppercase tracking-wide">{label}</span>
      <span className="text-[14px] font-semibold text-white tabular">{value}</span>
    </div>
  );
}
