/* ══ أوامرُ المستشار الآليّ ══ (‏D750 · D754 — بأمر المالك 2026-11-16)
   D750 على منهج «سندباد»: كلُّ «اشترِ» و«خفّف» أمرٌ بعدد أسهمه ومبلغه وسعره، ببوّاباته، ينتظر اعتمادَك، وللمستشار إيقافٌ وسجلُّ دقّة.
   D754 («كأنه كتالوج — أريده بمستوى الموثوقية، أعتمد عليه في الحياة الواقعية»): فالأمرُ **خطّةُ صفقةٍ كاملة** كتذكرة مدير محفظة —
   دخولٌ محدَّد ووقفُ خسارةٍ وهدفٌ على سلّمٍ واحد، والعائدُ بأضعاف المخاطرة، وما تخسره لو ضُرب الوقف، ولماذا هذا العددُ من الأسهم؛
   و**لوحةُ المخاطر** للمحفظة كلّها، و**حمايةُ كلّ مركزٍ قائم** بوقفه وهدفه وحاله؛ و**سجلُّ الخطط**: كم بلغ هدفَه وكم ضُرب وقفُه.
   والتطبيقُ لا ينفّذ صفقة — التنفيذُ في منصّة الوساطة. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, X, Pause, Play, RefreshCw, ShieldCheck, ArrowUp } from "lucide-react";
import { aiApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";
import CompanyLogo from "../common/CompanyLogo";

type Chk = { k: string; ok: boolean; d?: string };
type Order = { id: string; symbol: string; name: string; side: "شراء" | "بيع"; kind?: string; type?: string; shares: number; price: number;
  amount: number; confidence: number | null; stop?: number | null; stop_basis?: string; target?: number | null; target_basis?: string;
  rr?: number | null; risk?: number; risk_pct?: number; reward?: number; sizing?: string; after?: { weight: number; cash: number };
  why: string; checks: Chk[]; status: string; created?: string; why_closed?: string; outcome?: { k: string } };
type Prot = { symbol: string; name: string; price: number; stop: number | null; stop_basis: string; target: number | null; target_basis: string;
  d_stop: number | null; d_target: number | null; risk: number | null; state: string; trail: boolean; breakeven: boolean };

const mixA = (c: string, pct: number) => `color-mix(in srgb, ${c} ${pct}%, transparent)`;
const STATUS: Record<string, [string, string]> = {
  pending: ["بانتظار اعتمادك", "var(--brand-ink)"], approved: ["معتمد — نفّذه في منصّتك", "var(--pos-ink)"],
  executed: ["نُفّذ", "var(--pos-ink)"], rejected: ["رفضتَه", "var(--ink-muted)"], expired: ["انتهى", "var(--ink-muted)"],
};
const STATE: Record<string, string> = { "محميّ": "var(--pos-ink)", "قريب من الوقف": "var(--warn-ink)", "كُسر الوقف": "var(--neg-ink)", "بلا وقف": "var(--ink-muted)" };
const n0 = (v: number) => v.toLocaleString("en-US", { maximumFractionDigits: 0 });
const p2 = (v: number) => v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const pct = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(1)}٪`;
const Num = ({ v }: { v: string }) => <bdi className="tabular-nums" dir="ltr">{v}</bdi>;

/** سلّمُ الصفقة: الوقفُ في البداية، والدخولُ بينهما بنسبته، والهدفُ في النهاية — بمسافتَيهما من الدخول */
function Ladder({ o }: { o: Order }) {
  if (!o.stop || !o.target) return null;
  const at = Math.max(8, Math.min(92, ((o.price - o.stop) / (o.target - o.stop)) * 100));
  return (
    <div className="robo-ladder" data-role="robo-ladder" aria-label={`وقف ${p2(o.stop)} · دخول ${p2(o.price)} · هدف ${p2(o.target)}`}>
      <div className="robo-rail">
        <span className="robo-seg robo-seg-risk" style={{ width: `${at}%` }} />
        <span className="robo-seg robo-seg-gain" style={{ width: `${100 - at}%` }} />
        <span className="robo-pin" style={{ insetInlineStart: `${at}%` }} />
      </div>
      <div className="robo-marks">
        <span className="robo-mk" style={{ color: "var(--neg-ink)" }}>وقف <Num v={p2(o.stop)} /> <small><Num v={pct((o.stop / o.price - 1) * 100)} /></small></span>
        <span className="robo-mk robo-mk-mid">دخول <Num v={p2(o.price)} /></span>
        <span className="robo-mk" style={{ color: "var(--pos-ink)" }}>هدف <Num v={p2(o.target)} /> <small><Num v={pct((o.target / o.price - 1) * 100)} /></small></span>
      </div>
    </div>
  );
}

