import React from "react";
import PriceChart from "./PriceChart";
import NativeChart from "./NativeChart";
import { useAppStore } from "../../store/appStore";

/* ‏D607: بأمر المالك — حركةُ السعر والرسمُ البيانيّ في مكانٍ واحدٍ بمفتاح، اختصاراً للمسافة، والاختيارُ يُذكر.
   ‏(ملاحظةُ المالك 2026-10-09): «الرسمُ البيانيّ بجانب حركة السعر في كلّ مكانٍ تُفتح فيه صفحةُ السهم» — فصار مكوّناً
   واحداً تستعمله صفحةُ الشركة في المحفظة وصفحةُ السهم خارجها. والرسمُ هنا رسمٌ فقط بإطاراتٍ كتريدنق فيو. */
export default function PriceOrChart({ symbol }: { symbol: string }) {
  const theme = useAppStore(s => s.theme);
  const [view, setView] = React.useState<"price" | "chart">(() => {
    try { return (localStorage.getItem("sp_stock_view") as "price" | "chart") || "price"; } catch { return "price"; }
  });
  const pick = (v: "price" | "chart") => { setView(v); try { localStorage.setItem("sp_stock_view", v); } catch {} };
  return (
    <div className="space-y-2">
      <div className="flex justify-start gap-1.5">
        {([["price", "حركة السعر"], ["chart", "الرسم البياني"]] as const).map(([id, lbl]) => (
          <button key={id} onClick={() => pick(id)}
            className="px-3 min-h-[32px] rounded-lg text-[11px] font-bold border transition-all"
            style={view === id ? { color: "var(--brand-ink)", borderColor: "var(--brand)" }
                               : { color: "var(--ink-muted)", borderColor: "var(--hairline)" }}>
            {lbl}
          </button>
        ))}
      </div>
      {view === "price" ? <PriceChart symbol={symbol} />
        : <div className="card p-2"><NativeChart symbol={symbol} theme={theme === "light" ? "light" : "dark"} preset="d7m-weekly" height={380} /></div>}
    </div>
  );
}
