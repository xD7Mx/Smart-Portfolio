/* ══ أمرُ المالك ══ (‏D771 بأمر المالك 2026-11-20)
   «زرُّ تنفيذ — أنفّذه وأختار بالسعر الذي أحدّده، وأحدّد جميعَ الأوامر: جنيُ ربحٍ 30٪ 40٪، عند أمرٍ محدّدٍ يبيع أو عند أمرٍ محدّدٍ يشتري —
   عشان تكون محاكاةُ المحفظة كاملة». فالأمرُ: العقود، وسعرُ الشراء (عند العرض أو فوقه يُنفَّذ الآن، ودونه أمرٌ معلّقٌ حتى يبلغه العرض)،
   وجنيُ الربح ووقفُ الخسارة بالنسبة من سعر الشراء — يبيعهما صقر عندهما. */
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { marketApi } from "../../services/api";
import { usd, px } from "./saqr";

const Num = ({ v, className }: { v: string; className?: string }) => <bdi dir="ltr" className={"tabular-nums " + (className || "")}>{v}</bdi>;
const err = (e: any) => e?.response?.data?.detail || "تعذّر التنفيذ";
export const TP_CHOICES: [number | null, string][] = [[30, "+30%"], [40, "+40%"], [50, "+50%"], [100, "+100%"], [null, "بلا"]];
export const SL_CHOICES: [number | null, string][] = [[25, "−25%"], [40, "−40%"], [50, "−50%"], [null, "بلا"]];

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

export default function OrderForm({ contract, ask, onDone }: { contract: string; ask: number | null; onDone?: (msg: string) => void }) {
  const qc = useQueryClient();
  const [qty, setQty] = useState("1");
  const [limit, setLimit] = useState(ask ? ask.toFixed(2) : "");
  const [tp, setTp] = useState<number | null>(40);
  const [sl, setSl] = useState<number | null>(40);
  const [msg, setMsg] = useState<string | null>(null);
  const n = Math.max(1, Math.floor(Number(qty) || 1));
  const L = Number(limit) > 0 ? Number(limit) : null;
  const ref = L ?? ask;
  const now = !!(ask && (L == null || L >= ask));
  const send = useMutation({
    mutationFn: () => marketApi.saqrOrder({ contract, qty: n, limit: L, tp_pct: tp, sl_pct: sl }),
    onSuccess: r => {
      const v = r.data.data;
      qc.setQueryData(["saqr", "us"], v);
      const pending = (v?.orders || []).some((o: any) => o.contract === contract);
      const m = pending ? "سُجّل أمرٌ معلّق — يُنفَّذ في الجلسة متى بلغ العرضُ سعرَك، وتجده في المحفظة." : "نُفّذ — المركزُ في المحفظة بأمري الجني والوقف.";
      setMsg(m); onDone?.(m);
    },
    onError: (e: any) => setMsg(err(e)),
  });
  return (
    <form className="of" onSubmit={e => { e.preventDefault(); send.mutate(); }} data-role="order-form">
      <div className="of-row">
        <label><small>العقود</small><input className="sp-in" type="number" min={1} step={1} dir="ltr" value={qty} onChange={e => setQty(e.target.value)} data-role="of-qty" /></label>
        <label><small>سعرُ الشراء</small><input className="sp-in" type="number" min={0.01} step={0.01} dir="ltr" value={limit} placeholder={px(ask)}
          onChange={e => setLimit(e.target.value)} data-role="of-limit" /></label>
        <span className="of-hint">{ask ? <>العرضُ الآن <Num v={px(ask)} /> — {now ? "يُنفَّذ الآن" : "دونه: أمرٌ معلّقٌ حتى يبلغه العرض"}</> : "لا عرضَ حيٌّ الآن — أمرٌ معلّقٌ للجلسة"}</span>
      </div>
      <div className="of-row">
        <label><small>جنيُ الربح</small><PctChips value={tp} set={setTp} opts={TP_CHOICES} role="of-tp" /></label>
        <label><small>وقفُ الخسارة</small><PctChips value={sl} set={setSl} opts={SL_CHOICES} role="of-sl" /></label>
      </div>
      {ref ? (
        <p className="of-sum" data-role="of-sum">
          الكلفةُ نحو <b><Num v={usd(ref * 100 * n + 0.65 * n)} /></b>
          {tp ? <> · يبيع عند <b className="pos"><Num v={px(ref * (1 + tp / 100))} /></b></> : " · بلا أمر جني"}
          {sl ? <> · يوقف عند <b className="neg"><Num v={px(ref * (1 - sl / 100))} /></b></> : " · بلا وقف"}
        </p>
      ) : null}
      <div className="of-row">
        <button type="submit" className="btn-primary sp-btn" disabled={send.isPending} data-role="of-send"><Check size={14} /> {send.isPending ? "يُرسل…" : now ? "نفّذ الآن" : "سجّل الأمر"}</button>
        {msg && <span className={send.isError ? "sp-err" : "sq-ok"} role="status" data-role="of-msg">{msg}</span>}
      </div>
    </form>
  );
}
