/* ══ الأحداثُ الاقتصاديةُ الأمريكيةُ وأثرُها ══ (‏D761 · بأمر المالك 2026-11-17)
   «لازم يكون أيُّ حدث، أيُّ خبر — خبرٌ جللٌ اليوم كالفيدرالي — وما الأثر؟ تفسيرٌ وتحليل: ماذا أتوقّع؛ إذا رُفعت الفائدة هل يتضرّر السوق
   إلى كول أو بوت». فزرٌّ بعدد الأحداث العالية الأثر اليوم وغداً، ولوحةٌ بها كلُّها بوقت الرياض: ما يقيسه الحدث، وإن جاء أعلى من التوقّع
   فكذا، وأدنى فكذا، وميلُ الخيارات — والرقمُ الفعليُّ لا يتوفّر في المصدر فلا يُدّعى.
   ‏D782 (المالك 2026-11-21): «الأحداثُ أبغاها بالعربية… وتدعم السوقَ الأمريكيَّ والسعوديَّ كمان»: فلا سطرَ إنجليزيٌّ تحت الحدث (اسمُه عربيٌّ من
   قاموس الخادم)، وللسهم السعوديّ أحداثُه بقراءة السوق السعودي (الفيدراليّ والريالُ المربوط · النفط · الصين) — إيجابيٌّ أو سلبيٌّ له —
   ومعها أحداثُ الشركة نفسِها القادمة من مفكرتها. */
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import { Zap, X, TrendingUp, TrendingDown, Minus, CalendarDays } from "lucide-react";
import { marketApi } from "../../services/api";

type Ev = { id: string; title: string; ar?: string; impact: string; impact_ar: string; at: string; riyadh: string; day: string; past: boolean;
  forecast: string | null; previous: string | null; what?: string; above?: string; below?: string;
  above_lean?: Lean; below_lean?: Lean };
type Lean = "call" | "put" | "pos" | "neg" | "neutral";
type Co = { date: string; title: string; kind: string };

const LEAN = { call: ["ميلٌ لعقود الشراء Call", TrendingUp], put: ["ميلٌ لعقود البيع Put", TrendingDown], neutral: ["بلا ميلٍ واضح", Minus],
  pos: ["إيجابيٌّ للسوق السعودي", TrendingUp], neg: ["سلبيٌّ للسوق السعودي", TrendingDown] } as const;
/* ‏لكلّ سيناريو ميلُه صريحاً — «أعلى من المتوقّع ⇒ بيع» و«أدنى ⇒ شراء» مثلاً */
const Lean = ({ v }: { v?: Lean }) => {
  if (!v || !LEAN[v]) return null;
  const [t, Icon] = LEAN[v];
  const cls = v === "pos" ? "call" : v === "neg" ? "put" : v;
  return <span className={"ee-lean l-" + cls} data-role="ee-lean" data-lean={v}><Icon size={12} /> {t}</span>;
};

export function useEcon(market: "us" | "sa" = "us", symbol?: string, name?: string) {
  return useQuery<{ events: Ev[]; read_ok: boolean; company?: Co[] } | null>({
    queryKey: ["econ-events", market, market === "sa" ? symbol || "" : ""],
    queryFn: () => marketApi.econEvents(market, market === "sa" ? symbol : undefined, market === "sa" ? name : undefined).then(r => r.data?.data ?? null),
    staleTime: 10 * 60_000, refetchInterval: 15 * 60_000, retry: 0,
  });
}

export default function EconEvents({ compact = false, market = "us", symbol, name }: { compact?: boolean; market?: "us" | "sa"; symbol?: string; name?: string }) {
  const [open, setOpen] = useState(false);
  const [shown, setShown] = useState(false);
  const q = useEcon(market, symbol, name);
  const evs = q.data?.events || [];
  const co = q.data?.company || [];
  const sa = market === "sa";
  const title = sa ? "أحداثُ السوق السعودي" : "الأحداثُ الاقتصاديةُ الأمريكية";
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
      <button type="button" className={"btn-ghost ee-btn" + (soon.length ? " hot" : "")} onClick={() => setOpen(true)} data-role="ee-btn" data-market={market}
        title={`${title} وأثرُها`} aria-label={title}>
        <Zap size={13} />{compact ? "الأحداث" : "الأحداث الاقتصادية"}{soon.length > 0 && <span className="ee-n" data-role="ee-count">{soon.length}</span>}
      </button>
      {open && createPortal(
        <div className="d7m-modal ee-modal" data-shown={shown ? "1" : "0"} role="dialog" aria-label={title} onClick={() => setOpen(false)} data-role="ee" data-market={market}>
          <div className="d7m-sheet ee-sheet" onClick={e => e.stopPropagation()}>
            <div className="d7m-head">
              <strong><Zap size={15} className="inline-block align-[-2px] me-1" />{title}</strong>
              <button type="button" className="d7m-btn" onClick={() => setOpen(false)} aria-label="إغلاق"><X size={15} /></button>
            </div>
            {co.length > 0 && (
              <section className="ee-co" data-role="ee-company">
                <h4><CalendarDays size={14} className="inline-block align-[-2px] me-1" />أحداثُ الشركة</h4>
                <ul className="ee-list">
                  {co.map((c, i) => (
                    <li key={i} className="ee-item card-rise" style={{ animationDelay: `${Math.min(i, 8) * 30}ms` }} data-role="ee-co-item">
                      <div className="ee-top"><span className="ee-when" dir="ltr">{c.date.slice(8, 10)}/{c.date.slice(5, 7)}</span>
                        {c.kind && <span className="ee-day">{c.kind}</span>}<b className="ee-title">{c.title}</b></div>
                    </li>
                  ))}
                </ul>
              </section>
            )}
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
                        {(e.forecast || e.previous) && (
                          <div className="ee-sub" data-role="ee-sub">
                            {e.forecast && <span>التوقّع <b dir="ltr">{e.forecast}</b></span>}
                            {e.previous && <span>السابق <b dir="ltr">{e.previous}</b></span>}
                          </div>
                        )}
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
