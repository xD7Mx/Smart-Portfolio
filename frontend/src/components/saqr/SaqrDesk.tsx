/* ══ صقر — لوحةُ وكيل التداول الآليّ ══ (‏D763 بأمر المالك 2026-11-18)
   «أضف تبويباً ثالثاً باسم صقر — وكيلُ تداولٍ آليّ… automation… يبدأ من 100 دولار ويحاول أن يوصلها إلى 10,000… وهذه صورةُ شاشته».
   فاللوحةُ من الصورة: صقرٌ في المركز وأنظمتُه حوله (الإشاراتُ وإدارةُ المخاطر والوسيطُ ومحرّكُ الأوامر والوقفُ والجنيُ والأخبارُ والمستشار)
   بحالةِ كلٍّ منها، وفي الزوايا الصفقاتُ المفتوحة والربحُ الحاليّ ورابحةُ اليوم وخاسرتُه والمحقَّقُ بعد العمولات؛ وتحتها حالُ الأنظمة والتعرّضُ
   و‏SPY وجلسةُ السوق ونسبةُ النجاح ومنحنى رأس المال — ثمّ الإشاراتُ بقبولها ورفضها وأسبابها، والسجلّ، والقواعد. والوسيطُ «غيرُ مربوط»
   صراحةً: التنفيذُ بأسعار السوق الحقيقية لحظتَها حتى يُربط ‏IBKR. */
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bird, Radar, ShieldCheck, Unlink, Cpu, ShieldAlert, Target, Newspaper, Sparkles, Play, Pause, RefreshCw,
  LayoutDashboard, Activity, ScrollText, SlidersHorizontal, ArrowDownRight, ArrowUpRight, Info, BellRing, Hand } from "lucide-react";
import { marketApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";
import { useLive, useSessions } from "../chart/LiveQuote";
import { useSaqr, usd, susd, spct, hhmm, dday, tone, type SaqrState } from "./saqr";

const Num = ({ v, className }: { v: string; className?: string }) => <bdi dir="ltr" className={"tabular-nums " + (className || "")}>{v}</bdi>;
type Tab = "dash" | "signals" | "log" | "rules";
const TABS: [Tab, string, any][] = [["dash", "لوحة المتابعة", LayoutDashboard], ["signals", "الإشارات", Activity], ["log", "السجل", ScrollText], ["rules", "القواعد", SlidersHorizontal]];
type NState = "ok" | "warn" | "off";

const ago = (iso?: string | null) => (iso ? (Date.now() - new Date(iso).getTime()) / 60000 : Infinity);

function nodes(s: SaqrState, sesOpen: boolean): { k: string; t: string; d: ReactNode; tip: string; st: NState; icon: any }[] {
  const scanAge = ago(s.scan?.at);
  const frac = Math.round(s.tier.frac * 100), stop = Math.round((1 - s.rules.stop) * 100);
  const newsTxt = s.health.events === false ? "التقويم متعذّر" : s.health.news === false ? "القراءة متعذّرة" : "تُقرأ";
  const eng = s.on ? (sesOpen ? "يعمل" : "ينتظر الجلسة") : "موقوف";
  return [
    { k: "signals", t: "الإشارات", d: s.scan ? <><Num v={`${s.scan.universe}`} /> رمزاً</> : "لم يمسح بعد", tip: s.scan ? `${s.scan.universe} رمزاً` : "لم يمسح بعد",
      st: s.scan && scanAge < 90 ? "ok" : sesOpen ? "warn" : "off", icon: Radar },
    { k: "risk", t: "إدارة المخاطر", d: <><Num v={`${frac}%`} /> · <Num v={`${s.tier.seats}`} /> مراكز</>, tip: `${frac}% للصفقة · ${s.tier.seats} مراكز`,
      st: s.gates.some(g => g.includes("قاطع")) ? "warn" : "ok", icon: ShieldCheck },
    { k: "broker", t: s.broker.name || "IBKR", d: s.broker.linked ? "مربوط" : "غير مربوط", tip: s.broker.linked ? "مربوط" : "غير مربوط", st: s.broker.linked ? "ok" : "off", icon: Unlink },
    { k: "engine", t: "محرّك الأوامر", d: eng, tip: eng, st: s.on ? (sesOpen ? "ok" : "warn") : "off", icon: Cpu },
    { k: "stop", t: "وقف الخسارة", d: <><Num v={`-${stop}%`} /> ومتحرّك</>, tip: `-${stop}% ومتحرّك`, st: "ok", icon: ShieldAlert },
    { k: "take", t: "جني الأرباح", d: <><Num v={`×${s.rules.take}`} /> أو الهدف</>, tip: `×${s.rules.take} أو الهدف`, st: "ok", icon: Target },
    { k: "news", t: "الأخبار والأحداث", d: newsTxt, tip: newsTxt, st: s.health.events === false || s.health.news === false ? "warn" : "ok", icon: Newspaper },
    { k: "ai", t: "المستشار الذكي", d: "اليونانيات والحكم", tip: "اليونانيات والحكم", st: s.health.news === false ? "warn" : "ok", icon: Sparkles },
  ];
}

function Hub({ s, sesOpen }: { s: SaqrState; sesOpen: boolean }) {
  const ns = nodes(s, sesOpen);
  const R = 110, C = 150;
  const live = s.on && sesOpen;
  return (
    <div className={"sq-hub" + (live ? " live" : "")} data-role="sq-hub" data-live={live ? "1" : "0"}>
      <svg className="sq-wires" viewBox="0 0 300 300" aria-hidden>
        <circle cx={C} cy={C} r={R} className="sq-orbit" />
        {ns.map((n, i) => {
          const a = (i / ns.length) * Math.PI * 2 - Math.PI / 2;
          return <line key={n.k} x1={C} y1={C} x2={C + R * Math.cos(a)} y2={C + R * Math.sin(a)} className={"sq-wire " + n.st} />;
        })}
      </svg>
      <div className="sq-core" data-role="sq-core">
        <span className="sq-halo" aria-hidden />
        <Bird size={34} strokeWidth={1.6} />
        <b>صقر</b>
        <small>{s.on ? (sesOpen ? "يعمل" : "ينتظر الجلسة") : "موقوف"}</small>
      </div>
      {ns.map((n, i) => {
        const a = (i / ns.length) * 360 - 90;
        const x = 50 + (R / 300) * 100 * Math.cos((a * Math.PI) / 180), y = 50 + (R / 300) * 100 * Math.sin((a * Math.PI) / 180);
        const I = n.icon;
        return (
          <div key={n.k} className={"sq-node " + n.st} style={{ left: `${x}%`, top: `${y}%`, animationDelay: `${80 + i * 50}ms` }}
            data-role="sq-node" data-state={n.st} data-k={n.k} title={`${n.t}: ${n.tip}`}>
            <span className="sq-ni">{n.k === "ai" ? <Sparkles size={15} className="ai-star" /> : <I size={15} />}</span>
            <span className="sq-nt">{n.t}</span>
            <span className="sq-nd">{n.d}</span>
          </div>
        );
      })}
    </div>
  );
}

function Stat({ label, children, k }: { label: string; children: ReactNode; k: string }) {
  return <div className="sq-stat card" data-role="sq-stat" data-k={k}><small>{label}</small><div className="sq-sv">{children}</div></div>;
}

function Ring({ pct, wins, losses }: { pct: number | null; wins: number; losses: number }) {
  const r = 34, c = 2 * Math.PI * r, v = pct ?? 0;
  return (
    <div className="sq-ring" data-role="sq-ring">
      <svg viewBox="0 0 84 84" aria-hidden>
        <circle cx="42" cy="42" r={r} className="trk" />
        <circle cx="42" cy="42" r={r} className="val" strokeDasharray={`${(v / 100) * c} ${c}`} transform="rotate(-90 42 42)" />
      </svg>
      <b><Num v={pct == null ? "—" : `${pct.toFixed(0)}%`} /></b>
      <span className="sq-wl"><span className="pos">رابحة <Num v={`${wins}`} /></span><span className="neg">خاسرة <Num v={`${losses}`} /></span></span>
    </div>
  );
}

function Spark({ pts, base, label, role }: { pts: number[]; base?: number; label: string; role: string }) {
  if (pts.length < 2) return <div className="sq-spark empty" data-role={role}>لا نقاطَ كافية بعد</div>;
  const W = 300, H = 90;
  const lo = Math.min(...pts, base ?? Infinity), hi = Math.max(...pts, base ?? -Infinity);
  const y = (v: number) => H - 6 - ((v - lo) / (hi - lo || 1)) * (H - 12);
  const x = (i: number) => (i / (pts.length - 1)) * W;
  const d = pts.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const up = pts[pts.length - 1] >= (base ?? pts[0]);
  return (
    <svg className={"sq-spark " + (up ? "up" : "down")} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={label} data-role={role}>
      {[0.25, 0.5, 0.75].map(f => <line key={f} x1="0" x2={W} y1={H * f} y2={H * f} className="grid" />)}
      {base != null && <line x1="0" x2={W} y1={y(base)} y2={y(base)} className="base" />}
      <path d={`${d} L${W},${H} L0,${H} Z`} className="area" />
      <path d={d} className="line" pathLength={1} />
      <circle cx={x(pts.length - 1)} cy={y(pts[pts.length - 1])} r="3.5" className="end" />
    </svg>
  );
}

function useClock(on: boolean) {
  const [, t] = useState(0);
  useEffect(() => { if (!on) return; const i = setInterval(() => t(x => x + 1), 1000); return () => clearInterval(i); }, [on]);
}
const hms = (ms: number) => {
  const s = Math.max(0, Math.floor(ms / 1000));
  return [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60].map(v => String(v).padStart(2, "0")).join(":");
};

function SessionCard() {
  const ses = useSessions().data?.us;
  const st = ses?.state;
  const timed = st === "open" || st === "pre" || st === "post";
  useClock(timed);
  const left = ses?.next ? new Date(ses.next).getTime() - Date.now() : null;
  const early = /مبكّر/.test(ses?.detail || "");
  const span = (early ? 3.5 : 6.5) * 3600e3;
  const prog = st === "open" && left != null ? Math.max(0, Math.min(100, (1 - left / span) * 100)) : st === "post" || st === "closed" || st === "holiday" ? 100 : 0;
  return (
    <div className="sq-card card card-rise" data-role="sq-session" data-state={st || ""}>
      <h4>جلسة السوق الأمريكيّ</h4>
      <div className="sq-ses">
        <span className={"sq-pill s-" + (st || "closed")}>{ses ? (ses.holiday ? `عطلة: ${ses.holiday}` : ses.label) : "…"}</span>
        <b><Num v={timed && left != null ? hms(left) : "—"} /></b>
      </div>
      <small className="sq-muted">{ses?.detail || ""}</small>
      <span className="sp-bar"><i style={{ width: `${prog}%` }} /></span>
    </div>
  );
}

function SpyCard() {
  const live = useLive("SPY").data;
  const bars = useQuery({ queryKey: ["bars", "SPY", "1d"], queryFn: () => marketApi.bars("SPY", "1d").then(r => r.data?.data || []), staleTime: 15 * 60e3, retry: 0 });
  const pts = ((bars.data as any[]) || []).map(b => Number(b.close)).filter(v => isFinite(v) && v > 0).slice(-60);
  if (live?.price && pts.length) pts[pts.length - 1] = live.price;
  return (
    <div className="sq-card card card-rise" data-role="sq-spy">
      <h4>SPY</h4>
      <div className="sq-ses"><b><Num v={live?.price ? live.price.toFixed(2) : "—"} /></b>
        <span className={tone(live?.change_pct)}><Num v={spct(live?.change_pct, 2)} /></span></div>
      <Spark pts={pts} label="مسارُ SPY في ستين جلسة" role="sq-spy-line" />
    </div>
  );
}

const KIND: Record<string, [any, string]> = { buy: [ArrowUpRight, "pos"], sell: [ArrowDownRight, "neg"], alert: [BellRing, "warn"], manual: [Hand, "info"], info: [Info, ""], error: [ShieldAlert, "neg"] };

export default function SaqrDesk() {
  const owner = useAuthStore((st: any) => st.isOwner);
  const qc = useQueryClient();
  const q = useSaqr();
  const s = q.data;
  const ses = useSessions().data?.us;
  const sesOpen = ses?.state === "open";
  const [tab, setTab] = useState<Tab>(() => { try { return (localStorage.getItem("sp_saqr_tab") as Tab) || "dash"; } catch { return "dash"; } });
  const pick = (t: Tab) => { setTab(t); try { localStorage.setItem("sp_saqr_tab", t); } catch { /* */ } };
  const toggle = useMutation({ mutationFn: (on: boolean) => marketApi.saqrToggle(on), onSuccess: r => qc.setQueryData(["saqr"], r.data.data) });
  const run = useMutation({ mutationFn: () => marketApi.saqrRun(), onSuccess: () => setTimeout(() => q.refetch(), 700) });
  const curve = useMemo(() => (s?.equity_curve || []).map(p => p[1]), [s?.equity_curve]);
  if (!s) return <div className="sq" data-role="sq"><div className="h-60 skeleton rounded-xl" /></div>;
  const unreal = s.positions.reduce((a, p) => a + p.pl, 0);
  const busy = s.running?.on || run.isPending;

  return (
    <div className="sq" data-role="sq">
      <header className="sq-head">
        <span className="sq-id"><Bird size={20} /><b>صقر</b>
          <span className={"sq-pill " + (s.on ? (sesOpen ? "s-open" : "s-pre") : "s-closed")} data-role="sq-state">{s.on ? (sesOpen ? "يعمل الآن" : "يعمل في الجلسة") : "موقوف"}</span>
        </span>
        <span className="sq-sub">التنفيذُ بأسعار السوق الحقيقية · الوسيط {s.broker.linked ? "مربوط" : "غيرُ مربوط"}</span>
        {owner && (
          <span className="sq-acts">
            <button type="button" className="btn-ghost sq-btn" onClick={() => run.mutate()} disabled={busy} data-role="sq-run" title={s.running?.msg || "دورةٌ الآن"}>
              <RefreshCw size={14} className={busy ? "rl-spin" : ""} /> {busy ? (s.running?.msg || "يعمل") : "دورةٌ الآن"}
            </button>
            <button type="button" className={(s.on ? "btn-ghost" : "btn-primary") + " sq-btn"} onClick={() => toggle.mutate(!s.on)} disabled={toggle.isPending} data-role="sq-toggle">
              {s.on ? <><Pause size={14} /> إيقاف</> : <><Play size={14} /> تشغيل</>}
            </button>
          </span>
        )}
      </header>

      <section className="sq-top">
        <Stat label="صفقات مفتوحة" k="open"><b><Num v={`${s.positions.length}`} /></b><span className="sq-muted">من <Num v={`${s.tier.seats}`} /></span></Stat>
        <Stat label="الربح/الخسارة الحالي" k="unreal"><b className={tone(unreal)}><Num v={susd(unreal)} /></b></Stat>
        <Hub s={s} sesOpen={sesOpen} />
        <Stat label="رابحة / خاسرة اليوم" k="today"><b><Num v={`${s.today.wins}`} className="pos" /> / <Num v={`${s.today.losses}`} className="neg" /></b></Stat>
        <Stat label="المحقَّق اليوم بعد العمولات" k="real"><b className={tone(s.today.realized)}><Num v={susd(s.today.realized)} /></b></Stat>
      </section>

      <nav className="seg inline-flex sq-nav" role="tablist" aria-label="صقر" data-role="sq-nav">
        {TABS.map(([k, t, I]) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} className={"seg-btn chip" + (tab === k ? " on" : "")} onClick={() => pick(k)} data-view={k}>
            <I size={14} /> {t}
          </button>
        ))}
      </nav>

      <div key={tab} className="sq-pane">
        {tab === "dash" && (
          <div className="sq-grid">
            <div className="sq-card card card-rise" data-role="sq-health">
              <h4>حالة الأنظمة</h4>
              <ul className="sq-list">
                <li><span className={"sq-dot " + (sesOpen ? "ok" : "off")} />الجلسة<b>{ses ? (ses.holiday || ses.label) : "…"}</b></li>
                <li><span className={"sq-dot " + (ago(s.health.quotes) < 60 ? "ok" : "off")} />الأسعارُ الحيّة<b>{s.health.quotes ? hhmm(s.health.quotes) : "—"}</b></li>
                <li><span className={"sq-dot " + (s.health.news === false ? "warn" : "ok")} />قراءةُ الأخبار<b>{s.health.news === false ? "غير متوفّرة" : "تعمل"}</b></li>
                <li><span className={"sq-dot " + (s.health.events === false ? "warn" : "ok")} />التقويمُ الاقتصاديّ<b>{s.health.events === false ? "غير متوفّر" : "يعمل"}</b></li>
                <li><span className={"sq-dot " + (s.health.telegram ? "ok" : "off")} />تلغرام<b>{s.health.telegram ? "مربوط" : "غير مربوط"}</b></li>
                <li><span className={"sq-dot " + (s.broker.linked ? "ok" : "off")} />الوسيط {s.broker.name}<b>{s.broker.linked ? "مربوط" : "غير مربوط"}</b></li>
                <li><span className={"sq-dot " + (ago(s.last_cycle) < 15 ? "ok" : "off")} />آخرُ دورة<b>{s.last_cycle ? `${dday(s.last_cycle)} ${hhmm(s.last_cycle)}` : "—"}</b></li>
              </ul>
            </div>
            <div className="sq-card card card-rise" data-role="sq-exposure">
              <h4>التعرّض</h4>
              <div className="sq-kv">
                <span><small>العقود</small><b><Num v={`${s.exposure.contracts}`} /></b></span>
                <span><small>التكلفة</small><b><Num v={usd(s.exposure.cost)} /></b></span>
                <span><small>القيمة الحالية</small><b><Num v={usd(s.exposure.value)} /></b></span>
                <span><small>العائد</small><b className={tone(s.exposure.ret)}><Num v={spct(s.exposure.ret)} /></b></span>
              </div>
            </div>
            <SpyCard />
            <SessionCard />
            <div className="sq-card card card-rise" data-role="sq-win">
              <h4>نسبة النجاح</h4>
              <Ring pct={s.win_rate} wins={s.wins} losses={s.losses} />
            </div>
            <div className="sq-card card card-rise wide" data-role="sq-equity">
              <h4>منحنى رأس المال <span className="sq-muted">من <Num v={usd(s.capital, 0)} /> نحو <Num v={usd(s.goal, 0)} /></span></h4>
              <div className="sq-ses"><b><Num v={usd(s.equity)} /></b><span className={tone(s.pl)}><Num v={spct(s.pl_pct)} /></span></div>
              <Spark pts={curve} base={s.capital} label="منحنى رأس مال صقر" role="sq-curve" />
            </div>
            <div className="sq-card card card-rise wide" data-role="sq-gates">
              <h4>بوّاباتُ الدخول الآن</h4>
              {s.gates.length ? <ul className="sq-gl">{s.gates.map((g, i) => <li key={i}>{g}</li>)}</ul>
                : <p className="sq-muted">{s.on && sesOpen ? "مفتوحة — يدخل صقرٌ متى وجد عقداً يستوفي قواعده." : "تُقرأ في أوّل دورةٍ من الجلسة."}</p>}
            </div>
          </div>
        )}

        {tab === "signals" && (
          <div className="sq-card card card-rise" data-role="sq-signals">
            <h4>إشاراتُ آخر مسح {s.scan?.at && <span className="sq-muted"><Num v={`${dday(s.scan.at)} ${hhmm(s.scan.at)}`} /></span>}</h4>
            {s.scan && (
              <p className="sq-muted" data-role="sq-scan">قرأ <Num v={`${s.scan.universe}`} /> رمزاً (منها <Num v={`${s.scan.movers}`} /> من الأنشط اليوم) · رشّح <Num v={`${s.scan.pool}`} /> ·
                فحص عقودَ <Num v={`${s.scan.deep}`} /> · ميزانيةُ الصفقة <Num v={usd(s.scan.budget)} /></p>
            )}
            {s.signals.length === 0 ? <p className="sq-muted">لم يمسح صقرٌ السوقَ بعد — يمسح في الجلسة الرسمية كلَّ عشرين دقيقة.</p> : (
              <ul className="sq-sig">
                {s.signals.map((g, i) => (
                  <li key={g.sym + i} data-role="sq-signal" data-verdict={g.verdict} style={{ animationDelay: `${i * 25}ms` }}>
                    <span className={"sq-v v-" + g.verdict}>{g.verdict === "chosen" ? "نُفّذ" : g.verdict === "accepted" ? "مقبول" : "مرفوض"}</span>
                    <b><Num v={g.sym} /></b>
                    {g.side && <span className="sp-side" data-side={g.side}>{g.side === "call" ? "Call" : "Put"}</span>}
                    <span className="sq-why">{g.why}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {tab === "log" && (
          <div className="sq-card card card-rise" data-role="sq-log">
            <h4>السجل</h4>
            {s.log.length === 0 ? <p className="sq-muted">لا شيءَ بعد.</p> : (
              <ul className="sq-logl">
                {s.log.map((l, i) => {
                  const [I, c] = KIND[l.kind] || KIND.info;
                  return (
                    <li key={l.at + i} data-role="sq-log-row" data-kind={l.kind}>
                      <span className={"sq-li " + c}><I size={13} /></span>
                      <Num v={`${dday(l.at)} ${hhmm(l.at)}`} className="sq-muted" />
                      <span>{l.text}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}

        {tab === "rules" && (
          <div className="sq-grid">
            <div className="sq-card card card-rise wide" data-role="sq-rules">
              <h4>كيف يدخل</h4>
              <ul className="sq-gl">
                <li>السوقُ الأمريكيّ كلُّه: الأسيلُ خياراتٍ والأنشطُ تداولاً اليوم — مسارُ كلِّ سهمٍ من شموعه، والخبرُ القويُّ المعاكسُ يُسقط الصفقة.</li>
                <li>لا يعاكس حركةَ اليوم، ولا يدخل قبل أرباح الشركة بثلاثة أيام.</li>
                <li>العقد: أجلُ <Num v={`${s.rules.dte[0]}–${s.rules.dte[1]}`} /> يوماً، فارقٌ ≤ <Num v={`${s.rules.max_spread}%`} />، دلتا <Num v={`${s.rules.delta[0]}–${s.rules.delta[1]}`} />، تآكلٌ يوميّ ≤ <Num v={`${s.rules.burn}%`} />، وحكمُ المستشار بيونانياته «مناسب».</li>
                <li>لا دخولَ في أوّل ربع ساعةٍ ولا آخرِ عشرين دقيقة، ولا حول حدثٍ اقتصاديٍّ عالي الأثر (والفيدراليُّ يوماً كاملاً)، ولا بعد خسارة <Num v={`${s.rules.day_loss}%`} /> في اليوم، ولا أكثرَ من <Num v={`${s.rules.max_new_day}`} /> صفقاتٍ يومياً.</li>
              </ul>
            </div>
            <div className="sq-card card card-rise" data-role="sq-rules-exit">
              <h4>كيف يخرج</h4>
              <ul className="sq-gl">
                <li>وقفٌ عند <Num v={`${Math.round(s.rules.stop * 100)}%`} /> من سعر الشراء.</li>
                <li>من +50٪ يرتفع الوقفُ إلى الدخول، ومن +80٪ إلى 75٪ من القمّة.</li>
                <li>جنيٌ عند تضاعف العقد أو بلوغِ السهم الهدف.</li>
                <li>خروجٌ قبل <Num v={`${s.rules.exit_dte}`} /> يوماً من الانتهاء، وعند انكسار الأطروحة.</li>
              </ul>
            </div>
            <div className="sq-card card card-rise" data-role="sq-rules-size">
              <h4>حجمُ الصفقة</h4>
              <div className="sq-tiers">
                {s.rules.tiers.map(([lim, f, n], i) => (
                  <span key={i} className={s.tier.frac === f ? "on" : ""}>
                    <small>{lim == null ? "فوق 10,000" : <>دون <Num v={usd(lim, 0)} /></>}</small>
                    <b><Num v={`${Math.round(f * 100)}%`} /> · <Num v={`${n}`} /> مراكز</b>
                  </span>
                ))}
              </div>
              <small className="sq-muted">العمولة <Num v={usd(s.rules.fee)} /> للعقد في كلّ اتّجاه · الشراءُ بالعرض والبيعُ بالطلب.</small>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
