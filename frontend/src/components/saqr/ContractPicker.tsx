/* ══ اختر عقداً بنفسك ══ (‏D769 بأمر المالك 2026-11-19)
   «خلّ فيه خياراً أنّي أختار عقداً بنفسي، ويكون فيه تحليلُ السترايك الذي أختاره — مبسّطةً بسيطةً واضحة». فالخطواتُ بترتيبها: السهمُ والاتجاه،
   ثمّ الأجل، ثمّ السترايك (التسعةُ الأقربُ إلى سعر السهم)، ثمّ تحليلٌ مختصرٌ من محلّل العقود نفسِه (الحكم · الكلفة · التعادل · احتمالُ الربح ·
   التآكل)، فالشراءُ بسعر العرض الحيّ — ويديره صقر (وقفٌ وجنيٌ ووقفٌ متحرّك) إن شاء المالك، أو يبقى له يُغلقه متى شاء. */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, ShoppingCart } from "lucide-react";
import { marketApi } from "../../services/api";
import CheckBox from "../common/CheckBox";
import { dayMonth } from "../../lib/options";
import { usd, spct, px } from "./saqr";

const Num = ({ v, className }: { v: string; className?: string }) => <bdi dir="ltr" className={"tabular-nums " + (className || "")}>{v}</bdi>;
type Exp = { t: number; date: string; dte: number };
type G = { delta: number; pop: number; be: number; theta: number; px: number; iv: number } | null;
type Row = { contract: string; strike: number; bid: number | null; ask: number | null; g?: G };
const VERDICT_CLS: Record<string, string> = { ok: "s-open", warn: "s-pre", no: "s-closed" };
const err = (e: any) => e?.response?.data?.detail || "تعذّر التنفيذ";

