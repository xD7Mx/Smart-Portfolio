import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CandlestickChart, LayoutGrid } from "lucide-react";
import WatchlistTab from "../components/market/WatchlistTab";
import StockSheet from "../components/market/StockSheet";
import ChartPage from "./ChartPage";

/* ══ غرفة التداول ══ (بأمر المالك · D687 — كانت «الشاشة» · D683، وقبلها «المراقبة» · D677)
   تبويبان داخليّان بلغة تبويبات المحفظة: «الشركات» بطاقاتٍ، و«الرسم البياني» (كان قسماً في القائمة — ورابطُه القديم
   /chart يفتحه هنا). والتنقّلُ بينهما بحركةٍ لا قفزة. */
const TABS = [["board", "الشركات", LayoutGrid], ["chart", "الرسم البياني", CandlestickChart]] as const;

export default function WatchlistPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "chart" ? "chart" : "board";
  const setTab = (t: string) => setParams(t === "chart" ? { tab: "chart" } : {}, { replace: true });
  const [sheet, setSheet] = useState<string | null>(null);
  return (
    <div className="space-y-3 fade-in">
      <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
        <CandlestickChart size={22} className="text-[var(--brand-ink)]" /> غرفة التداول
      </h1>
      <nav className="flex gap-2 pb-1">
        {TABS.map(([id, label, Icon]) => (
          <button key={id} onClick={() => setTab(id)} aria-pressed={tab === id}
            className="flex flex-col md:flex-row items-center justify-center gap-1 md:gap-2 flex-1 min-w-0 px-1.5 md:px-3 py-2 md:py-2.5 rounded-xl text-[10px] md:text-sm transition-colors duration-200"
            style={tab === id
              ? { background: "color-mix(in srgb, var(--brand) 12%, transparent)", color: "var(--brand-ink)", fontWeight: 700 }
              : { background: "transparent", color: "var(--ink-muted)" }}>
            <Icon size={18} className="md:w-4 md:h-4 shrink-0" />
            <span className="whitespace-nowrap">{label}</span>
          </button>
        ))}
      </nav>
      <div key={tab} className="fade-in">
        {tab === "chart" ? <ChartPage embedded /> : <WatchlistTab onOpen={setSheet} />}
      </div>
      {sheet && <StockSheet symbol={sheet} onClose={() => setSheet(null)} />}
    </div>
  );
}
