/* ══ سلسلةُ عقود الخيارات — بطريقة «إنتراكتف بروكرز» ══ (‏D747 · ‏D761 بأمر المالك 2026-11-17)
   «أبغاها مثل إنتراكتف بروكر — بوريك صورة — تعرف طريقتهم في وضع العقود بشكلٍ مرتّب»: الشراءُ (Call) يساراً وسعرُ التنفيذ في الوسط
   والبيعُ (Put) يميناً، ولكلّ عقدٍ طلبُه وعرضُه وآخرُ سعره وتحتها الدلتا والتذبذبُ والتغيّر، والسعرُ الحاليُّ شارةٌ بين سعرَي التنفيذ،
   والعقودُ في النقود مظلّلة؛ وفي الرأس حالةُ السوق وتذبذبُ النقود والحركةُ المتوقّعة ونسبةُ البيع للشراء وألمُ الحدّ الأقصى — والجدولُ
   يتجدّد وحده والسوقُ في جلسة. و«تحليلٌ ذكيّ» يقرأ اليونانيات والمسارَ والأخبارَ والأحداثَ ويقول الأنسبَ لميزانيتك أو يمتنع،
   والضغطُ على عقدٍ يفتح بطاقتَه: يونانياتُه كاملةً وحكمُ التحليل عليه، ورسمُه، وإضافتُه للقائمة. */
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, X, Sparkles, LineChart, RefreshCw, ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";
import { marketApi } from "../../services/api";
import CompanyLogo from "../common/CompanyLogo";
import { dayMonth, dteLabel, optionTitle, parseOption } from "../../lib/options";
import { SessionBadge, useLive } from "../chart/LiveQuote";
import EconEvents from "./EconEvents";

type G = { iv: number; delta: number; gamma: number; theta: number; vega: number; itm: number; pop: number; px: number; src: string; spread: number | null; be: number };
type Row = { contract: string; strike: number; last: number | null; bid: number | null; ask: number | null; pct: number | null;
  volume: number | null; oi: number | null; iv: number | null; itm: boolean; g?: G | null; sbid?: number; sask?: number; sat?: string };
type Stats = { atm_iv: number | null; move: number | null; move_pct: number | null; pcr_vol: number | null; pcr_oi: number | null; max_pain: number | null;
  vol: { call: number; put: number }; oi: { call: number; put: number } };
type Chain = { symbol: string; name?: string; price?: number; expirations: { t: number; date: string; dte: number }[]; expiry: number | null;
  calls: Row[]; puts: Row[]; stats?: Stats; session?: any };
type Card = { contract: string; type: "call" | "put"; strike: number; expiry: string; dte: number; cost: number; px_src?: string; g: G; oi: number | null;
  volume: number | null; verdict: "ok" | "warn" | "no"; verdict_ar: string; pros: string[]; cons: string[]; need_pct: number | null };

const f2 = (v: number | null | undefined) => (v == null || !isFinite(v) ? "—" : v.toFixed(2));
const fk = (v: number | null | undefined) => (v == null ? "—" : v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e4 ? `${(v / 1e3).toFixed(0)}K` : v.toLocaleString("en-US"));
const sg = (v: number, d = 1) => (v >= 0 ? "+" : "") + v.toFixed(d);
const usd = (v: number, d = 2) => `${v < 0 ? "-" : ""}$${Math.abs(v).toFixed(d)}`;
const lsGet = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const lsSet = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* */ } };
const VIcon = ({ v }: { v: Card["verdict"] }) => (v === "ok" ? <ShieldCheck size={13} /> : v === "warn" ? <ShieldAlert size={13} /> : <ShieldX size={13} />);
const ACTIVE = new Set(["pre", "open", "post"]);

