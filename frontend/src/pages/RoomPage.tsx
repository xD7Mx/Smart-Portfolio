import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LayoutGrid, Pencil, Check, X } from "lucide-react";
import { marketApi } from "../services/api";
import { useAppStore } from "../store/appStore";
import CompanyLogo from "../components/common/CompanyLogo";
import InlineStockSearch from "../components/market/InlineStockSearch";
import StockSheet from "../components/market/StockSheet";

/* ══ غرفة التداول ══ (بأمر المالك · D551) — بطاقةٌ كبيرةٌ كويدجت تريدنق فيو بمساحةٍ
   ونطاقٍ أكبر: الرموزُ يضيفها المالكُ ويحذفها على كيفه، وتعبر أجهزته مع التخطيط.
   الأسعارُ من «تداول» أوّلاً (تاسي من خدمة مؤشّره)، والعالميُّ من ياهو. */

const IDX: Record<string, string> = { "^TASI.SR": "TASI", "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "^DJI": "DOW",
  "BZ=F": "BRENT", "GC=F": "GOLD", "BTC-USD": "BTC" };

const fmt = (v: any, d = 2) => (typeof v === "number" ? v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }) : "—");
const tone = (v: any) => (typeof v === "number" && v !== 0 ? (v > 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]") : "text-[var(--ink-muted)]");
const hhmm = (t: any) => {
  const m = String(t || "").match(/(\d{2}):(\d{2})/);
  return m ? `${m[1]}:${m[2]}` : "";
};

export default function RoomPage() {
  const { roomSymbols, setRoomSymbols } = useAppStore();
  const [edit, setEdit] = useState(false);
  const [sheet, setSheet] = useState<string | null>(null);
  const { data = [] } = useQuery({
    queryKey: ["room", roomSymbols.join(",")],
    queryFn: () => marketApi.room(roomSymbols).then(r => (Array.isArray(r.data?.data) ? r.data.data : [])),
    refetchInterval: 30_000, staleTime: 15_000, placeholderData: (p: any) => p,
  });
  const by: Record<string, any> = Object.fromEntries((data as any[]).map(q => [q.symbol, q]));
  const add = (s: string) => {
    const k = /^\d{4}(\.SR)?$/i.test(s) ? s.slice(0, 4) : s.toUpperCase();
    if (!roomSymbols.includes(k)) setRoomSymbols([...roomSymbols, k]);
  };
  const remove = (s: string) => setRoomSymbols(roomSymbols.filter(x => x !== s));

  return (
    <div className="space-y-4 fade-in">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
          <LayoutGrid size={22} className="text-[var(--brand-ink)]" /> غرفة التداول
        </h1>
        <div className="flex items-center gap-2">
          {edit && <InlineStockSearch onPick={add} global />}
          <button type="button" onClick={() => setEdit(e => !e)} aria-pressed={edit}
            className={"inline-flex items-center gap-1.5 min-h-[32px] px-3 py-1.5 rounded-xl text-xs font-bold border " +
              (edit ? "text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink)]")}
            style={{ background: "var(--panel)" }}>
            {edit ? <Check size={14} /> : <Pencil size={14} />} {edit ? "تمّ" : "تعديل"}
          </button>
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-px" style={{ background: "var(--hairline)" }}>
          {roomSymbols.map((s) => {
            const q = by[s] || {};
            const label = IDX[s] || s;
            return (
              <div key={s} className="relative" style={{ background: "var(--surface)" }}>
                <button type="button" onClick={() => !edit && /^\d{4}$/.test(s) && setSheet(s)}
                  className="w-full flex items-center gap-3 px-3 sm:px-4 py-3 min-h-[76px] text-start hover:bg-[var(--field)]">
                  {IDX[s]
                    ? <span className="w-10 h-10 shrink-0 rounded-full flex items-center justify-center text-[10px] font-bold"
                        style={{ background: "var(--brand)", color: "var(--bg)" }} dir="ltr">{label.slice(0, 4)}</span>
                    : <CompanyLogo symbol={s} size={40} />}
                  <span className="flex-1 min-w-0">
                    <span className="flex items-baseline justify-between gap-2">
                      <span className="text-[15px] font-bold text-[var(--ink)] tabular-nums truncate" dir="ltr">{label}</span>
                      <span className="text-[11px] text-[var(--ink-muted)] tabular-nums" dir="ltr">{hhmm(q.time)}</span>
                    </span>
                    <span className="block text-[15px] font-bold tabular-nums text-[var(--ink)] mt-0.5 truncate" dir="ltr" style={{ textAlign: "right" }}>{fmt(q.price)}</span>
                    <span className={"block text-[12px] font-bold tabular-nums truncate " + tone(q.change)} dir="ltr" style={{ textAlign: "right" }}>
                      {typeof q.change === "number" ? `${q.change > 0 ? "+" : ""}${fmt(q.change)}` : ""}
                      {typeof q.change_pct === "number" ? ` (${q.change_pct > 0 ? "+" : ""}${q.change_pct.toFixed(2)}%)` : ""}</span>
                  </span>
                </button>
                {edit && (
                  <button type="button" onClick={() => remove(s)} aria-label={`حذف ${label}`}
                    className="absolute top-1 end-1 w-8 h-8 rounded-full flex items-center justify-center text-[var(--neg-ink)]"
                    style={{ background: "var(--panel)" }}>
                    <X size={15} />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
      {sheet && <StockSheet symbol={sheet} onClose={() => setSheet(null)} />}
    </div>
  );
}