function Ticket({ o, i, owner, decide, busy }: { o: Order; i: number; owner: boolean; decide: (id: string, ok: boolean) => void; busy: boolean }) {
  const [st, sc] = STATUS[o.status] || [o.status, "var(--ink-muted)"];
  const buy = o.side === "شراء";
  const side = buy ? "var(--pos-ink)" : o.kind === "stop" ? "var(--neg-ink)" : "var(--warn-ink)";
  const passed = (o.checks || []).filter(c => c.ok).length;
  return (
    <div className="robo-order card-rise" style={{ animationDelay: `${i * 40}ms` }} data-role="robo-order" data-kind={o.kind || ""}>
      <div className="flex items-center gap-2 min-w-0">
        <CompanyLogo symbol={o.symbol} size={28} />
        <span className="text-[13px] font-semibold text-[var(--ink)] truncate">{o.name}</span>
        <span className="ms-auto robo-chip" style={{ color: side, background: mixA(side, 12) }}>
          {o.kind === "stop" ? "خروج حماية" : o.side}
        </span>
      </div>
      <p className="robo-line" data-role="robo-line">
        <span className="robo-type">{o.type || "محدَّد"}</span>
        {o.side} <b><Num v={n0(o.shares)} /></b> سهم عند <b><Num v={p2(o.price)} /></b> = <b><Num v={n0(o.amount)} /></b> ريال
      </p>
      {buy && <Ladder o={o} />}
      <div className="robo-metrics" data-role="robo-metrics">
        {o.rr != null && <span className="robo-m"><small>العائد : المخاطرة</small><b style={{ color: o.rr >= 3 ? "var(--pos-ink)" : "var(--ink)" }}><Num v={`1 : ${o.rr.toFixed(1)}`} /></b></span>}
        {o.risk != null && <span className="robo-m"><small>إن ضُرب الوقف</small><b style={{ color: "var(--neg-ink)" }}><Num v={`−${n0(o.risk)}`} /></b>
          <small><Num v={`${(o.risk_pct ?? 0).toFixed(2)}٪`} /> من المحفظة</small></span>}
        {o.reward != null && <span className="robo-m"><small>إن بلغ الهدف</small><b style={{ color: "var(--pos-ink)" }}><Num v={`+${n0(o.reward)}`} /></b></span>}
        {o.confidence != null && <span className="robo-m"><small>الثقة</small><b style={{ color: o.confidence >= 70 ? "var(--pos-ink)" : "var(--warn-ink)" }}><Num v={`${o.confidence}٪`} /></b></span>}
      </div>
      {(o.sizing || o.after) && (
        <p className="robo-note" data-role="robo-sizing">
          {o.sizing && <>الحجمُ يحكمه <b>{o.sizing}</b></>}
          {o.after && <> · بعده: وزنُه <Num v={`${o.after.weight.toFixed(1)}٪`} /> والنقد <Num v={n0(o.after.cash)} /></>}
        </p>
      )}
      {o.why && <p className="robo-why">{o.why}</p>}
      <details className="robo-gates">
        <summary data-role="robo-gates"><span>اجتاز <Num v={`${passed}`} /> من <Num v={`${(o.checks || []).length}`} /> بوّابات</span></summary>
        <ul className="robo-checks">
          {(o.checks || []).map((c, j) => (
            <li key={j} className={c.ok ? "ok" : "no"}><span aria-hidden>{c.ok ? "✓" : "✗"}</span> {c.k}{c.d ? <small> — {c.d}</small> : null}</li>
          ))}
        </ul>
      </details>
      <div className="flex items-center gap-1.5 mt-2">
        <span className="robo-chip" style={{ color: sc, background: mixA(sc, 11) }} data-role="robo-status">{st}</span>
        {owner && o.status === "pending" && (
          <span className="ms-auto inline-flex gap-1.5">
            <button type="button" className="btn-primary robo-btn" onClick={() => decide(o.id, true)} disabled={busy} data-role="robo-approve"><Check size={14} /> اعتماد</button>
            <button type="button" className="btn-ghost robo-btn" onClick={() => decide(o.id, false)} disabled={busy} data-role="robo-reject"><X size={14} /> رفض</button>
          </span>
        )}
      </div>
    </div>
  );
}