export default function OptionChain({ underlying, onPick, onAdd, onClose }: {
  underlying: string; onPick: (contract: string) => void; onAdd?: (contract: string, name: string) => void; onClose: () => void;
}) {
  const [exp, setExp] = useState<number | null>(null);
  const [all, setAll] = useState(false);
  const [shown, setShown] = useState(false);
  const [sel, setSel] = useState<{ row: Row; call: boolean } | null>(null);
  const [smart, setSmart] = useState(false);
  const [budget, setBudget] = useState<string>(() => lsGet("sp_oc_budget") || "");
  const [ask, setAsk] = useState<{ b: number | null; n: number } | null>(null);
  useEffect(() => { const id = requestAnimationFrame(() => setShown(true)); return () => cancelAnimationFrame(id); }, []);
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") { if (sel) setSel(null); else onClose(); } };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose, sel]);

  const { data: live } = useLive(underlying);
  const active = ACTIVE.has(live?.session?.state || "");
  const q = useQuery<Chain | null>({
    queryKey: ["option-chain", underlying, exp],
    queryFn: () => marketApi.optionChain(underlying, exp).then(r => r.data.data ?? null),
    refetchInterval: () => (document.visibilityState === "hidden" ? false : active ? 15_000 : 60_000),
    placeholderData: prev => prev,
  });
  const c = q.data;
  const cur = exp ?? c?.expiry ?? null;
  const S = live?.price ?? c?.price ?? null;
  const curExp = c?.expirations?.find(e => e.t === cur);
  /* صفوفُ التنفيذ: كلُّ سعر تنفيذٍ صفٌّ واحدٌ بعقدَيه (شراءٌ يساراً وبيعٌ يميناً) */
  const strikes = useMemo(() => {
    if (!c) return [] as { k: number; call?: Row; put?: Row }[];
    const m = new Map<number, { k: number; call?: Row; put?: Row }>();
    for (const r of c.calls || []) m.set(r.strike, { ...(m.get(r.strike) || { k: r.strike }), call: r });
    for (const r of c.puts || []) m.set(r.strike, { ...(m.get(r.strike) || { k: r.strike }), put: r });
    const list = [...m.values()].sort((a, b) => a.k - b.k);
    if (all || !S || list.length <= 25) return list;
    const i = list.findIndex(r => r.k >= S);
    const at = i < 0 ? list.length - 1 : i;
    return list.slice(Math.max(0, at - 12), at + 12);
  }, [c, all, S]);
  const pxAt = S != null ? strikes.findIndex(r => r.k >= S) : -1;

  const advice = useQuery({
    queryKey: ["opt-advice", underlying, ask?.b ?? null, ask?.n ?? 0],
    queryFn: () => marketApi.optionAdvice({ symbol: underlying, budget: ask?.b ?? undefined }).then(r => r.data.data),
    enabled: !!ask, staleTime: 5 * 60_000, retry: 0,
  });
  const runSmart = () => {
    const b = Number(budget);
    lsSet("sp_oc_budget", budget);
    setSmart(true); setAsk({ b: b >= 10 ? b : null, n: Date.now() });
  };
  const nameOf = (r: Row) => { const o = parseOption(r.contract); return o ? `${optionTitle(o)} · ${dayMonth(o.expiry)}` : r.contract; };
  const st = c?.stats;

  const cell = (r: Row | undefined, call: boolean, itm: boolean) => {
    if (!r) return <div className={"ocx-side" + (call ? " ocx-c" : " ocx-p")} />;
    const g = r.g;
    const on = sel?.row.contract === r.contract;
    /* ‏D762: السوقُ مغلقٌ والمصدرُ يصفّر الطلبَ والعرض — فيُعرضان من آخر جلسةٍ بلونٍ خافت */
    const snap = !(r.bid && r.ask) && !!(r.sbid && r.sask);
    const bid = snap ? r.sbid! : r.bid, ask = snap ? r.sask! : r.ask;
    return (
      <button type="button" className={"ocx-side" + (call ? " ocx-c" : " ocx-p") + (itm ? " itm" : "") + (on ? " on" : "")}
        onClick={() => setSel({ row: r, call })} data-role="oc-cell" data-side={call ? "call" : "put"} title={nameOf(r)}>
        <span className="ocx-v"><b className={snap ? "snap" : ""}>{f2(bid)}</b><small>{g ? `Δ${g.delta.toFixed(2)}` : "—"}</small></span>
        <span className="ocx-v"><b className={snap ? "snap" : ""}>{f2(ask)}</b><small>{g ? `${g.iv.toFixed(0)}%` : r.iv != null ? `${r.iv.toFixed(0)}%` : "—"}</small></span>
        <span className="ocx-v"><b>{f2(r.last)}</b><small className={r.pct == null ? "" : r.pct >= 0 ? "pos" : "neg"}>{r.pct == null ? "—" : sg(r.pct)}</small></span>
      </button>
    );
  };

  return (
    <div className="d7m-modal oc-modal" data-shown={shown ? "1" : "0"} role="dialog" aria-label={`عقود خيارات ${underlying}`} onClick={onClose} data-role="oc">
      <div className="d7m-sheet oc-sheet ocx" onClick={e => e.stopPropagation()}>
        <div className="d7m-head">
          <CompanyLogo symbol={underlying} size={26} />
          <strong className="oc-title"><span dir="ltr">{underlying}</span> <span className="oc-sub">عقود الخيارات</span></strong>
          {live?.session && <SessionBadge s={live.session} />}
          {S != null && <span className="oc-px" dir="ltr" data-role="oc-price">{f2(S)}</span>}
          {live?.change_pct != null && <span className={"ocx-chg " + (live.change_pct >= 0 ? "pos" : "neg")} dir="ltr">{sg(live.change_pct, 2)}%</span>}
          <button type="button" className="d7m-btn" onClick={onClose} aria-label="إغلاق"><X size={15} /></button>
        </div>

        {st && (
          <div className="ocx-stats" data-role="oc-stats">
            <span><small>تذبذب النقود</small><b dir="ltr">{st.atm_iv != null ? `${st.atm_iv}%` : "—"}</b></span>
            <span><small>الحركة المتوقّعة</small><b dir="ltr">{st.move != null ? `±${f2(st.move)} (${st.move_pct}%)` : "—"}</b></span>
            <span><small>بيع/شراء (كمية)</small><b dir="ltr">{st.pcr_vol ?? "—"}</b></span>
            <span><small>بيع/شراء (مفتوحة)</small><b dir="ltr">{st.pcr_oi ?? "—"}</b></span>
            <span><small>ألم الحدّ الأقصى</small><b dir="ltr">{st.max_pain != null ? f2(st.max_pain) : "—"}</b></span>
            <span><small>الكمية</small><b dir="ltr">{fk((st.vol.call || 0) + (st.vol.put || 0))}</b></span>
          </div>
        )}

        <div className="ocx-smart" data-role="oc-smartbar">
          <button type="button" className="btn-primary ocx-ai" onClick={runSmart} data-role="oc-smart" disabled={advice.isFetching}>
            {advice.isFetching ? <RefreshCw size={14} className="rl-spin" /> : <Sparkles size={14} className="ai-star" />} تحليل ذكي
          </button>
          <label className="ocx-budget">
            <span>الميزانية $</span>
            <input type="text" inputMode="numeric" dir="ltr" value={budget} placeholder="اختياري" aria-label="ميزانية العقد بالدولار" data-role="oc-budget"
              onChange={e => setBudget(e.target.value.replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 0x0660)).replace(/[^\d]/g, "").slice(0, 6))}
              onKeyDown={e => { if (e.key === "Enter") runSmart(); }} />
          </label>
          <EconEvents compact />
          <span className="oc-late">{live?.delayed ? `مؤجّل ${live.delayed} د` : "أسعارُ العقود متأخّرة 15 دقيقة"}</span>
        </div>

        {smart && <Smart q={advice} onClose={() => setSmart(false)} onOpen={k => onPick(k)} onAdd={onAdd} budget={ask?.b ?? null} />}

        {!!c?.expirations?.length && (
          <div className="oc-exps" role="group" aria-label="الآجال">
            {c.expirations.map(e => (
              <button key={e.t} type="button" className={"seg-btn chip oc-exp" + (cur === e.t ? " on" : "")} onClick={() => { setExp(e.t); setSel(null); }} data-role="oc-exp">
                <b>{dayMonth(e.date)}</b><small>{dteLabel(e.dte)}</small>
              </button>
            ))}
          </div>
        )}

        {q.isPending && !c ? <div className="oc-empty">…</div> : !c || !strikes.length ? (
          <div className="oc-empty" data-role="oc-empty">لا عقودَ خياراتٍ لهذا الرمز.</div>
        ) : (
          <div className="ocx-table" data-role="oc-table" dir="ltr" style={{ opacity: q.isFetching && !q.isRefetching ? 0.6 : 1 }}>
            <div className="ocx-row ocx-h1">
              <div className="ocx-side ocx-c"><span className="ocx-cap">شراء · CALLS</span></div>
              <div className="ocx-k">{curExp ? dteLabel(curExp.dte) : ""}</div>
              <div className="ocx-side ocx-p"><span className="ocx-cap">بيع · PUTS</span></div>
            </div>
            <div className="ocx-row ocx-h2">
              <div className="ocx-side ocx-c"><span>طلب</span><span>عرض</span><span>آخر</span></div>
              <div className="ocx-k">التنفيذ</div>
              <div className="ocx-side ocx-p"><span>طلب</span><span>عرض</span><span>آخر</span></div>
            </div>
            {strikes.map((r, i) => (
              <div key={r.k}>
                {i === pxAt && S != null && <div className="ocx-pxline" data-role="oc-pxline"><span dir="ltr">{f2(S)}</span></div>}
                <div className="ocx-row" data-role="oc-row">
                  {cell(r.call, true, S != null && r.k < S)}
                  <div className="ocx-k"><b>{f2(r.k)}</b></div>
                  {cell(r.put, false, S != null && r.k > S)}
                </div>
              </div>
            ))}
            {pxAt === -1 && S != null && <div className="ocx-pxline"><span dir="ltr">{f2(S)}</span></div>}
          </div>
        )}
        {!!c && <button type="button" className="seg-btn chip ocx-range" onClick={() => setAll(a => !a)} data-role="oc-range">{all ? "قربَ السعر" : "كلُّ الأسعار"}</button>}

        {sel && <Detail row={sel.row} call={sel.call} S={S} underlying={underlying} budget={Number(budget) >= 10 ? Number(budget) : null}
          onClose={() => setSel(null)} onOpen={() => onPick(sel.row.contract)} onAdd={onAdd ? () => onAdd(sel.row.contract, nameOf(sel.row)) : undefined} />}
      </div>
    </div>
  );
}