export default function ContractPicker({ budget, onDone }: { budget?: number | null; onDone: () => void }) {
  const qc = useQueryClient();
  const [sym, setSym] = useState("");
  const [q, setQ] = useState("");
  const [side, setSide] = useState<"call" | "put">("call");
  const [t, setT] = useState<number | null>(null);
  const [k, setK] = useState<string | null>(null);
  const [qty, setQty] = useState("1");
  const [managed, setManaged] = useState(true);

  const base = useQuery({ queryKey: ["pick-chain", q], queryFn: async () => (await marketApi.optionChain(q)).data.data, enabled: !!q, staleTime: 60_000, retry: 0 });
  const exps: Exp[] = ((base.data?.expirations || []) as Exp[]).filter(e => e.dte >= 3 && e.dte <= 400).slice(0, 12);
  const ch = useQuery({ queryKey: ["pick-chain", q, t], queryFn: async () => (await marketApi.optionChain(q, t)).data.data, enabled: !!q && t != null,
    staleTime: 30_000, retry: 0 });
  const S: number | undefined = ch.data?.price ?? base.data?.price;
  const rows: Row[] = ch.data ? ((side === "call" ? ch.data.calls : ch.data.puts) || []) : [];
  const near = S ? rows.filter(r => r.strike).sort((a, b) => Math.abs(a.strike - S) - Math.abs(b.strike - S)).slice(0, 9).sort((a, b) => a.strike - b.strike) : [];
  const row = rows.find(r => r.contract === k);
  const ask = row ? (row.ask || row.g?.px || null) : null;
  const adv = useQuery({ queryKey: ["pick-adv", k, budget], queryFn: async () => (await marketApi.optionAdvice({ symbol: q, contract: k!, ...(budget && budget >= 10 ? { budget } : {}) })).data.data,
    enabled: !!k, staleTime: 30_000, retry: 0 });
  const c = adv.data?.contract;
  const n = Math.max(1, Math.floor(Number(qty) || 1));
  const buy = useMutation({
    mutationFn: () => marketApi.saqrOpen(k!, n, null, "us", managed),
    onSuccess: r => { qc.setQueryData(["saqr", "us"], r.data.data); onDone(); },
  });
  const go = (e: React.FormEvent) => { e.preventDefault(); const v = sym.trim().toUpperCase(); if (v) { setQ(v); setT(null); setK(null); } };
  const pickSide = (v: "call" | "put") => { setSide(v); setK(null); };

  return (
    <div className="pk" data-role="sp-picker">
      <form className="pk-row" onSubmit={go}>
        <label><small>السهم</small><input className="sp-in" dir="ltr" placeholder="AAPL" value={sym} onChange={e => setSym(e.target.value)} data-role="pk-sym" aria-label="رمزُ السهم" /></label>
        <span className="seg inline-flex" role="group" aria-label="الاتجاه" data-role="pk-side">
          <button type="button" className={"seg-btn chip" + (side === "call" ? " on" : "")} onClick={() => pickSide("call")} data-v="call">شراء Call</button>
          <button type="button" className={"seg-btn chip" + (side === "put" ? " on" : "")} onClick={() => pickSide("put")} data-v="put">بيع Put</button>
        </span>
        <button type="submit" className="btn-primary sp-btn" disabled={!sym.trim()} data-role="pk-go"><Search size={14} /> اعرض العقود</button>
      </form>

      {q && base.isLoading && <p className="sp-empty">يقرأ عقودَ <Num v={q} />…</p>}
      {q && !base.isLoading && !exps.length && <p className="sp-empty" data-role="pk-none">لا عقودَ خياراتٍ لهذا الرمز.</p>}

      {exps.length > 0 && (
        <div className="pk-step">
          <small>الأجل {S != null && <>· السهمُ الآن <Num v={px(S)} /></>}</small>
          <div className="pk-chips">
            {exps.map(e => (
              <button key={e.t} type="button" className={"seg-btn chip" + (t === e.t ? " on" : "")} onClick={() => { setT(e.t); setK(null); }} data-role="pk-exp">
                {dayMonth(e.date)} · <Num v={`${e.dte}`} /> يوماً
              </button>
            ))}
          </div>
        </div>
      )}

      {t != null && (
        <div className="pk-step">
          <small>السترايك {side === "call" ? "(شراء)" : "(بيع)"} — وتحته كلفةُ العقد الواحد (مئةُ سهم)</small>
          {ch.isLoading ? <p className="sp-empty">يقرأ السلسلة…</p> : !near.length ? <p className="sp-empty">لا عقودَ في هذا الأجل.</p> : (
            <div className="pk-strikes">
              {near.map(r => {
                const a = r.ask || r.g?.px || null;
                const itm = S != null && (side === "call" ? r.strike < S : r.strike > S);
                return (
                  <button key={r.contract} type="button" className={"pk-k" + (k === r.contract ? " on" : "") + (itm ? " itm" : "")} onClick={() => setK(r.contract)}
                    data-role="pk-strike" aria-pressed={k === r.contract}>
                    <b><Num v={`${r.strike}`} /></b>
                    <span><Num v={a ? usd(a * 100, 0) : "—"} /></span>
                    <small>دلتا <Num v={r.g ? r.g.delta.toFixed(2) : "—"} /></small>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {k && (
        <div className="pk-an" data-role="pk-analysis">
          {adv.isLoading ? <p className="sp-empty">يحلّل العقد…</p> : !c ? <p className="sp-err">{adv.data?.error || "تعذّر تحليلُ العقد."}</p> : (
            <>
              <div className="pk-head">
                <span className={"sq-pill " + (VERDICT_CLS[c.verdict] || "")} data-role="pk-verdict">{c.verdict_ar}</span>
                <b><Num v={`${q} ${c.strike} ${c.type === "call" ? "Call" : "Put"}`} /> · {dayMonth(c.expiry)}</b>
              </div>
              <div className="pk-facts">
                <span><small>الكلفة</small><b><Num v={usd(c.cost * n, 0)} /></b>{n > 1 && <em><Num v={`${n} × ${usd(c.cost, 0)}`} /></em>}</span>
                <span><small>التعادل عند الانتهاء</small><b><Num v={px(c.g?.be)} /></b><em>يحتاج السهم <Num v={spct(c.need_pct)} /></em></span>
                <span><small>احتمالُ الربح</small><b><Num v={c.g ? `${Math.round(c.g.pop)}%` : "—"} /></b></span>
                <span><small>التآكلُ اليوميّ</small><b className="neg"><Num v={c.g ? usd(Math.abs(c.g.theta)) : "—"} /></b><em>للعقد</em></span>
              </div>
              <ul className="pk-why">
                {(c.cons || []).slice(0, 2).map((w: string, i: number) => <li key={"c" + i} className="con">{w}</li>)}
                {(c.pros || []).slice(0, c.cons?.length ? 1 : 2).map((w: string, i: number) => <li key={"p" + i} className="pro">{w}</li>)}
              </ul>
              <div className="pk-buy">
                <label><small>العقود</small><input className="sp-in" type="number" min={1} step={1} dir="ltr" value={qty} onChange={e => setQty(e.target.value)} data-role="pk-qty" /></label>
                <span data-role="pk-managed"><CheckBox checked={managed} onChange={setManaged} className="pk-chk" label="يديره صقر — وقفٌ وجنيٌ ووقفٌ متحرّك" /></span>
                <button type="button" className={(c.verdict === "no" ? "btn-ghost" : "btn-primary") + " sp-btn"} onClick={() => buy.mutate()} disabled={buy.isPending || !ask}
                  data-role="pk-buy"><ShoppingCart size={14} /> {buy.isPending ? "يشتري…" : <>اشترِ بسعر العرض <Num v={px(ask)} /></>}{c.verdict === "no" ? " رغم التحفّظ" : ""}</button>
                {buy.isError && <span className="sp-err">{err(buy.error)}</span>}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
