/* ══ تذكرةُ الأمر ══ (‏D771 · ‏D777 بأمر المالك 2026-11-20)
   ‏D771: «زرُّ تنفيذ — أنفّذه بالسعر الذي أحدّده، وأحدّد جميعَ الأوامر: جنيُ ربحٍ 30٪ 40٪، عند أمرٍ محدّدٍ يبيع أو يشتري».
   ‏D777: «محاكاةُ المحفظة مثل إنتراكتف بروكرز — سعرُ الشراء بأمرٍ محدّد، وسعرُ البيع بأمرٍ محدّد، والوقفُ المطارِد… بالعربي عشان نتعلّم عليها».
   فالتذكرةُ كتذكرة الوسيط: الكمّية · نوعُ الأمر (سوق · محدَّد · إيقاف · إيقافٌ محدَّد) · مدّتُه (اليوم · حتى الإلغاء) · الأمرُ المرفق (لا شيء ·
   جنيُ ربح · وقفُ خسارة · وقفٌ مطارِد · براكت) بأسعارٍ يكتبها المالكُ أو يختارها بنسبةٍ سريعة — ولكلّ خيارٍ سطرٌ يشرحه. */
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Minus, Plus } from "lucide-react";
import { marketApi } from "../../services/api";
import { usd, px } from "./saqr";

const Num = ({ v, className }: { v: string; className?: string }) => <bdi dir="ltr" className={"tabular-nums " + (className || "")}>{v}</bdi>;
const err = (e: any) => e?.response?.data?.detail || "تعذّر التنفيذ";
export const TP_CHOICES: [number | null, string][] = [[30, "+30%"], [40, "+40%"], [50, "+50%"], [100, "+100%"], [null, "بلا"]];
export const SL_CHOICES: [number | null, string][] = [[25, "−25%"], [40, "−40%"], [50, "−50%"], [null, "بلا"]];
const TRAIL_CHOICES: [number | null, string][] = [[10, "10%"], [15, "15%"], [20, "20%"], [30, "30%"]];

export function PctChips({ value, set, opts, role }: { value: number | null; set: (v: number | null) => void; opts: [number | null, string][]; role: string }) {
  return (
    <span className="seg inline-flex" role="group" data-role={role}>
      {opts.map(([v, t]) => (
        <button key={t} type="button" className={"seg-btn chip" + (value === v ? " on" : "")} aria-pressed={value === v} onClick={() => set(v)} data-v={v ?? "none"}>
          <Num v={t} /></button>
      ))}
    </span>
  );
}

/** خياراتٌ بنصٍّ عربيّ وسطرٍ يشرح المختار — لنتعلّم عليها */
function Choice<T extends string>({ value, set, opts, role, label }: { value: T; set: (v: T) => void; opts: [T, string, string][]; role: string; label: string }) {
  const hint = opts.find(o => o[0] === value)?.[2];
  return (
    <div className="of-field">
      <small>{label}</small>
      <span className="seg inline-flex of-seg" role="group" aria-label={label} data-role={role}>
        {opts.map(([v, t]) => (
          <button key={v} type="button" className={"seg-btn chip" + (value === v ? " on" : "")} aria-pressed={value === v} onClick={() => set(v)} data-v={v}>{t}</button>
        ))}
      </span>
      {hint && <span className="of-hint" data-role={`${role}-hint`}>{hint}</span>}
    </div>
  );
}

