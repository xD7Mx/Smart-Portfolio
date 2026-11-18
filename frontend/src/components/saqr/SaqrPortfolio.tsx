/* ══ المحفظة — محفظةُ صقر المستقلّة لعقود الخيارات ══ (‏D763 بأمر المالك 2026-11-18)
   «أضف تبويباً اسمه المحفظة… أحطّ فيها ميزانية… يبدأ من 100 دولار ويحاول أن يوصلها إلى 10,000». فالمحفظةُ رأسُ مالٍ ونقدٌ ومراكزُ وصفقاتٌ
   مغلقة — بأسعار السوق الحقيقية (الشراءُ بالعرض والبيعُ بالطلب وعمولةُ كلّ عقد) — ولا تمسّ محفظةَ المالك السعودية. والمالكُ يُدخل مركزاً نفّذه
   بنفسه أو يُغلق مركزاً بسعره (تعديلاتُه تتقدّم)، ويبدأ تجربةً جديدةً برأس مالٍ يحدّده. */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LineChart, Plus, X, RotateCcw, Target } from "lucide-react";
import { marketApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";
import CompanyLogo from "../common/CompanyLogo";
import { optionTitle, parseOption, dayMonth, daysTo } from "../../lib/options";
import { useSaqr, useSaqrMarket, money, smoney, spct, px, dday, tone, type SPos, type Market } from "./saqr";
import MarketSwitch from "./MarketSwitch";

const Num = ({ v, className }: { v: string; className?: string }) => <bdi dir="ltr" className={"tabular-nums " + (className || "")}>{v}</bdi>;
const lsSet = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* */ } };
const title = (c: string) => { const o = parseOption(c); return o ? optionTitle(o) : c; };
const err = (e: any) => e?.response?.data?.detail || "تعذّر التنفيذ";
const ALERT: Record<string, string> = { stop: "بلغ الوقف", trail: "الوقفُ المتحرّك", take: "تضاعف العقد", target: "بلغ السهمُ الهدف", time: "اقترب الأجل",
  stale: "لم يتقدّم", regime: "انقلب السوقُ العامّ", geo: "خطرٌ جيوسياسيّ", results: "نتائجُ مخيّبة", broken: "انكسرت الأطروحة" };

