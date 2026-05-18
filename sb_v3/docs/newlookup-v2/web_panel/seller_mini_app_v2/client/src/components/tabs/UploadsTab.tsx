/* ═══════════════════════════════════════════════════════
   UploadsTab — Upload Center v6 (full spec rewrite)
   Design: Obsidian Glass

   SECTIONS (10 total):
   1. Banks      — category → bank list+custom, product type, MM+DD+YYYY reg date,
                   balance, email/phone access+rental+extend/swap, return toggle, file
   2. Brute Bank — bank+custom, exact balance, account type, 5 toggles,
                   bulk: BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price
                   auto-detect attributes from non-empty fields
   3. CC         — single: all fields + BIN auto-detect bank, NON VBV toggle
                   bulk: NUMBER|EXP|CVV|NAME|ZIP|STATE|COUNTRY|BANK|TYPE|NON_VBV
                   two prices: regular + NON VBV
   4. NFC        — type, bank via moderation only, balance, country, file
   5. OTP        — bank, balance, SMS toggle (in chat/file), Has Fullz → expanded fields
   6. Selfreg CC — bank → card names, reg date MM+DD+YYYY, VCC toggle, phone access
                   full ON/OFF + days + extend + swap, return toggle
   7. Enrollment — portal+custom, bank+custom, name/addr/dob/ssn/phone/email toggles,
                   add info, docs, file
   8. Logs       — SINGLE only: all fields with toggles, multiple accounts feature,
                   format: LOGIN|PASS|AN|RN|BALANCE|STATE|ROUTING|NAME|ADDRESS|ZIP|
                           CVV|ZELLE|WIRE|BT|PROMO|SAFEPASS|EMAIL|SCREENSHOT
   9. Checks     — PS/PHOTO, type, bank via moderation only, amount, state, scan
  10. Selfreg BA — single + bulk
   ═══════════════════════════════════════════════════════ */

import { useState, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import { useApp } from "@/contexts/AppContext";
import { apiFetch, apiFormData, api } from "@/lib/api";
import { toast } from "sonner";
import { UPLOAD_INSTRUCTIONS } from "@/lib/uploadInstructions";
import type { UploadLang } from "@/lib/uploadInstructions";
import {
  Lock, ChevronRight, ChevronLeft, Info, FileText, Plus,
  Building2, CreditCard, Smartphone, KeyRound,
  Banknote, ClipboardList, FileCheck, Database, Upload, Search,
  RotateCcw, Calendar, Trash2, PlusCircle,
} from "lucide-react";

/* ─── Bank Catalog (Banks section) ─────────────────────── */

const VCC_BANKS = [
  { id: "vcc_chime", name: "Chime VCC" }, { id: "vcc_paypal", name: "PayPal VCC" },
  { id: "vcc_onepay", name: "One Pay VCC" }, { id: "vcc_current", name: "Current VCC" },
  { id: "vcc_neteller", name: "Neteller VCC" }, { id: "vcc_wise", name: "Wise Personal VCC" },
  { id: "vcc_netspend", name: "Netspend VCC" }, { id: "vcc_greenfi", name: "GreenFi VCC" },
  { id: "vcc_quickbooks", name: "QuickBooks VCC" }, { id: "vcc_go2bank", name: "Go2Bank + VCC" },
  { id: "vcc_venmo", name: "Venmo" }, { id: "vcc_kikoff", name: "Kikoff" },
  { id: "vcc_shopify", name: "Shopify" }, { id: "vcc_varo", name: "Varo + VCC" },
];
const PERSONAL_BANKS = [
  { id: "pers_citi", name: "Citi Personal" }, { id: "pers_citi_gold", name: "Citi Gold" },
  { id: "pers_usalliance", name: "Usalliance" }, { id: "pers_usbank", name: "US Bank" },
  { id: "pers_ally", name: "Ally Bank" }, { id: "pers_regions", name: "Regions Bank" },
  { id: "pers_chase", name: "Chase" }, { id: "pers_wells", name: "Wells Fargo" },
  { id: "pers_schwab", name: "Charles Schwab" }, { id: "pers_citizens", name: "Citizens Bank" },
  { id: "pers_huntington", name: "Huntington Bank" }, { id: "pers_td", name: "TD Bank" },
  { id: "pers_boa", name: "Bank of America" }, { id: "pers_alliant", name: "Alliant CU" },
  { id: "pers_pnc", name: "PNC Bank" },
];
const BUSINESS_BANKS = [
  { id: "biz_quickbooks", name: "QuickBooks (LLC/CORP)" }, { id: "biz_bmo", name: "BMO Business" },
  { id: "biz_boa", name: "BofA Business" }, { id: "biz_usbank", name: "US Business" },
  { id: "biz_north_one", name: "North One (LLC/Corp)" }, { id: "biz_lili", name: "Lili Business VCC" },
  { id: "biz_pnc", name: "PNC Business" }, { id: "biz_capital_one", name: "Capital One Business" },
  { id: "biz_chase", name: "Chase Business" }, { id: "biz_wells", name: "Wells Fargo Business" },
];
const CRYPTO_BANKS = [
  { id: "crypto_cashapp", name: "Cash App + BTC" }, { id: "crypto_blockchain", name: "Blockchain Gold" },
  { id: "crypto_kraken", name: "Kraken" }, { id: "crypto_coinbase", name: "CoinBase" },
  { id: "crypto_crypto_com", name: "Crypto.com" }, { id: "crypto_binance", name: "Binance" },
];
const MERCHANT_BANKS = [
  { id: "mrch_mercury", name: "Mercury LLC" }, { id: "mrch_rho", name: "Rho LLC" },
  { id: "mrch_relay", name: "Relay LLC Europe/USA" }, { id: "mrch_revolut_biz", name: "Revolut Business LLC" },
  { id: "mrch_bluevine", name: "Blue Vine LLC" }, { id: "mrch_novobank", name: "Novobank LLC" },
  { id: "mrch_wise_biz", name: "Wise Business LLC" }, { id: "mrch_payoneer", name: "Payoneer LLC" },
  { id: "mrch_revolut_pers", name: "Revolut Personal EMU" },
];

const BANK_CATALOG: Record<string, { id: string; name: string }[]> = {
  vcc: VCC_BANKS, personal: PERSONAL_BANKS, business: BUSINESS_BANKS,
  crypto: CRYPTO_BANKS, merchant: MERCHANT_BANKS,
};
const BANK_CATEGORY_LABELS: Record<string, string> = {
  vcc: "VCC", personal: "Personal", business: "Business", crypto: "Crypto", merchant: "Merchant",
};

const PRODUCT_TYPES: Record<string, string[]> = {
  vcc:      ["Virtual Card", "Prepaid Card", "Gift Card"],
  personal: ["Checking Account", "Savings Account", "Money Market", "CD Account"],
  business: ["Business Checking", "Business Savings", "Merchant Account", "LLC Account", "Corp Account"],
  crypto:   ["Spot Account", "Futures Account", "Wallet", "Exchange Account"],
  merchant: ["Merchant Account", "Business Account", "Payment Gateway", "LLC Account"],
};

/* ─── Brute Attributes ──────────────────────────────────── */

const BRUTE_ATTRIBUTES = [
  "AN:RN", "AN:RN+INST YODLEE", "AN:RN+INST FINICITY", "AN:RN+INST PLAID",
  "AN:RN+INST YODLEE+INST FINICITY", "AN:RN+INST YODLEE+INST FINICITY+NAME+ADDRESS",
  "AN:RN+INST YODLEE+NAME+ADDRESS", "AN:RN+INST FINICITY+NAME+ADDRESS",
  "AN:RN+INST FINICITY+NAME", "AN:RN+ONLINE ACCESS+NAME+ADDRESS", "AN:RN+NAME+ADDRESS",
  "INST FINICITY", "ZELLE WIRE AN:RN", "ZELLE WIRE AN:RN+INST YODLEE",
];

const ACCOUNT_TYPES = ["CHECKING", "SAVINGS", "BUSINESS", "MONEY MARKET"];

/* ─── Shared bank lists ─────────────────────────────────── */

const NFC_OTP_BANKS = [
  "Chase", "Bank of America", "Wells Fargo", "Citi", "US Bank", "PNC Bank",
  "TD Bank", "Capital One", "Regions Bank", "Truist", "Fifth Third", "KeyBank",
  "Huntington", "Citizens Bank", "M&T Bank", "Ally Bank", "SunTrust", "BB&T",
  "Navy Federal CU", "USAA",
];

const BRUTE_BANKS = [
  "Chase", "Bank of America", "Wells Fargo", "Citi", "US Bank", "PNC Bank",
  "TD Bank", "Capital One", "Regions Bank", "Truist", "Fifth Third", "KeyBank",
  "Huntington", "Citizens Bank", "M&T Bank", "Ally Bank", "SunTrust", "BB&T",
  "Navy Federal CU", "USAA", "Discover", "American Express",
];

const ENROLL_BANKS = [
  "Chase", "Bank of America", "Wells Fargo", "Citi", "US Bank", "PNC Bank",
  "TD Bank", "Capital One", "Regions Bank", "Truist", "Fifth Third", "KeyBank",
  "Huntington", "Citizens Bank", "M&T Bank", "Ally Bank", "Navy Federal CU", "USAA",
  "Discover", "American Express", "Barclays", "Synchrony",
];

const NFC_COUNTRIES = [
  { code: "US", name: "🇺🇸 USA" }, { code: "CA", name: "🇨🇦 Canada" },
  { code: "GB", name: "🇬🇧 UK" }, { code: "AU", name: "🇦🇺 Australia" },
  { code: "DE", name: "🇩🇪 Germany" }, { code: "FR", name: "🇫🇷 France" },
  { code: "NL", name: "🇳🇱 Netherlands" }, { code: "SE", name: "🇸🇪 Sweden" },
  { code: "NO", name: "🇳🇴 Norway" }, { code: "DK", name: "🇩🇰 Denmark" },
  { code: "CH", name: "🇨🇭 Switzerland" }, { code: "SG", name: "🇸🇬 Singapore" },
  { code: "JP", name: "🇯🇵 Japan" }, { code: "OTHER", name: "🌍 Other" },
];

const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
  "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
  "VA","WA","WV","WI","WY","DC",
];

/* ─── Enrollment Portals ────────────────────────────────── */

const ENROLL_PORTALS = [
  { code: "fdecs", name: "FDECS" }, { code: "digitalcardservice", name: "Digital Card Service" },
  { code: "mycardinfo", name: "MyCardInfo" }, { code: "cardsuite_light", name: "Card Suite Light" },
  { code: "cardnav", name: "CardNav" }, { code: "firefighters", name: "FIREFIGHTERS" },
  { code: "coast_central", name: "Coast Central" }, { code: "web_access", name: "Web Access" },
  { code: "cardsuite", name: "Card Suite" }, { code: "myaccountaccess", name: "MyAccountAccess" },
  { code: "centresuite", name: "CentreSuite (minik)" }, { code: "elan", name: "Elan" },
];

/* ─── Selfreg CC ─────────────────────────────────────────── */

const SELFREG_CC_BANKS = [
  { code: "chase", name: "Chase" }, { code: "bofa", name: "Bank of America" },
  { code: "citi", name: "Citi" }, { code: "wells", name: "Wells Fargo" },
  { code: "capital_one", name: "Capital One" }, { code: "discover", name: "Discover" },
  { code: "amex", name: "American Express" }, { code: "usbank", name: "US Bank" },
  { code: "pnc", name: "PNC Bank" }, { code: "td", name: "TD Bank" },
  { code: "barclays", name: "Barclays" }, { code: "synchrony", name: "Synchrony" },
];

const SELFREG_CC_CARD_NAMES: Record<string, string[]> = {
  chase:      ["Chase Freedom Unlimited", "Chase Freedom Flex", "Chase Sapphire Preferred", "Chase Sapphire Reserve", "Chase Ink Business Cash", "Chase Ink Business Unlimited"],
  bofa:       ["Bank of America Customized Cash Rewards", "Bank of America Unlimited Cash Rewards", "Bank of America Travel Rewards", "Bank of America Premium Rewards"],
  citi:       ["Citi Double Cash", "Citi Custom Cash", "Citi Premier", "Citi Rewards+", "Citi Simplicity"],
  wells:      ["Wells Fargo Active Cash", "Wells Fargo Autograph", "Wells Fargo Reflect", "Wells Fargo Attune"],
  capital_one:["Capital One Venture X", "Capital One Venture", "Capital One Quicksilver", "Capital One SavorOne", "Capital One Savor"],
  discover:   ["Discover it Cash Back", "Discover it Miles", "Discover it Student Cash Back", "Discover it Chrome"],
  amex:       ["American Express Gold", "American Express Platinum", "American Express Blue Cash Preferred", "American Express Blue Cash Everyday", "American Express Green"],
  usbank:     ["US Bank Altitude Connect", "US Bank Altitude Go", "US Bank Cash+", "US Bank Shopper Cash Rewards"],
  pnc:        ["PNC Cash Rewards", "PNC Points Visa", "PNC Core Visa"],
  td:         ["TD Cash Credit Card", "TD First Class Visa", "TD Aeroplan Visa"],
  barclays:   ["Barclays AAdvantage Aviator Red", "Barclays Wyndham Rewards Earner", "Barclays JetBlue Plus"],
  synchrony:  ["Synchrony Premier World Mastercard", "Synchrony HOME Credit Card", "Synchrony Car Care"],
};

/* ─── Selfreg BA Banks ──────────────────────────────────── */

