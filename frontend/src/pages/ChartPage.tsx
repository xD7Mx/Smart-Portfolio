import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { CandlestickChart, ChevronDown } from "lucide-react";
import NativeChart from "../components/analysis/NativeChart";
import CompanyLogo from "../components/common/CompanyLogo";
import InlineStockSearch from "../components/market/InlineStockSearch";
import { lookupCompany } from "../data/saudiCompanies";
import { holdingsApi, marketApi } from "../services/api";
import { useAppStore } from "../store/appStore";

/* ══ غرفةُ التداول ══ (بأمر المالك · D521)
   السوقان السعوديُّ والعالميُّ في رسمٍ واحدٍ وحقلِ بحثٍ واحد — لا تبويبَين.
   وتحت العنوان درجان: «محفظتك» و«المؤشرات» (تاسي أوّلاً ثمّ العالمية). */
const INDICES: [string, string][] = [
  ["^TASI.SR", "تاسي"], ["^GSPC", "S&P 500"], ["^IXIC", "ناسداك"], ["^DJI", "داو جونز"],
  ["BZ=F", "برنت"], ["GC=F", "الذهب"], ["BTC-USD", "بتكوين"],
];

type Drawer = null | "mine" | "idx" | "stars";

const chipCls = (on: boolean) =>
  "shrink-0 min-h-[32px] px-2.5 py-1.5 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5 " +
  (on ? "text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)] hover:text-[var(--ink)]");

export default function ChartPage() {
  const { theme } = useAppStore();
  const [chosen, setChosen] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<Drawer>(null);

  // الأزرار السريعة من حيازات المحفظة النشطة (معزولة بالمحفظة).
  const { data: holdings = [] } = useQuery({
    queryKey: ["holdings"],
    queryFn: () => holdingsApi.list().then(r => (Array.isArray(r.data?.data) ? r.data.data : [])),
  });
  const chips = useMemo(
    () => holdings
      .filter((h: any) => h.company?.symbol)
      .map((h: any) => ({ symbol: h.company.symbol, name: h.company.name_ar || h.company.name || h.company.company_name, logo_url: h.company.logo_url })),
    [holdings]
  );

  // «نجوم تاسي 20» (D522) — تُجلب عند فتح درجها فقط.
  const { data: stars, isLoading: starsLoading } = useQuery({
    queryKey: ["tasi-stars"], enabled: drawer === "stars", staleTime: 5 * 60_000,
    queryFn: () => marketApi.tasiStars().then(r => r.data?.data || null),
  });
  const pct = (v: any) => (typeof v === "number" ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}%` : "غير متوفّر");
  const tone = (v: any) => (typeof v === "number" ? (v >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]") : "text-[var(--ink-muted)]");

  // الافتراضيّ: أوّلُ شركةٍ في المحفظة، وإلا تاسي — فلا تبدأ الغرفةُ فارغة.
  const symbol = chosen ?? (chips[0]?.symbol ?? "^TASI.SR");
  const pick = (s: string) => { setChosen(s.toUpperCase()); setDrawer(null); };
  const title = INDICES.find(([s]) => s === symbol)?.[1] || lookupCompany(symbol)?.name_ar || symbol;
  const flip = (d: Drawer) => setDrawer(o => (o === d ? null : d));

  const tab = (d: Exclude<Drawer, null>, label: string) => (
    <button type="button" onClick={() => flip(d)} aria-expanded={drawer === d}
      className={"inline-flex items-center gap-1.5 min-h-[32px] px-3 py-1.5 rounded-xl text-xs font-bold border transition-all " +
        (drawer === d ? "text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink)]")}
      style={{ background: "var(--panel)" }}>
      {label}
      <ChevronDown size={14} className={"text-[var(--ink-muted)] transition-transform duration-200 " + (drawer === d ? "rotate-180" : "")} />
    </button>
  );

  return (
    <div className="space-y-4 fade-in">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
          <CandlestickChart size={22} className="text-[var(--brand-ink)]" /> غرفة التداول
        </h1>
        <InlineStockSearch onPick={pick} global />
      </div>

      <div className="flex items-center gap-2">
        {chips.length > 0 && tab("mine", "محفظتك")}
        {tab("idx", "المؤشرات")}
        {tab("stars", "نجوم تاسي")}
        <span className="ms-auto min-w-0 truncate text-sm font-semibold text-[var(--ink)]">{title}</span>
      </div>

      <div style={{ display: "grid", gridTemplateRows: drawer ? "1fr" : "0fr", opacity: drawer ? 1 : 0, transition: "grid-template-rows .24s ease, opacity .2s ease" }}>
        <div style={{ overflow: "hidden" }}>
          <div className="flex items-center gap-2 overflow-x-auto pb-1 pt-0.5" style={{ scrollbarWidth: "none" }}>
            {drawer === "mine" && chips.map((c: any) => (
              <button key={c.symbol} onClick={() => pick(c.symbol)} title={c.name} className={chipCls(symbol === c.symbol)}>
                <CompanyLogo symbol={c.symbol} size={18} logoUrl={c.logo_url} />
                <span>{c.symbol}</span>
              </button>
            ))}
            {drawer === "stars" && (starsLoading ? (
              <div className="h-8 w-full skeleton rounded-xl" />
            ) : !stars?.members?.length ? (
              <span className="text-xs text-[var(--ink-muted)]">غير متوفّر</span>
            ) : (
              <>
                <div className="shrink-0 flex items-center gap-2 px-2.5 min-h-[32px] rounded-xl border border-[var(--hairline)] text-xs font-bold">
                  <span className="text-[var(--ink-muted)]">منذ</span>
                  <span dir="ltr" className="tabular-nums text-[var(--ink)]">{stars.since}</span>
                  <span className={"tabular-nums " + tone(stars.perf?.ret)} dir="ltr">{pct(stars.perf?.ret)}</span>
                  <span className="text-[var(--ink-muted)]">تاسي</span>
                  <span className={"tabular-nums " + tone(stars.perf?.tasi_ret)} dir="ltr">{pct(stars.perf?.tasi_ret)}</span>
                </div>
                {stars.members.map((m: any) => (
                  <button key={m.symbol} onClick={() => pick(m.symbol)} title={m.name} className={chipCls(symbol === m.symbol)}>
                    <CompanyLogo symbol={m.symbol} size={18} />
                    <span>{m.symbol}</span>
                    <span dir="ltr" className="tabular-nums text-[var(--pos-ink)]">{pct(m.upside)}</span>
                  </button>
                ))}
              </>
            ))}
            {drawer === "idx" && INDICES.map(([s, lbl]) => (
              <button key={s} onClick={() => pick(s)} className={chipCls(symbol === s)}>{lbl}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="card chart-lock">
        <NativeChart symbol={symbol} theme={theme === "light" ? "light" : "dark"} />
      </div>
    </div>
  );
}