/* ── بطاقةُ العقد: يونانياتُه كاملةً وحكمُ التحليل الذكيّ عليه ── */
function Detail({ row, call, S, underlying, budget, onClose, onOpen, onAdd }: {
  row: Row; call: boolean; S: number | null; underlying: string; budget: number | null; onClose: () => void; onOpen: () => void; onAdd?: () => void;
}) {
  const g = row.g;
  const o = parseOption(row.contract);
  const [judge, setJudge] = useState(false);
  const j = useQuery({
    queryKey: ["opt-judge", row.contract, budget],
    queryFn: () => marketApi.optionAdvice({ symbol: underlying, contract: row.contract, budget: budget ?? undefined }).then(r => r.data.data),
    enabled: judge, staleTime: 5 * 60_000, retry: 0,
  });
  const k: Card | undefined = j.data?.contract;
  const M = ([t, v]: [string, string]) => <span key={t}><small>{t}</small><b dir="ltr">{v}</b></span>;
  return (
    <div className="ocx-detail card-rise" data-role="oc-detail">
      <div className="ocx-dhead">
        <b>{o ? `${optionTitle(o)} · ${dayMonth(o.expiry)}` : row.contract}</b>
        <span className={"ocx-side-chip " + (call ? "c" : "p")}>{call ? "Call" : "Put"}</span>
        <button type="button" className="d7m-btn ms-auto" onClick={onClose} aria-label="إغلاق البطاقة"><X size={14} /></button>
      </div>
      <div className="ocx-dgrid">
        {([["طلب", f2(row.bid || row.sbid)], ["عرض", f2(row.ask || row.sask)], ["آخر", f2(row.last)], ["الكمية", fk(row.volume)], ["المفتوحة", fk(row.oi)],
           ["التذبذب الضمني", g ? `${g.iv}%` : "—"], ["الدلتا", g ? g.delta.toFixed(3) : "—"], ["الغاما", g ? g.gamma.toFixed(4) : "—"],
           ["الثيتا/يوم", g ? usd(g.theta) : "—"], ["الفيغا", g ? usd(g.vega) : "—"],
           ["في النقود عند الانتهاء", g ? `${g.itm}%` : "—"], ["احتمال الربح", g ? `${g.pop}%` : "—"], ["التعادل", g ? f2(g.be) : "—"],
           ["الكلفة", g ? `$${(g.px * 100).toFixed(0)}` : "—"], ["الفارق", g?.spread != null ? `${g.spread}%` : "—"],
           ["الحركة للتعادل", g && S ? `${sg(((g.be / S) - 1) * 100 * (call ? 1 : -1))}%` : "—"]] as [string, string][]).map(M)}
      </div>
      {g?.src === "last" && <p className="ocx-note">السوقُ مغلق: الأرقامُ من سعر آخر صفقة — والفارقُ مجهول.</p>}
      {g?.src === "snap" && <p className="ocx-note">السوقُ مغلق: الطلبُ والعرضُ من آخر جلسة{row.sat ? ` (${row.sat.slice(0, 16).replace("T", " ")})` : ""}.</p>}
      <div className="ocx-dbtns">
        <button type="button" className="btn-primary" onClick={() => setJudge(true)} disabled={j.isFetching} data-role="oc-judge">
          {j.isFetching ? <RefreshCw size={14} className="rl-spin" /> : <Sparkles size={14} className="ai-star" />} رأي التحليل الذكي
        </button>
        <button type="button" className="btn-ghost" onClick={onOpen} data-role="oc-open"><LineChart size={14} /> الرسم</button>
        {onAdd && <button type="button" className="btn-ghost" onClick={onAdd} data-role="oc-add"><Plus size={14} /> أضف للقائمة</button>}
      </div>
      {judge && !j.isFetching && (k ? <Verdict c={k} /> : j.data?.error ? <p className="ocx-note">{j.data.error}</p> : null)}
    </div>
  );
}