const SELFREG_BA_BANKS = [
  "Chase", "Bank of America", "Wells Fargo", "Citi", "US Bank", "PNC Bank",
  "TD Bank", "Capital One", "Regions Bank", "Truist", "Fifth Third", "KeyBank",
  "Huntington", "Citizens Bank", "M&T Bank", "Ally Bank", "Navy Federal CU", "USAA",
  "SunTrust", "BB&T",
];

/* ─── BIN → Bank lookup (simplified) ───────────────────── */

function detectBankFromBin(cardNumber: string): string {
  const n = cardNumber.replace(/\s/g, "");
  if (!n || n.length < 4) return "";
  const prefix = n.substring(0, 6);
  const p4 = n.substring(0, 4);
  if (prefix.startsWith("4") && ["4111", "4147", "4000", "4012", "4024", "4532", "4539", "4916"].some(x => prefix.startsWith(x.substring(0, 4)))) return "Visa (Generic)";
  if (prefix.startsWith("4147") || prefix.startsWith("4000")) return "Chase";
  if (prefix.startsWith("5424") || prefix.startsWith("5425") || prefix.startsWith("5426")) return "Bank of America";
  if (prefix.startsWith("4") && parseInt(prefix) >= 400000 && parseInt(prefix) <= 499999) return "Visa";
  if ((parseInt(prefix) >= 510000 && parseInt(prefix) <= 559999) || (parseInt(prefix) >= 222100 && parseInt(prefix) <= 272099)) return "Mastercard";
  if (prefix.startsWith("34") || prefix.startsWith("37")) return "American Express";
  if (prefix.startsWith("6011") || prefix.startsWith("622") || prefix.startsWith("64") || prefix.startsWith("65")) return "Discover";
  if (prefix.startsWith("3528") || prefix.startsWith("3589")) return "JCB";
  if (prefix.startsWith("62")) return "UnionPay";
  if (p4 === "4147") return "Chase";
  if (p4 === "5424") return "Bank of America";
  if (p4 === "4532") return "Wells Fargo";
  return "";
}

/* ─── Section definitions ───────────────────────────────── */

type SectionId = "banks" | "brute" | "cc" | "nfc" | "otp" | "selfreg_cc" | "enroll" | "logs" | "checks" | "selfreg_ba";

interface SectionDef {
  id: SectionId;
  label: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  depositKey: string;
  depositAmount: number;
}

const SECTIONS: SectionDef[] = [
  { id: "banks",      label: "Banks",      subtitle: "VCC, Personal, Business, Crypto, Merchant",          icon: Building2,    depositKey: "banks",      depositAmount: 150 },
  { id: "brute",      label: "Brute Bank", subtitle: "Bank credentials with balance — single & bulk",      icon: Database,     badge: "BULK",            depositKey: "brute",      depositAmount: 150 },
  { id: "cc",         label: "CC",         subtitle: "Credit cards — single & bulk, NON VBV",               icon: CreditCard,   badge: "BULK",            depositKey: "cc",         depositAmount: 200 },
  { id: "nfc",        label: "NFC",        subtitle: "Apple Pay, Google Pay — file upload",                 icon: Smartphone,   badge: "FILE",            depositKey: "nfc",        depositAmount: 150 },
  { id: "otp",        label: "OTP",        subtitle: "OTP cards with SMS access — in chat or file",         icon: KeyRound,                               depositKey: "otp",        depositAmount: 100 },
  { id: "selfreg_cc", label: "Selfreg CC", subtitle: "Self-registered credit cards by bank",                icon: CreditCard,   badge: "ATM",             depositKey: "selfreg_cc", depositAmount: 150 },
  { id: "enroll",     label: "Enrollment", subtitle: "Enrollment portal accounts (FDECS, CardNav, Elan…)", icon: ClipboardList,                          depositKey: "enroll",     depositAmount: 100 },
  { id: "logs",       label: "Logs",       subtitle: "Full bank logs — single entry with all fields",       icon: FileText,                               depositKey: "logs",       depositAmount: 200 },
  { id: "checks",     label: "Checks",     subtitle: "Personal, Business, Payroll, Cashier checks",         icon: FileCheck,    badge: "FILE",            depositKey: "checks",     depositAmount: 150 },
  { id: "selfreg_ba", label: "Selfreg BA", subtitle: "Self-registered bank accounts — single & bulk",       icon: Banknote,     badge: "BULK",            depositKey: "selfreg_ba", depositAmount: 100 },
];

interface PackageDef {
  id: string; label: string; subtitle: string; sections: SectionId[]; price: number; color: string;
}
const PACKAGES: PackageDef[] = [
  { id: "reger",  label: "Reger",       subtitle: "Selfreg CC + Selfreg BA",      sections: ["selfreg_cc", "selfreg_ba"],                                                                   price: 200, color: "from-violet-600/20 to-purple-600/10 border-violet-500/20" },
  { id: "enroll", label: "Enroll",      subtitle: "CC + NFC + OTP",               sections: ["cc", "nfc", "otp"],                                                                           price: 350, color: "from-blue-600/20 to-cyan-600/10 border-blue-500/20" },
  { id: "bank",   label: "Bank",        subtitle: "Brute Bank + Logs",            sections: ["brute", "logs"],                                                                              price: 300, color: "from-emerald-600/20 to-teal-600/10 border-emerald-500/20" },
  { id: "checks", label: "Checks",      subtitle: "Checks only",                  sections: ["checks"],                                                                                     price: 150, color: "from-amber-600/20 to-orange-600/10 border-amber-500/20" },
  { id: "full",   label: "Full Access", subtitle: "All 10 sections • Best value", sections: ["banks","brute","cc","nfc","otp","selfreg_cc","enroll","logs","checks","selfreg_ba"],         price: 750, color: "from-rose-600/20 to-pink-600/10 border-rose-500/20" },
];

const INSTRUCTIONS: Record<SectionId, string> = {
  banks:      "Category → bank (or add custom) → product type → date MM/DD/YYYY → balance → access toggles. Return Item = buyer can return within N days.",
  brute:      "Single: bank, balance, account type, 5 data toggles. Bulk: BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price — attributes auto-detected from non-empty fields.",
  cc:         "Single: all card fields, bank auto-detected from BIN. Bulk: NUMBER|EXP|CVV|NAME|ZIP|STATE|COUNTRY|BANK|TYPE|NON_VBV — two prices: regular and NON VBV.",
  nfc:        "Type (Apple Pay / Google Pay / Other) → bank via moderation only → balance → country → upload .zip.",
  otp:        "Bank → balance → SMS toggle (In Chat = you forward OTP; File = access file). Has Fullz expands personal data fields. Upload access file always required.",
  selfreg_cc: "Bank → card name → reg date MM/DD/YYYY → VCC toggle → Phone Access (ON: days+extend; OFF: swap). Return Item toggle.",
  enroll:     "Portal → bank → personal data toggles (name/addr/dob/ssn/phone/email) → docs → upload file.",
  logs:       "Single log entry: all fields with toggles. Add multiple accounts (name + balance each). Format: LOGIN|PASS|AN|RN|BALANCE|STATE|ROUTING|NAME|ADDRESS|ZIP|CVV|ZELLE|WIRE|BT|PROMO|SAFEPASS|EMAIL|SCREENSHOT",
  checks:     "PS (printed scan) or PHOTO → check type → bank via moderation → amount → upload scan.",
  selfreg_ba: "Single: all fields. Bulk: BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|ATTRS.",
};

/* ─── Shared UI helpers ─────────────────────────────────── */

function Field({ label, required, children, hint }: { label: string; required?: boolean; children: React.ReactNode; hint?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
        {label}{required && <span className="text-rose-400 ml-0.5">*</span>}
      </label>
      {children}
      {hint && <span className="text-[10px] text-zinc-700">{hint}</span>}
    </div>
  );
}

function Input({ value, onChange, placeholder, type = "text", className }: {
  value: string; onChange: (v: string) => void; placeholder?: string; type?: string; className?: string;
}) {
  return (
    <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} type={type}
      className={cn("w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-[13px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40 transition-colors", className)} />
  );
}

function SelectField({ value, onChange, options, placeholder }: {
  value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[]; placeholder?: string;
}) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-[13px] text-white outline-none focus:border-blue-500/40 transition-colors appearance-none">
      {placeholder && <option value="" disabled>{placeholder}</option>}
      {options.map(o => <option key={o.value} value={o.value} className="bg-zinc-900">{o.label}</option>)}
    </select>
  );
}

function Toggle({ value, onChange, label, sublabel }: { value: boolean; onChange: (v: boolean) => void; label: string; sublabel?: string }) {
  return (
    <button onClick={() => onChange(!value)}
      className={cn("flex items-center justify-between w-full px-3 py-2.5 rounded-xl border transition-all",
        value ? "bg-blue-500/15 border-blue-500/25 text-blue-300" : "bg-white/[0.03] border-white/[0.07] text-zinc-500")}>
      <div className="text-left">
        <span className="text-[12px] font-medium">{label}</span>
        {sublabel && <div className="text-[10px] text-zinc-600 mt-0.5">{sublabel}</div>}
      </div>
      <div className={cn("w-9 h-5 rounded-full transition-all relative flex-shrink-0 ml-3", value ? "bg-blue-500" : "bg-zinc-700")}>
        <div className={cn("absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all", value ? "left-4" : "left-0.5")} />
      </div>
    </button>
  );
}