type OT = "mkt" | "lmt" | "stp" | "stp_lmt";
type TIF = "day" | "gtc";
export type Att = "none" | "tp" | "sl" | "trail" | "bracket";
const OT_OPTS: [OT, string, string][] = [
  ["mkt", "سوق", "يُنفَّذ فوراً بسعر العرض الآن — والسوقُ مغلقٌ: عند أوّل عرضٍ في الجلسة."],
  ["lmt", "محدَّد", "يُنفَّذ بسعرك أو أقلّ — وإلا ينتظر حتى يبلغه العرض."],
  ["stp", "إيقاف", "ينتظر حتى يرتفع العرضُ إلى سعر التفعيل ثمّ يشتري بالسوق — للدخول مع الاندفاع."],
  ["stp_lmt", "إيقافٌ محدَّد", "متى بلغ العرضُ سعرَ التفعيل صار أمراً محدَّداً بسعرك — فلا تدفع أكثر منه."],
];
const TIF_OPTS: [TIF, string, string][] = [
  ["day", "اليوم", "يُلغى تلقائياً إن لم يُنفَّذ في جلسته."],
  ["gtc", "حتى الإلغاء", "يبقى قائماً حتى يُنفَّذ أو تلغيه أنت."],
];
export const ATT_OPTS: [Att, string, string][] = [
  ["none", "لا شيء", "بلا أمر بيعٍ مرفق — تبيع أنت متى شئت."],
  ["tp", "جنيُ ربح", "أمرُ بيعٍ محدَّدٌ عند سعرك: يبيع متى بلغه الطلب."],
  ["sl", "وقفُ خسارة", "يبيع بالسوق إن هبط الطلبُ إلى سعر الوقف — يحدّ الخسارة."],
  ["trail", "وقفٌ مطارِد", "يتبع أعلى سعرٍ بلغه العقد ويبيع إن هبط عنه بالنسبة — يحمي الربح."],
  ["bracket", "براكت", "جنيٌ ووقفٌ معاً — أيُّهما بلغ أوّلاً باع وأُلغي الآخر."],
];
const hasTp = (a: Att) => a === "tp" || a === "bracket";
const hasSl = (a: Att) => a === "sl" || a === "bracket";
const f2 = (v: number) => (Math.round(v * 100) / 100).toFixed(2);

export type Exit = { att: Att; tp: string; tpPct: number | null; sl: string; slPct: number | null; trail: number | null };
export const exitInit = (ref: number | null, att: Att = "bracket", tpPct = 40, slPct = 40): Exit =>
  ({ att, tp: ref ? f2(ref * (1 + tpPct / 100)) : "", tpPct, sl: ref ? f2(ref * (1 - slPct / 100)) : "", slPct, trail: 15 });
/** أوامرُ البيع المرفقة بأسعارها (أو نسبةِ المطارِد) — ما ليس في المرفق المختار لا يُرسَل */
export const exitPayload = (ex: Exit) => ({
  tp_px: hasTp(ex.att) && Number(ex.tp) > 0 ? Number(ex.tp) : null,
  sl_px: hasSl(ex.att) && Number(ex.sl) > 0 ? Number(ex.sl) : null,
  trail_pct: ex.att === "trail" ? ex.trail : null,
});

