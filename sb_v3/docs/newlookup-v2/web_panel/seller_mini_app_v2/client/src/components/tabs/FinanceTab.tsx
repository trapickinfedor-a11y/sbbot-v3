/* ═══════════════════════════════════════════════════════
   FinanceTab — Balance, transactions, withdrawals, export
   Obsidian Glass design
   ═══════════════════════════════════════════════════════ */

import { useState, useEffect } from "react";
import { cn, fmtMoney } from "@/lib/utils";
import { api, type FinanceSummary, type Transaction } from "@/lib/api";
import { MOCK_FINANCE } from "@/lib/mockData";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { DollarSign, Download, ArrowUpRight, Clock, Shield, TrendingUp, Receipt } from "lucide-react";

/* ── Transaction type labels ── */
const TX_LABELS: Record<string, string> = {
  order_payment: "Sale",
  withdrawal:    "Withdraw",
  deposit:       "Deposit",
  refund:        "Refund",
  adjustment:    "Adjust",
};

/* ── Mock transactions for demo mode ── */
function buildMockTransactions(): Transaction[] {
  const now = Date.now();
  const day = 86_400_000;
  return [
    {
      id: 1,
      type: "order_payment",
      amount: 100,
      balance_after: 1947.30,
      description: "Order #1001 — Chase Business",
      created_at: new Date(now - 3 * day).toISOString(),
      order_id: 1001,
    },
    {
      id: 2,
      type: "withdrawal",
      amount: -500,
      balance_after: 1447.30,
      description: "Auto-payout to wallet",
      created_at: new Date(now - 5 * day).toISOString(),
      order_id: null,
    },
    {
      id: 3,
      type: "order_payment",
      amount: 80,
      balance_after: 1527.30,
      description: "Order #1002 — Wells Fargo",
      created_at: new Date(now - 7 * day).toISOString(),
      order_id: 1002,
    },
  ];
}