function Textarea({ value, onChange, placeholder, rows = 5 }: {
  value: string; onChange: (v: string) => void; placeholder?: string; rows?: number;
}) {
  return (
    <textarea value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={rows}
      className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-[12px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40 transition-colors resize-none font-mono" />
  );
}

function SubmitBtn({ loading, onClick, label = "Submit for Review" }: { loading: boolean; onClick: () => void; label?: string }) {
  return (
    <button onClick={onClick} disabled={loading}
      className="w-full py-3 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-[14px] transition-all disabled:opacity-50 flex items-center justify-center gap-2 mt-1">
      {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Upload className="w-4 h-4" />}
      {loading ? "Submitting…" : label}
    </button>
  );
}

function FileUploadBtn({ file, onFile, accept, label }: { file: File | null; onFile: (f: File) => void; accept: string; label: string }) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <>
      <input ref={ref} type="file" accept={accept} className="hidden"
        onChange={e => e.target.files?.[0] && onFile(e.target.files[0])} />
      <button onClick={() => ref.current?.click()}
        className={cn("flex items-center justify-center gap-2 py-2.5 rounded-xl border text-[12px] transition-all w-full",
          file ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-white/[0.04] border-white/[0.08] text-zinc-500 hover:border-white/[0.15]")}>
        <FileText className="w-3.5 h-3.5" />
        {file ? file.name : label}
      </button>
    </>
  );
}

/* BankSearchList — searchable grid with custom bank option */
function BankSearchList({ banks, value, onChange, customValue, onCustom }: {
  banks: string[]; value: string; onChange: (v: string) => void;
  customValue: string; onCustom: (v: string) => void;
}) {
  const [q, setQ] = useState("");
  const filtered = q ? banks.filter(b => b.toLowerCase().includes(q.toLowerCase())) : banks;
  const isCustom = value === "__custom__";
  return (
    <div className="flex flex-col gap-1.5">
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-600" />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search bank…"
          className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl pl-8 pr-3 py-2 text-[12px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40" />
      </div>
      <div className="grid grid-cols-2 gap-1 max-h-36 overflow-y-auto">
        {filtered.map(b => (
          <button key={b} onClick={() => onChange(b)}
            className={cn("px-2.5 py-2 rounded-xl text-left text-[11px] font-medium transition-all border",
              value === b ? "bg-blue-500/20 border-blue-500/30 text-blue-300" : "bg-white/[0.03] border-white/[0.06] text-zinc-400 hover:border-white/[0.12]")}>
            {b}
          </button>
        ))}
        {filtered.length === 0 && <div className="col-span-2 text-center text-[11px] text-zinc-700 py-2">No results</div>}
      </div>
      <button onClick={() => onChange(isCustom ? "" : "__custom__")}
        className="flex items-center gap-1.5 text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors">
        <Plus className="w-3 h-3" /> {isCustom ? "← Back to list" : "Add custom bank"}
      </button>
      {isCustom && <Input value={customValue} onChange={onCustom} placeholder="Enter bank name…" />}
    </div>
  );
}

/* BankSearchListObj — for Banks section (object list with id/name) */
function BankSearchListObj({ banks, value, onChange }: {
  banks: { id: string; name: string }[]; value: string; onChange: (v: string) => void;
}) {
  const [q, setQ] = useState("");
  const filtered = q ? banks.filter(b => b.name.toLowerCase().includes(q.toLowerCase())) : banks;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-600" />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search bank…"
          className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl pl-8 pr-3 py-2 text-[12px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40" />
      </div>
      <div className="grid grid-cols-2 gap-1 max-h-36 overflow-y-auto">
        {filtered.map(b => (
          <button key={b.id} onClick={() => onChange(b.id)}
            className={cn("px-2.5 py-2 rounded-xl text-left text-[11px] font-medium transition-all border",
              value === b.id ? "bg-blue-500/20 border-blue-500/30 text-blue-300" : "bg-white/[0.03] border-white/[0.06] text-zinc-400 hover:border-white/[0.12]")}>
            {b.name}
          </button>
        ))}
        {filtered.length === 0 && <div className="col-span-2 text-center text-[11px] text-zinc-700 py-2">No results</div>}
      </div>
    </div>
  );
}

/* DateField — 3 separate inputs MM / DD / YYYY */
function DateField({ label, mm, onMm, dd, onDd, yyyy, onYyyy, required }: {
  label: string; mm: string; onMm: (v: string) => void;
  dd: string; onDd: (v: string) => void; yyyy: string; onYyyy: (v: string) => void;
  required?: boolean;
}) {
  return (
    <Field label={label} required={required}>
      <div className="grid grid-cols-3 gap-1.5">
        <input value={mm} onChange={e => { const v = e.target.value.replace(/\D/g, "").slice(0,2); onMm(v); }} placeholder="MM" maxLength={2}
          className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-[13px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40 transition-colors text-center" />
        <input value={dd} onChange={e => { const v = e.target.value.replace(/\D/g, "").slice(0,2); onDd(v); }} placeholder="DD" maxLength={2}
          className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-[13px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40 transition-colors text-center" />
        <input value={yyyy} onChange={e => { const v = e.target.value.replace(/\D/g, "").slice(0,4); onYyyy(v); }} placeholder="YYYY" maxLength={4}
          className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-[13px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40 transition-colors text-center" />
      </div>
    </Field>
  );
}

/* ReturnToggle */
function ReturnToggle({ value, onChange, days, onDays }: {
  value: boolean; onChange: (v: boolean) => void; days: string; onDays: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Toggle value={value} onChange={onChange} label="Return Item" sublabel="Allow buyer to return within N days" />
      {value && (
        <div className="flex items-center gap-2 pl-1">
          <RotateCcw className="w-3.5 h-3.5 text-zinc-600 flex-shrink-0" />
          <Input value={days} onChange={onDays} placeholder="e.g. 7" type="number" />
          <span className="text-[11px] text-zinc-600 whitespace-nowrap">days</span>
        </div>
      )}
    </div>
  );
}

/* PhoneAccessToggle — ON: days + extend; OFF: swap */
function PhoneAccessToggle({ value, onChange, days, onDays, canExtend, onExtend, canSwap, onSwap }: {
  value: boolean; onChange: (v: boolean) => void;
  days: string; onDays: (v: string) => void;
  canExtend: boolean; onExtend: (v: boolean) => void;
  canSwap: boolean; onSwap: (v: boolean) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Toggle value={value} onChange={onChange} label="Phone Access (OTP)" sublabel="Buyer can receive OTP via phone" />
      {value ? (
        <>
          <div className="flex items-center gap-2 pl-1">
            <Calendar className="w-3.5 h-3.5 text-zinc-600 flex-shrink-0" />
            <Input value={days} onChange={onDays} placeholder="e.g. 7" type="number" />
            <span className="text-[11px] text-zinc-600 whitespace-nowrap">days</span>
          </div>
          <Toggle value={canExtend} onChange={onExtend} label="Can extend rental?" sublabel="Buyer can purchase extra days" />
        </>
      ) : (
        <Toggle value={canSwap} onChange={onSwap} label="Can swap number?" sublabel="Buyer can change phone number" />
      )}
    </div>
  );
}

/* ─── Form: Banks ────────────────────────────────────────── */

function BanksForm({ onBack }: { onBack: () => void }) {
  const [cat, setCat] = useState<string>("");
  const [bankId, setBankId] = useState("");
  const [customBank, setCustomBank] = useState("");
  const [useCustom, setUseCustom] = useState(false);
  const [productType, setProductType] = useState("");
  const [customProductType, setCustomProductType] = useState("");
  const [regMm, setRegMm] = useState(""); const [regDd, setRegDd] = useState(""); const [regYyyy, setRegYyyy] = useState("");
  const [balance, setBalance] = useState("");
  const [emailAccess, setEmailAccess] = useState(false);
  const [phoneAccess, setPhoneAccess] = useState(false);
  const [phoneDays, setPhoneDays] = useState("");
  const [phoneExtend, setPhoneExtend] = useState(false);
  const [phoneSwap, setPhoneSwap] = useState(false);
  const [returnItem, setReturnItem] = useState(false);
  const [returnDays, setReturnDays] = useState("");
  const [price, setPrice] = useState("");
  const [accessFile, setAccessFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  const banks = cat ? (BANK_CATALOG[cat] ?? []) : [];
  const productTypes = cat ? (PRODUCT_TYPES[cat] ?? []) : [];
  const finalBankId = useCustom ? `custom_${customBank.toLowerCase().replace(/\s+/g, "_")}` : bankId;
  const finalBankName = useCustom ? customBank : (banks.find(b => b.id === bankId)?.name ?? "");
  const regDate = [regMm, regDd, regYyyy].filter(Boolean).join("/");

  const submit = async () => {
    if (!cat || !finalBankId || !price) { toast.error("Fill required fields"); return; }
    if (useCustom && !customBank.trim()) { toast.error("Enter custom bank name"); return; }
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("item_type", "bank"); fd.append("category", cat);
      fd.append("bank_id", finalBankId); fd.append("bank_name", finalBankName);
      fd.append("product_type", productType === "__custom__" ? customProductType : productType); fd.append("registration_date", regDate);
      fd.append("balance", balance); fd.append("email_access", String(emailAccess));
      fd.append("phone_access", String(phoneAccess)); fd.append("phone_rental_days", phoneDays);
      fd.append("phone_can_extend", String(phoneExtend)); fd.append("phone_can_swap", String(phoneSwap));
      fd.append("return_item", String(returnItem)); fd.append("return_days", returnDays);
      fd.append("price", price);
      if (accessFile) fd.append("access_file", accessFile);
      await apiFormData("/uploads/submit", fd);
      toast.success("Submitted for review"); onBack();
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-3">
      <Field label="Bank Category" required>
        <div className="grid grid-cols-5 gap-1.5">
          {Object.entries(BANK_CATEGORY_LABELS).map(([k, v]) => (
            <button key={k} onClick={() => { setCat(k); setBankId(""); setUseCustom(false); setProductType(""); }}
              className={cn("py-2 rounded-xl text-[11px] font-semibold border transition-all",
                cat === k ? "bg-blue-500/20 border-blue-500/30 text-blue-300" : "bg-white/[0.03] border-white/[0.06] text-zinc-500 hover:border-white/[0.12]")}>
              {v}
            </button>
          ))}
        </div>
      </Field>

      {cat && (
        <Field label="Bank" required>
          {!useCustom ? (
            <>
              <BankSearchListObj banks={banks} value={bankId} onChange={setBankId} />
              <button onClick={() => setUseCustom(true)}
                className="flex items-center gap-1.5 text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors mt-1">
                <Plus className="w-3 h-3" /> Add custom bank
              </button>
            </>
          ) : (
            <div className="flex flex-col gap-1.5">
              <Input value={customBank} onChange={setCustomBank} placeholder="Enter bank name…" />
              <button onClick={() => { setUseCustom(false); setCustomBank(""); }}
                className="text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors text-left">
                ← Back to list
              </button>
            </div>
          )}
        </Field>
      )}

      <Field label="Product Type" required>
        {productTypes.length > 0 ? (
          <SelectField value={productType} onChange={setProductType} placeholder="Select product type…"
            options={[...productTypes.map(t => ({ value: t, label: t })), { value: "__custom__", label: "✏️ Custom…" }]} />
        ) : (
          <Input value={productType} onChange={setProductType} placeholder="e.g. Checking Account" />
        )}
        {productType === "__custom__" && (
          <Input value={customProductType} onChange={setCustomProductType} placeholder="Enter product type…" className="mt-1.5" />
        )}
      </Field>

      <DateField label="Registration Date" mm={regMm} onMm={setRegMm} dd={regDd} onDd={setRegDd} yyyy={regYyyy} onYyyy={setRegYyyy} />

      <Field label="Balance">
        <Input value={balance} onChange={setBalance} placeholder="e.g. $5,000" />
      </Field>

      <div className="flex flex-col gap-1.5">
        <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">Access</div>
        <Toggle value={emailAccess} onChange={setEmailAccess} label="Email Access" />
        <PhoneAccessToggle
          value={phoneAccess} onChange={setPhoneAccess}
          days={phoneDays} onDays={setPhoneDays}
          canExtend={phoneExtend} onExtend={setPhoneExtend}
          canSwap={phoneSwap} onSwap={setPhoneSwap}
        />
      </div>

      <ReturnToggle value={returnItem} onChange={setReturnItem} days={returnDays} onDays={setReturnDays} />

      <Field label="Price ($)" required>
        <Input value={price} onChange={setPrice} placeholder="0.00" type="number" />
      </Field>

      <Field label="Access File" hint="Upload .txt or .zip for buyer">
        <FileUploadBtn file={accessFile} onFile={setAccessFile} accept=".txt,.zip" label="Upload .txt / .zip" />
      </Field>

      <SubmitBtn loading={loading} onClick={submit} />
    </div>
  );
}

/* ─── Form: Brute Bank ───────────────────────────────────── */

function BruteForm({ onBack }: { onBack: () => void }) {
  const [mode, setMode] = useState<"single" | "bulk">("single");
  const [bankName, setBankName] = useState(""); const [customBank, setCustomBank] = useState("");
  const [exactBalance, setExactBalance] = useState(""); const [accountType, setAccountType] = useState("");
  const [hasLogin, setHasLogin] = useState(false); const [login, setLogin] = useState(""); const [password, setPassword] = useState("");
  const [hasAnRn, setHasAnRn] = useState(false); const [accountNumber, setAccountNumber] = useState(""); const [routingNumber, setRoutingNumber] = useState("");
  const [hasNameAddr, setHasNameAddr] = useState(false); const [holderName, setHolderName] = useState(""); const [address, setAddress] = useState("");
  const [hasAddInfo, setHasAddInfo] = useState(false); const [addInfo, setAddInfo] = useState("");
  const [hasDocs, setHasDocs] = useState(false);
  const [price, setPrice] = useState("");
  const [bulkText, setBulkText] = useState(""); const [bulkFile, setBulkFile] = useState<File | null>(null); const [loading, setLoading] = useState(false);

  const finalBank = bankName === "__custom__" ? customBank : bankName;

  // Bulk parser: BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price
  // Auto-detect attributes from non-empty fields
  const bulkLines = bulkText.trim().split("\n").filter(Boolean);

  interface BulkGroup { count: number; attrs: string[]; price: string; }
  const bulkGroups: Record<string, BulkGroup> = {};
  let bulkErrors = 0;

  bulkLines.forEach(line => {
    const p = line.split("|");
    if (p.length < 3) { bulkErrors++; return; }
    const bank = p[0]?.trim() || "Unknown";
    const attrs: string[] = [];
    if (p[3]?.trim()) attrs.push("AN");
    if (p[4]?.trim()) attrs.push("RN");
    if (p[7]?.trim()) attrs.push("NAME");
    if (p[8]?.trim()) attrs.push("ADDR");
    if (p[9]?.trim()) attrs.push("ZIP");
    const attrStr = attrs.length ? attrs.join("+") : "LOGIN";
    const priceVal = p[10]?.trim() || "";
    const key = `${bank} [${attrStr}]`;
    if (!bulkGroups[key]) bulkGroups[key] = { count: 0, attrs, price: priceVal };
    bulkGroups[key].count++;
  });

  const groupEntries = Object.entries(bulkGroups).sort((a, b) => b[1].count - a[1].count);

  const handleFile = (f: File) => {
    setBulkFile(f);
    const reader = new FileReader();
    reader.onload = e => setBulkText(e.target?.result as string);
    reader.readAsText(f);
  };

  const submit = async () => {
    setLoading(true);
    try {
      if (mode === "single") {
        if (!finalBank || !price) { toast.error("Fill required fields"); setLoading(false); return; }
        await apiFetch("/uploads/submit", {
          method: "POST",
          json: {
            item_type: "brute_bank", mode: "single", bank_name: finalBank,
            exact_balance: exactBalance, account_type: accountType,
            has_login: hasLogin, login: hasLogin ? login : "", password: hasLogin ? password : "",
            has_an_rn: hasAnRn, account_number: hasAnRn ? accountNumber : "", routing_number: hasAnRn ? routingNumber : "",
            has_name_addr: hasNameAddr, holder_name: hasNameAddr ? holderName : "", address: hasNameAddr ? address : "",
            has_add_info: hasAddInfo, add_info: hasAddInfo ? addInfo : "",
            has_docs: hasDocs, price: parseFloat(price),
          },
        });
      } else {
        if (!bulkText) { toast.error("Paste or upload bulk data"); setLoading(false); return; }
        await apiFetch("/uploads/submit", {
          method: "POST",
          json: { item_type: "brute_bank", mode: "bulk", bulk_data: bulkText },
        });
      }
      toast.success("Submitted for review"); onBack();
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2">
        {(["single", "bulk"] as const).map(m => (
          <button key={m} onClick={() => setMode(m)}
            className={cn("py-2.5 rounded-xl text-[12px] font-semibold border transition-all capitalize",
              mode === m ? "bg-blue-500/20 border-blue-500/30 text-blue-300" : "bg-white/[0.03] border-white/[0.06] text-zinc-500")}>
            {m}
          </button>
        ))}
      </div>

      {mode === "single" ? (
        <>
          <Field label="Bank Name" required>
            <BankSearchList banks={BRUTE_BANKS} value={bankName} onChange={setBankName} customValue={customBank} onCustom={setCustomBank} />
          </Field>

          <div className="grid grid-cols-2 gap-2">
            <Field label="Exact Balance" hint="Exact account balance">
              <Input value={exactBalance} onChange={setExactBalance} placeholder="e.g. $4,820" />
            </Field>
            <Field label="Account Type">
              <SelectField value={accountType} onChange={setAccountType} placeholder="Select type…"
                options={ACCOUNT_TYPES.map(t => ({ value: t, label: t }))} />
            </Field>
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">Included Data</div>
            <Toggle value={hasLogin} onChange={setHasLogin} label="Have Login?" sublabel="Online banking credentials" />
            {hasLogin && (
              <div className="grid grid-cols-2 gap-2 pl-1">
                <Input value={login} onChange={setLogin} placeholder="Login / email" />
                <Input value={password} onChange={setPassword} placeholder="Password" />
              </div>
            )}
            <Toggle value={hasAnRn} onChange={setHasAnRn} label="Have AN / RN?" sublabel="Account & routing numbers" />
            {hasAnRn && (
              <div className="grid grid-cols-2 gap-2 pl-1">
                <Input value={accountNumber} onChange={setAccountNumber} placeholder="Account #" />
                <Input value={routingNumber} onChange={setRoutingNumber} placeholder="Routing #" />
              </div>
            )}
            <Toggle value={hasNameAddr} onChange={setHasNameAddr} label="Have Name + Address?" sublabel="Holder full name and address" />
            {hasNameAddr && (
              <div className="flex flex-col gap-1.5 pl-1">
                <Input value={holderName} onChange={setHolderName} placeholder="Full name" />
                <Input value={address} onChange={setAddress} placeholder="Address" />
              </div>
            )}
            <Toggle value={hasAddInfo} onChange={setHasAddInfo} label="Additional Info?" sublabel="Extra account details" />
            {hasAddInfo && (
              <div className="pl-1">
                <Textarea value={addInfo} onChange={setAddInfo} placeholder="Additional information…" rows={2} />
              </div>
            )}
            <Toggle value={hasDocs} onChange={setHasDocs} label="Have Docs?" sublabel="ID documents available" />
          </div>

          <Field label="Price ($)" required>
            <Input value={price} onChange={setPrice} placeholder="0.00" type="number" />
          </Field>
        </>
      ) : (
        <>
          <div className="bg-zinc-900/60 border border-white/[0.06] rounded-xl p-3 text-[11px] text-zinc-500 font-mono leading-relaxed">
            <span className="text-zinc-300 font-semibold">Format (one account per line):</span><br />
            <span className="text-zinc-600">BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price</span><br />
            <span className="text-zinc-700 text-[10px]">Attributes auto-detected from non-empty fields</span>
          </div>

          <Field label="Bulk Data (paste or upload)" required>
            <Textarea value={bulkText} onChange={setBulkText}
              placeholder={"Chase|user@email.com|pass|123456789|021000021|$5000|NY|John Doe|123 Main St|10001|15.00\nWells Fargo|user2@email.com|pass2||||$2000|CA||||10.00"} rows={6} />
          </Field>

          <FileUploadBtn file={bulkFile} onFile={handleFile} accept=".txt,.csv" label="Upload .txt / .csv file" />

          {bulkLines.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <span className="text-[11px] px-2 py-1 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  📋 {bulkLines.length} accounts
                </span>
                {bulkErrors > 0 && (
                  <span className="text-[11px] px-2 py-1 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    ⚠️ {bulkErrors} invalid
                  </span>
                )}
              </div>
              {groupEntries.length > 0 && (
                <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-2.5 flex flex-col gap-1.5">
                  <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">Auto-grouped by bank + attributes</div>
                  {groupEntries.map(([key, g]) => (
                    <div key={key} className="flex items-center justify-between text-[11px]">
                      <span className="text-zinc-400 truncate flex-1">{key}</span>
                      <div className="flex items-center gap-2 ml-2 flex-shrink-0">
                        {g.price && <span className="text-emerald-400 font-mono">${g.price}</span>}
                        <span className="text-blue-400 font-semibold">×{g.count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      <SubmitBtn loading={loading} onClick={submit} />
    </div>
  );
}

/* ─── Form: CC ───────────────────────────────────────────── */

function CCForm({ onBack }: { onBack: () => void }) {
  const [mode, setMode] = useState<"single" | "bulk">("single");
  const [cardNumber, setCardNumber] = useState("");
  const [cardExp, setCardExp] = useState(""); const [cardCvv, setCardCvv] = useState("");
  const [cardName, setCardName] = useState(""); const [cardZip, setCardZip] = useState("");
  const [cardState, setCardState] = useState(""); const [cardCountry, setCardCountry] = useState("US");
  const [cardType, setCardType] = useState("VISA"); const [isNonVbv, setIsNonVbv] = useState(false);
  const [price, setPrice] = useState("");
  const [bulkText, setBulkText] = useState(""); const [bulkPrice, setBulkPrice] = useState("");
  const [bulkNonVbvPrice, setBulkNonVbvPrice] = useState("");
  const [bulkFile, setBulkFile] = useState<File | null>(null); const [loading, setLoading] = useState(false);

  const detectedBank = detectBankFromBin(cardNumber);

  const bulkLines = bulkText.trim().split("\n").filter(Boolean);
  const nonVbvCount = bulkLines.filter(l => /NON.?VBV/i.test(l)).length;
  const usCount = bulkLines.filter(l => { const p = l.split("|"); return p[6]?.toUpperCase() === "US" || p[6]?.toUpperCase() === "USA"; }).length;

  const handleFile = (f: File) => {
    setBulkFile(f);
    const reader = new FileReader();
    reader.onload = e => setBulkText(e.target?.result as string);
    reader.readAsText(f);
  };

  const submit = async () => {
    setLoading(true);
    try {
      if (mode === "single") {
        if (!cardNumber || !cardExp || !cardCvv || !price) { toast.error("Fill required fields"); setLoading(false); return; }
        await apiFetch("/uploads/submit", {
          method: "POST",
          json: {
            item_type: "cc", mode: "single",
            card_number: cardNumber, card_exp: cardExp, card_cvv: cardCvv,
            card_name: cardName, card_zip: cardZip, card_state: cardState,
            card_country: cardCountry, card_bank: detectedBank, card_type: cardType,
            is_non_vbv: isNonVbv, price: parseFloat(price),
          },
        });
      } else {
        if (!bulkText || !bulkPrice) { toast.error("Paste data and set price"); setLoading(false); return; }
        await apiFetch("/uploads/submit", {
          method: "POST",
          json: { item_type: "cc", mode: "bulk", bulk_data: bulkText, price: parseFloat(bulkPrice), non_vbv_price: parseFloat(bulkNonVbvPrice) || 0 },
        });
      }
      toast.success("Submitted for review"); onBack();
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2">
        {(["single", "bulk"] as const).map(m => (
          <button key={m} onClick={() => setMode(m)}
            className={cn("py-2.5 rounded-xl text-[12px] font-semibold border transition-all capitalize",
              mode === m ? "bg-blue-500/20 border-blue-500/30 text-blue-300" : "bg-white/[0.03] border-white/[0.06] text-zinc-500")}>
            {m}
          </button>
        ))}
      </div>

      {mode === "single" ? (
        <>
          <Field label="Card Number" required>
            <Input value={cardNumber} onChange={setCardNumber} placeholder="4111 1111 1111 1111" />
            {detectedBank && (
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-[10px] text-zinc-600">Detected bank:</span>
                <span className="text-[11px] font-semibold text-blue-400">{detectedBank}</span>
              </div>
            )}
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Expiry" required hint="MM/YY or MM/YYYY">
              <Input value={cardExp} onChange={setCardExp} placeholder="12/26" />
            </Field>
            <Field label="CVV" required>
              <Input value={cardCvv} onChange={setCardCvv} placeholder="123" />
            </Field>
          </div>
          <Field label="Cardholder Name">
            <Input value={cardName} onChange={setCardName} placeholder="John Doe" />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="ZIP">
              <Input value={cardZip} onChange={setCardZip} placeholder="10001" />
            </Field>
            <Field label="State">
              <SelectField value={cardState} onChange={setCardState} placeholder="State…"
                options={US_STATES.map(s => ({ value: s, label: s }))} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Country">
              <Input value={cardCountry} onChange={setCardCountry} placeholder="US" />
            </Field>
            <Field label="Card Type">
              <SelectField value={cardType} onChange={setCardType}
                options={["VISA","MC","AMEX","DISCOVER","JCB","UNIONPAY"].map(t => ({ value: t, label: t }))} />
            </Field>
          </div>
          <Toggle value={isNonVbv} onChange={setIsNonVbv} label="NON VBV" sublabel="No 3D Secure — passes without OTP" />
          <Field label="Price ($)" required>
            <Input value={price} onChange={setPrice} placeholder="0.00" type="number" />
          </Field>
        </>
      ) : (
        <>
          <div className="bg-zinc-900/60 border border-white/[0.06] rounded-xl p-3 text-[11px] text-zinc-500 font-mono leading-relaxed">
            <span className="text-zinc-300 font-semibold">Format (one card per line):</span><br />
            <span className="text-zinc-600">NUMBER|EXP|CVV|NAME|ZIP|STATE|COUNTRY|BANK|TYPE</span><br />
            <span className="text-zinc-700 text-[10px]">Add |NON_VBV at end for non-VBV cards. BANK = optional (auto-detected by BIN)</span>
          </div>
          <Field label="Bulk Card Data" required>
            <Textarea value={bulkText} onChange={setBulkText}
              placeholder={"4111...|12/26|123|John Doe|10001|NY|US||VISA\n5500...|06/27|456|Jane Smith|90210|CA|US||MC|NON_VBV"} rows={7} />
          </Field>
          <FileUploadBtn file={bulkFile} onFile={handleFile} accept=".txt,.csv" label="Upload .txt / .csv file" />
          {bulkLines.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[11px] px-2 py-1 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">💳 {bulkLines.length} cards</span>
              {usCount > 0 && <span className="text-[11px] px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">🇺🇸 {usCount} US</span>}
              {bulkLines.length - usCount > 0 && <span className="text-[11px] px-2 py-1 rounded-lg bg-violet-500/10 text-violet-400 border border-violet-500/20">🌍 {bulkLines.length - usCount} World</span>}
              {nonVbvCount > 0 && <span className="text-[11px] px-2 py-1 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">⛔ {nonVbvCount} NON VBV</span>}
            </div>
          )}
          <div className="grid grid-cols-2 gap-2">
            <Field label="Price per card ($)" required>
              <Input value={bulkPrice} onChange={setBulkPrice} placeholder="0.00" type="number" />
            </Field>
            <Field label="NON VBV price ($)" hint="Leave empty to use same price">
              <Input value={bulkNonVbvPrice} onChange={setBulkNonVbvPrice} placeholder="0.00" type="number" />
            </Field>
          </div>
        </>
      )}

      <SubmitBtn loading={loading} onClick={submit} />
    </div>
  );
}

/* ─── Form: NFC ──────────────────────────────────────────── */

function NFCForm({ onBack }: { onBack: () => void }) {
  const [nfcType, setNfcType] = useState("");
  const [bankName, setBankName] = useState("");
  const [balance, setBalance] = useState("");
  const [country, setCountry] = useState("US");
  const [state, setState] = useState(""); const [zip, setZip] = useState("");
  const [price, setPrice] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [requestName, setRequestName] = useState(""); const [showRequest, setShowRequest] = useState(false);
  const [loading, setLoading] = useState(false);

  const submitRequest = async () => {
    if (!requestName.trim()) return;
    setLoading(true);
    try {
      await apiFetch("/uploads/request-category", {
        method: "POST", json: { category_type: "nfc_bank", name: requestName },
      });
      toast.success("Request submitted — review within 1–6 hours");
      setShowRequest(false); setRequestName("");
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  const submit = async () => {
    if (!nfcType || !bankName || !price) { toast.error("Fill required fields"); return; }
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("item_type", "nfc"); fd.append("nfc_type", nfcType);
      fd.append("bank_name", bankName); fd.append("balance", balance);
      fd.append("country", country); fd.append("state", state); fd.append("zip", zip);
      fd.append("price", price);
      if (file) fd.append("file", file);
      await apiFormData("/uploads/submit", fd);
      toast.success("Submitted for review"); onBack();
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-3">
      <Field label="NFC Type" required>
        <div className="grid grid-cols-3 gap-2">
          {[["ap", "🍎 Apple Pay"], ["gp", "🤖 Google Pay"], ["other", "📎 Other"]].map(([v, l]) => (
            <button key={v} onClick={() => setNfcType(v)}
              className={cn("py-2.5 rounded-xl text-[11px] font-semibold border transition-all",
                nfcType === v ? "bg-blue-500/20 border-blue-500/30 text-blue-300" : "bg-white/[0.03] border-white/[0.06] text-zinc-500")}>
              {l}
            </button>
          ))}
        </div>
      </Field>

      <Field label="Bank" required hint="Banks are added via moderation — request if not listed">
        <SelectField value={bankName} onChange={setBankName} placeholder="Select bank…"
          options={NFC_OTP_BANKS.map(b => ({ value: b, label: b }))} />
        <button onClick={() => setShowRequest(!showRequest)}
          className="flex items-center gap-1.5 text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors mt-1">
          <Plus className="w-3 h-3" /> Request bank via moderation (1–6h)
        </button>
        {showRequest && (
          <div className="flex gap-2 mt-1">
            <Input value={requestName} onChange={setRequestName} placeholder="Bank name to add…" />
            <button onClick={submitRequest} disabled={loading}
              className="px-3 py-2 rounded-xl bg-blue-600 text-white text-[12px] font-medium hover:bg-blue-500 transition-all disabled:opacity-50 whitespace-nowrap">
              Request
            </button>
          </div>
        )}
      </Field>

      <Field label="Card Balance">
        <Input value={balance} onChange={setBalance} placeholder="e.g. $2,500" />
      </Field>

      <Field label="Country" required>
        <SelectField value={country} onChange={setCountry}
          options={NFC_COUNTRIES.map(c => ({ value: c.code, label: c.name }))} />
      </Field>

      {country === "US" && (
        <div className="grid grid-cols-2 gap-2">
          <Field label="State">
            <SelectField value={state} onChange={setState} placeholder="State…"
              options={US_STATES.map(s => ({ value: s, label: s }))} />
          </Field>
          <Field label="ZIP">
            <Input value={zip} onChange={setZip} placeholder="10001" />
          </Field>
        </div>
      )}

      <Field label="Price ($)" required>
        <Input value={price} onChange={setPrice} placeholder="0.00" type="number" />
      </Field>

      <Field label="ZIP File" hint="Archive with device token + card data">
        <FileUploadBtn file={file} onFile={setFile} accept=".zip" label="Upload .zip archive" />
      </Field>

      <SubmitBtn loading={loading} onClick={submit} />
    </div>
  );
}

/* ─── Form: OTP ──────────────────────────────────────────── */

function OTPForm({ onBack }: { onBack: () => void }) {
  const [bankName, setBankName] = useState(""); const [customBank, setCustomBank] = useState("");
  const [balance, setBalance] = useState(""); const [state, setState] = useState(""); const [zip, setZip] = useState("");
  const [smsInChat, setSmsInChat] = useState(true); // true = In Chat, false = File
  const [hasFullz, setHasFullz] = useState(false);
  // Personal data toggles
  const [hasName, setHasName] = useState(false); const [hasAddress, setHasAddress] = useState(false);
  const [hasDob, setHasDob] = useState(false); const [hasSsn, setHasSsn] = useState(false);
  const [hasPhone, setHasPhone] = useState(false); const [hasEmail, setHasEmail] = useState(false);
  // Personal data fields
  const [fzFirst, setFzFirst] = useState(""); const [fzLast, setFzLast] = useState("");
  const [fzDobMm, setFzDobMm] = useState(""); const [fzDobDd, setFzDobDd] = useState(""); const [fzDobYyyy, setFzDobYyyy] = useState("");
  const [fzSsn, setFzSsn] = useState(""); const [fzAddress, setFzAddress] = useState("");
  const [fzCity, setFzCity] = useState(""); const [fzState, setFzState] = useState(""); const [fzZip, setFzZip] = useState("");
  const [fzPhone, setFzPhone] = useState(""); const [fzEmail, setFzEmail] = useState("");
  const [price, setPrice] = useState("");
  const [accessFile, setAccessFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  const isCustom = bankName === "__custom__";
  const finalBank = isCustom ? customBank : bankName;

  const submit = async () => {
    if (!finalBank || !price) { toast.error("Fill required fields"); return; }
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("item_type", "otp"); fd.append("bank_name", finalBank);
      fd.append("balance", balance); fd.append("state", state); fd.append("zip", zip);
      fd.append("sms_access_type", smsInChat ? "in_chat" : "file");
      fd.append("has_fullz", String(hasFullz));
      if (hasFullz) {
        fd.append("fullz_first", fzFirst); fd.append("fullz_last", fzLast);
        fd.append("fullz_dob", [fzDobMm, fzDobDd, fzDobYyyy].join("/"));
        fd.append("fullz_ssn", fzSsn); fd.append("fullz_address", fzAddress);
        fd.append("fullz_city", fzCity); fd.append("fullz_state", fzState); fd.append("fullz_zip", fzZip);
      }
      fd.append("price", price);
      if (accessFile) fd.append("access_file", accessFile);
      await apiFormData("/uploads/submit", fd);
      toast.success("Submitted for review"); onBack();
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-3">
      <Field label="Bank" required>
        <SelectField value={bankName} onChange={setBankName} placeholder="Select bank…"
          options={[...NFC_OTP_BANKS.map(b => ({ value: b, label: b })), { value: "__custom__", label: "✏️ Other / Custom…" }]} />
        {isCustom && <Input value={customBank} onChange={setCustomBank} placeholder="Enter bank name…" className="mt-1.5" />}
      </Field>

      <Field label="Account Balance">
        <Input value={balance} onChange={setBalance} placeholder="e.g. $5,000" />
      </Field>

      <div className="grid grid-cols-2 gap-2">
        <Field label="State">
          <SelectField value={state} onChange={setState} placeholder="State…"
            options={US_STATES.map(s => ({ value: s, label: s }))} />
        </Field>
        <Field label="ZIP">
          <Input value={zip} onChange={setZip} placeholder="10001" />
        </Field>
      </div>

      {/* SMS Access — card style */}
      <Field label="SMS Access" required>
        <div className="grid grid-cols-2 gap-2">
          {([[true, "In Chat", "You forward OTP to buyer in chat"], [false, "File", "Access file sent to buyer"]] as [boolean, string, string][]).map(([v, l, d]) => (
            <button key={l} onClick={() => setSmsInChat(v as boolean)}
              className={cn("py-2.5 px-3 rounded-xl text-left border transition-all",
                smsInChat === v ? "bg-blue-500/20 border-blue-500/30" : "bg-white/[0.03] border-white/[0.06]")}>
              <div className={cn("text-[12px] font-semibold", smsInChat === v ? "text-blue-300" : "text-zinc-400")}>{l}</div>
              <div className="text-[10px] text-zinc-600">{d}</div>
            </button>
          ))}
        </div>
      </Field>

      {/* Personal Data section with individual toggles */}
      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 flex flex-col gap-2">
        <div className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Personal Data</div>
        <Toggle value={hasName} onChange={setHasName} label="Have Name?" sublabel="First and last name" />
        {hasName && (
          <div className="grid grid-cols-2 gap-2 pl-1">
            <Field label="First Name"><Input value={fzFirst} onChange={setFzFirst} placeholder="John" /></Field>
            <Field label="Last Name"><Input value={fzLast} onChange={setFzLast} placeholder="Doe" /></Field>
          </div>
        )}
        <Toggle value={hasAddress} onChange={setHasAddress} label="Have Address?" sublabel="Billing / mailing address" />
        {hasAddress && (
          <div className="flex flex-col gap-2 pl-1">
            <Field label="Address"><Input value={fzAddress} onChange={setFzAddress} placeholder="123 Main St" /></Field>
            <div className="grid grid-cols-3 gap-2">
              <Field label="City"><Input value={fzCity} onChange={setFzCity} placeholder="New York" /></Field>
              <Field label="State"><SelectField value={fzState} onChange={setFzState} placeholder="State…" options={US_STATES.map(s => ({ value: s, label: s }))} /></Field>
              <Field label="ZIP"><Input value={fzZip} onChange={setFzZip} placeholder="10001" /></Field>
            </div>
          </div>
        )}
        <Toggle value={hasDob} onChange={setHasDob} label="Have Date of Birth?" sublabel="MM/DD/YYYY" />
        {hasDob && <div className="pl-1"><DateField label="Date of Birth" mm={fzDobMm} onMm={setFzDobMm} dd={fzDobDd} onDd={setFzDobDd} yyyy={fzDobYyyy} onYyyy={setFzDobYyyy} /></div>}
        <Toggle value={hasSsn} onChange={setHasSsn} label="Have SSN?" sublabel="Social Security Number" />
        {hasSsn && <div className="pl-1"><Field label="SSN"><Input value={fzSsn} onChange={setFzSsn} placeholder="XXX-XX-XXXX" /></Field></div>}
        <Toggle value={hasPhone} onChange={setHasPhone} label="Have Phone?" sublabel="Phone number" />
        {hasPhone && <div className="pl-1"><Field label="Phone"><Input value={fzPhone} onChange={setFzPhone} placeholder="+1 (555) 000-0000" /></Field></div>}
        <Toggle value={hasEmail} onChange={setHasEmail} label="Have Email?" sublabel="Email address" />
        {hasEmail && <div className="pl-1"><Field label="Email"><Input value={fzEmail} onChange={setFzEmail} placeholder="user@example.com" /></Field></div>}
      </div>

      {/* Has Fullz summary toggle */}
      <Toggle value={hasFullz} onChange={setHasFullz}
        label="Has Fullz"
        sublabel="Includes full personal data package (ID info + date info)" />

      <Field label="Access File" hint="Required — upload for buyer access transfer">
        <FileUploadBtn file={accessFile} onFile={setAccessFile} accept="*" label="Upload access file" />
      </Field>

      <SubmitBtn loading={loading} onClick={submit} />
    </div>
  );
}

/* ─── Form: Selfreg CC ───────────────────────────────────── */

function SelfregCCForm({ onBack }: { onBack: () => void }) {
  const [bankCode, setBankCode] = useState(""); const [cardName, setCardName] = useState(""); const [customCardName, setCustomCardName] = useState("");
  const [regMm, setRegMm] = useState(""); const [regDd, setRegDd] = useState(""); const [regYyyy, setRegYyyy] = useState("");
  const [hasVcc, setHasVcc] = useState(false); const [vccLimit, setVccLimit] = useState(""); const [vccBin, setVccBin] = useState("");
  const [state, setState] = useState(""); const [zip, setZip] = useState("");
  const [emailAccess, setEmailAccess] = useState(false);
  const [phoneAccess, setPhoneAccess] = useState(false);
  const [phoneDays, setPhoneDays] = useState(""); const [phoneExtend, setPhoneExtend] = useState(false); const [phoneSwap, setPhoneSwap] = useState(false);
  const [returnItem, setReturnItem] = useState(false); const [returnDays, setReturnDays] = useState("");
  const [price, setPrice] = useState(""); const [loading, setLoading] = useState(false);

  const cardNames = bankCode ? (SELFREG_CC_CARD_NAMES[bankCode] ?? []) : [];
  const regDate = [regMm, regDd, regYyyy].filter(Boolean).join("/");

  const submit = async () => {
    if (!bankCode || !price) { toast.error("Fill required fields"); return; }
    setLoading(true);
    try {
      await apiFetch("/uploads/submit", {
        method: "POST",
        json: {
          item_type: "selfreg_cc", bank_code: bankCode, card_name: cardName === "__custom__" ? customCardName : cardName,
          registration_date: regDate, state, zip,
          has_vcc: hasVcc, vcc_limit: hasVcc ? parseFloat(vccLimit) || 0 : 0, vcc_bin: hasVcc ? vccBin : "",
          email_access: emailAccess,
          phone_access: phoneAccess, phone_rental_days: phoneDays,
          phone_can_extend: phoneExtend, phone_can_swap: phoneSwap,
          return_item: returnItem, return_days: returnDays,
          price: parseFloat(price),
        },
      });
      toast.success("Submitted for review"); onBack();
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-3">
      <Field label="Bank" required>
        <div className="grid grid-cols-2 gap-1.5 max-h-44 overflow-y-auto">
          {SELFREG_CC_BANKS.map(b => (
            <button key={b.code} onClick={() => { setBankCode(b.code); setCardName(""); }}
              className={cn("px-2.5 py-2 rounded-xl text-[11px] font-medium border transition-all text-left",
                bankCode === b.code ? "bg-blue-500/20 border-blue-500/30 text-blue-300" : "bg-white/[0.03] border-white/[0.06] text-zinc-400 hover:border-white/[0.12]")}>
              {b.name}
            </button>
          ))}
        </div>
      </Field>

      <Field label="Card Name" hint="e.g. Chase Freedom Unlimited">
        {cardNames.length > 0 ? (
          <SelectField value={cardName} onChange={setCardName} placeholder="Select card name…"
            options={[...cardNames.map(n => ({ value: n, label: n })), { value: "__custom__", label: "✏️ Custom…" }]} />
        ) : (
          <Input value={cardName} onChange={setCardName} placeholder="e.g. Chase Freedom Unlimited" />
        )}
        {cardName === "__custom__" && (
          <Input value={customCardName} onChange={setCustomCardName} placeholder="Enter card name…" className="mt-1.5" />
        )}
      </Field>

      <DateField label="Registration Date" mm={regMm} onMm={setRegMm} dd={regDd} onDd={setRegDd} yyyy={regYyyy} onYyyy={setRegYyyy} />

      <Toggle value={hasVcc} onChange={setHasVcc} label="Have VCC?" sublabel="Virtual credit card included" />
      {hasVcc && (
        <div className="grid grid-cols-2 gap-2 pl-1">
          <Field label="VCC Limit ($)">
            <Input value={vccLimit} onChange={setVccLimit} placeholder="e.g. 2000" type="number" />
          </Field>
          <Field label="VCC BIN">
            <Input value={vccBin} onChange={setVccBin} placeholder="e.g. 411111" />
          </Field>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <Field label="State">
          <SelectField value={state} onChange={setState} placeholder="State…"
            options={US_STATES.map(s => ({ value: s, label: s }))} />
        </Field>
        <Field label="ZIP">
          <Input value={zip} onChange={setZip} placeholder="10001" />
        </Field>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">Access</div>
        <Toggle value={emailAccess} onChange={setEmailAccess} label="Email Access" />
        <PhoneAccessToggle
          value={phoneAccess} onChange={setPhoneAccess}
          days={phoneDays} onDays={setPhoneDays}
          canExtend={phoneExtend} onExtend={setPhoneExtend}
          canSwap={phoneSwap} onSwap={setPhoneSwap}
        />
      </div>

      <ReturnToggle value={returnItem} onChange={setReturnItem} days={returnDays} onDays={setReturnDays} />

      <Field label="Price ($)" required>
        <Input value={price} onChange={setPrice} placeholder="0.00" type="number" />
      </Field>

      <SubmitBtn loading={loading} onClick={submit} />
    </div>
  );
}

/* ─── Form: Enrollment ───────────────────────────────────── */

function EnrollForm({ onBack }: { onBack: () => void }) {
  const [portalCode, setPortalCode] = useState(""); const [bankName, setBankName] = useState(""); const [customBank, setCustomBank] = useState("");
  const [hasName, setHasName] = useState(false); const [firstName, setFirstName] = useState(""); const [lastName, setLastName] = useState("");
  const [hasAddress, setHasAddress] = useState(false); const [address, setAddress] = useState("");
  const [hasDob, setHasDob] = useState(false); const [dobMm, setDobMm] = useState(""); const [dobDd, setDobDd] = useState(""); const [dobYyyy, setDobYyyy] = useState("");
  const [hasSsn, setHasSsn] = useState(false); const [ssn, setSsn] = useState("");
  const [hasPhone, setHasPhone] = useState(false); const [phone, setPhone] = useState("");
  const [hasEmail, setHasEmail] = useState(false); const [email, setEmail] = useState("");
  const [addInfo, setAddInfo] = useState(""); const [hasDocs, setHasDocs] = useState(false);
  const [price, setPrice] = useState(""); const [accessFile, setAccessFile] = useState<File | null>(null);
  const [requestName, setRequestName] = useState(""); const [showRequest, setShowRequest] = useState(false);
  const [loading, setLoading] = useState(false);

  const submitRequest = async () => {
    if (!requestName.trim()) return;
    setLoading(true);
    try {
      await apiFetch("/uploads/request-category", {
        method: "POST", json: { category_type: "enroll", name: requestName },
      });
      toast.success("Request submitted — review within 1–6 hours");
      setShowRequest(false); setRequestName("");
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  const submit = async () => {
    if (!portalCode || !bankName || !price) { toast.error("Fill required fields"); return; }
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("item_type", "enroll"); fd.append("portal_code", portalCode);
      fd.append("bank_name", bankName === "__custom__" ? customBank : bankName);
      fd.append("has_name", String(hasName));
      fd.append("first_name", hasName ? firstName : ""); fd.append("last_name", hasName ? lastName : "");
      fd.append("has_address", String(hasAddress)); fd.append("address", hasAddress ? address : "");
      fd.append("has_dob", String(hasDob)); fd.append("dob", hasDob ? [dobMm, dobDd, dobYyyy].join("/") : "");
      fd.append("has_ssn", String(hasSsn)); fd.append("ssn", hasSsn ? ssn : "");
      fd.append("has_phone", String(hasPhone)); fd.append("phone", hasPhone ? phone : "");
      fd.append("has_email", String(hasEmail)); fd.append("email_addr", hasEmail ? email : "");
      fd.append("add_info", addInfo); fd.append("has_docs", String(hasDocs));
      fd.append("price", price);
      if (accessFile) fd.append("access_file", accessFile);
      await apiFormData("/uploads/submit", fd);
      toast.success("Submitted for review"); onBack();
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-3">
      <Field label="Enrollment Portal" required>
        <div className="grid grid-cols-2 gap-1.5 max-h-44 overflow-y-auto">
          {ENROLL_PORTALS.map(p => (
            <button key={p.code} onClick={() => setPortalCode(p.code)}
              className={cn("px-2.5 py-2 rounded-xl text-[11px] font-medium border transition-all text-left",
                portalCode === p.code ? "bg-blue-500/20 border-blue-500/30 text-blue-300" : "bg-white/[0.03] border-white/[0.06] text-zinc-400 hover:border-white/[0.12]")}>
              {p.name}
            </button>
          ))}
        </div>
        <button onClick={() => setShowRequest(!showRequest)}
          className="flex items-center gap-1.5 text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors mt-1">
          <Plus className="w-3 h-3" /> Request new portal (1–6h review)
        </button>
        {showRequest && (
          <div className="flex gap-2 mt-1">
            <Input value={requestName} onChange={setRequestName} placeholder="Portal name…" />
            <button onClick={submitRequest} disabled={loading}
              className="px-3 py-2 rounded-xl bg-blue-600 text-white text-[12px] font-medium hover:bg-blue-500 transition-all disabled:opacity-50 whitespace-nowrap">
              Request
            </button>
          </div>
        )}
      </Field>

      <Field label="Bank Name" required>
        <BankSearchList banks={ENROLL_BANKS} value={bankName} onChange={setBankName} customValue={customBank} onCustom={setCustomBank} />
      </Field>

      <div className="flex flex-col gap-1.5">
        <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">Personal Data</div>

        <Toggle value={hasName} onChange={setHasName} label="Have Name?" sublabel="First and last name" />
        {hasName && (
          <div className="grid grid-cols-2 gap-2 pl-1">
            <Input value={firstName} onChange={setFirstName} placeholder="First name" />
            <Input value={lastName} onChange={setLastName} placeholder="Last name" />
          </div>
        )}

        <Toggle value={hasAddress} onChange={setHasAddress} label="Have Address?" sublabel="Billing / mailing address" />
        {hasAddress && (
          <div className="pl-1">
            <Input value={address} onChange={setAddress} placeholder="Full address…" />
          </div>
        )}

        <Toggle value={hasDob} onChange={setHasDob} label="Have Date of Birth?" sublabel="MM/DD/YYYY" />
        {hasDob && (
          <div className="pl-1">
            <DateField label="" mm={dobMm} onMm={setDobMm} dd={dobDd} onDd={setDobDd} yyyy={dobYyyy} onYyyy={setDobYyyy} />
          </div>
        )}

        <Toggle value={hasSsn} onChange={setHasSsn} label="Have SSN?" sublabel="Social Security Number" />
        {hasSsn && (
          <div className="pl-1">
            <Input value={ssn} onChange={setSsn} placeholder="XXX-XX-XXXX" />
          </div>
        )}

        <Toggle value={hasPhone} onChange={setHasPhone} label="Have Phone?" sublabel="Phone number" />
        {hasPhone && (
          <div className="pl-1">
            <Input value={phone} onChange={setPhone} placeholder="+1 (555) 000-0000" />
          </div>
        )}

        <Toggle value={hasEmail} onChange={setHasEmail} label="Have Email?" sublabel="Email address" />
        {hasEmail && (
          <div className="pl-1">
            <Input value={email} onChange={setEmail} placeholder="user@email.com" />
          </div>
        )}
      </div>

      <Field label="Additional Info" hint="Any extra details (free text)">
        <Textarea value={addInfo} onChange={setAddInfo} placeholder="Extra account details…" rows={2} />
      </Field>

      <Toggle value={hasDocs} onChange={setHasDocs} label="Have Docs?" sublabel="ID documents available" />

      <Field label="Price ($)" required>
        <Input value={price} onChange={setPrice} placeholder="0.00" type="number" />
      </Field>

      <Field label="Access File" hint="Upload .txt or .zip for buyer access">
        <FileUploadBtn file={accessFile} onFile={setAccessFile} accept=".txt,.zip" label="Upload .txt / .zip" />
      </Field>

      <SubmitBtn loading={loading} onClick={submit} />
    </div>
  );
}

/* ─── Form: Logs (SINGLE only) ───────────────────────────── */

interface LogAccount { id: string; name: string; balance: string; type: string; }

function LogsForm({ onBack }: { onBack: () => void }) {
  const [bankName, setBankName] = useState(""); const [customBank, setCustomBank] = useState("");
  const [login, setLogin] = useState(""); const [password, setPassword] = useState("");
  const [hasAn, setHasAn] = useState(false); const [accountNumber, setAccountNumber] = useState("");
  const [hasRn, setHasRn] = useState(false); const [routingNumber, setRoutingNumber] = useState("");
  const [balance, setBalance] = useState(""); const [logState, setLogState] = useState("");
  const [hasName, setHasName] = useState(false); const [firstName, setFirstName] = useState(""); const [lastName, setLastName] = useState("");
  const [hasAddress, setHasAddress] = useState(false); const [address, setAddress] = useState(""); const [city, setCity] = useState(""); const [addrState, setAddrState] = useState(""); const [addrZip, setAddrZip] = useState("");
  const [hasCvv, setHasCvv] = useState(false); const [cvv, setCvv] = useState("");
  const [hasZelle, setHasZelle] = useState(false);
  const [hasWire, setHasWire] = useState(false);
  const [hasBt, setHasBt] = useState(false);
  const [hasPromo, setHasPromo] = useState(false); const [promoCode, setPromoCode] = useState("");
  const [hasSafepass, setHasSafepass] = useState(false);
  const [hasEmail, setHasEmail] = useState(false); const [emailAddr, setEmailAddr] = useState("");
  const [hasScreenshot, setHasScreenshot] = useState(false); const [screenshotFile, setScreenshotFile] = useState<File | null>(null);
  // Multiple accounts
  const [accounts, setAccounts] = useState<LogAccount[]>([]);
  const [price, setPrice] = useState("");
  const [loading, setLoading] = useState(false);

  const isCustom = bankName === "__custom__";
  const finalBank = isCustom ? customBank : bankName;

  const addAccount = () => setAccounts(prev => [...prev, { id: Date.now().toString(), name: "", balance: "", type: "CHECKING" }]);
  const removeAccount = (id: string) => setAccounts(prev => prev.filter(a => a.id !== id));
  const updateAccount = (id: string, field: keyof LogAccount, value: string) =>
    setAccounts(prev => prev.map(a => a.id === id ? { ...a, [field]: value } : a));

  // Build flag summary
  const flags = [
    { label: "AN", active: hasAn }, { label: "RN", active: hasRn },
    { label: "CVV", active: hasCvv }, { label: "Zelle", active: hasZelle },
    { label: "Wire", active: hasWire }, { label: "BT", active: hasBt },
    { label: "Promo", active: hasPromo }, { label: "Safepass", active: hasSafepass },
    { label: "Email", active: hasEmail }, { label: "Screenshot", active: hasScreenshot },
    { label: "Name", active: hasName }, { label: "Address", active: hasAddress },
  ].filter(f => f.active);

  const submit = async () => {
    if (!finalBank || !login || !price) { toast.error("Fill required fields (bank, login, price)"); return; }
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("item_type", "logs");
      fd.append("bank_name", finalBank); fd.append("login", login); fd.append("password", password);
      fd.append("balance", balance); fd.append("state", logState);
      fd.append("has_an", String(hasAn)); fd.append("account_number", hasAn ? accountNumber : "");
      fd.append("has_rn", String(hasRn)); fd.append("routing_number", hasRn ? routingNumber : "");
      fd.append("has_name", String(hasName)); fd.append("first_name", hasName ? firstName : ""); fd.append("last_name", hasName ? lastName : "");
      fd.append("has_address", String(hasAddress)); fd.append("address", hasAddress ? address : "");
      fd.append("city", hasAddress ? city : ""); fd.append("addr_state", hasAddress ? addrState : ""); fd.append("addr_zip", hasAddress ? addrZip : "");
      fd.append("has_cvv", String(hasCvv)); fd.append("cvv", hasCvv ? cvv : "");
      fd.append("has_zelle", String(hasZelle)); fd.append("has_wire", String(hasWire));
      fd.append("has_bt", String(hasBt)); fd.append("has_promo", String(hasPromo)); fd.append("promo_code", hasPromo ? promoCode : "");
      fd.append("has_safepass", String(hasSafepass)); fd.append("has_email", String(hasEmail)); fd.append("email_addr", hasEmail ? emailAddr : "");
      fd.append("has_screenshot", String(hasScreenshot));
      fd.append("accounts", JSON.stringify(accounts));
      fd.append("price", price);
      if (screenshotFile) fd.append("screenshot", screenshotFile);
      await apiFormData("/uploads/submit", fd);
      toast.success("Submitted for review"); onBack();
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Format reference */}
      <div className="bg-zinc-900/60 border border-white/[0.06] rounded-xl p-3 text-[10px] text-zinc-600 font-mono leading-relaxed">
        <span className="text-zinc-400 font-semibold">Format:</span>{" "}
        LOGIN|PASS|AN|RN|BALANCE|STATE|ROUTING|NAME|ADDRESS|ZIP|CVV|ZELLE|WIRE|BT|PROMO|SAFEPASS|EMAIL|SCREENSHOT
      </div>

      {/* Bank */}
      <Field label="Bank" required>
        <BankSearchList banks={BRUTE_BANKS} value={bankName} onChange={setBankName} customValue={customBank} onCustom={setCustomBank} />
      </Field>

      {/* Credentials */}
      <div className="grid grid-cols-2 gap-2">
        <Field label="Login" required>
          <Input value={login} onChange={setLogin} placeholder="user@email.com" />
        </Field>
        <Field label="Password">
          <Input value={password} onChange={setPassword} placeholder="password" />
        </Field>
      </div>

      {/* Balance + State */}
      <div className="grid grid-cols-2 gap-2">
        <Field label="Balance">
          <Input value={balance} onChange={setBalance} placeholder="e.g. $5,000" />
        </Field>
        <Field label="State">
          <SelectField value={logState} onChange={setLogState} placeholder="State…"
            options={US_STATES.map(s => ({ value: s, label: s }))} />
        </Field>
      </div>

      {/* Data toggles */}
      <div className="flex flex-col gap-1.5">
        <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">Account Data</div>

        <Toggle value={hasName} onChange={setHasName} label="Have Name?" sublabel="Account holder name" />
        {hasName && (
          <div className="grid grid-cols-2 gap-2 pl-1">
            <Input value={firstName} onChange={setFirstName} placeholder="First name" />
            <Input value={lastName} onChange={setLastName} placeholder="Last name" />
          </div>
        )}

        <Toggle value={hasAddress} onChange={setHasAddress} label="Have Address?" sublabel="Full billing address" />
        {hasAddress && (
          <div className="flex flex-col gap-1.5 pl-1">
            <Input value={address} onChange={setAddress} placeholder="Street address" />
            <div className="grid grid-cols-3 gap-1.5">
              <Input value={city} onChange={setCity} placeholder="City" />
              <SelectField value={addrState} onChange={setAddrState} placeholder="State…"
                options={US_STATES.map(s => ({ value: s, label: s }))} />
              <Input value={addrZip} onChange={setAddrZip} placeholder="ZIP" />
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">Services</div>

        <Toggle value={hasCvv} onChange={setHasCvv} label="CVV" sublabel="Debit/credit card CVV" />
        {hasCvv && <div className="pl-1"><Input value={cvv} onChange={setCvv} placeholder="123" /></div>}

        <Toggle value={hasZelle} onChange={setHasZelle} label="Zelle" sublabel="Zelle enrolled" />
        <Toggle value={hasWire} onChange={setHasWire} label="Wire" sublabel="Wire transfer enabled" />
        <Toggle value={hasBt} onChange={setHasBt} label="Balance Transfer (BT)" sublabel="BT available" />

        <Toggle value={hasPromo} onChange={setHasPromo} label="Promo" sublabel="Promotional offer / code" />
        {hasPromo && <div className="pl-1"><Input value={promoCode} onChange={setPromoCode} placeholder="Promo code or offer description" /></div>}

        <Toggle value={hasSafepass} onChange={setHasSafepass} label="Safepass" sublabel="Safepass security feature" />

        <Toggle value={hasEmail} onChange={setHasEmail} label="Email Access" sublabel="Email address included" />
        {hasEmail && <div className="pl-1"><Input value={emailAddr} onChange={setEmailAddr} placeholder="user@email.com" /></div>}

        <Toggle value={hasScreenshot} onChange={setHasScreenshot} label="Screenshot" sublabel="Account screenshot available" />
        {hasScreenshot && (
          <div className="pl-1">
            <FileUploadBtn file={screenshotFile} onFile={setScreenshotFile} accept="image/*" label="Upload screenshot" />
          </div>
        )}
      </div>

      {/* Active flags summary */}
      {flags.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          {flags.map(f => (
            <span key={f.label} className="text-[10px] px-2 py-0.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 font-semibold">
              {f.label}
            </span>
          ))}
        </div>
      )}

      {/* Multiple Accounts */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">
            Accounts ({accounts.length + 1} total)
          </div>
          <button onClick={addAccount}
            className="flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300 transition-colors">
            <PlusCircle className="w-3.5 h-3.5" /> Add account
          </button>
        </div>

        {/* Primary account summary */}
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 flex items-center justify-between">
          <div className="flex flex-col">
            <span className="text-[11px] font-semibold text-zinc-300">Primary Account</span>
            <span className="text-[10px] text-zinc-600">{balance || "No balance"} · {logState || "No state"}</span>
          </div>
          <span className="text-[10px] text-zinc-600 bg-blue-500/10 px-2 py-0.5 rounded-lg text-blue-400 border border-blue-500/20">Main</span>
        </div>

        {accounts.map((acc, i) => (
          <div key={acc.id} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-2.5 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Account {i + 2}</span>
              <button onClick={() => removeAccount(acc.id)}
                className="w-6 h-6 rounded-lg bg-rose-500/10 flex items-center justify-center hover:bg-rose-500/20 transition-colors">
                <Trash2 className="w-3 h-3 text-rose-400" />
              </button>
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              <div className="col-span-2">
                <input value={acc.name} onChange={e => updateAccount(acc.id, "name", e.target.value)}
                  placeholder="Account name (e.g. Savings)"
                  className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-2.5 py-2 text-[12px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40" />
              </div>
              <input value={acc.balance} onChange={e => updateAccount(acc.id, "balance", e.target.value)}
                placeholder="Balance"
                className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-2.5 py-2 text-[12px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40" />
            </div>
            <select value={acc.type} onChange={e => updateAccount(acc.id, "type", e.target.value)}
              className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-2.5 py-2 text-[12px] text-white outline-none focus:border-blue-500/40 appearance-none">
              {ACCOUNT_TYPES.map(t => <option key={t} value={t} className="bg-zinc-900">{t}</option>)}
            </select>
          </div>
        ))}

        {accounts.length > 0 && (
          <div className="text-[11px] text-zinc-600 px-1">
            Total balance: {[balance, ...accounts.map(a => a.balance)].filter(Boolean).join(" + ")}
          </div>
        )}
      </div>

      <Field label="Price ($)" required>
        <Input value={price} onChange={setPrice} placeholder="0.00" type="number" />
      </Field>

      <SubmitBtn loading={loading} onClick={submit} />
    </div>
  );
}

/* ─── Form: Checks ───────────────────────────────────────── */

function ChecksForm({ onBack }: { onBack: () => void }) {
  const [checkFormat, setCheckFormat] = useState<"ps" | "photo" | "">("");
  const [checkType, setCheckType] = useState("");
  const [bankName, setBankName] = useState(""); const [customBank, setCustomBank] = useState(""); const [requestName, setRequestName] = useState(""); const [showRequest, setShowRequest] = useState(false);
  const [amount, setAmount] = useState(""); const [state, setState] = useState("");
  const [price, setPrice] = useState(""); const [scanFile, setScanFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  const submitRequest = async () => {
    if (!requestName.trim()) return;
    setLoading(true);
    try {
      await apiFetch("/uploads/request-category", {
        method: "POST", json: { category_type: "checks_bank", name: requestName },
      });
      toast.success("Request submitted — review within 1–6 hours");
      setShowRequest(false); setRequestName("");
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  const submit = async () => {
    if (!checkFormat || !checkType || !bankName || !amount || !price) { toast.error("Fill required fields"); return; }
    setLoading(true);
    try {
      const fd = new FormData();
      const finalBank = bankName === "__custom__" ? customBank : bankName === "__moderation__" ? requestName : bankName;
      fd.append("item_type", "checks"); fd.append("check_format", checkFormat);
      fd.append("check_type", checkType); fd.append("bank_name", finalBank);
      fd.append("amount", amount); fd.append("state", state); fd.append("price", price);
      if (scanFile) fd.append("scan", scanFile);
      await apiFormData("/uploads/submit", fd);
      toast.success("Submitted for review"); onBack();
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-3">
      <Field label="Check Format" required>
        <div className="grid grid-cols-2 gap-2">
          {[["ps", "PS", "Printed scan (high quality)"], ["photo", "PHOTO", "Photo of physical check"]].map(([v, l, d]) => (
            <button key={v} onClick={() => setCheckFormat(v as "ps" | "photo")}
              className={cn("py-2.5 px-3 rounded-xl text-left border transition-all",
                checkFormat === v ? "bg-blue-500/20 border-blue-500/30" : "bg-white/[0.03] border-white/[0.06]")}>
              <div className={cn("text-[12px] font-semibold", checkFormat === v ? "text-blue-300" : "text-zinc-400")}>{l}</div>
              <div className="text-[10px] text-zinc-600">{d}</div>
            </button>
          ))}
        </div>
      </Field>

      <Field label="Check Type" required>
        <div className="grid grid-cols-2 gap-1.5">
          {["Personal", "Business", "Payroll", "Cashier"].map(t => (
            <button key={t} onClick={() => setCheckType(t.toLowerCase())}
              className={cn("py-2.5 rounded-xl text-[12px] font-semibold border transition-all",
                checkType === t.toLowerCase() ? "bg-blue-500/20 border-blue-500/30 text-blue-300" : "bg-white/[0.03] border-white/[0.06] text-zinc-500")}>
              {t}
            </button>
          ))}
        </div>
      </Field>

      <Field label="Bank" required>
        <SelectField value={bankName} onChange={setBankName} placeholder="Select bank…"
          options={[
            ...ENROLL_BANKS.map(b => ({ value: b, label: b })),
            { value: "__custom__", label: "✏️ Custom / Other…" },
            { value: "__moderation__", label: "🔔 Request via moderation (1–6h)" },
          ]} />
        {bankName === "__custom__" && (
          <Input value={customBank} onChange={setCustomBank} placeholder="Enter bank name…" className="mt-1.5" />
        )}
        {bankName === "__moderation__" && (
          <div className="flex gap-2 mt-1.5">
            <Input value={requestName} onChange={setRequestName} placeholder="Bank name to request…" />
            <button onClick={submitRequest} disabled={loading}
              className="px-3 py-2 rounded-xl bg-blue-600 text-white text-[12px] font-medium hover:bg-blue-500 transition-all disabled:opacity-50 whitespace-nowrap">
              Send
            </button>
          </div>
        )}
      </Field>

      <div className="grid grid-cols-2 gap-2">
        <Field label="Check Amount ($)" required>
          <Input value={amount} onChange={setAmount} placeholder="500.00" type="number" />
        </Field>
        <Field label="State">
          <SelectField value={state} onChange={setState} placeholder="State…"
            options={US_STATES.map(s => ({ value: s, label: s }))} />
        </Field>
      </div>

      <Field label="Price ($)" required>
        <Input value={price} onChange={setPrice} placeholder="0.00" type="number" />
      </Field>

      <Field label="Check Scan / Photo" hint="Upload scan or photo of the check">
        <FileUploadBtn file={scanFile} onFile={setScanFile} accept="image/*,.pdf" label="Upload scan / photo" />
      </Field>

      <SubmitBtn loading={loading} onClick={submit} />
    </div>
  );
}

/* ─── Form: Selfreg BA ───────────────────────────────────── */

function SelfregBAForm({ onBack }: { onBack: () => void }) {
  const [mode, setMode] = useState<"single" | "bulk">("single");
  const [bankName, setBankName] = useState(""); const [customBank, setCustomBank] = useState("");
  const [login, setLogin] = useState(""); const [password, setPassword] = useState("");
  const [accountNumber, setAccountNumber] = useState(""); const [routingNumber, setRoutingNumber] = useState("");
  const [balance, setBalance] = useState(""); const [state, setState] = useState("");
  const [holderName, setHolderName] = useState(""); const [address, setAddress] = useState(""); const [zip, setZip] = useState("");
  const [accountType, setAccountType] = useState("CHECKING"); const [price, setPrice] = useState("");
  const [bulkText, setBulkText] = useState(""); const [bulkFile, setBulkFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  const finalBank = bankName === "__custom__" ? customBank : bankName;
  const lines = bulkText.trim().split("\n").filter(Boolean);
  const bankCounts: Record<string, number> = {};
  lines.forEach(line => { const bank = line.split("|")[0]?.trim(); if (bank) bankCounts[bank] = (bankCounts[bank] || 0) + 1; });
  const topBanks = Object.entries(bankCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);
  const bulkErrors = lines.filter(l => l.split("|").length < 7).length;

  const handleFile = (f: File) => {
    setBulkFile(f);
    const reader = new FileReader();
    reader.onload = e => setBulkText(e.target?.result as string);
    reader.readAsText(f);
  };

  const submit = async () => {
    if (mode === "single") {
      if (!finalBank || !login || !price) { toast.error("Fill required fields"); return; }
      setLoading(true);
      try {
        await apiFetch("/uploads/submit", {
          method: "POST",
          json: {
            item_type: "selfreg_ba", mode: "single", bank_name: finalBank,
            login, password, account_number: accountNumber, routing_number: routingNumber,
            balance, state, holder_name: holderName, address, zip,
            account_type: accountType, price: parseFloat(price),
          },
        });
        toast.success("Submitted for review"); onBack();
      } catch (e) { toast.error((e as Error).message); }
      finally { setLoading(false); }
    } else {
      if (!bulkText) { toast.error("Paste or upload bulk data"); return; }
      setLoading(true);
      try {
        await apiFetch("/uploads/submit", {
          method: "POST",
          json: { item_type: "selfreg_ba", mode: "bulk", bulk_data: bulkText, price: parseFloat(price) },
        });
        toast.success("Submitted for review"); onBack();
      } catch (e) { toast.error((e as Error).message); }
      finally { setLoading(false); }
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2">
        {(["single", "bulk"] as const).map(m => (
          <button key={m} onClick={() => setMode(m)}
            className={cn("py-2.5 rounded-xl text-[12px] font-semibold border transition-all capitalize",
              mode === m ? "bg-blue-500/20 border-blue-500/30 text-blue-300" : "bg-white/[0.03] border-white/[0.06] text-zinc-500")}>
            {m}
          </button>
        ))}
      </div>

      {mode === "single" ? (
        <>
          <Field label="Bank" required>
            <BankSearchList banks={SELFREG_BA_BANKS} value={bankName} onChange={setBankName} customValue={customBank} onCustom={setCustomBank} />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Login" required hint="Email or username">
              <Input value={login} onChange={setLogin} placeholder="user@email.com" />
            </Field>
            <Field label="Password">
              <Input value={password} onChange={setPassword} placeholder="password" />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Account Number (AN)">
              <Input value={accountNumber} onChange={setAccountNumber} placeholder="123456789" />
            </Field>
            <Field label="Routing Number (RN)">
              <Input value={routingNumber} onChange={setRoutingNumber} placeholder="021000021" />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Balance">
              <Input value={balance} onChange={setBalance} placeholder="e.g. $5,000" />
            </Field>
            <Field label="Account Type">
              <SelectField value={accountType} onChange={setAccountType}
                options={ACCOUNT_TYPES.map(t => ({ value: t, label: t }))} />
            </Field>
          </div>
          <Field label="Holder Name">
            <Input value={holderName} onChange={setHolderName} placeholder="John Doe" />
          </Field>
          <Field label="Address">
            <Input value={address} onChange={setAddress} placeholder="123 Main St" />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="State">
              <SelectField value={state} onChange={setState} placeholder="State…"
                options={US_STATES.map(s => ({ value: s, label: s }))} />
            </Field>
            <Field label="ZIP">
              <Input value={zip} onChange={setZip} placeholder="10001" />
            </Field>
          </div>
          <Field label="Price ($)" required>
            <Input value={price} onChange={setPrice} placeholder="0.00" type="number" />
          </Field>
        </>
      ) : (
        <>
          <div className="bg-zinc-900/60 border border-white/[0.06] rounded-xl p-3 text-[11px] text-zinc-500 font-mono leading-relaxed">
            <span className="
text-zinc-300 font-semibold">Format (one account per line):</span><br />
            <span className="text-zinc-600">BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price</span>
          </div>

          <Field label="Bulk Data (paste or upload)" required>
            <Textarea value={bulkText} onChange={setBulkText}
              placeholder={"Chase|user@email.com|pass|123456789|021000021|$5000|NY|John Doe|123 Main St|10001|15.00"} rows={6} />
          </Field>

          <FileUploadBtn file={bulkFile} onFile={handleFile} accept=".txt,.csv" label="Upload .txt / .csv file" />

          {lines.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center gap-2">
                <span className="text-[11px] px-2 py-1 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  📋 {lines.length} accounts
                </span>
                {bulkErrors > 0 && (
                  <span className="text-[11px] px-2 py-1 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    ⚠️ {bulkErrors} invalid
                  </span>
                )}
              </div>
              {topBanks.length > 0 && (
                <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-2.5 flex flex-col gap-1">
                  <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">Top banks</div>
                  {topBanks.map(([bank, count]) => (
                    <div key={bank} className="flex items-center justify-between text-[11px]">
                      <span className="text-zinc-400">{bank}</span>
                      <span className="text-blue-400 font-semibold">×{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <Field label="Price per account ($)">
            <Input value={price} onChange={setPrice} placeholder="0.00" type="number" />
          </Field>
        </>
      )}

      <SubmitBtn loading={loading} onClick={submit} />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Main UploadsTab Component
   ═══════════════════════════════════════════════════════════ */

/* ─── Moderation Request Modal ──────────────────────────── */

function ModerationRequestModal({
  requestType,
  onClose,
  isDemoMode,
}: {
  requestType: "custom_bank" | "custom_portal";
  onClose: () => void;
  isDemoMode: boolean;
}) {
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!name.trim()) { toast.error("Name is required"); return; }
    setLoading(true);
    try {
      if (isDemoMode) {
        await new Promise(r => setTimeout(r, 500));
        toast.success(`Request submitted (Demo): "${name.trim()}"`);
      } else {
        await api.submitModerationRequest(requestType, name.trim(), notes.trim() || undefined);
        toast.success(`Request submitted — admin will review within 24h`);
      }
      onClose();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const label = requestType === "custom_bank" ? "bank" : "portal";

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative w-full max-w-[480px] glass-card rounded-t-3xl p-5 flex flex-col gap-4 pb-8"
        style={{ background: "oklch(0.11 0.013 260)" }}>
        <div className="flex items-center justify-between">
          <div className="text-[15px] font-bold text-white">Add custom {label}</div>
          <button onClick={onClose} className="w-8 h-8 rounded-xl bg-white/[0.06] flex items-center justify-center">
            <PlusCircle className="w-4 h-4 text-zinc-500 rotate-45" />
          </button>
        </div>
        <div className="bg-blue-500/[0.08] border border-blue-500/20 rounded-xl p-3 text-[11px] text-blue-300/80 leading-relaxed">
          Request will be sent to admin for review. You'll be notified via bot when it's approved.
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
            {label.charAt(0).toUpperCase() + label.slice(1)} name *
          </label>
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder={`Enter ${label} name…`}
            className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-[13px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40 transition-colors"
          />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Notes (optional)</label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Any additional details…"
            rows={2}
            className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-[13px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40 transition-colors resize-none"
          />
        </div>
        <button
          onClick={submit}
          disabled={loading || !name.trim()}
          className="w-full py-3 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-[14px] transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading
            ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            : <PlusCircle className="w-4 h-4" />}
          {loading ? "Submitting…" : "Submit Request"}
        </button>
      </div>
    </div>
  );
}

export default function UploadsTab() {
  const { seller, isDemoMode, language } = useApp();
  const [activeSection, setActiveSection] = useState<SectionId | null>(null);
  const [showPackages, setShowPackages] = useState(false);
  const [showInstructions, setShowInstructions] = useState(false);
  const [moderationRequestType, setModerationRequestType] = useState<"custom_bank" | "custom_portal" | null>(null);

  const unlockedSections = seller?.allowed_categories ?? [];
  const isUnlocked = useCallback((id: SectionId) => unlockedSections.includes(id), [unlockedSections]);

  // Determine moderation request type for current section
  const getSectionModerationRequestType = (id: SectionId): "custom_bank" | "custom_portal" | null => {
    if (["banks", "brute", "checks"].includes(id)) return "custom_bank";
    if (id === "enroll") return "custom_portal";
    return null;
  };

  if (activeSection) {
    const section = SECTIONS.find(s => s.id === activeSection)!;
    const lang = (language as UploadLang) in UPLOAD_INSTRUCTIONS[activeSection]
      ? (language as UploadLang)
      : "en";
    const instruction = UPLOAD_INSTRUCTIONS[activeSection]?.[lang];
    const moderationType = getSectionModerationRequestType(activeSection);

    return (
      <div className="flex flex-col h-full">
        {/* Moderation Request Modal */}
        {moderationRequestType && (
          <ModerationRequestModal
            requestType={moderationRequestType}
            onClose={() => setModerationRequestType(null)}
            isDemoMode={isDemoMode}
          />
        )}

        {/* Header */}
        <div className="flex items-center gap-3 px-4 pt-4 pb-3 border-b border-white/[0.06]">
          <button onClick={() => setActiveSection(null)}
            className="w-8 h-8 rounded-xl bg-white/[0.05] flex items-center justify-center hover:bg-white/[0.08] transition-colors">
            <ChevronLeft className="w-4 h-4 text-zinc-400" />
          </button>
          <div className="flex-1 min-w-0">
            <div className="text-[14px] font-semibold text-white truncate">{section.label}</div>
            <div className="text-[11px] text-zinc-600 truncate">{section.subtitle}</div>
          </div>
          {moderationType && (
            <button
              onClick={() => setModerationRequestType(moderationType)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-[11px] font-medium hover:bg-cyan-500/15 transition-all flex-shrink-0"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              {moderationType === "custom_bank" ? "Add bank" : "Add portal"}
            </button>
          )}
          <button onClick={() => setShowInstructions(!showInstructions)}
            className={cn(
              "w-8 h-8 rounded-xl flex items-center justify-center transition-colors flex-shrink-0",
              showInstructions ? "bg-amber-500/20 text-amber-400" : "bg-white/[0.05] hover:bg-white/[0.08] text-zinc-500"
            )}>
            <Info className="w-4 h-4" />
          </button>
        </div>

        {showInstructions && instruction && (
          <div className="mx-4 mt-3 bg-amber-500/[0.08] border border-amber-500/20 rounded-xl p-3.5 flex flex-col gap-2.5">
            <div className="text-[12px] font-semibold text-amber-300">{instruction.title}</div>
            <ol className="flex flex-col gap-1.5">
              {instruction.steps.map((step, i) => (
                <li key={i} className="flex items-start gap-2 text-[11px] text-amber-300/80 leading-relaxed">
                  <span className="flex-shrink-0 w-4 h-4 rounded-full bg-amber-500/20 text-amber-400 text-[9px] font-bold flex items-center justify-center mt-0.5">{i + 1}</span>
                  {step}
                </li>
              ))}
            </ol>
            {instruction.format && (
              <div className="bg-zinc-900/60 border border-white/[0.06] rounded-xl p-2.5 mt-1">
                <div className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-1">Format</div>
                <code className="text-[10px] text-zinc-400 font-mono leading-relaxed break-all">{instruction.format}</code>
              </div>
            )}
            {instruction.conversionPrompt && (
              <div className="bg-violet-500/[0.07] border border-violet-500/20 rounded-xl p-2.5">
                <div className="text-[10px] font-semibold text-violet-400 uppercase tracking-wider mb-1">Data Conversion Prompt (AI)</div>
                <div className="text-[10px] text-violet-300/70 leading-relaxed">{instruction.conversionPrompt}</div>
              </div>
            )}
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-4 py-3">
          {activeSection === "banks"      && <BanksForm onBack={() => setActiveSection(null)} />}
          {activeSection === "brute"      && <BruteForm onBack={() => setActiveSection(null)} />}
          {activeSection === "cc"         && <CCForm onBack={() => setActiveSection(null)} />}
          {activeSection === "nfc"        && <NFCForm onBack={() => setActiveSection(null)} />}
          {activeSection === "otp"        && <OTPForm onBack={() => setActiveSection(null)} />}
          {activeSection === "selfreg_cc" && <SelfregCCForm onBack={() => setActiveSection(null)} />}
          {activeSection === "enroll"     && <EnrollForm onBack={() => setActiveSection(null)} />}
          {activeSection === "logs"       && <LogsForm onBack={() => setActiveSection(null)} />}
          {activeSection === "checks"     && <ChecksForm onBack={() => setActiveSection(null)} />}
          {activeSection === "selfreg_ba" && <SelfregBAForm onBack={() => setActiveSection(null)} />}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-3 border-b border-white/[0.06]">
        <div>
          <div className="text-[16px] font-bold text-white">Upload Center</div>
          <div className="text-[11px] text-zinc-600">{unlockedSections.length} / {SECTIONS.length} sections unlocked</div>
        </div>
        <button onClick={() => setShowPackages(!showPackages)}
          className={cn("px-3 py-1.5 rounded-xl text-[11px] font-semibold border transition-all",
            showPackages ? "bg-blue-500/20 border-blue-500/30 text-blue-300" : "bg-white/[0.05] border-white/[0.08] text-zinc-400 hover:border-white/[0.15]")}>
          Packages
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
        {/* Packages panel */}
        {showPackages && (
          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Access Packages</div>
            {PACKAGES.map(pkg => (
              <div key={pkg.id} className={cn("bg-gradient-to-br rounded-xl p-3 border", pkg.color)}>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-[13px] font-bold text-white">{pkg.label}</div>
                    <div className="text-[11px] text-zinc-500 mt-0.5">{pkg.subtitle}</div>
                  </div>
                  <div className="text-[14px] font-bold text-white">${pkg.price}</div>
                </div>
                <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                  {pkg.sections.map(s => (
                    <span key={s} className="text-[10px] px-1.5 py-0.5 rounded-md bg-white/[0.08] text-zinc-400 border border-white/[0.06]">
                      {SECTIONS.find(sec => sec.id === s)?.label}
                    </span>
                  ))}
                </div>
                <button className="mt-2.5 w-full py-2 rounded-xl bg-white/[0.08] hover:bg-white/[0.12] text-white text-[12px] font-semibold transition-all border border-white/[0.08]">
                  Purchase Package
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Section grid */}
        <div className="flex flex-col gap-2">
          {SECTIONS.map(section => {
            const unlocked = isUnlocked(section.id);
            const Icon = section.icon;
            return (
              <button key={section.id}
                onClick={() => unlocked ? setActiveSection(section.id) : toast.info(`Deposit $${section.depositAmount} to unlock ${section.label}`)}
                className={cn(
                  "flex items-center gap-3 px-4 py-3.5 rounded-2xl border text-left transition-all",
                  unlocked
                    ? "bg-white/[0.04] border-white/[0.08] hover:bg-white/[0.07] hover:border-white/[0.14]"
                    : "bg-white/[0.02] border-white/[0.04] opacity-60"
                )}>
                <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0",
                  unlocked ? "bg-blue-500/15" : "bg-white/[0.04]")}>
                  <Icon className={cn("w-4.5 h-4.5", unlocked ? "text-blue-400" : "text-zinc-600")} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={cn("text-[13px] font-semibold", unlocked ? "text-white" : "text-zinc-600")}>
                      {section.label}
                    </span>
                    {section.badge && (
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-blue-500/15 text-blue-400 border border-blue-500/20">
                        {section.badge}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-zinc-600 truncate mt-0.5">{section.subtitle}</div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {!unlocked && (
                    <div className="flex items-center gap-1 text-[10px] text-zinc-600">
                      <Lock className="w-3 h-3" />
                      <span>${section.depositAmount}</span>
                    </div>
                  )}
                  <ChevronRight className={cn("w-4 h-4", unlocked ? "text-zinc-500" : "text-zinc-700")} />
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
