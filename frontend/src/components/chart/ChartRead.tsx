/* ══ تحليلُ الرسم بالذكاء ══ (‏D782 · بأمر المالك 2026-11-21)
   «داخل الرسم البيانيّ ضع زرّاً: تحليلُ الرسم… الذكاءُ يقرأ الرسمَ فين متوجّه، ويتعرّف على المؤشّرات الموجودة ويقرأها نيابةً عنّي… ويفهم
   المستويات: متى البيعُ ومتى الشراء… استنتاجاتٌ واقعية» — والزرُّ بجانب «الأحداث» في مكان شارة حالة السوق (والحالةُ أيقونةٌ بجانب الاسم).
   فالزرُّ يأخذ لقطةَ الرسم (صورتَه وأرقامَه — ولكلّ شاشةٍ في الشاشات المتعدّدة) ويرسلها، والخادمُ يحرس القراءة: لا مستوىً إلا برقمٍ من
   اللقطة، ولا جملةَ برقمٍ لا أصلَ له (‏services/chart_read). */
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useMutation } from "@tanstack/react-query";
import { Sparkles, X, RotateCw, TrendingUp, TrendingDown, MoveHorizontal } from "lucide-react";
import { marketApi } from "../../services/api";

export type ReadFrame = Record<string, any>;
type Reading = {
  bias: "صاعد" | "هابط" | "عرضي"; headline: string | null; frames: { tf: string; reading: string }[];
  levels: { kind: "مقاومة" | "دعم"; price: number; from: string; note: string }[];
  indicators: { name: string; reading: string }[]; buy: string | null; sell: string | null; invalid: string | null; risk: string | null;
};

const fmt = (v: number) => v.toLocaleString("en-US", { minimumFractionDigits: Math.abs(v) >= 1 ? 2 : 4, maximumFractionDigits: Math.abs(v) >= 1 ? 2 : 4 });
const BiasIc = ({ b }: { b: string }) => (b === "صاعد" ? <TrendingUp size={15} /> : b === "هابط" ? <TrendingDown size={15} /> : <MoveHorizontal size={15} />);

export default function ChartRead({ symbol, name, market, frames }: {
  symbol: string; name?: string; market: "us" | "sa"; frames: () => ReadFrame[];
}) {
  const [open, setOpen] = useState(false);
  const [shown, setShown] = useState(false);
  const m = useMutation({
    mutationFn: () => {
      const fr = frames().filter(Boolean);
      if (!fr.length) return Promise.reject(new Error("لا شموع"));
      return marketApi.chartRead({ symbol, name, market, frames: fr }).then(r => r.data?.data);
    },
  });
  useEffect(() => { if (!open) { setShown(false); return; } const id = requestAnimationFrame(() => setShown(true)); return () => cancelAnimationFrame(id); }, [open]);
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopImmediatePropagation(); setOpen(false); } };
    window.addEventListener("keydown", k, true);
    return () => window.removeEventListener("keydown", k, true);
  }, [open]);
  useEffect(() => { setOpen(false); m.reset(); }, [symbol]);   // eslint-disable-line react-hooks/exhaustive-deps
  const go = () => { setOpen(true); m.mutate(); };
  const d = m.data as { ok: boolean; reading?: Reading; at?: string } | undefined;
  const r = d?.ok ? d.reading : null;
  const tone = r ? (r.bias === "صاعد" ? "pos" : r.bias === "هابط" ? "neg" : "warn") : "muted";
  return (
    <>
      <button type="button" className="btn-ghost ee-btn cr-btn" onClick={go} data-role="chart-read-btn" title="الذكاءُ يقرأ الرسمَ ومؤشّراتِه ومستوياتِه"
        aria-label="تحليل الرسم"><Sparkles size={13} className="ai-star" />تحليل الرسم</button>
      {open && createPortal(
        <div className="d7m-modal ee-modal cr-modal" data-shown={shown ? "1" : "0"} role="dialog" aria-label="تحليل الرسم" onClick={() => setOpen(false)} data-role="chart-read">
          <div className="d7m-sheet ee-sheet cr-sheet" onClick={e => e.stopPropagation()}>
            <div className="d7m-head">
              <strong><Sparkles size={15} className="inline-block align-[-2px] me-1 ai-star" />تحليلُ الرسم <span className="cr-sym" dir="ltr">{symbol.replace(".SR", "")}</span></strong>
              <button type="button" className="d7m-btn cr-again" onClick={() => m.mutate()} disabled={m.isPending} aria-label="أعِد التحليل" title="أعِد التحليل"
                data-role="chart-read-again"><RotateCw size={14} className={m.isPending ? "rl-spin" : ""} /></button>
              <button type="button" className="d7m-btn" onClick={() => setOpen(false)} aria-label="إغلاق"><X size={15} /></button>
            </div>
            {m.isPending ? (
              <div className="cr-wait" role="status" data-role="chart-read-wait">
                <span className="cr-wait-t">يقرأ الرسمَ ومؤشّراتِه ومستوياتِه…</span>
                <i /><i /><i />
              </div>
            ) : m.isError || (d && !d.ok) ? (
              <div className="cr-err" role="status" data-role="chart-read-err">
                <p>تعذّر التحليلُ الآن.</p>
                <button type="button" className="btn-primary" onClick={() => m.mutate()}>أعِد المحاولة</button>
              </div>
            ) : r ? (
              <div className="cr-body" data-role="chart-read-body">
                <div className={`cr-head cr-${tone}`}>
                  <span className="cr-bias" data-role="chart-read-bias"><BiasIc b={r.bias} />{r.bias}</span>
                  {r.headline && <p className="cr-headline">{r.headline}</p>}
                </div>
                {r.frames.length > 1 && (
                  <section className="cr-sec">
                    <h4>الأطر</h4>
                    {r.frames.map((f, i) => <p key={i} className="cr-frame"><b className="cr-tf">{f.tf}</b>{f.reading}</p>)}
                  </section>
                )}
                {r.levels.length > 0 && (
                  <section className="cr-sec" data-role="chart-read-levels">
                    <h4>المستويات</h4>
                    <ul className="cr-levels">
                      {r.levels.map((l, i) => (
                        <li key={i} className={"cr-lv " + (l.kind === "مقاومة" ? "neg" : "pos")}>
                          <span className="cr-kind">{l.kind}</span>
                          <b className="cr-px" dir="ltr">{fmt(l.price)}</b>
                          <span className="cr-from">{l.from}</span>
                          {l.note && <span className="cr-note">{l.note}</span>}
                        </li>
                      ))}
                    </ul>
                  </section>
                )}
                {r.indicators.length > 0 && (
                  <section className="cr-sec">
                    <h4>المؤشّرات</h4>
                    {r.indicators.map((x, i) => <p key={i} className="cr-ind"><b dir="ltr">{x.name}</b>{x.reading}</p>)}
                  </section>
                )}
                {(r.buy || r.sell || r.invalid) && (
                  <section className="cr-sec cr-plan" data-role="chart-read-plan">
                    <h4>الخطّة</h4>
                    {r.buy && <p className="cr-p pos"><b>متى الشراء</b>{r.buy}</p>}
                    {r.sell && <p className="cr-p neg"><b>متى البيع</b>{r.sell}</p>}
                    {r.invalid && <p className="cr-p"><b>ما يُبطلها</b>{r.invalid}</p>}
                  </section>
                )}
                {r.risk && <p className="cr-risk"><b>المخاطرة</b>{r.risk}</p>}
              </div>
            ) : null}
          </div>
        </div>, document.body,
      )}
    </>
  );
}
