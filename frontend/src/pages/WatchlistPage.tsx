import { useSearchParams } from "react-router-dom";
import { CandlestickChart, FlaskConical } from "lucide-react";
import TradeRoom from "../components/market/TradeRoom";
import ResearchLab from "./ResearchLab";

/* ══ غرفة التداول ══ (بأمر المالك · D687 — كانت «الشاشة» · D683، وقبلها «المراقبة» · D677)
   ‏D736 (المالك 2026-11-15): «خلّها الرسم البياني الآن ومختبر الأبحاث… وألغِ الشركات، ما أشوف لها داعي». فالتبويبان:
   «الرسم البياني» (الرسمُ الاحترافيُّ وقوائمُ المراقبة) و«مختبر الأبحاث» — قسمُ الأبحاث (‏D745: تقريرٌ يوميٌّ وتوصياتٌ ومكتبة؛ كان في «تحليل الذكاء» — وروابطُه القديمة
   /stars · /ai?tab=lab · /portfolio?tab=lab تفتحه هنا). والتنقّلُ بينهما بحركةٍ لا قفزة. */
const TABS = [["chart", "الرسم البياني", CandlestickChart], ["lab", "مختبر الأبحاث", FlaskConical]] as const;

export default function WatchlistPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "lab" ? "lab" : "chart";
  const setTab = (t: string) => setParams(t === "lab" ? { tab: "lab" } : {}, { replace: true });
  return (
    <div className="space-y-3 fade-in">
      <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
        <CandlestickChart size={22} className="text-[var(--brand-ink)]" /> غرفة التداول
      </h1>
      <nav className="flex gap-2 pb-1" aria-label="أقسام غرفة التداول">
        {TABS.map(([id, label, Icon]) => (
          <button key={id} onClick={() => setTab(id)} aria-pressed={tab === id} data-role="room-tab"
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
        {tab === "chart" ? <TradeRoom /> : <ResearchLab />}
      </div>
    </div>
  );
}
