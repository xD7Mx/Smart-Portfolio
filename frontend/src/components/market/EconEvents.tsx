/* ══ الأحداثُ الاقتصاديةُ الأمريكيةُ وأثرُها ══ (‏D761 · بأمر المالك 2026-11-17)
   «لازم يكون أيُّ حدث، أيُّ خبر — خبرٌ جللٌ اليوم كالفيدرالي — وما الأثر؟ تفسيرٌ وتحليل: ماذا أتوقّع؛ إذا رُفعت الفائدة هل يتضرّر السوق
   إلى كول أو بوت». فزرٌّ بعدد الأحداث العالية الأثر اليوم وغداً، ولوحةٌ بها كلُّها بوقت الرياض: ما يقيسه الحدث، وإن جاء أعلى من التوقّع
   فكذا، وأدنى فكذا، وميلُ الخيارات — والرقمُ الفعليُّ لا يتوفّر في المصدر فلا يُدّعى. */
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import { Zap, X, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { marketApi } from "../../services/api";

type Ev = { id: string; title: string; ar?: string; impact: string; impact_ar: string; at: string; riyadh: string; day: string; past: boolean;
  forecast: string | null; previous: string | null; what?: string; above?: string; below?: string;
  above_lean?: "call" | "put" | "neutral"; below_lean?: "call" | "put" | "neutral" };

const LEAN = { call: ["ميلٌ لعقود الشراء Call", TrendingUp], put: ["ميلٌ لعقود البيع Put", TrendingDown], neutral: ["بلا ميلٍ واضح", Minus] } as const;
/* ‏لكلّ سيناريو ميلُه صريحاً — «أعلى من المتوقّع ⇒ بيع» و«أدنى ⇒ شراء» مثلاً */
const Lean = ({ v }: { v?: "call" | "put" | "neutral" }) => {
  if (!v) return null;
  const [t, Icon] = LEAN[v];
  return <span className={"ee-lean l-" + v} data-role="ee-lean" data-lean={v}><Icon size={12} /> {t}</span>;
};

export function useEcon() {
  return useQuery<{ events: Ev[]; read_ok: boolean } | null>({
    queryKey: ["econ-events"], queryFn: () => marketApi.econEvents().then(r => r.data?.data ?? null),
    staleTime: 10 * 60_000, refetchInterval: 15 * 60_000, retry: 0,
  });
}

export default function EconEvents({ compact = false }: { compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const [shown, setShown] = useState(false);
  const q = useEcon();
  const evs = q.data?.events || [];
  const soon = evs.filter(e => e.impact === "High" && !e.past && (e.day === "اليوم" || e.day === "غداً"));
  useEffect(() => { if (!open) { setShown(false); return; } const id = requestAnimationFrame(() => setShown(true)); return () => cancelAnimationFrame(id); }, [open]);
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopImmediatePropagation(); setOpen(false); } };
    window.addEventListener("keydown", k, true);
    return () => window.removeEventListener("keydown", k, true);
  }, [open]);
  return (
    <>
      <button type="button" className={"btn-ghost ee-btn" + (soon.length ? " hot" : "")} onClick={() => setOpen(true)} data-role="ee-btn"
        title="الأحداثُ الاقتصاديةُ الأمريكية وأثرُها" aria-label="الأحداث الاقتصادية الأمريكية">
        <Zap size={13} />{compact ? "الأحداث" : "الأحداث الاقتصادية"}{soon.length > 0 && <span className="ee-n" data-role="ee-count">{soon.length}</span>}
      </button>
      {open && createPortal(
        <div className="d7m-modal ee-modal" data-shown={shown ? "1" : "0"} role="dialog" aria-label="الأحداث الاقتصادية الأمريكية" onClick={() => setOpen(false)} data-role="ee">
          <div className="d7m-sheet ee-sheet" onClick={e => e.stopPropagation()}>
            <div className="d7m-head">
              <strong><Zap size={15} className="inline-block align-[-2px] me-1" />الأحداثُ الاقتصاديةُ الأمريكية</strong>
              <button type="button" className="d7m-btn" onClick={() => setOpen(false)} aria-label="إغلاق"><X size={15} /></button>
            </div>
            {q.isPending ? <p className="ocx-note">…</p> : !evs.length ? <p className="ocx-note">لا أحداثَ مهمّةً متوفّرةٌ الآن.</p> : (
              <>
                {!q.data?.read_ok && <p className="ocx-note">قراءةُ الأثر غيرُ متوفّرة الآن — الأحداثُ بأوقاتها وتوقّعاتها.</p>}
                <ul className="ee-list">
                  {evs.map((e, i) => {
                    return (
                      <li key={e.id} className={"ee-item card-rise" + (e.past ? " past" : "") + (e.impact === "High" ? " high" : "")}
                        style={{ animationDelay: `${Math.min(i, 12) * 30}ms` }} data-role="ee-item">
                        <div className="ee-top">
                          <span className="ee-when" dir="ltr">{e.riyadh.slice(-5)}</span>
                          <span className="ee-day">{e.day}</span>
                          <b className="ee-title">{e.ar || e.title}</b>
                          <span className={"ee-imp " + (e.impact === "High" ? "h" : "m")}>{e.impact_ar}</span>
                        </div>
                        <div className="ee-sub" dir="ltr">{e.title}{e.forecast ? ` · التوقّع ${e.forecast}` : ""}{e.previous ? ` · السابق ${e.previous}` : ""}</div>
                        {e.what && <p className="ee-what">{e.what}</p>}
                        {(e.above || e.below) && (
                          <div className="ee-sc">
                            {e.above && <div className="ee-s"><p><b>أعلى من المتوقّع:</b> {e.above}</p><Lean v={e.above_lean} /></div>}
                            {e.below && <div className="ee-s"><p><b>أدنى من المتوقّع:</b> {e.below}</p><Lean v={e.below_lean} /></div>}
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </>
            )}
          </div>
        </div>, document.body,
      )}
    </>
  );
}
