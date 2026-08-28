import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { CandlestickChart, Search, ChevronDown } from "lucide-react";
import NativeChart from "../components/analysis/NativeChart";
import TradingViewChart from "../components/analysis/TradingViewChart";
import CompanyLogo from "../components/common/CompanyLogo";
import { searchCompanies, SaudiCompany } from "../data/saudiCompanies";
import { holdingsApi } from "../services/api";
import { useAppStore } from "../store/appStore";

export default function ChartPage() {
  const { theme } = useAppStore();
  const [q, setQ] = useState("");
  const [sug, setSug] = useState<SaudiCompany[]>([]);
  const [chosen, setChosen] = useState<string | null>(null);
  const [engine, setEngine] = useState<"native" | "tv">("native");
  const [picksOpen, setPicksOpen] = useState(false);

  // الأزرار السريعة من حيازات المحفظة النشطة (معزولة بالمحفظة) — تتفاعل مع
  // تبديل المحافظ ووضع التوحيد تلقائيًا عبر إبطال الكاش.
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

  // default: first portfolio company; if none, nothing until the user searches
  const symbol = chosen ?? (chips[0]?.symbol ?? null);
  const pick = (s: string) => { setChosen(s.toUpperCase()); setQ(""); setSug([]); };

  return (
    <div className="space-y-5 fade-in">
      <div>
        <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
          <CandlestickChart size={22} className="text-[var(--brand-ink)]" /> الرسم البياني
        </h1>
      </div>
      {/* مربع البحث أسفل العنوان مباشرةً (كسابق عهده) */}
      <div className="relative w-full sm:max-w-md">
          <Search size={15} className="absolute end-3 top-1/2 -translate-y-1/2 text-[var(--ink-muted)]" />
          <input className="input px-9" placeholder="ابحث عن سهم (بالرمز أو الاسم)…" value={q}
            onChange={e => { setQ(e.target.value); setSug(searchCompanies(e.target.value)); }}
            onKeyDown={e => { if (e.key === "Enter" && q) pick(q); }} />
          {sug.length > 0 && (
            <div className="absolute z-20 top-full mt-1 w-full rounded-xl overflow-hidden shadow-2xl"
              style={{ background: "var(--pop)", border: "1px solid var(--line)", maxHeight: 260, overflowY: "auto" }}>
              {sug.map(c => (
                <button key={c.symbol} type="button" onClick={() => pick(c.symbol)}
                  className="w-full text-start px-3 py-2.5 hover:bg-[var(--field)] flex items-center gap-3 transition-colors">
                  <CompanyLogo symbol={c.symbol} size={26} />
                  <span className="tag-b shrink-0">{c.symbol}</span>
                  <span className="text-[var(--ink)] text-sm font-semibold">{c.name_ar}</span>
                  <span className="text-[var(--ink-muted)] text-xs ms-auto">{c.name_en}</span>
                </button>
              ))}
            </div>
          )}
      </div>
      {/* صفّ واحد (RTL): محفظتك ثم السوق السعودي ثم السوق العالمي */}
      <div className="flex flex-wrap items-center gap-2">
        {chips.length > 0 && (
          <button onClick={() => setPicksOpen(o => !o)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border border-[var(--hairline)] text-[var(--ink)] hover:text-[var(--ink)] transition-all"
            style={{ background: "var(--panel)" }}>
            محفظتك
            <ChevronDown size={14} className={"text-[var(--ink-muted)] transition-transform duration-200 " + (picksOpen ? "rotate-180" : "")} />
          </button>
        )}
        {symbol && (
          <>
            <button onClick={() => setEngine("native")}
              className={"px-3 py-1.5 rounded-xl text-xs font-bold border transition-all " + (engine === "native" ? " text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)] hover:text-[var(--ink)]")}>
              السوق السعودي
            </button>
            <button onClick={() => setEngine("tv")}
              className={"px-3 py-1.5 rounded-xl text-xs font-bold border transition-all " + (engine === "tv" ? " text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)] hover:text-[var(--ink)]")}>
              السوق العالمي
            </button>
          </>
        )}
      </div>

      {/* درج شركات المحفظة — صفّ أفقي واحد يتحرّك (كشخصيات الملف الشخصي) */}
      {chips.length > 0 && (
        <div style={{ display: "grid", gridTemplateRows: picksOpen ? "1fr" : "0fr", opacity: picksOpen ? 1 : 0, transition: "grid-template-rows .24s ease, opacity .2s ease" }}>
          <div style={{ overflow: "hidden" }}>
            <div className="flex items-center gap-2 overflow-x-auto pb-1 pt-0.5" style={{ scrollbarWidth: "none" }}>
              {chips.map((c: any) => (
                <button key={c.symbol} onClick={() => pick(c.symbol)} title={c.name}
                  className={"shrink-0 px-2.5 py-1.5 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5 " +
                    (symbol === c.symbol ? " text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)] hover:text-[var(--ink)]")}>
                  <CompanyLogo symbol={c.symbol} size={18} logoUrl={c.logo_url} />
                  <span>{c.symbol}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {symbol ? (
        <>

          {engine === "native" ? (
            <div className="card chart-lock">
              <NativeChart symbol={symbol} theme={theme === "light" ? "light" : "dark"} />
            </div>
          ) : (
            <>
              <div className="card chart-lock p-0 overflow-hidden" style={{ height: "72vh", minHeight: 480 }}>
                <TradingViewChart symbol={symbol} theme={theme === "light" ? "light" : "dark"} />
              </div>
            </>
          )}
        </>
      ) : (
        <div className="card">
          <div className="py-16 text-center text-[var(--ink-muted)]">
            <CandlestickChart size={40} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">ابحث عن سهم من مربع البحث بالأعلى لعرض شارته.</p>
            <p className="text-xs mt-1 text-[var(--ink-muted)]">أضِف شركات إلى محفظتك لتظهر هنا كأزرار سريعة.</p>
          </div>
        </div>
      )}
    </div>
  );
}