export default function RoboOrders() {
  const qc = useQueryClient();
  const owner = useAuthStore((s: any) => s.isOwner);
  const { data } = useQuery({ queryKey: ["robo"], queryFn: () => aiApi.robo().then(r => r.data.data), staleTime: 60_000 });
  const set = (d: any) => qc.setQueryData(["robo"], d);
  const decide = useMutation({ mutationFn: (a: { id: string; ok: boolean }) => aiApi.roboDecide(a.id, a.ok ? "approve" : "reject"),
    onSuccess: r => set(r.data.data) });
  const pause = useMutation({ mutationFn: (p: boolean) => aiApi.roboPause(p), onSuccess: r => set(r.data.data) });
  const refresh = useMutation({ mutationFn: () => aiApi.roboRefresh(), onSuccess: r => set(r.data.data) });
  if (!data) return null;
  const L = data.limits || {};
  const rec = data.record || {};
  const plans = rec.plans || {};
  const R = data.risk;
  const prot: Prot[] = data.protect || [];
  const orders: Order[] = data.orders || [];
  const heatC = !R ? "var(--ink-muted)" : R.heat_pct > R.heat_max ? "var(--neg-ink)" : R.heat_pct > R.heat_max * 0.66 ? "var(--warn-ink)" : "var(--ink)";
  const over = (w: number, m: number) => (w > m ? "var(--neg-ink)" : w > m * 0.85 ? "var(--warn-ink)" : "var(--ink)");

  return (
    <div className="robo rounded-2xl p-3.5 space-y-3" data-role="robo" style={{ border: "1px solid var(--hairline)" }}>
      <div className="flex items-center gap-2 flex-wrap">
        <p className="text-[13px] font-bold text-[var(--ink)] flex items-center gap-1.5">
          <ShieldCheck size={14} className="text-[var(--brand-ink)]" />المستشار الآلي — أوامر وحماية
        </p>
        <span className="robo-chip" data-role="robo-state" style={{ color: data.paused ? "var(--warn-ink)" : "var(--pos-ink)",
          background: mixA(data.paused ? "var(--warn-ink)" : "var(--pos-ink)", 12) }}>{data.paused ? "موقوف" : "يعمل"}</span>
        {data.asof && <span className="text-[11px] text-[var(--ink-muted)]">آخر بناء <Num v={String(data.asof).replace("T", " ")} /></span>}
        {owner && (
          <span className="ms-auto inline-flex gap-1.5">
            <button type="button" className="btn-ghost robo-btn" onClick={() => refresh.mutate()} disabled={refresh.isPending || data.paused}
              data-role="robo-refresh" aria-label="ابنِ أوامر اليوم الآن" title="ابنِ أوامر اليوم الآن">
              <RefreshCw size={14} className={refresh.isPending ? "animate-spin" : ""} /></button>
            <button type="button" className="btn-ghost robo-btn" onClick={() => pause.mutate(!data.paused)} disabled={pause.isPending}
              data-role="robo-pause" aria-label={data.paused ? "استئناف المستشار" : "إيقاف المستشار"} title={data.paused ? "استئناف" : "إيقاف"}>
              {data.paused ? <Play size={14} /> : <Pause size={14} />}<span className="text-[12px]">{data.paused ? "استئناف" : "إيقاف"}</span></button>
          </span>
        )}
      </div>

      {R && (
        <div className="robo-risk" data-role="robo-risk">
          <div className="robo-tile">
            <small>لو ضُربت الوقوفُ كلُّها</small>
            <b style={{ color: heatC }}><Num v={`−${n0(R.heat)}`} /></b>
            <span><Num v={`${R.heat_pct.toFixed(2)}٪`} /> من المحفظة · الحدّ <Num v={`${R.heat_max}٪`} /></span>
          </div>
          <div className="robo-tile">
            <small>النقد</small>
            <b><Num v={n0(R.cash)} /></b>
            <span><Num v={`${R.cash_pct.toFixed(1)}٪`} /> من المحفظة</span>
          </div>
          <div className="robo-tile">
            <small>أكبر سهم</small>
            <b style={{ color: over(R.top_stock.w, R.top_stock.max) }}><Num v={`${R.top_stock.w.toFixed(1)}٪`} /></b>
            <span className="truncate">{R.top_stock.name || "—"} · الحدّ <Num v={`${R.top_stock.max}٪`} /></span>
          </div>
          <div className="robo-tile">
            <small>أكبر قطاع</small>
            <b style={{ color: over(R.top_sector.w, R.top_sector.max) }}><Num v={`${R.top_sector.w.toFixed(1)}٪`} /></b>
            <span className="truncate">{R.top_sector.name} · الحدّ <Num v={`${R.top_sector.max}٪`} /></span>
          </div>
        </div>
      )}

      {orders.length === 0 ? (
        <p className="text-[12px] text-[var(--ink-muted)]" data-role="robo-empty">
          {data.paused ? "المستشار موقوف — لا أوامر حتى تستأنفه." : "لا أمرَ اليوم — لم تكتمل خطّةُ شراءٍ بشروطها، ولم يُكسر وقفٌ، ولا مركزَ يستحقّ التخفيف."}
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {orders.map((o, i) => <Ticket key={o.id} o={o} i={i} owner={!!owner} busy={decide.isPending} decide={(id, ok) => decide.mutate({ id, ok })} />)}
        </div>
      )}

      {prot.length > 0 && (
        <div className="robo-prot" data-role="robo-protect">
          <p className="robo-sub">حماية المراكز <span className="text-[var(--ink-muted)] font-semibold">(<Num v={String(prot.length)} />)</span>
            {R && (R.broken > 0 || R.near > 0) && <span className="robo-chip ms-2" style={{ color: R.broken ? "var(--neg-ink)" : "var(--warn-ink)",
              background: mixA(R.broken ? "var(--neg-ink)" : "var(--warn-ink)", 12) }}>{R.broken ? `${R.broken} كُسر وقفُه` : `${R.near} قريب من وقفه`}</span>}
          </p>
          <div className="robo-tbl-wrap">
            <table className="robo-tbl">
              <thead><tr><th>السهم</th><th>السعر</th><th>الوقف</th><th>الهدف</th><th className="robo-st">الحال</th></tr></thead>
              <tbody>
                {prot.map(r => (
                  <tr key={r.symbol} data-role="robo-prot-row" data-state={r.state}>
                    <td className="robo-nm">{r.name}<small className="robo-st-m" style={{ color: STATE[r.state] || "var(--ink-muted)" }}>{r.state}</small></td>
                    <td><Num v={p2(r.price)} /></td>
                    <td title={r.stop_basis}>{r.stop ? <><Num v={p2(r.stop)} /> <small style={{ color: "var(--neg-ink)" }}><Num v={pct(-(r.d_stop ?? 0))} /></small>
                      {r.trail && <span className="robo-tr" title="رُفع الوقف"><ArrowUp size={11} /></span>}</> : "—"}
                      {r.breakeven && <small className="block text-[var(--pos-ink)]">على التكلفة</small>}</td>
                    <td title={r.target_basis}>{r.target ? <><Num v={p2(r.target)} /> <small style={{ color: "var(--pos-ink)" }}><Num v={pct(r.d_target ?? 0)} /></small></> : "—"}</td>
                    <td className="robo-st"><span className="robo-chip" style={{ color: STATE[r.state] || "var(--ink-muted)", background: mixA(STATE[r.state] || "var(--ink-muted)", 12) }}>{r.state}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-1.5" data-role="robo-limits">
        {[`مخاطرة الأمر ≤ ${L.risk_pct}٪`, `العائد ≥ ${L.min_rr} أضعاف المخاطرة`, `حدّ السهم ${L.stock_max}٪`, `حدّ القطاع ${L.sector_max}٪`,
          `سيولة السهم ≥ ${(L.min_adv || 0) / 1e6} مليون`, `الأمر ≤ ${L.adv_share}٪ من تداوله`].map(t => <span key={t} className="robo-chip robo-lim">{t}</span>)}
      </div>
      <p className="robo-note" data-role="robo-record">
        {plans.n ? <>سجلّ الخطط: <b><Num v={String(plans.target || 0)} /></b> بلغت هدفها · <b><Num v={String(plans.stop || 0)} /></b> ضُرب وقفها ·{" "}
          <Num v={String(plans.open || 0)} /> قائمة{plans.avg_r != null && <> · متوسّط الناتج <Num v={`${plans.avg_r > 0 ? "+" : ""}${plans.avg_r}R`} /></>}</>
          : "سجلّ الخطط يبدأ مع أوّل أمر شراء."}
        {" · "}
        {rec.n >= 5 ? <>بعد <Num v={String(rec.measure_days)} /> يوماً مقابل تاسي: <Num v={`${rec.hits}/${rec.n}`} /> (<Num v={`${rec.rate}٪`} />)</>
          : <>المقارنة بتاسي تُقاس بعد <Num v={String(rec.measure_days || 30)} /> يوماً من كلّ أمر{rec.n ? <> — قِيس <Num v={String(rec.n)} /></> : null}</>}
      </p>

      {(data.held || []).length > 0 && (
        <details className="robo-held" data-role="robo-held">
          <summary>مؤجّلة بشروطها ({data.held.length})</summary>
          <ul>{data.held.map((h: any) => <li key={h.symbol + h.why}><b>{h.name}</b> — {h.why}</li>)}</ul>
        </details>
      )}
      {(data.history || []).length > 0 && (
        <details className="robo-held" data-role="robo-history">
          <summary>الأوامر السابقة ({data.history.length})</summary>
          <ul>{data.history.map((o: Order) => (
            <li key={o.id}><Num v={(o.created || "").slice(0, 10)} /> · {o.side} <Num v={n0(o.shares)} /> {o.name} — {STATUS[o.status]?.[0] || o.status}
              {o.why_closed ? ` (${o.why_closed})` : ""}
              {o.outcome && <b style={{ color: o.outcome.k === "target" ? "var(--pos-ink)" : "var(--neg-ink)" }}> · {o.outcome.k === "target" ? "بلغ هدفه" : "ضُرب وقفه"}</b>}</li>
          ))}</ul>
        </details>
      )}
    </div>
  );
}
