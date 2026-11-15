/* ══ سلسلةُ عقود الخيارات ══ (‏D747 · بأمر المالك 2026-11-15)
   «أضف الخيارات — أختار عقدي من هنا، اللي بعد أسبوع ولا بعد يومين — تريدنق فيو يدعمه فندعمه». فالسلسلةُ لأيّ سهمٍ أو صندوقٍ
   أمريكيّ: الآجالُ بتواريخها وأيامها الباقية، وعقودُ الشراء (Call) والبيع (Put) بسعر التنفيذ والعرض والطلب وآخر سعرٍ والتغيّر
   والكمّية والعقود المفتوحة والتذبذب الضمنيّ — ما قربُ السعر أوّلاً والكلُّ بضغطة. والضغطُ على عقدٍ يفتح رسمَه، و«+» يضيفه للقائمة. */
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { marketApi } from "../../services/api";
import CompanyLogo from "../common/CompanyLogo";
import { dayMonth, dteLabel, optionTitle, parseOption } from "../../lib/options";

type Row = { contract: string; strike: number; last: number | null; bid: number | null; ask: number | null; pct: number | null;
  volume: number | null; oi: number | null; iv: number | null; itm: boolean };
type Chain = { symbol: string; name?: string; price?: number; expirations: { t: number; date: string; dte: number }[]; expiry: number | null;
  calls: Row[]; puts: Row[] };

const f2 = (v: number | null | undefined) => (v == null || !isFinite(v) ? "—" : v.toFixed(2));
const fi = (v: number | null | undefined) => (v == null ? "—" : v.toLocaleString("en-US"));

export default function OptionChain({ underlying, onPick, onAdd, onClose }: {
  underlying: string; onPick: (contract: string) => void; onAdd?: (contract: string, name: string) => void; onClose: () => void;
}) {
  const [exp, setExp] = useState<number | null>(null);
  const [side, setSide] = useState<"calls" | "puts">("calls");
  const [all, setAll] = useState(false);
  const [shown, setShown] = useState(false);
  useEffect(() => { const id = requestAnimationFrame(() => setShown(true)); return () => cancelAnimationFrame(id); }, []);
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);

  const q = useQuery<Chain | null>({
    queryKey: ["option-chain", underlying, exp],
    queryFn: () => marketApi.optionChain(underlying, exp).then(r => r.data.data ?? null),
    refetchInterval: 60_000,
    placeholderData: prev => prev,
  });
  const c = q.data;
  const cur = exp ?? c?.expiry ?? null;
  const rows = useMemo(() => {
    const list = (c?.[side] || []) as Row[];
    if (all || !c?.price || list.length <= 21) return list;
    const i = list.findIndex(r => r.strike >= (c.price as number));
    const at = i < 0 ? list.length - 1 : i;
    return list.slice(Math.max(0, at - 10), at + 11);
  }, [c, side, all]);
  const atIdx = c?.price ? rows.findIndex(r => r.strike >= (c.price as number)) : -1;

  return (
    <div className="d7m-modal oc-modal" data-shown={shown ? "1" : "0"} role="dialog" aria-label={`عقود خيارات ${underlying}`} onClick={onClose} data-role="oc">
      <div className="d7m-sheet oc-sheet" onClick={e => e.stopPropagation()}>
        <div className="d7m-head">
          <CompanyLogo symbol={underlying} size={26} />
          <strong className="oc-title"><span dir="ltr">{underlying}</span> <span className="oc-sub">عقود الخيارات</span></strong>
          {c?.price != null && <span className="oc-px" dir="ltr">{f2(c.price)}</span>}
          <span className="oc-late">أسعارٌ متأخّرة 15 دقيقة</span>
          <button type="button" className="d7m-btn" onClick={onClose} aria-label="إغلاق"><X size={15} /></button>
        </div>

        {!!c?.expirations?.length && (
          <div className="oc-exps" role="group" aria-label="الآجال">
            {c.expirations.map(e => (
              <button key={e.t} type="button" className={"seg-btn chip oc-exp" + (cur === e.t ? " on" : "")} onClick={() => setExp(e.t)} data-role="oc-exp">
                <b>{dayMonth(e.date)}</b><small>{dteLabel(e.dte)}</small>
              </button>
            ))}
          </div>
        )}

        <div className="oc-bar">
          <div className="seg inline-flex" role="tablist" aria-label="نوع العقد">
            {([["calls", "شراء · Call"], ["puts", "بيع · Put"]] as const).map(([k, t]) => (
              <button key={k} type="button" role="tab" aria-selected={side === k} className={"seg-btn chip" + (side === k ? " on" : "")}
                onClick={() => setSide(k)} data-role="oc-side">{t}</button>
            ))}
          </div>
          <button type="button" className="seg-btn chip" onClick={() => setAll(a => !a)} data-role="oc-range">{all ? "قربَ السعر" : "كلُّ الأسعار"}</button>
        </div>

        {q.isPending && !c ? <div className="oc-empty">…</div> : !c || !rows.length ? (
          <div className="oc-empty" data-role="oc-empty">لا عقودَ خياراتٍ لهذا الرمز.</div>
        ) : (
          <div className="oc-table" data-role="oc-table" style={{ opacity: q.isFetching ? 0.6 : 1 }}>
            <div className="oc-tr oc-th">
              <div className="oc-cols"><span>التنفيذ</span><span>آخر</span><span>العرض</span><span>الطلب</span><span>التغيّر %</span><span>الكمية</span><span>المفتوحة</span><span>التذبذب %</span></div>
              <span />
            </div>
            {rows.map((r, i) => {
              const o = parseOption(r.contract);
              const name = o ? `${optionTitle(o)} · ${dayMonth(o.expiry)}` : r.contract;
              return (
                <div key={r.contract} className={"oc-tr" + (r.itm ? " itm" : "") + (i === atIdx ? " atm" : "")}>
                  <button type="button" className="oc-pick oc-cols" onClick={() => onPick(r.contract)} data-role="oc-row" title={`افتح رسم ${name}`}>
                    <b dir="ltr">{f2(r.strike)}</b><span dir="ltr">{f2(r.last)}</span><span dir="ltr">{f2(r.bid)}</span><span dir="ltr">{f2(r.ask)}</span>
                    <span dir="ltr" className={r.pct == null ? "" : r.pct >= 0 ? "pos" : "neg"}>{r.pct == null ? "—" : (r.pct >= 0 ? "+" : "") + r.pct.toFixed(1)}</span>
                    <span dir="ltr">{fi(r.volume)}</span><span dir="ltr">{fi(r.oi)}</span><span dir="ltr">{r.iv == null ? "—" : r.iv.toFixed(1)}</span>
                  </button>
                  {onAdd ? (
                    <button type="button" className="btn-ghost troom-icon" onClick={() => onAdd(r.contract, name)} aria-label={`أضف ${name} إلى القائمة`}
                      title="أضف إلى القائمة" data-role="oc-add"><Plus size={14} /></button>
                  ) : <span />}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