function Verdict({ c }: { c: Card }) {
  return (
    <div className={`ocx-verdict v-${c.verdict}`} data-role="oc-verdict" data-verdict={c.verdict}>
      <span className="ocx-vchip"><VIcon v={c.verdict} /> {c.verdict_ar}</span>
      <ul>
        {c.pros.map((t, i) => <li key={`p${i}`} className="pro">{t}</li>)}
        {c.cons.map((t, i) => <li key={`c${i}`} className="con">{t}</li>)}
      </ul>
    </div>
  );
}

/* ── لوحةُ التحليل الذكيّ ── */
function Smart({ q, onClose, onOpen, onAdd, budget }: { q: any; onClose: () => void; onOpen: (k: string) => void; onAdd?: (k: string, n: string) => void; budget: number | null }) {
  const d = q.data;
  return (
    <section className="ocx-ai-panel card-rise" data-role="oc-ai">
      <div className="ocx-dhead">
        <b><Sparkles size={14} className="ai-star inline-block align-[-2px] me-1" />رأي التحليل الذكي{budget ? ` · ميزانية $${budget}` : ""}</b>
        <button type="button" className="d7m-btn ms-auto" onClick={onClose} aria-label="إغلاق التحليل"><X size={14} /></button>
      </div>
      {q.isFetching && !d ? <p className="ocx-note" role="status">يقرأ السلسلةَ واليونانياتِ والمسارَ والأخبارَ والأحداث…</p>
        : !d ? <p className="ocx-note">تعذّر التحليلُ الآن.</p> : d.error ? <p className="ocx-note">{d.error}</p> : (
        <>
          {d.summary && <p className="ocx-sum" data-role="oc-summary">{d.summary}</p>}
          <div className="ocx-ctx">
            {d.trend && <span className={"ocx-tag t-" + (d.trend.state === "صاعد" ? "up" : d.trend.state === "هابط" ? "dn" : "fl")}>المسار {d.trend.state}</span>}
            {d.news?.event && <span className="ocx-tag" title={d.news.event}>الأخبار: {d.news.impact}</span>}
            {d.hv != null && <span className="ocx-tag">التذبذب التاريخي {d.hv}%</span>}
            {d.earnings && <span className="ocx-tag">الأرباح {d.earnings.slice(0, 10)}</span>}
            {(d.events || []).slice(0, 2).map((e: any) => <span key={e.id} className="ocx-tag t-ev">{e.day} {e.riyadh.slice(-5)} · {e.title}</span>)}
          </div>
          {d.abstain ? <p className="ocx-abstain" data-role="oc-abstain">{d.abstain}</p> : d.lean_note && <p className="ocx-note">{d.lean_note}</p>}
          {d.fit && (
            <div className={"ocx-fit" + (d.fit.ok ? " ok" : "")} data-role="oc-fit">
              <p>{d.fit.text}</p>
              {d.fit.alt && <p><b>{d.fit.alt.text}</b></p>}
              {d.fit.alt_none && <p>{d.fit.alt_none}</p>}
              {d.fit.lab && <p>بدائلُ ضمن ميزانيتك من مختبر الأبحاث: {d.fit.lab.map((x: any) => `${x.symbol} ($${Math.round(x.cost)} · ${Math.round(x.pop)}%)`).join(" · ")}</p>}
            </div>
          )}
          {(d.best || []).length > 0 && <h4 className="ocx-h">{d.abstain ? "إن أصررت — بحذر" : "الأنسب"}</h4>}
          {(d.best || []).map((c: Card) => {
            const o = parseOption(c.contract);
            return (
              <article key={c.contract} className="ocx-card" data-role="oc-best">
                <div className="ocx-dhead">
                  <b>{o ? `${optionTitle(o)} · ${dayMonth(o.expiry)}` : c.contract}</b>
                  <span className="ocx-cost" dir="ltr">${c.cost.toFixed(0)}</span>
                </div>
                <div className="ocx-mini">
                  <span>الدلتا <bdi dir="ltr">{c.g.delta.toFixed(2)}</bdi></span><span>الثيتا <bdi dir="ltr">{usd(c.g.theta)}</bdi>/يوم</span>
                  <span>التذبذب <bdi dir="ltr">{c.g.iv}%</bdi></span><span>احتمال الربح <bdi dir="ltr">{c.g.pop}%</bdi></span><span><bdi dir="ltr">{c.dte}</bdi> يوماً</span>
                </div>
                <Verdict c={c} />
                <div className="ocx-dbtns">
                  <button type="button" className="btn-ghost" onClick={() => onOpen(c.contract)}><LineChart size={14} /> الرسم</button>
                  {onAdd && <button type="button" className="btn-ghost" onClick={() => onAdd(c.contract, o ? `${optionTitle(o)} · ${dayMonth(o.expiry)}` : c.contract)}>
                    <Plus size={14} /> أضف للقائمة</button>}
                </div>
              </article>
            );
          })}
          {(d.refused || []).length > 0 && (
            <details className="ocx-refused" data-role="oc-refused">
              <summary>أمتنع عنها ({d.refused.length})</summary>
              <ul>{d.refused.map((c: Card) => { const o = parseOption(c.contract); return <li key={c.contract}><b>{o ? optionTitle(o) : c.contract} · ${c.cost.toFixed(0)}</b> — {c.cons[0]}</li>; })}</ul>
            </details>
          )}
        </>
      )}
    </section>
  );
}