/** الأمرُ المرفق: النوعُ وأسعارُه — مشتركٌ بين تذكرة الشراء وأوامر المركز القائم */
export function ExitFields({ ex, set, base, role }: { ex: Exit; set: (e: Exit) => void; base: number | null; role: string }) {
  const ref = base;            // «ref» اسمٌ محجوزٌ في React فلا يُمرَّر خاصيّة
  const tpChip = (v: number | null) => {
    if (v == null) return set({ ...ex, att: ex.att === "bracket" ? "sl" : "none", tpPct: null });
    set({ ...ex, att: ex.att === "sl" ? "bracket" : ex.att === "bracket" ? "bracket" : "tp", tpPct: v, tp: ref ? f2(ref * (1 + v / 100)) : ex.tp });
  };
  const slChip = (v: number | null) => {
    if (v == null) return set({ ...ex, att: ex.att === "bracket" ? "tp" : "none", slPct: null });
    set({ ...ex, att: ex.att === "tp" ? "bracket" : ex.att === "bracket" ? "bracket" : "sl", slPct: v, sl: ref ? f2(ref * (1 - v / 100)) : ex.sl });
  };
  const pickAtt = (a: Att) => set({ ...ex, att: a,
    tp: hasTp(a) && !ex.tp && ref ? f2(ref * 1.4) : ex.tp, sl: hasSl(a) && !ex.sl && ref ? f2(ref * 0.6) : ex.sl });
  return (
    <>
      <Choice<Att> value={ex.att} set={pickAtt} opts={ATT_OPTS} role={`${role}-att`} label="الأمرُ المرفق (البيع)" />
      <div className={"of-x" + (hasTp(ex.att) ? " open" : "")} aria-hidden={!hasTp(ex.att)}>
        <div className="of-row">
          <label><small>سعرُ جني الربح</small><input className="sp-in" type="number" min={0.01} step={0.01} dir="ltr" value={ex.tp} tabIndex={hasTp(ex.att) ? 0 : -1}
            onChange={e => set({ ...ex, tp: e.target.value, tpPct: null })} data-role={`${role}-tp-px`} /></label>
          <PctChips value={hasTp(ex.att) ? ex.tpPct : null} set={tpChip} opts={TP_CHOICES} role={`${role}-tp`} />
        </div>
      </div>
      <div className={"of-x" + (hasSl(ex.att) ? " open" : "")} aria-hidden={!hasSl(ex.att)}>
        <div className="of-row">
          <label><small>سعرُ الوقف</small><input className="sp-in" type="number" min={0.01} step={0.01} dir="ltr" value={ex.sl} tabIndex={hasSl(ex.att) ? 0 : -1}
            onChange={e => set({ ...ex, sl: e.target.value, slPct: null })} data-role={`${role}-sl-px`} /></label>
          <PctChips value={hasSl(ex.att) ? ex.slPct : null} set={slChip} opts={SL_CHOICES} role={`${role}-sl`} />
        </div>
      </div>
      <div className={"of-x" + (ex.att === "trail" ? " open" : "")} aria-hidden={ex.att !== "trail"}>
        <div className="of-row">
          <label><small>يبيع إن هبط عن القمّة بـ</small><PctChips value={ex.trail} set={v => set({ ...ex, trail: v })} opts={TRAIL_CHOICES} role={`${role}-trail`} /></label>
        </div>
      </div>
    </>
  );
}