function Position({ p, owner, onChart, i, market, ccy }: { p: SPos; owner: boolean; onChart: (c: string) => void; i: number; market: Market; ccy: string }) {
  const qc = useQueryClient();
  const [closing, setClosing] = useState(false);
  const [price, setPrice] = useState("");
  const usd = money(ccy), susd = smoney(ccy);
  const close = useMutation({
    mutationFn: () => marketApi.saqrClose(p.id, price ? Number(price) : null, market),
    onSuccess: r => { qc.setQueryData(["saqr", market], r.data.data); setClosing(false); },
  });
  const stock = p.kind === "stock";
  const call = p.type === "call";
  const dte = p.expiry ? daysTo(p.expiry) : 0;
  const range = p.target && p.S0 ? Math.max(0, Math.min(100, ((p.S ?? p.S0) - p.S0) / (p.target - p.S0) * 100)) : null;
  return (
    <article className="sp-pos card-rise" style={{ animationDelay: `${i * 40}ms` }} data-role="sp-pos" data-src={p.src}>
      <header className="sp-pos-h">
        <CompanyLogo symbol={market === "sa" ? `${p.symbol}.SR` : p.symbol} size={26} />
        {stock
          ? <span className="sp-pos-t"><b><Num v={p.symbol} />{p.name ? ` · ${p.name}` : ""}</b><small>منذ {dday(p.opened)}</small></span>
          : <span className="sp-pos-t"><b>{title(p.contract)}</b><small>ينتهي {dayMonth(p.expiry || "")} · <Num v={`${dte}`} /> يوماً</small></span>}
        <span className={"sp-chip " + (p.src === "manual" ? "man" : "auto")}>{p.src === "manual" ? "يدويّ" : "صقر"}</span>
        <span className="sp-side" data-side={stock ? "stock" : p.type}>{stock ? "سهم" : call ? "Call" : "Put"}</span>
      </header>
      <div className="sp-pos-m">
        <span><small>{stock ? "الأسهم" : "العقود"}</small><b><Num v={`${p.qty}`} /></b></span>
        <span><small>سعرُ الشراء</small><b><Num v={px(p.entry_px)} /></b></span>
        <span><small>الطلبُ الآن</small><b><Num v={px(p.bid)} /></b></span>
        <span><small>القيمة</small><b><Num v={usd(p.value)} /></b></span>
        <span><small>الربح/الخسارة</small><b className={tone(p.pl)}><Num v={susd(p.pl)} /> <Num v={spct(p.pl_pct)} className="sp-sub" /></b></span>
        <span><small>الوقف</small><b className="neg"><Num v={px(p.stop)} /></b></span>
      </div>
      {range != null && (
        <div className="sp-path" aria-label="مسارُ السهم نحو الهدف" data-role="sp-path">
          <span className="sp-path-l"><Target size={12} /> السهم <Num v={px(p.S)} /> ⇐ الهدف <Num v={px(p.target)} /></span>
          <span className="sp-bar"><i style={{ width: `${range}%` }} /></span>
        </div>
      )}
      {p.alert && <p className="sp-alert" data-role="sp-alert">إشارةُ خروج: {ALERT[p.alert] || "انكسرت الأطروحة"}</p>}
      {p.why?.length > 0 && <ul className="sp-why">{p.why.slice(0, 3).map((w, j) => <li key={j}>{w}</li>)}</ul>}
      <div className="sp-acts">
        <button type="button" className="btn-ghost sp-btn" onClick={() => onChart(p.contract)} data-role="sp-chart"><LineChart size={14} /> فتح في الرسم</button>
        {owner && !closing && <button type="button" className="btn-ghost sp-btn" onClick={() => setClosing(true)} data-role="sp-close"><X size={14} /> إغلاق</button>}
        {owner && closing && (
          <form className="sp-closef" onSubmit={e => { e.preventDefault(); close.mutate(); }}>
            <input type="number" step="0.01" min="0" inputMode="decimal" dir="ltr" placeholder={px(p.bid)} value={price} onChange={e => setPrice(e.target.value)}
              aria-label="سعرُ البيع (فارغٌ = سعرُ الطلب الحيّ)" className="sp-in" />
            <button type="submit" className="btn-primary sp-btn" disabled={close.isPending} data-role="sp-close-ok">بِع</button>
            <button type="button" className="btn-ghost sp-btn" onClick={() => setClosing(false)} aria-label="تراجع"><X size={14} /></button>
            {close.isError && <span className="sp-err">{err(close.error)}</span>}
          </form>
        )}
      </div>
    </article>
  );
}