/* ── Date formatter ── */
function fmtDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function FinanceTab() {
  const { isDemoMode } = useApp();
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [requisites, setRequisites] = useState("");
  const [withdrawing, setWithdrawing] = useState(false);
  const [exporting, setExporting] = useState(false);

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [txLoading, setTxLoading] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (isDemoMode) {
          await new Promise((r) => setTimeout(r, 200));
          setSummary(MOCK_FINANCE);
        } else {
          const data = await api.financeSummary();
          setSummary(data);
        }
      } catch (e) {
        toast.error((e as Error).message ?? "Failed to load finance data");
        setSummary(null);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [isDemoMode]);

  useEffect(() => {
    const loadTx = async () => {
      setTxLoading(true);
      try {
        if (isDemoMode) {
          await new Promise((r) => setTimeout(r, 300));
          setTransactions(buildMockTransactions());
        } else {
          const data = await api.financeTransactions(20);
          setTransactions(data);
        }
      } catch {
        setTransactions([]);
      } finally {
        setTxLoading(false);
      }
    };
    loadTx();
  }, [isDemoMode]);

  const handleWithdraw = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(withdrawAmount);
    if (!amount || amount <= 0) { toast.error("Enter a valid amount"); return; }
    if (amount < 10) { toast.error("Minimum withdrawal is $10"); return; }
    if (!requisites.trim()) { toast.error("Enter payment requisites"); return; }
    if (summary && amount > summary.withdrawable_balance) {
      toast.error("Insufficient balance");
      return;
    }
    setWithdrawing(true);
    try {
      if (isDemoMode) {
        await new Promise((r) => setTimeout(r, 600));
        toast.success("Withdrawal request submitted! (Demo mode)");
        setWithdrawAmount("");
        setRequisites("");
      } else {
        await api.withdraw(amount, requisites.trim());
        toast.success("Withdrawal request submitted!");
        setWithdrawAmount("");
        setRequisites("");
        const data = await api.financeSummary();
        setSummary(data);
      }
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setWithdrawing(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      if (isDemoMode) {
        await new Promise((r) => setTimeout(r, 400));
        // Generate demo CSV
        const csv = "Date,Order,Amount,Status\n2026-03-20,#1001,$100.00,completed\n2026-03-19,#1002,$65.00,completed\n";
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `finance_demo_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success("Demo export downloaded!");
      } else {
        const blob = await api.financeExport();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `finance_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success("Export downloaded!");
      }
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="section-gap">
      {/* Balance cards */}
      {summary && (
        <>
          {/* Main balance */}
          <div
            className="glass-card p-5 relative overflow-hidden"
            style={{
              background: "linear-gradient(135deg, oklch(0.62 0.22 258 / 0.15), oklch(0.70 0.18 196 / 0.10))",
              borderColor: "oklch(0.62 0.22 258 / 0.25)",
            }}
          >
            <div className="absolute top-0 right-0 w-32 h-32 rounded-full bg-blue-500/5 -translate-y-8 translate-x-8" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-1">
                <DollarSign className="w-4 h-4 text-blue-400" />
                <span className="text-[11px] text-zinc-400 uppercase tracking-wide font-medium">
                  Available Balance
                </span>
              </div>
              <div className="text-[36px] font-bold text-white tabular leading-none mt-2">
                {fmtMoney(summary.withdrawable_balance)}
              </div>
              <div className="flex items-center gap-1.5 mt-2 text-[12px] text-zinc-500">
                <Clock className="w-3.5 h-3.5" />
                Pending: {fmtMoney(summary.pending_balance)}
              </div>
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-2.5">
            <FinanceCard
              label="Total Earned"
              value={fmtMoney(summary.total_earned)}
              icon={TrendingUp}
              color="green"
            />
            <FinanceCard
              label="Security Deposit"
              value={fmtMoney(summary.security_deposit_balance)}
              icon={Shield}
              color="amber"
            />
          </div>
        </>
      )}

      {/* Transaction history */}
      <div className="glass-card p-4 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Receipt className="w-3.5 h-3.5 text-zinc-400" />
          <h4 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
            Recent Transactions
          </h4>
        </div>

        {txLoading ? (
          <div className="flex items-center justify-center py-6">
            <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
          </div>
        ) : transactions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-6 gap-1.5">
            <Receipt className="w-6 h-6 text-zinc-700" />
            <p className="text-[12px] text-zinc-600">No transactions yet</p>
          </div>
        ) : (
          <div className="flex flex-col divide-y divide-white/[0.05]">
            {transactions.map((tx) => {
              const isPositive = tx.amount >= 0;
              const amountStr = isPositive
                ? `+$${tx.amount.toFixed(2)}`
                : `-$${Math.abs(tx.amount).toFixed(2)}`;
              const amountClass = isPositive ? "text-emerald-400" : "text-rose-400";
              const label = TX_LABELS[tx.type] ?? tx.type;

              return (
                <div
                  key={tx.id}
                  className="flex items-center justify-between py-2.5 gap-3 first:pt-0 last:pb-0"
                >
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <span className="text-[13px] text-white truncate leading-tight">
                      {tx.description}
                    </span>
                    <span className="text-[11px] text-zinc-600">
                      {fmtDate(tx.created_at)}
                    </span>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span className={cn("text-[14px] font-semibold tabular", amountClass)}>
                      {amountStr}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-white/[0.06] text-zinc-400 font-medium uppercase tracking-wide">
                      {label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Withdraw form */}
      <div className="glass-card p-4 flex flex-col gap-3">
        <h4 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
          Withdraw Funds
        </h4>
        <form onSubmit={handleWithdraw} className="flex flex-col gap-3">
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 text-sm">$</span>
            <input
              type="number"
              value={withdrawAmount}
              onChange={(e) => setWithdrawAmount(e.target.value)}
              placeholder="Amount"
              min="1"
              step="0.01"
              className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl pl-7 pr-3 py-2.5 text-sm text-white placeholder:text-zinc-600 outline-none focus:border-blue-500/40 transition-colors"
            />
          </div>
          <textarea
            value={requisites}
            onChange={(e) => setRequisites(e.target.value)}
            placeholder="Enter withdrawal details (wallet address)"
            rows={2}
            className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-sm text-white placeholder:text-zinc-600 outline-none resize-none focus:border-blue-500/40 transition-colors"
          />
          {summary && (
            <p className="text-[11px] text-zinc-600">
              Max: {fmtMoney(summary.withdrawable_balance)} available
            </p>
          )}
          <button
            type="submit"
            disabled={withdrawing}
            className="w-full py-3 rounded-xl bg-blue-500 text-white font-semibold text-[14px] disabled:opacity-50 transition-all hover:bg-blue-400 shadow-[0_0_16px_oklch(0.62_0.22_258/0.3)]"
          >
            {withdrawing ? "Processing…" : "Request Withdrawal"}
          </button>
        </form>
      </div>

      {/* Export */}
      <button
        onClick={handleExport}
        disabled={exporting}
        className="w-full glass-card p-4 flex items-center justify-between gap-3 hover:border-white/[0.12] transition-all active:scale-[0.99]"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 flex items-center justify-center">
            <Download className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-left">
            <div className="text-[14px] font-medium text-white">Export CSV</div>
            <div className="text-[11px] text-zinc-500">Download full transaction history</div>
          </div>
        </div>
        <ArrowUpRight className="w-4 h-4 text-zinc-500" />
      </button>
    </div>
  );
}

type FinColor = "blue" | "green" | "cyan" | "amber";

function FinanceCard({
  label, value, icon: Icon, color,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  color: FinColor;
}) {
  const colorMap: Record<FinColor, { text: string; bg: string }> = {
    blue:  { text: "text-blue-400",    bg: "bg-blue-500/10" },
    green: { text: "text-emerald-400", bg: "bg-emerald-500/10" },
    cyan:  { text: "text-cyan-400",    bg: "bg-cyan-500/10" },
    amber: { text: "text-amber-400",   bg: "bg-amber-500/10" },
  };
  const c = colorMap[color];

  return (
    <div className="glass-card p-3.5 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-zinc-500 uppercase tracking-wide font-medium">{label}</span>
        <div className={cn("w-7 h-7 rounded-lg flex items-center justify-center", c.bg)}>
          <Icon className={cn("w-3.5 h-3.5", c.text)} />
        </div>
      </div>
      <span className={cn("text-[18px] font-bold tabular leading-none", c.text)}>{value}</span>
    </div>
  );
}
