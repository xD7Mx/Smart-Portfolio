/* ══ قائمةُ صقر — سكرتيرُ المالك ══ (‏D771 بأمر المالك 2026-11-20)
   «أبغى شاشةً توضّح لي إيش الأشياء المضبوطة اليوم وأنا أختار منها — لا إشاراتِ مسحٍ مرفوضٍ ومرفوض… مثل عقود الخيارات، وزرُّ تنفيذ».
   فالقائمةُ عقودٌ طويلةُ الأجل أعدّها صقر للجلسة القادمة (بعد الإغلاق) أو لجلسة اليوم: لكلٍّ كلفتُه وربحُه عند الهدف واحتمالُه، وسعرُ السهم الذي
   يربح عنده 30٪، وإيجابياتُه وسلبياتُه — وما زادت سلبياتُه لم يدخلها — وزرُّ «تنفيذ» بأمر المالك. */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Play, LineChart, Check, AlertTriangle } from "lucide-react";
import { marketApi } from "../../services/api";
import CompanyLogo from "../common/CompanyLogo";
import { dayMonth } from "../../lib/options";
import { usd, px, stamp, spct, type SaqrState, type SList, type SListItem } from "./saqr";
import OrderForm from "./OrderForm";

const Num = ({ v, className }: { v: string; className?: string }) => <bdi dir="ltr" className={"tabular-nums " + (className || "")}>{v}</bdi>;
type Side = "all" | "call" | "put";

function Item({ it, owner, i, onChart }: { it: SListItem; owner: boolean; i: number; onChart: (s: string) => void }) {
  const [open, setOpen] = useState(false);
  const call = it.type === "call";
  return (
    <article className="sl-card card-rise" style={{ animationDelay: `${Math.min(i, 12) * 35}ms` }} data-role="sl-item" data-side={it.type}>
      <header className="sl-h">
        <CompanyLogo symbol={it.symbol} size={26} />
        <span className="sl-t"><b><Num v={it.symbol} />{it.name ? ` · ${it.name}` : ""}</b>
          <small>سترايك <Num v={`${it.strike}`} /> · {dayMonth(it.expiry)} · <Num v={`${it.dte}`} /> يوماً</small></span>
        <span className={"sl-grade" + (it.grade === "قويّة" ? " strong" : "")} data-role="sl-grade">{it.grade}</span>
        <span className="sp-side" data-side={it.type}>{call ? "Call" : "Put"}</span>
      </header>
      <div className="sl-m">
        <span><small>الكلفة</small><b><Num v={usd(it.cost, 0)} /></b><em>العرض <Num v={px(it.ask)} />{it.px_src === "snap" ? " · آخرُ جلسة" : ""}</em></span>
        <span><small>الربحُ عند الهدف</small><b className="pos"><Num v={`+${it.gain_target}%`} /></b><em>الهدف <Num v={px(it.target)} /></em></span>
        <span><small>احتمالُ الربح</small><b><Num v={`${Math.round(it.pop)}%`} /></b><em>لمسُ الهدف <Num v={`${Math.round(it.p_touch)}%`} /></em></span>
        <span data-role="sl-tp30"><small>ربحُ 30٪ عند السهم</small><b><Num v={px(it.tp30.price)} /></b>
          <em>{it.tp30.pct != null && it.tp30.pct > 0 ? <>يحتاج <Num v={spct(it.tp30.pct)} /></> : call ? "السهمُ فوقه الآن" : "السهمُ دونه الآن"}</em></span>
      </div>
      <div className="sl-pc">
        <ul className="sl-why" data-role="sl-pros">{it.pros.slice(0, 4).map((w, j) => <li key={j} className="pro">{w}</li>)}</ul>
        {it.cons.length > 0 && <ul className="sl-why" data-role="sl-cons">{it.cons.slice(0, 3).map((w, j) => <li key={j} className="con">{w}</li>)}</ul>}
        <small className="sq-muted">إيجابيات <Num v={`${it.pros.length}`} /> · سلبيات <Num v={`${it.cons.length}`} /></small>
      </div>
      <div className="sp-acts">
        {owner && <button type="button" className={(open ? "btn-ghost" : "btn-primary") + " sp-btn"} onClick={() => setOpen(v => !v)} aria-expanded={open} data-role="sl-exec">
          <Play size={14} /> {open ? "إغلاق النموذج" : "تنفيذ"}</button>}
        <button type="button" className="btn-ghost sp-btn" onClick={() => onChart(it.symbol)} data-role="sl-chart"><LineChart size={14} /> الرسم</button>
      </div>
      <div className={"sp-addf-wrap" + (open ? " open" : "")} aria-hidden={!open}>
        <div>{open && <OrderForm contract={it.contract} ask={it.ask} />}</div>
      </div>
    </article>
  );
}

