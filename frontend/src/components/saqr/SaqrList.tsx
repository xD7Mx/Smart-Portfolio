/* ══ قائمةُ صقر — سكرتيرُ المالك ══ (‏D771 بأمر المالك 2026-11-20)
   «أبغى شاشةً توضّح لي إيش الأشياء المضبوطة اليوم وأنا أختار منها — لا إشاراتِ مسحٍ مرفوضٍ ومرفوض… مثل عقود الخيارات، وزرُّ تنفيذ».
   فالقائمةُ عقودٌ طويلةُ الأجل أعدّها صقر للجلسة القادمة (بعد الإغلاق) أو لجلسة اليوم: لكلٍّ كلفتُه وربحُه عند الهدف واحتمالُه، وسعرُ السهم الذي
   يربح عنده 30٪، وإيجابياتُه وسلبياتُه — وما زادت سلبياتُه لم يدخلها — وزرُّ «تنفيذ» بأمر المالك. */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Play, LineChart, Check, AlertTriangle, Users } from "lucide-react";
import { marketApi } from "../../services/api";
import CompanyLogo from "../common/CompanyLogo";
import { dayMonth } from "../../lib/options";
import { usd, px, stamp, spct, type SaqrState, type SList, type SListItem } from "./saqr";
import OrderForm from "./OrderForm";

const Num = ({ v, className }: { v: string; className?: string }) => <bdi dir="ltr" className={"tabular-nums " + (className || "")}>{v}</bdi>;
type Side = "all" | "call" | "put";

/* ‏D775 — المالك: «الأفضلُ أن تكون الميزانيةُ كستمايز: 300، 150، 100 — كلَّ يومٍ يجي خيرٌ معه». فالميزانيةُ تُختار هنا وتُعرض بها القائمةُ فوراً
   (صقر يحفظ لكلّ سهمٍ أفضلَ عقدٍ عند كلّ كلفة)، وبجانب كلّ ميزانيةٍ جاهزةٍ عددُ عقودها. */
/* ‏D776 — المالك: «لو اخترتُ نسبةَ نجاحٍ لا تقلّ عن 90٪…». فالحدُّ الأدنى بيده، وبجانب كلٍّ عددُ عقوده بميزانيته — والنسبةُ تقديرُ السوق (التذبذبُ
   الضمنيّ) لبلوغ +30٪ قبل الوقف، وسجلُّ الفريق يقيس الفعليّ. */
function WinBar({ L, owner }: { L: SList; owner: boolean }) {
  const qc = useQueryClient();
  const cur = Math.round(L.min_win || 0);
  const m = useMutation({
    mutationFn: (w: number) => marketApi.saqrSettings({ min_win: w }, "us"),
    onSuccess: r => { qc.setQueryData(["saqr", "us"], r.data.data); qc.invalidateQueries({ queryKey: ["saqr-list"] }); },
  });
  const lv = Object.entries(L.wins || {}).map(([w, n]) => [Number(w), n] as [number, number]).sort((a, b) => a[0] - b[0]);
  const T = L.track;
  return (
    <div className="sl-bud" data-role="sl-winbar">
      <small>نسبةُ النجاح الدنيا</small>
      <span className="seg inline-flex sl-bud-seg" role="group" aria-label="نسبةُ النجاح الدنيا">
        {lv.map(([w, n]) => (
          <button key={w} type="button" className={"seg-btn chip" + (w === cur ? " on" : "")} aria-pressed={w === cur} disabled={!owner || m.isPending}
            onClick={() => w !== cur && m.mutate(w)} data-v={w} data-role="sl-win-lv">
            {w === 0 ? "الكلّ" : <Num v={`${w}%`} />} <em className="sl-bud-n"><Num v={`${n}`} /></em></button>
        ))}
      </span>
      <span className="sl-track" data-role="sl-track"><Users size={13} /> سجلُّ الفريق: {T && T.closed > 0
        ? <>نجح <Num v={`${T.wins}`} /> من <Num v={`${T.closed}`} /> أُغلقت (<Num v={`${Math.round(T.rate ?? 0)}%`} />) · يُتابَع <Num v={`${T.open}`} /></>
        : T && T.open > 0 ? <>يُتابَع <Num v={`${T.open}`} /> عقداً اختارها الفريق — ولم يُغلق أيٌّ بعد</> : "يبدأ مع أوّل اختيارٍ للفريق"}</span>
    </div>
  );
}