export default function OrderForm({ contract, ask, onDone }: { contract: string; ask: number | null; onDone?: (msg: string) => void }) {
  const qc = useQueryClient();
  const [qty, setQty] = useState(1);
  const [ot, setOt] = useState<OT>("lmt");                      // كالوسيط: «محدَّد» أوّلاً بسعر العرض
  const [limit, setLimit] = useState(ask ? ask.toFixed(2) : "");
  const [stop, setStop] = useState(ask ? f2(ask * 1.05) : "");
  const [tif, setTif] = useState<TIF>("gtc");
  const [ex, setEx] = useState<Exit>(() => exitInit(ask));
  const [msg, setMsg] = useState<string | null>(null);
  const L = Number(limit) > 0 ? Number(limit) : null, S = Number(stop) > 0 ? Number(stop) : null;
  const ref = (ot === "lmt" || ot === "stp_lmt" ? L : ot === "stp" ? S : ask) ?? ask;
  const now = !!(ask && (ot === "mkt" || (ot === "lmt" && L != null && L >= ask)));
  const onOt = (v: OT) => { setOt(v); setMsg(null); if ((v === "stp" || v === "stp_lmt") && !stop && ask) setStop(f2(ask * 1.05)); };
  const pay = exitPayload(ex);
  const send = useMutation({
    mutationFn: () => marketApi.saqrOrder({ contract, qty, otype: ot, limit: ot === "lmt" || ot === "stp_lmt" ? L : null, stop: ot === "stp" || ot === "stp_lmt" ? S : null,
      tif, ...pay }),
    onSuccess: r => {
      const v = r.data.data;
      qc.setQueryData(["saqr", "us"], v);
      const pending = (v?.orders || []).some((o: any) => o.contract === contract);
      const m = pending ? "سُجّل أمرٌ معلّق — يُنفَّذ متى استوفى العرضُ شرطَه، وتجده في المحفظة." : "نُفّذ — المركزُ في المحفظة بأوامره المرفقة.";
      setMsg(m); onDone?.(m);
    },
    onError: (e: any) => setMsg(err(e)),
  });
  const loss = pay.sl_px && ref ? (ref - pay.sl_px) * 100 * qty : pay.trail_pct && ref ? ref * pay.trail_pct / 100 * 100 * qty : null;
  return (
    <form className="of" onSubmit={e => { e.preventDefault(); send.mutate(); }} data-role="order-form">
      <div className="of-row of-q">
        <span className="of-field"><small>الكمّية (عقود)</small>
          <span className="of-step">
            <button type="button" className="btn-ghost sp-btn" onClick={() => setQty(n => Math.max(1, n - 1))} aria-label="أنقص عقداً" data-role="of-minus"><Minus size={14} /></button>
            <input className="sp-in" type="number" min={1} step={1} dir="ltr" value={qty} aria-label="الكمّية"
              onChange={e => setQty(Math.max(1, Math.floor(Number(e.target.value) || 1)))} data-role="of-qty" />
            <button type="button" className="btn-ghost sp-btn" onClick={() => setQty(n => n + 1)} aria-label="زد عقداً" data-role="of-plus"><Plus size={14} /></button>
          </span>
        </span>
        <span className="of-hint">{ask ? <>العرضُ الآن <Num v={px(ask)} /></> : "لا عرضَ حيٌّ الآن — يُعلَّق الأمرُ للجلسة"}</span>
      </div>
      <Choice<OT> value={ot} set={onOt} opts={OT_OPTS} role="of-type" label="نوعُ الأمر" />
      <div className={"of-x" + (ot === "lmt" || ot === "stp_lmt" ? " open" : "")} aria-hidden={!(ot === "lmt" || ot === "stp_lmt")}>
        <div className="of-row"><label><small>سعرُ الحدّ (أعلى ما تدفعه)</small><input className="sp-in" type="number" min={0.01} step={0.01} dir="ltr" value={limit}
          placeholder={px(ask)} tabIndex={ot === "lmt" || ot === "stp_lmt" ? 0 : -1} onChange={e => setLimit(e.target.value)} data-role="of-limit" /></label></div>
      </div>
      <div className={"of-x" + (ot === "stp" || ot === "stp_lmt" ? " open" : "")} aria-hidden={!(ot === "stp" || ot === "stp_lmt")}>
        <div className="of-row"><label><small>سعرُ التفعيل</small><input className="sp-in" type="number" min={0.01} step={0.01} dir="ltr" value={stop}
          tabIndex={ot === "stp" || ot === "stp_lmt" ? 0 : -1} onChange={e => setStop(e.target.value)} data-role="of-stop" /></label></div>
      </div>
      <Choice<TIF> value={tif} set={setTif} opts={TIF_OPTS} role="of-tif" label="مدّةُ الأمر" />
      <ExitFields ex={ex} set={setEx} base={ref} role="of" />
      {ref ? (
        <p className="of-sum" data-role="of-sum">
          الكلفةُ نحو <b><Num v={usd(ref * 100 * qty + 0.65 * qty)} /></b>
          {pay.tp_px ? <> · يبيع عند <b className="pos"><Num v={px(pay.tp_px)} /></b></> : null}
          {pay.sl_px ? <> · يوقف عند <b className="neg"><Num v={px(pay.sl_px)} /></b></> : null}
          {pay.trail_pct ? <> · يطارد القمّةَ بـ<b className="neg"><Num v={`${pay.trail_pct}%`} /></b></> : null}
          {loss != null ? <> · أقصى خسارةٍ نحو <b className="neg"><Num v={usd(loss)} /></b></> : <> · أقصى الخسارة كاملُ الكلفة</>}
        </p>
      ) : null}
      <div className="of-row">
        <button type="submit" className="btn-primary sp-btn" disabled={send.isPending} data-role="of-send"><Check size={14} /> {send.isPending ? "يُرسل…" : now ? "نفّذ الآن" : "سجّل الأمر"}</button>
        {msg && <span className={send.isError ? "sp-err" : "sq-ok"} role="status" data-role="of-msg">{msg}</span>}
      </div>
    </form>
  );
}