export default function SaqrList({ s, owner }: { s: SaqrState; owner: boolean }) {
  const qc = useQueryClient();
  const nav = useNavigate();
  const [side, setSide] = useState<Side>("all");
  const q = useQuery({
    queryKey: ["saqr-list"], queryFn: async () => (await marketApi.saqrList()).data.data as { list: SList | null; job: { on: boolean; msg: string } },
    refetchInterval: (qq: any) => (qq?.state?.data?.job?.on ? 4000 : 60000),
  });
  const run = useMutation({ mutationFn: () => marketApi.saqrListRun(), onSuccess: r => qc.setQueryData(["saqr-list"], r.data.data) });
  const L = q.data?.list, job = q.data?.job;
  const busy = !!job?.on || run.isPending;
  const items = (L?.items || []).filter(it => side === "all" || it.type === side);
  const nCall = (L?.items || []).filter(it => it.type === "call").length, nPut = (L?.items || []).length - nCall;
  const per = s.settings?.per_trade;
  const onChart = (sym: string) => { try { localStorage.setItem("sp_room_symbol", sym); } catch { /* */ } nav("/watchlist"); };
  return (
    <div className="sl" data-role="sl">
      <div className="sq-card card card-rise wide sl-head" data-role="sl-head">
        <div>
          <h4>عقودُ {L?.label || "الجلسة القادمة"}</h4>
          <p className="sq-muted">{L
            ? <>أُعدّت <Num v={stamp(L.at)} /> · ميزانيةُ العقد <Num v={usd(L.budget, 0)} /> · <Num v={`${L.items.length}`} /> عقداً طويلَ الأجل من <Num v={`${L.scanned}`} /> ورقةً
              فحصها (من <Num v={`${L.universe}`} /> اجتازت الأساس)</>
            : busy ? <>صقرٌ يُعدّ القائمة — {job?.msg || "يبدأ"}…</> : "لم تُعدّ القائمةُ بعد."}</p>
          {L && per && L.budget !== per && <p className="sl-warn" data-role="sl-stale"><AlertTriangle size={13} /> القائمةُ بميزانية <Num v={usd(L.budget, 0)} /> وميزانيتُك الآن <Num v={usd(per, 0)} /> — حدّثها.</p>}
          {L?.snap && <p className="sq-muted">أسعارُ العقود من آخر جلسة — تُراجَع عند الافتتاح قبل التنفيذ.</p>}
        </div>
        {owner && <button type="button" className="btn-ghost sq-btn" onClick={() => run.mutate()} disabled={busy} data-role="sl-run">
          <RefreshCw size={14} className={busy ? "rl-spin" : ""} /> {busy ? (job?.msg || "يُعدّ") : "حدّث القائمة"}</button>}
      </div>
      {L && L.items.length > 0 && (
        <span className="seg inline-flex sl-filter" role="group" data-role="sl-filter">
          {([["all", "الكلّ", L.items.length], ["call", "شراء Call", nCall], ["put", "بيع Put", nPut]] as [Side, string, number][]).map(([k, t, n]) => (
            <button key={k} type="button" className={"seg-btn chip" + (side === k ? " on" : "")} aria-pressed={side === k} onClick={() => setSide(k)} data-v={k}>
              {t} <Num v={`${n}`} /></button>
          ))}
        </span>
      )}
      {L && L.items.length === 0 && (
        <p className="sp-empty" data-role="sl-none">لا عقدَ طويلَ الأجل يستوفي الشروط بميزانية <Num v={usd(L.budget, 0)} />
          {L.cheapest ? <> — أرخصُ عقدٍ صالحٍ وُجد <Num v={usd(L.cheapest, 0)} /></> : null}.</p>
      )}
      <div className="sl-grid">
        {items.map((it, i) => <Item key={it.contract} it={it} owner={owner} i={i} onChart={onChart} />)}
      </div>
      {L && Object.keys(L.excluded || {}).length > 0 && (
        <p className="sq-muted sl-ex" data-role="sl-excluded"><Check size={12} /> استبعد صقر: {Object.entries(L.excluded).map(([k, n]) => `${k} ${n}`).join(" · ")}</p>
      )}
    </div>
  );
}