function BudgetBar({ L, owner }: { L: SList; owner: boolean }) {
  const qc = useQueryClient();
  const [v, setV] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const cur = Math.round(L.budget);
  const m = useMutation({
    mutationFn: (b: number) => marketApi.saqrSettings({ per_trade: b }, "us"),
    onSuccess: r => { qc.setQueryData(["saqr", "us"], r.data.data); qc.invalidateQueries({ queryKey: ["saqr-list"] }); setV(""); setErr(null); },
    onError: (e: any) => setErr(e?.response?.data?.detail || "تعذّر الحفظ"),
  });
  const levels = Object.entries(L.levels || {}).map(([b, n]) => [Number(b), n] as [number, number]).sort((a, b) => a[0] - b[0]);
  const custom = Math.round(Number(v));
  const canSet = custom >= 20 && custom !== cur;   // خارجَ الوسم: «>» داخلَه يقطعه عند قارئ اللجنة (‏S-DEADBTN)
  return (
    <div className="sl-bud" data-role="sl-budget">
      <small>ميزانيةُ العقد</small>
      <span className="seg inline-flex sl-bud-seg" role="group" aria-label="ميزانيةُ العقد">
        {levels.map(([b, n]) => (
          <button key={b} type="button" className={"seg-btn chip" + (b === cur ? " on" : "")} aria-pressed={b === cur} disabled={!owner || m.isPending}
            onClick={() => b !== cur && m.mutate(b)} data-v={b} data-role="sl-bud-lv">
            <Num v={usd(b, 0)} /> <em className="sl-bud-n"><Num v={`${n}`} /></em></button>
        ))}
      </span>
      {owner && (
        <span className="sl-bud-c">
          <input className="sp-in" type="number" min={20} step={10} dir="ltr" inputMode="numeric" placeholder="مبلغٌ آخر" value={v} aria-label="ميزانيةٌ أخرى للعقد"
            onChange={e => { setV(e.target.value); setErr(null); }} onKeyDown={e => { if (e.key === "Enter" && custom >= 20) m.mutate(custom); }} data-role="sl-bud-in" />
          <button type="button" className="btn-ghost sq-btn" disabled={!canSet || m.isPending} onClick={() => m.mutate(custom)}
            data-role="sl-bud-set">طبّق</button>
        </span>
      )}
      {err && <span className="sl-warn" role="alert"><AlertTriangle size={13} /> {err}</span>}
    </div>
  );
}

function Item({ it, owner, i, onChart }: { it: SListItem; owner: boolean; i: number; onChart: (s: string) => void }) {
  const [open, setOpen] = useState(false);
  const call = it.type === "call";
  return (
    <article className="sl-card card-rise" style={{ animationDelay: `${Math.min(i, 12) * 35}ms` }} data-role="sl-item" data-side={it.type}>
      <header className="sl-h">
        <CompanyLogo symbol={it.symbol} size={26} />
        <span className="sl-t"><b><Num v={it.symbol} />{it.name ? ` · ${it.name}` : ""}</b>
          <small>سترايك <Num v={`${it.strike}`} /> · {dayMonth(it.expiry)} · <Num v={`${it.dte}`} /> يوماً</small></span>
        <span className={"sl-grade" + (it.team.warns === 0 ? " strong" : "")} data-role="sl-grade">الفريقُ {it.team.verdict}</span>
        <span className="sp-side" data-side={it.type}>{call ? "Call" : "Put"}</span>
      </header>
      <div className="sl-m">
        <span><small>الكلفة</small><b><Num v={usd(it.cost, 0)} /></b><em>العرض <Num v={px(it.ask)} />{it.px_src === "snap" ? " · آخرُ جلسة" : ""}</em></span>
        <span data-role="sl-win"><small>نسبةُ النجاح</small><b className={(it.team.p30 ?? 0) >= 55 ? "pos" : ""}>{it.team.p30 != null ? <Num v={`${Math.round(it.team.p30)}%`} /> : "غير متوفّر"}</b>
          <em><Num v="+30%" /> قبل الوقف</em></span>
        <span><small>الربحُ عند الهدف</small><b className="pos"><Num v={`+${it.gain_target}%`} /></b><em>الهدف <Num v={px(it.target)} /></em></span>
        <span data-role="sl-tp30"><small>ربحُ 30٪ عند السهم</small><b><Num v={px(it.tp30.price)} /></b>
          <em>{it.tp30.pct != null && it.tp30.pct > 0 ? <>يحتاج <Num v={spct(it.tp30.pct)} /></> : call ? "السهمُ فوقه الآن" : "السهمُ دونه الآن"}</em></span>
      </div>
      <ul className="sl-team" data-role="sl-team" aria-label="حكمُ الفريق">
        {it.team.members.map(m => (
          <li key={m.role} data-v={m.v} data-role="sl-mem">
            <i className="sl-mem-i" aria-hidden>{m.v === "ok" ? <Check size={11} /> : <AlertTriangle size={11} />}</i>
            <b>{m.role}</b><span>{m.say}</span>
          </li>
        ))}
      </ul>
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
  const onChart = (sym: string) => { try { localStorage.setItem("sp_room_symbol", sym); } catch { /* */ } nav("/watchlist"); };
  return (
    <div className="sl" data-role="sl">
      <div className="sq-card card card-rise wide sl-head" data-role="sl-head">
        <div>
          <h4>عقودُ {L?.label || "الجلسة القادمة"}</h4>
          <p className="sq-muted">{L
            ? <>أُعدّت <Num v={stamp(L.at)} /> · ميزانيةُ العقد <Num v={usd(L.budget, 0)} /> · <Num v={`${L.items.length}`} /> عقداً طويلَ الأجل من <Num v={`${L.scanned}`} /> ورقةً
              فحصها (من <Num v={`${L.universe}`} /> اجتازت الأساس){L.more && L.items.length < 50 ? <span data-role="sl-more"> · يُكمل الفحصَ كلَّ نصف ساعة</span> : null}</>
            : busy ? <>صقرٌ يُعدّ القائمة — {job?.msg || "يبدأ"}…</> : "لم تُعدّ القائمةُ بعد."}</p>
          {L?.snap && <p className="sq-muted">أسعارُ العقود من آخر جلسة — تُراجَع عند الافتتاح قبل التنفيذ.</p>}
        </div>
        {owner && <button type="button" className="btn-ghost sq-btn" onClick={() => run.mutate()} disabled={busy} data-role="sl-run">
          <RefreshCw size={14} className={busy ? "rl-spin" : ""} /> {busy ? (job?.msg || "يُعدّ") : "حدّث القائمة"}</button>}
      </div>
      {L && <BudgetBar L={L} owner={owner} />}
      {L && <WinBar L={L} owner={owner} />}
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
