import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { CandlestickChart, ChevronDown } from "lucide-react";
import NativeChart from "../components/analysis/NativeChart";
import CompanyLogo from "../components/common/CompanyLogo";
import InlineStockSearch from "../components/market/InlineStockSearch";
import { holdingsApi } from "../services/api";
import { useAppStore } from "../store/appStore";

/* ══ الرسم البياني ══ (بأمر المالك · D521 · D529)
   السوقان السعوديُّ والعالميُّ في رسمٍ واحدٍ وحقلِ بحثٍ واحد — لا تبويبَين.
   وتحت العنوان درجان: «محفظتك» و«المؤشرات» (تاسي أوّلاً ثمّ العالمية). */
const INDICES: [string, string][] = [
  ["^TASI.SR", "تاسي"], ["^GSPC", "S&P 500"], ["^IXIC", "ناسداك"], ["^DJI", "داو جونز"],
  ["BZ=F", "برنت"], ["GC=F", "الذهب"], ["BTC-USD", "بتكوين"],
];

type Drawer = null | "mine" | "idx";

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

  // الافتراضيّ: أوّلُ شركةٍ في المحفظة، وإلا تاسي — فلا تبدأ الغرفةُ فارغة.
  const symbol = chosen ?? (chips[0]?.symbol ?? "^TASI.SR");
  const pick = (s: string) => { setChosen(s.toUpperCase()); setDrawer(null); };
  const idxLabel = INDICES.find(([s]) => s === symbol)?.[1];
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
      <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
        <CandlestickChart size={22} className="text-[var(--brand-ink)]" /> الرسم البياني
      </h1>

      {/* الدرجُ ملتصقٌ بالتبويبات: ينزل منها بحركةٍ ويعود إليها — بلا فراغٍ حين يُطوى. */}
      <div>
        <div className="flex items-center gap-2">
          {chips.length > 0 && tab("mine", "محفظتك")}
          {tab("idx", "المؤشرات")}
          {/* ‏D550: البحثُ بجانب المؤشرات (بأمر المالك) — واسمُ الشركة انتقل إلى سطر السعر شعاراً ورمزاً */}
          <InlineStockSearch onPick={pick} global />
        </div>
        <div style={{ display: "grid", gridTemplateRows: drawer ? "1fr" : "0fr", opacity: drawer ? 1 : 0,
                      transform: drawer ? "translateY(0)" : "translateY(-6px)",
                      transition: "grid-template-rows .28s ease, opacity .22s ease, transform .28s ease" }}>
          <div style={{ overflow: "hidden" }}>
            <div className="flex items-center gap-2 overflow-x-auto pt-2" style={{ scrollbarWidth: "none" }}>
              {drawer === "mine" && chips.map((c: any) => (
                <button key={c.symbol} onClick={() => pick(c.symbol)} title={c.name} className={chipCls(symbol === c.symbol)}>
                  <CompanyLogo symbol={c.symbol} size={18} logoUrl={c.logo_url} />
                  <span>{c.symbol}</span>
                </button>
              ))}
              {drawer === "idx" && INDICES.map(([s, lbl]) => (
                <button key={s} onClick={() => pick(s)} className={chipCls(symbol === s)}>{lbl}</button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="card chart-lock">
        <NativeChart symbol={symbol} theme={theme === "light" ? "light" : "dark"}
          identity={<span className="flex items-center gap-1.5 shrink-0">
            {!idxLabel && <CompanyLogo symbol={symbol} size={26} />}
            <span className="text-[14px] font-bold text-[var(--ink)] tabular-nums" dir="ltr">{idxLabel || symbol.replace(".SR", "")}</span>
          </span>} />
      </div>
    </div>
  );
}