export default function SaqrPortfolio() {
  const owner = useAuthStore((s: any) => s.isOwner);
  const nav = useNavigate();
  const qc = useQueryClient();
  const [market, setMarket] = useSaqrMarket();
  const q = useSaqr(market);
  const s = q.data;
  const usd = money(s?.ccy), susd = smoney(s?.ccy);
  const [adding, setAdding] = useState(false);
  const [f, setF] = useState({ contract: "", qty: "1", price: "" });
  const [reset, setReset] = useState<string | null>(null);
  const open = useMutation({
    mutationFn: () => marketApi.saqrOpen(f.contract.trim().toUpperCase(), Number(f.qty) || 1, f.price ? Number(f.price) : null, market),
    onSuccess: r => { qc.setQueryData(["saqr", market], r.data.data); setAdding(false); setF({ contract: "", qty: "1", price: "" }); },
  });
  const cap = useMutation({
    mutationFn: (a: number) => marketApi.saqrCapital(a, market),
    onSuccess: r => { qc.setQueryData(["saqr", market], r.data.data); setReset(null); },
  });
  const onChart = (c: string) => { lsSet("sp_room_symbol", market === "sa" ? `${c}.SR` : c); nav("/watchlist"); };
  const head = <MarketSwitch value={market} onChange={m => { setMarket(m); setAdding(false); setReset(null); }} />;

  if (!s) return <div className="sp" data-role="sp">{head}<div className="h-40 skeleton rounded-xl" /></div>;
  const mult = s.capital ? s.equity / s.capital : 1;
  const goalX = s.capital ? s.goal / s.capital : 100;
  return (
    <div className="sp" data-role="sp" data-market={market}>
      {head}
      <section key={market} className="sp-sum card card-rise" data-role="sp-sum">
        <div className="sp-kpi big"><small>رأسُ المال الآن</small><b><Num v={usd(s.equity)} /></b>
          <span className={tone(s.pl)}><Num v={susd(s.pl)} /> (<Num v={spct(s.pl_pct)} />) منذ البداية</span></div>
        <div className="sp-kpi"><small>النقد</small><b><Num v={usd(s.cash)} /></b><span>للصفقة الواحدة حتى <Num v={`${Math.round(s.tier.frac * 100)}%`} /> · <Num v={`${s.tier.seats}`} /> مراكز</span></div>
        <div className="sp-kpi"><small>المحقَّق</small><b className={tone(s.realized)}><Num v={susd(s.realized)} /></b><span>العمولات <Num v={usd(s.fees)} /></span></div>
        <div className="sp-goal" data-role="sp-goal">
          <div className="sp-goal-h"><span>من <Num v={usd(s.capital, 0)} /> إلى <Num v={usd(s.goal, 0)} /></span><b><Num v={`×${mult.toFixed(2)}`} /> من <Num v={`×${goalX.toFixed(0)}`} /></b></div>
          <span className="sp-bar gold"><i style={{ width: `${s.progress ?? 0}%` }} /></span>
        </div>
      </section>

      <section className="sp-sec" data-role="sp-open">
        <header className="sp-sec-h">
          <h3>المراكزُ المفتوحة <Num v={`${s.positions.length}`} className="sp-count" /></h3>
          {owner && (
            <button type="button" className={"btn-ghost sp-btn" + (adding ? " on" : "")} onClick={() => setAdding(a => !a)} aria-expanded={adding} data-role="sp-add">
              <Plus size={14} /> مركزٌ نفّذتُه
            </button>
          )}
        </header>
        <div className={"sp-addf-wrap" + (adding ? " open" : "")} aria-hidden={!adding}>
          <form className="sp-addf" onSubmit={e => { e.preventDefault(); open.mutate(); }} data-role="sp-addf">
            <label><small>{market === "sa" ? "رمزُ الشركة" : "رمزُ العقد أو السهم"}</small><input className="sp-in wide" dir="ltr"
              placeholder={market === "sa" ? "2222" : "F270115C00012000 · AAPL"} value={f.contract}
              onChange={e => setF({ ...f, contract: e.target.value })} required tabIndex={adding ? 0 : -1} /></label>
            <label><small>الكمّية</small><input className="sp-in" type="number" min={1} step={1} dir="ltr" value={f.qty} onChange={e => setF({ ...f, qty: e.target.value })} tabIndex={adding ? 0 : -1} /></label>
            <label><small>سعرُ التنفيذ</small><input className="sp-in" type="number" min={0} step="0.01" dir="ltr" placeholder="العرضُ الحيّ" value={f.price}
              onChange={e => setF({ ...f, price: e.target.value })} tabIndex={adding ? 0 : -1} /></label>
            <button type="submit" className="btn-primary sp-btn" disabled={open.isPending || !f.contract} tabIndex={adding ? 0 : -1}>أضِف</button>
            {open.isError && <span className="sp-err">{err(open.error)}</span>}
          </form>
        </div>
        {s.positions.length === 0
          ? <p className="sp-empty" data-role="sp-none">لا مراكزَ مفتوحة — {s.session?.state === "open" ? "صقرٌ يبحث في السوق." : `السوقُ الأمريكيّ ${s.session?.label || "مغلق"}${s.session?.detail ? ` (${s.session.detail})` : ""}.`}</p>
          : <div className="sp-grid">{s.positions.map((p, i) => <Position key={p.id} p={p} owner={owner} onChart={onChart} i={i} market={market} ccy={s.ccy} />)}</div>}
      </section>

      <section className="sp-sec" data-role="sp-closed">
        <header className="sp-sec-h"><h3>الصفقاتُ المغلقة <Num v={`${s.n_closed}`} className="sp-count" /></h3>
          {s.win_rate != null && <span className="sp-meta">رابحة <Num v={`${s.wins}`} /> · خاسرة <Num v={`${s.losses}`} /> · النجاح <Num v={`${s.win_rate.toFixed(0)}%`} /></span>}
        </header>
        {s.closed.length === 0 ? <p className="sp-empty">لم تُغلق صفقةٌ بعد.</p> : (
          <div className="sp-table" role="table" aria-label="الصفقاتُ المغلقة">
            <div className="sp-tr head" role="row"><span>العقد</span><span>الدخول ⇐ الخروج</span><span>السعر</span><span>النتيجة</span><span>السبب</span></div>
            {s.closed.map(c => (
              <div key={c.id + c.closed} className="sp-tr" role="row" data-role="sp-closed-row">
                <span><b>{c.kind === "stock" ? <><Num v={c.symbol} />{c.name ? ` · ${c.name}` : ""}</> : title(c.contract)}</b> <Num v={`×${c.qty}`} className="sp-sub" /></span>
                <span><Num v={`${dday(c.opened)} ⇐ ${dday(c.closed)}`} /></span>
                <span><Num v={`${px(c.entry_px)} ⇐ ${px(c.exit_px)}`} /></span>
                <span className={tone(c.pl)}><Num v={susd(c.pl)} /> <Num v={spct(c.pl_pct)} className="sp-sub" /></span>
                <span className="sp-reason">{c.reason_ar}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {owner && (
        <section className="sp-sec" data-role="sp-reset">
          <header className="sp-sec-h"><h3>تجربةٌ جديدة</h3>
            {reset == null && <button type="button" className="btn-ghost sp-btn" onClick={() => setReset(String(s.capital))} data-role="sp-reset-open"><RotateCcw size={14} /> برأس مالٍ جديد</button>}
          </header>
          {reset != null && (
            <form className="sp-addf" onSubmit={e => { e.preventDefault(); const a = Number(reset); if (a >= 10) cap.mutate(a); }}>
              <label><small>رأسُ المال</small><input className="sp-in" type="number" min={10} step={10} dir="ltr" value={reset} onChange={e => setReset(e.target.value)} /></label>
              <span className="sp-warn">تُغلق التجربةُ الحالية (<Num v={usd(s.equity)} />) وتُحفظ ملخّصةً، وتبدأ أخرى من الصفر.</span>
              <button type="submit" className="btn-primary sp-btn" disabled={cap.isPending} data-role="sp-reset-ok">ابدأ</button>
              <button type="button" className="btn-ghost sp-btn" onClick={() => setReset(null)}>تراجع</button>
            </form>
          )}
          {s.runs.length > 0 && (
            <ul className="sp-runs">{s.runs.map(r => <li key={r.started}><Num v={`${dday(r.started)} ⇐ ${dday(r.ended)}`} /> · <Num v={usd(r.capital, 0)} /> ⇐ <Num v={usd(r.equity)} /> · <Num v={`${r.trades}`} /> صفقة</li>)}</ul>
          )}
        </section>
      )}
    </div>
  );
}
