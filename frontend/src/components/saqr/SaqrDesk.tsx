/* ══ صقر — لوحةُ وكيل التداول الآليّ ══ (‏D763 بأمر المالك 2026-11-18)
   «أضف تبويباً ثالثاً باسم صقر — وكيلُ تداولٍ آليّ… automation… يبدأ من 100 دولار ويحاول أن يوصلها إلى 10,000… وهذه صورةُ شاشته».
   فاللوحةُ من الصورة: صقرٌ في المركز وأنظمتُه حوله (الإشاراتُ وإدارةُ المخاطر والوسيطُ ومحرّكُ الأوامر والوقفُ والجنيُ والأخبارُ والمستشار)
   بحالةِ كلٍّ منها، وفي الزوايا الصفقاتُ المفتوحة والربحُ الحاليّ ورابحةُ اليوم وخاسرتُه والمحقَّقُ بعد العمولات؛ وتحتها حالُ الأنظمة والتعرّضُ
   و‏SPY وجلسةُ السوق ونسبةُ النجاح ومنحنى رأس المال — ثمّ الإشاراتُ بقبولها ورفضها وأسبابها، والسجلّ، والقواعد. والوسيطُ «غيرُ مربوط»
   صراحةً: التنفيذُ بأسعار السوق الحقيقية لحظتَها حتى يُربط ‏IBKR. */
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Radar, ShieldCheck, Cpu, ShieldAlert, Target, Newspaper, Sparkles, Play, Pause, RefreshCw,
  LayoutDashboard, Activity, ScrollText, SlidersHorizontal, ArrowDownRight, ArrowUpRight, Info, BellRing, Hand, LineChart, FileText, Filter, BarChart3, Check, Flame, Wallet, Layers } from "lucide-react";
import { marketApi } from "../../services/api";
import { useAuthStore } from "../../store/authStore";
import { useLive, useSessions } from "../chart/LiveQuote";
import { useSaqr, useSaqrMarket, money, smoney, spct, hhmm, dday, tone, type SaqrState, type Market } from "./saqr";
import MarketSwitch from "./MarketSwitch";
import SaqrEmblem from "./SaqrEmblem";
import SaqrPortfolio from "./SaqrPortfolio";
import OptionPicks from "../market/OptionPicks";

const Num = ({ v, className }: { v: string; className?: string }) => <bdi dir="ltr" className={"tabular-nums " + (className || "")}>{v}</bdi>;
type Tab = "dash" | "portfolio" | "signals" | "options" | "log" | "rules";
/* ‏D769 (المالك): «المحفظةُ داخل صقر — بجانب لوحة المعلومات والسجل»؛ و‏D777: «خلِّ عقود الخيارات داخل صقر» — للسوق الأمريكيّ */
const TABS: [Tab, string, any][] = [["dash", "لوحة المتابعة", LayoutDashboard], ["portfolio", "المحفظة", Wallet], ["signals", "الإشارات", Activity],
  ["options", "عقود الخيارات", Layers], ["log", "السجل", ScrollText], ["rules", "الإعدادات", SlidersHorizontal]];
type NState = "ok" | "warn" | "off";

const ago = (iso?: string | null) => (iso ? (Date.now() - new Date(iso).getTime()) / 60000 : Infinity);

function nodes(s: SaqrState, sesOpen: boolean): { k: string; t: string; d: ReactNode; tip: string; st: NState; icon: any }[] {
  /* ‏D767 (المالك): «أزل IBKR من القائمة التي فوق علامة صقر» — والأمريكيُّ يأخذ مكانَه «الفرزُ الأساسيّ» (قلبُ عمله الآن)، والسعوديُّ نبضُ سوقه */
  const scanAge = ago(s.scan?.at);
  const frac = Math.round(s.tier.frac * 100);
  const optStop = Math.round(s.settings?.opt_stop ?? (1 - (s.rules.stop ?? 0.6)) * 100);
  const stockStop = Math.round(s.settings?.stock_stop ?? 6);
  const newsTxt = s.health.events === false ? "التقويم متعذّر" : s.health.news === false ? "القراءة متعذّرة" : "تُقرأ";
  const eng = s.on ? (sesOpen ? "يعمل" : "ينتظر الجلسة") : "موقوف";
  const unit = s.market !== "sa" && s.settings?.per_trade ? `$${s.settings.per_trade}` : `${frac}%`;   // ‏D771: ميزانيةُ العقد أمرُ المالك
  const risk = { k: "risk", t: "إدارة المخاطر", d: <><Num v={unit} /> · <Num v={`${s.tier.seats}`} /> مراكز</>, tip: `${unit} للصفقة · ${s.tier.seats} مراكز`,
    st: (s.gates.some(x => x.includes("قاطع")) ? "warn" : "ok") as NState, icon: ShieldCheck };
  const engine = { k: "engine", t: "محرّك الأوامر", d: eng, tip: eng, st: (s.on ? (sesOpen ? "ok" : "warn") : "off") as NState, icon: Cpu };
  if (s.market === "sa") {
    const r = s.regime, pu = s.pulse;
    const tasi = r ? `${r.verdict}${r.chg != null ? ` · ${r.chg > 0 ? "+" : ""}${r.chg.toFixed(1)}%` : ""}` : "غير متوفّر";
    const br = pu ? pu.adv / Math.max(1, pu.adv + pu.dec) : null;
    return [
      { k: "signals", t: "الإشارات", d: s.scan ? <><Num v={`${s.scan.universe}`} /> شركة</> : "لم يمسح بعد", tip: s.scan ? `${s.scan.universe} شركة` : "لم يمسح بعد",
        st: s.scan && scanAge < 90 ? "ok" : sesOpen ? "warn" : "off", icon: Radar },
      { k: "results", t: "النتائج الربعية", d: pu ? <><Num v={`${pu.results.strong}`} /> قوية · <Num v={`${pu.results.weak}`} /> مخيّبة</> : <>نموّ ≥ <Num v={`${s.rules.growth}%`} /></>,
        tip: `نموُّ صافي الربح ≥ ${s.rules.growth}%`, st: "ok", icon: FileText },
      { k: "tasi", t: "مؤشّر تاسي", d: tasi, tip: tasi, st: !r ? "off" : r.verdict === "هابط" ? "warn" : "ok", icon: LineChart },
      { k: "breadth", t: "اتّساع السوق", d: pu ? <><Num v={`${pu.adv}`} /> صاعدة · <Num v={`${pu.dec}`} /> هابطة</> : "يُقرأ في الجلسة",
        tip: pu ? `${pu.adv} صاعدة · ${pu.dec} هابطة · ${pu.unch} ثابتة` : "يُقرأ في الجلسة", st: br == null ? "off" : br >= 0.5 ? "ok" : "warn", icon: BarChart3 },
      risk, engine,
      { k: "stop", t: "وقف الخسارة", d: <><Num v={`-${stockStop}%`} /> ومتحرّك</>, tip: "وقفٌ ومتحرّك", st: "ok", icon: ShieldAlert },
    ];
  }
  const full = s.scan?.full;
  return [
    { k: "signals", t: "الإشارات", d: full?.optionable ? <><Num v={`${full.optionable}`} /> ورقة</> : s.scan ? <><Num v={`${s.scan.universe}`} /> رمزاً</> : "لم يمسح بعد",
      tip: full?.optionable ? `${full.optionable} ورقةً لها عقودُ خيارات` : "لم يمسح بعد", st: s.scan && scanAge < 90 ? "ok" : sesOpen ? "warn" : "off", icon: Radar },
    { k: "fund", t: "الفرز الأساسي", d: full?.passed ? <><Num v={`${full.passed}`} /> متينة</> : "قبل الفنّ", tip: "الأساسُ قبل الفنّ: لا شطبَ ولا ضيقَ ماليّ ولا ضعف",
      st: full?.passed ? "ok" : sesOpen ? "warn" : "off", icon: Filter },
    risk, engine,
    { k: "stop", t: "وقف الخسارة", d: <><Num v={`-${optStop}%`} /> ومتحرّك</>, tip: `-${optStop}% ومتحرّك`, st: "ok", icon: ShieldAlert },
    { k: "take", t: "جني الأرباح", d: <><Num v={`×${s.settings?.take_x ?? s.rules.take}`} /> أو الهدف</>, tip: "جنيٌ عند المضاعف أو الهدف", st: "ok", icon: Target },
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
        <SaqrEmblem size={160} live={live} />
      </div>
      <span className={"sq-cstate " + (live ? "on" : "")} data-role="sq-cstate">{s.on ? (sesOpen ? "يصطاد" : "ينتظر الجلسة") : "موقوف"}</span>
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

function SessionCard({ market }: { market: Market }) {
  const ses = useSessions().data?.[market];
  const st = ses?.state;
  const timed = st === "open" || st === "pre" || st === "post" || st === "preopen" || st === "auction";
  useClock(timed);
  const left = ses?.next ? new Date(ses.next).getTime() - Date.now() : null;
  const early = /مبكّر/.test(ses?.detail || "");
  const span = (market === "sa" ? 5 : early ? 3.5 : 6.5) * 3600e3;
  const prog = st === "open" && left != null ? Math.max(0, Math.min(100, (1 - left / span) * 100)) : st === "post" || st === "closed" || st === "holiday" ? 100 : 0;
  return (
    <div className="sq-card card card-rise" data-role="sq-session" data-state={st || ""}>
      <h4>جلسة السوق {market === "sa" ? "السعوديّ" : "الأمريكيّ"}</h4>
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

function TasiCard({ s }: { s: SaqrState }) {
  const bars = useQuery({ queryKey: ["bars", "^TASI.SR", "1d"], queryFn: () => marketApi.bars("^TASI.SR", "1d").then(r => r.data?.data || []), staleTime: 15 * 60e3, retry: 0 });
  const pts = ((bars.data as any[]) || []).map(b => Number(b.close)).filter(v => isFinite(v) && v > 0).slice(-60);
  const r = s.regime;
  return (
    <div className="sq-card card card-rise" data-role="sq-tasi">
      <h4>تاسي {r && <span className={"sq-pill " + (r.verdict === "هابط" ? "s-closed" : r.verdict === "صاعد" ? "s-open" : "s-pre")}>{r.verdict}</span>}</h4>
      <div className="sq-ses"><b><Num v={r ? r.close.toLocaleString("en-US", { maximumFractionDigits: 0 }) : "—"} /></b>
        <span className={tone(r?.chg)}><Num v={spct(r?.chg, 2)} /></span></div>
      <Spark pts={pts} label="مسارُ تاسي في ستين جلسة" role="sq-tasi-line" />
    </div>
  );
}

function SaPulse({ s }: { s: SaqrState }) {
  /* ‏D767 (المالك): «في السوق السعوديّ أعد صياغتها كاملةً بشكلٍ احترافيّ — الأحداثُ الجيوسياسية ما لها دخلٌ أن تُكتب هنا»: نبضُ السوق بمقاييسه */
  const r = s.regime, pu = s.pulse;
  const n0 = (v: number) => v.toLocaleString("en-US", { maximumFractionDigits: 0 });
  const tot = pu ? pu.adv + pu.dec + pu.unch : 0;
  return (
    <div className="sq-card card card-rise wide" data-role="sq-pulse">
      <h4>نبضُ السوق السعوديّ {pu?.at && <span className="sq-muted"><Num v={`${dday(pu.at)} ${hhmm(pu.at)}`} /></span>}</h4>
      <div className="sq-pulse">
        <div className="sq-pk" data-k="tasi"><small>مؤشّر تاسي</small>
          {r ? <><b><Num v={n0(r.close)} /> <span className={tone(r.chg)}><Num v={spct(r.chg, 2)} /></span></b>
            <span>الاتجاه {r.verdict} · متوسّط 50 <Num v={n0(r.sma50)} /> · متوسّط 200 <Num v={n0(r.sma200)} /> · ثلاثة أشهر <Num v={spct(r.ret3m)} /></span></>
            : <span>غير متوفّر</span>}
        </div>
        <div className="sq-pk" data-k="breadth"><small>اتّساعُ السوق</small>
          {pu ? <><b><Num v={`${pu.adv}`} className="pos" /> صاعدة · <Num v={`${pu.dec}`} className="neg" /> هابطة · <Num v={`${pu.unch}`} /> ثابتة</b>
            <span className="sq-bar2" aria-hidden><i className="up" style={{ width: `${tot ? (pu.adv / tot) * 100 : 0}%` }} /><i className="fl" style={{ width: `${tot ? (pu.unch / tot) * 100 : 0}%` }} /><i className="dn" style={{ width: `${tot ? (pu.dec / tot) * 100 : 0}%` }} /></span></>
            : <span>يُقرأ في الجلسة</span>}
        </div>
        <div className="sq-pk" data-k="turnover"><small>قيمةُ التداول</small>
          {pu ? <b><Num v={(pu.turnover / 1e9).toFixed(2)} /> مليار ريال</b> : <span>يُقرأ في الجلسة</span>}
        </div>
        <div className="sq-pk" data-k="sectors"><small>القطاعاتُ اليوم</small>
          {pu?.leaders?.length ? <>
            <span>القائدة: {pu.leaders.map(([n, v], i) => <span key={n}>{i ? " · " : ""}{n} <Num v={spct(v, 2)} className={tone(v)} /></span>)}</span>
            <span>المتأخّرة: {pu.laggards.map(([n, v], i) => <span key={n}>{i ? " · " : ""}{n} <Num v={spct(v, 2)} className={tone(v)} /></span>)}</span></>
            : <span>يُقرأ في الجلسة</span>}
        </div>
        <div className="sq-pk" data-k="results"><small>موسمُ النتائج{pu ? <> — الربعُ المنتهي <Num v={pu.quarter} /></> : null}</small>
          {pu ? <b><Num v={`${pu.results.strong}`} className="pos" /> قوية · <Num v={`${pu.results.neutral}`} /> محايدة · <Num v={`${pu.results.weak}`} className="neg" /> مخيّبة</b>
            : <span>يُقرأ في الجلسة</span>}
        </div>
        <div className="sq-pk" data-k="oil"><small>خامُ برنت</small>
          {pu?.brent ? <b><Num v={`$${pu.brent.px.toFixed(2)}`} /> <span className={tone(pu.brent.chg)}><Num v={spct(pu.brent.chg, 2)} /></span></b> : <span>غير متوفّر</span>}
        </div>
      </div>
    </div>
  );
}

function Settings({ s, market, owner }: { s: SaqrState; market: Market; owner: boolean }) {
  /* ‏D767 (المالك): «أضف خيارَ تحديد الميزانية — 150 أو 100 — وخلّ فيه مرونة، أقدر أغيّر الخيارات؛ هو العقلُ المدبّر وأنا أضع الأوامر» */
  const qc = useQueryClient();
  const sa = market === "sa";
  const st = s.settings || {};
  const usd = money(s.ccy);
  /* ‏D769: القيمةُ الآن لا المموَّل — وتُرسَل إن غيّرها المالك وحدها (المحفظةُ تتحرّك بين العرض والحفظ فلا يُموَّل فرقُها خطأً) */
  const [budDirty, setBudDirty] = useState(false);
  const [f, setF] = useState(() => ({ budget: String(Math.round(s.equity)), per_trade: st.per_trade ? String(st.per_trade) : "", max_positions: st.max_positions ? String(st.max_positions) : "",
    instruments: st.instruments || "both", sides: st.sides || "both", opt_stop: String(st.opt_stop ?? 40), stock_stop: String(st.stock_stop ?? (sa ? 6 : 7)), take_x: String(st.take_x ?? 2),
    mode: st.mode || "balanced", day_target: st.day_target ? String(st.day_target) : "" }));
  const [msg, setMsg] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: () => marketApi.saqrSettings({ ...(budDirty ? { equity_to: f.budget } : {}), per_trade: f.per_trade || null, max_positions: f.max_positions || null,
      ...(sa ? {} : { instruments: f.instruments, sides: f.sides, opt_stop: f.opt_stop, take_x: f.take_x, day_target: f.day_target || null }), stock_stop: f.stock_stop }, market),
    onSuccess: r => { qc.setQueryData(["saqr", market], r.data.data); setBudDirty(false); setMsg("حُفظت الأوامر — تسري على الصفقات الجديدة، وقيمةُ المحفظة فوراً."); },
    onError: (e: any) => setMsg(e?.response?.data?.detail || "تعذّر الحفظ"),
  });
  const presets = sa ? [1000, 5000, 10000] : [100, 150, 300, 500];
  const set = (k: string, v: string) => { setF(x => ({ ...x, [k]: v })); setMsg(null); if (k === "budget") setBudDirty(true); };
  const Seg = ({ k, opts }: { k: "instruments" | "sides" | "mode"; opts: [string, string][] }) => (
    <span className="seg inline-flex" role="group">
      {opts.map(([v, t]) => <button key={v} type="button" disabled={!owner} className={"seg-btn chip" + (f[k] === v ? " on" : "")} onClick={() => set(k, v)} data-v={v}>{t}</button>)}
    </span>
  );
  return (
    <form className="sq-card card card-rise wide sq-set" data-role="sq-settings" onSubmit={e => { e.preventDefault(); if (owner) save.mutate(); }}>
      <h4>أوامرُك لصقر {sa ? "السعوديّ" : "الأمريكيّ"}</h4>
      {!sa && (
        <div className="sq-set-grid" data-k="mode">
          <label><small>هدفُ اليوم $</small><input className="sp-in" type="number" min={1} dir="ltr" placeholder="بلا هدف" value={f.day_target} disabled={!owner}
            onChange={e => set("day_target", e.target.value)} data-role="sq-day-target" /></label>
          <small className="sq-muted sq-set-note">العقودُ طويلةُ الأجل وحدها (150–430 يوماً). «حدُّ الصفقة الواحدة» هو ميزانيةُ العقد التي تُبنى بها قائمةُ صقر.</small>
        </div>
      )}
      <div className="sq-set-row" data-k="budget">
        <label><small>قيمةُ المحفظة الآن</small>
          <span className="op-field"><span aria-hidden>{sa ? "ر.س" : "$"}</span>
            <input type="number" min={10} step={10} dir="ltr" value={f.budget} disabled={!owner} onChange={e => set("budget", e.target.value)} data-role="sq-budget" aria-label="قيمةُ المحفظة الآن" /></span>
        </label>
        <span className="op-presets">{presets.map(v => <button key={v} type="button" disabled={!owner} className={"seg-btn chip" + (Number(f.budget) === v ? " on" : "")}
          onClick={() => set("budget", String(v))} data-role="sq-budget-preset"><Num v={usd(v, 0)} /></button>)}</span>
        <small className="sq-muted">قيمتُها الآن <Num v={usd(s.equity)} /> — اكتب ما تريد، والفرقُ يُضاف إلى النقد أو يُسحب منه بلا محوٍ للسجلّ.</small>
      </div>
      <div className="sq-set-grid">
        <label><small>حدُّ الصفقة الواحدة</small><input className="sp-in" type="number" min={5} dir="ltr" placeholder="تلقائيّ" value={f.per_trade} disabled={!owner}
          onChange={e => set("per_trade", e.target.value)} data-role="sq-per-trade" /></label>
        <label><small>أقصى المراكز</small><input className="sp-in" type="number" min={1} max={12} dir="ltr" placeholder="تلقائيّ" value={f.max_positions} disabled={!owner}
          onChange={e => set("max_positions", e.target.value)} data-role="sq-max-pos" /></label>
        {!sa && <label><small>وقفُ العقد ٪</small><input className="sp-in" type="number" min={20} max={70} dir="ltr" value={f.opt_stop} disabled={!owner} onChange={e => set("opt_stop", e.target.value)} /></label>}
        <label><small>وقفُ السهم ٪</small><input className="sp-in" type="number" min={2} max={20} dir="ltr" value={f.stock_stop} disabled={!owner} onChange={e => set("stock_stop", e.target.value)} /></label>
        {!sa && <label><small>جنيُ العقد ×</small><input className="sp-in" type="number" min={1.3} max={5} step={0.1} dir="ltr" value={f.take_x} disabled={!owner} onChange={e => set("take_x", e.target.value)} /></label>}
      </div>
      {!sa && (
        <div className="sq-set-grid">
          <label><small>الأداة</small><Seg k="instruments" opts={[["both", "عقودٌ وأسهم"], ["options", "عقودٌ فقط"], ["stocks", "أسهمٌ فقط"]]} /></label>
          <label><small>الاتجاه</small><Seg k="sides" opts={[["both", "شراءٌ وبيع"], ["calls", "شراءٌ فقط"]]} /></label>
        </div>
      )}
      {owner && (
        <div className="sq-set-act">
          <button type="submit" className="btn-primary sq-btn" disabled={save.isPending} data-role="sq-save"><Check size={14} /> حفظ الأوامر</button>
          {msg && <span className={save.isError ? "sp-err" : "sq-ok"} role="status" data-role="sq-save-msg">{msg}</span>}
        </div>
      )}
    </form>
  );
}

const KIND: Record<string, [any, string]> = { buy: [ArrowUpRight, "pos"], sell: [ArrowDownRight, "neg"], alert: [BellRing, "warn"], manual: [Hand, "info"], info: [Info, ""], error: [ShieldAlert, "neg"] };

export default function SaqrDesk() {
  const owner = useAuthStore((st: any) => st.isOwner);
  const qc = useQueryClient();
  const [market, setMarket] = useSaqrMarket();
  const sa = market === "sa";
  const q = useSaqr(market);
  const s = q.data;
  const ses = useSessions().data?.[market];
  const sesOpen = ses?.state === "open";
  const usd = money(s?.ccy), susd = smoney(s?.ccy);
  const [tab0, setTab] = useState<Tab>(() => { try { return (localStorage.getItem("sp_saqr_tab") as Tab) || "dash"; } catch { return "dash"; } });
  // عقودُ الخيارات للسوق الأمريكيّ وحده؛ و«الإشارات» للسعوديّ وحده (‏D778: «قائمةُ العقود لا فايدة منها — نكتفي بعقود الخيارات»)
  const tab: Tab = sa && tab0 === "options" ? "dash" : !sa && tab0 === "signals" ? "options" : tab0;
  const pick = (t: Tab) => { setTab(t); try { localStorage.setItem("sp_saqr_tab", t); } catch { /* */ } };
  const toggle = useMutation({ mutationFn: (on: boolean) => marketApi.saqrToggle(on, market), onSuccess: r => qc.setQueryData(["saqr", market], r.data.data) });
  /* ‏D771 (المالك): «زرٌّ أوقف التداولَ الآليّ — وهو يطلع العقودَ ويشتغل مثل السكرتير»: الأمريكيُّ ينفّذ أوامرَ المالك، وآلياً من قائمته إن شغّله */
  const autoM = useMutation({ mutationFn: (on: boolean) => marketApi.saqrSettings({ auto: on }, "us"), onSuccess: r => qc.setQueryData(["saqr", "us"], r.data.data) });
  const run = useMutation({ mutationFn: () => marketApi.saqrRun(market), onSuccess: () => setTimeout(() => q.refetch(), 700) });
  const curve = useMemo(() => (s?.equity_curve || []).map(p => p[1]), [s?.equity_curve]);
  const sw = <MarketSwitch value={market} onChange={setMarket} />;
  const nav = (
    <nav className="seg inline-flex sq-nav" role="tablist" aria-label="صقر" data-role="sq-nav">
      {TABS.filter(([k]) => !(sa && k === "options") && !(!sa && k === "signals")).map(([k, t, I]) => (
        <button key={k} type="button" role="tab" aria-selected={tab === k} className={"seg-btn chip" + (tab === k ? " on" : "")} onClick={() => pick(k)} data-view={k}>
          <I size={14} /> {t}
        </button>
      ))}
    </nav>
  );
  // ‏D777: عقودُ الخيارات لا تنتظر حالَ صقر — تُفتح فوراً
  if (!s || !Array.isArray(s.positions)) return (
    <div className="sq" data-role="sq">{sw}{nav}{tab === "options" ? <div key="options" className="sq-pane"><OptionPicks /></div> : <div className="h-60 skeleton rounded-xl" />}</div>
  );
  const unreal = s.positions.reduce((a, p) => a + p.pl, 0);
  const busy = s.running?.on || run.isPending;

  return (
    <div className="sq" data-role="sq" data-market={market}>
      {sw}
      <header key={market} className="sq-head">
        <span className="sq-id"><SaqrEmblem size={30} live={s.on && sesOpen} /><b>صقر {sa ? "السعوديّ" : "الأمريكيّ"}</b>
          {sa ? <span className={"sq-pill " + (s.on ? (sesOpen ? "s-open" : "s-pre") : "s-closed")} data-role="sq-state">{s.on ? (sesOpen ? "يعمل الآن" : "يعمل في الجلسة") : "موقوف"}</span>
            : <span className={"sq-pill " + (s.settings?.auto ? (sesOpen ? "s-open" : "s-pre") : "s-pre")} data-role="sq-state">{s.settings?.auto ? (sesOpen ? "يتداول آلياً" : "آليٌّ في الجلسة") : "ينفّذ أوامرك"}</span>}
        </span>
        <span className="sq-sub">{sa ? "أسهمُ الشركات" : "عقودُ الخيارات الطويلة"} · التنفيذُ بأسعار السوق الحقيقية</span>
        {owner && (
          <span className="sq-acts">
            <button type="button" className="btn-ghost sq-btn" onClick={() => run.mutate()} disabled={busy} data-role="sq-run" title={s.running?.msg || "دورةٌ الآن"}>
              <RefreshCw size={14} className={busy ? "rl-spin" : ""} /> {busy ? (s.running?.msg || "يعمل") : "دورةٌ الآن"}
            </button>
            {sa ? (
              <button type="button" className={(s.on ? "btn-ghost" : "btn-primary") + " sq-btn"} onClick={() => toggle.mutate(!s.on)} disabled={toggle.isPending} data-role="sq-toggle">
                {s.on ? <><Pause size={14} /> إيقاف</> : <><Play size={14} /> تشغيل</>}
              </button>
            ) : (
              <button type="button" className={(s.settings?.auto ? "btn-ghost" : "btn-primary") + " sq-btn"} onClick={() => autoM.mutate(!s.settings?.auto)} disabled={autoM.isPending}
                data-role="sq-auto" aria-pressed={!!s.settings?.auto}>
                {s.settings?.auto ? <><Pause size={14} /> أوقف التداول الآليّ</> : <><Play size={14} /> شغّل التداول الآليّ</>}
              </button>
            )}
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

      {nav}

      <div key={tab} className="sq-pane">
        {tab === "dash" && (
          <div className="sq-grid">
            {s.day?.target ? (
              <div className="sq-card card card-rise wide" data-role="sq-day">
                <h4><Flame size={14} aria-hidden /> هدفُ اليوم <span className="sq-muted"><Num v={usd(s.day.target, 0)} />{s.settings?.mode === "attack" ? " · النمطُ الهجوميّ" : ""}</span></h4>
                <div className="sq-ses"><b className={tone(s.day.pl)}><Num v={susd(s.day.pl)} /></b>
                  <span className="sq-muted">{s.day.hit ? <>بلغه <Num v={hhmm(s.day.hit)} /> — الرابحاتُ محميّةٌ عند دخولها والصيدُ مستمرّ</> : <>صفقاتُ اليوم <Num v={`${s.day.new}`} /></>}</span></div>
                <span className="sp-bar"><i style={{ width: `${s.day.progress ?? 0}%` }} /></span>
              </div>
            ) : null}
            <div className="sq-card card card-rise" data-role="sq-health">
              <h4>حالة الأنظمة</h4>
              <ul className="sq-list">
                <li><span className={"sq-dot " + (sesOpen ? "ok" : "off")} />الجلسة<b>{ses ? (ses.holiday || ses.label) : "…"}</b></li>
                <li><span className={"sq-dot " + (ago(s.health.quotes) < 60 ? "ok" : "off")} />{sa ? "لقطةُ «تداول» الحيّة" : "الأسعارُ الحيّة"}<b>{s.health.quotes ? hhmm(s.health.quotes) : "—"}</b></li>
                {sa ? <>
                  <li><span className={"sq-dot " + (s.health.events === false ? "warn" : "ok")} />مسارُ تاسي<b>{s.health.events === false ? "غير متوفّر" : "يعمل"}</b></li>
                  <li><span className={"sq-dot " + (s.pulse ? "ok" : "off")} />النتائجُ الربعية<b>{s.pulse ? <><Num v={`${Object.values(s.pulse.results).reduce((a, b) => a + b, 0)}`} /> شركة</> : "—"}</b></li>
                </> : <>
                  <li><span className={"sq-dot " + (s.health.news === false ? "warn" : "ok")} />قراءةُ الأخبار<b>{s.health.news === false ? "غير متوفّرة" : "تعمل"}</b></li>
                  <li><span className={"sq-dot " + (s.health.events === false ? "warn" : "ok")} />التقويمُ الاقتصاديّ<b>{s.health.events === false ? "غير متوفّر" : "يعمل"}</b></li>
                  <li><span className={"sq-dot " + (s.scan?.full?.passed ? "ok" : "off")} />الفرزُ الأساسيّ<b>{s.scan?.full?.passed ? <><Num v={`${s.scan.full.passed}`} /> متينة</> : "—"}</b></li>
                </>}
                <li><span className="sq-dot ok" />التنفيذ<b>بأسعار السوق</b></li>
                <li><span className={"sq-dot " + (ago(s.last_cycle) < 15 ? "ok" : "off")} />آخرُ دورة<b>{s.last_cycle ? `${dday(s.last_cycle)} ${hhmm(s.last_cycle)}` : "—"}</b></li>
              </ul>
            </div>
            <div className="sq-card card card-rise" data-role="sq-exposure">
              <h4>التعرّض</h4>
              <div className="sq-kv">
                <span><small>{sa ? "الأسهم" : "العقود والأسهم"}</small><b><Num v={`${s.exposure.contracts}`} /></b></span>
                <span><small>التكلفة</small><b><Num v={usd(s.exposure.cost)} /></b></span>
                <span><small>القيمة الحالية</small><b><Num v={usd(s.exposure.value)} /></b></span>
                <span><small>العائد</small><b className={tone(s.exposure.ret)}><Num v={spct(s.exposure.ret)} /></b></span>
              </div>
            </div>
            {sa ? <TasiCard s={s} /> : <SpyCard />}
            <SessionCard market={market} />
            <div className="sq-card card card-rise" data-role="sq-win">
              <h4>نسبة النجاح</h4>
              <Ring pct={s.win_rate} wins={s.wins} losses={s.losses} />
            </div>
            <div className="sq-card card card-rise wide" data-role="sq-equity">
              <h4>منحنى رأس المال <span className="sq-muted">من <Num v={usd(s.capital, 0)} /> نحو <Num v={usd(s.goal, 0)} /></span></h4>
              <div className="sq-ses"><b><Num v={usd(s.equity)} /></b><span className={tone(s.pl)}><Num v={spct(s.pl_pct)} /></span></div>
              <Spark pts={curve} base={s.capital} label="منحنى رأس مال صقر" role="sq-curve" />
            </div>
            {sa && <SaPulse s={s} />}
            <div className="sq-card card card-rise wide" data-role="sq-gates">
              <h4>بوّاباتُ الدخول الآن</h4>
              {s.gates.length ? <ul className="sq-gl">{s.gates.map((g, i) => <li key={i}>{g}</li>)}</ul>
                : <p className="sq-muted">{s.on && sesOpen ? `مفتوحة — يدخل صقرٌ متى وجد ${sa ? "شركةً تستوفي" : "عقداً أو سهماً يستوفي"} قواعده.` : "تُقرأ في أوّل دورةٍ من الجلسة."}</p>}
            </div>
          </div>
        )}


        {tab === "signals" && sa && (
          <div className="sq-card card card-rise" data-role="sq-signals">
            <h4>إشاراتُ آخر مسح {s.scan?.at && <span className="sq-muted"><Num v={`${dday(s.scan.at)} ${hhmm(s.scan.at)}`} /></span>}</h4>
            {s.scan && (
              <p className="sq-muted" data-role="sq-scan">{sa
                ? <>قرأ <Num v={`${s.scan.universe}`} /> شركة · اجتاز السيولةَ والنتائج <Num v={`${s.scan.pool}`} /> · فحص مسارَ <Num v={`${s.scan.deep}`} /> · ميزانيةُ الصفقة <Num v={usd(s.scan.budget)} /></>
                : s.scan.full && !s.scan.full.fallback
                  ? <>قرأ <Num v={`${s.scan.full.optionable}`} /> ورقةً لها عقودُ خيارات (من دليل سيبوي) · اجتاز الأساسَ <Num v={`${s.scan.full.passed}`} /> ·
                    رشّح <Num v={`${s.scan.pool}`} /> · فحص عقودَ <Num v={`${s.scan.deep}`} /> · ميزانيةُ الصفقة <Num v={usd(s.scan.budget)} /></>
                  : <>قرأ <Num v={`${s.scan.universe}`} /> رمزاً (منها <Num v={`${s.scan.movers}`} /> من الأنشط اليوم) · رشّح <Num v={`${s.scan.pool}`} /> ·
                    فحص عقودَ <Num v={`${s.scan.deep}`} /> · ميزانيةُ الصفقة <Num v={usd(s.scan.budget)} /></>}</p>
            )}
            {!sa && s.scan?.full?.excluded && Object.keys(s.scan.full.excluded).length > 0 && (
              <details className="robo-held" data-role="sq-fund">
                <summary><span>الفرزُ الأساسيّ قبل الفنّ — استُبعد <Num v={`${Object.values(s.scan.full.excluded as Record<string, number>).reduce((a, b) => a + b, 0)}`} /></span></summary>
                <ul>{Object.entries(s.scan.full.excluded as Record<string, number>).map(([k, n]) => <li key={k}>{k}: <b><Num v={`${n}`} /></b></li>)}</ul>
              </details>
            )}
            {s.signals.length === 0 ? <p className="sq-muted">لم يمسح صقرٌ السوقَ بعد — يمسح في الجلسة الرسمية كلَّ عشرين دقيقة.</p> : (
              <ul className="sq-sig">
                {s.signals.map((g, i) => (
                  <li key={g.sym + i} data-role="sq-signal" data-verdict={g.verdict} style={{ animationDelay: `${i * 25}ms` }}>
                    <span className={"sq-v v-" + g.verdict}>{g.verdict === "chosen" ? "نُفّذ" : g.verdict === "accepted" ? "مقبول" : "مرفوض"}</span>
                    <b><Num v={g.sym} />{g.name ? <small className="sq-muted"> {g.name}</small> : null}</b>
                    {g.side && <span className="sp-side" data-side={g.side}>{g.side === "call" ? "Call" : "Put"}</span>}
                    <span className="sq-why">{g.why}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {tab === "portfolio" && <SaqrPortfolio market={market} />}
        {tab === "options" && !sa && <OptionPicks />}

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

        {tab === "rules" && <Settings key={market} s={s} market={market} owner={owner} />}

        {tab === "rules" && sa && (
          <div className="sq-grid">
            <div className="sq-card card card-rise wide" data-role="sq-rules">
              <h4>منهجيةُ الاختيار — أسهمُ السوق السعوديّ</h4>
              <ul className="sq-gl">
                <li>اتجاهُ المؤشّر العامّ أوّلاً: تاسي دون متوسّطيه ⇐ لا مراكزَ جديدة، وفي نطاقٍ عرضيّ ⇐ نصفُ الحجم، وتراجعُه <Num v={`${s.rules.tasi_panic}%`} /> في الجلسة ⇐ لا دخولَ اليوم.</li>
                <li>النتائجُ الربعية: نموُّ صافي الربح عن الربع المماثل <Num v={`${s.rules.growth}%`} /> فأكثر بإعلانٍ حديث، وتُستبعد الخاسرةُ والمتراجعة، ولا دخولَ قبل نتائجَ لم تصدر في مهلتها.</li>
                <li>جودةُ السهم: تداولُ اليوم <Num v={`${(s.rules.min_turnover / 1e6).toFixed(0)}`} /> ملايين ريال فأكثر، وفارقُ العرض والطلب <Num v={`${s.rules.max_spread}%`} /> فأقلّ، والموقوفةُ مستبعَدة.</li>
                <li>القوّةُ النسبية: مسارٌ صاعدٌ فوق متوسّط 50، وأداءٌ يتفوّق على تاسي في ثلاثة أشهر — ولا مطاردةَ لارتفاعٍ يوميّ فوق 6٪.</li>
                <li>الانضباط: لا دخولَ في أوّل ربع ساعةٍ ولا قبل المزاد، وحدٌّ يوميّ <Num v={`${s.rules.max_new_day}`} /> صفقتين، وتوقّفٌ عند خسارة <Num v={`${s.rules.day_loss}%`} /> في اليوم.</li>
              </ul>
            </div>
            <div className="sq-card card card-rise" data-role="sq-rules-exit">
              <h4>إدارةُ المركز</h4>
              <ul className="sq-gl">
                <li>وقفُ خسارةٍ عند <Num v={`-${Math.round(s.settings?.stock_stop ?? 6)}%`} />، ويرتفع إلى سعر الدخول من +8٪، وإلى 94٪ من القمّة من +12٪.</li>
                <li>جنيُ الربح عند الهدف الفنيّ (قمّةُ السنة أو +12٪).</li>
                <li>خروجٌ إذا انقلب تاسي هابطاً والمركزُ خاسر، أو صدرت نتائجُ مخيّبة بعد الدخول.</li>
                <li>تحريرُ المال من مركزٍ لم يتقدّم 3٪ في ستّة أسابيع.</li>
              </ul>
            </div>
            <div className="sq-card card card-rise" data-role="sq-rules-size">
              <h4>حجمُ الصفقة</h4>
              <div className="sq-tiers">
                {s.rules.tiers.map(([lim, f, n]: [number | null, number, number], i: number) => (
                  <span key={i} className={s.tier.frac === f ? "on" : ""}>
                    <small>{lim == null ? "فوق 50,000" : <>دون <Num v={usd(lim, 0)} /></>}</small>
                    <b><Num v={`${Math.round(f * 100)}%`} /> · <Num v={`${n}`} /> مراكز</b>
                  </span>
                ))}
              </div>
              <small className="sq-muted">العمولة <Num v={`${s.rules.fee_pct.toFixed(3)}%`} /> لكلّ جهة · الشراءُ بالعرض والبيعُ بالطلب من لقطة «تداول».</small>
            </div>
          </div>
        )}

        {tab === "rules" && !sa && (
          <div className="sq-grid">
            <div className="sq-card card card-rise wide" data-role="sq-rules">
              <h4>كيف تُبنى قائمةُ العقود</h4>
              <ul className="sq-gl">
                <li>السوقُ الأمريكيّ كلُّه: كلُّ ورقةٍ لها عقودُ خيارات (دليلُ سيبوي) وسائلة.</li>
                <li>الأساسُ قبل الفنّ: لا سعرَ دون 5 دولارات (منطقةُ الشطب)، ولا قيمةَ دون ملياري دولار، ولا ضيقَ ماليّ (Altman دون 1.81)، ولا متانةَ دون
                  الممتاز (Piotroski ‏5 من 9 فأكثر)، ولا خسارةً تحرق النقد، ولا دينَ مفرطاً ولا سيولةً ضعيفة — ودرجةُ المتانة 65 فأكثر؛ والصناديقُ العميقةُ
                  وحدها (تداولٌ يوميّ ≥ 200 مليون دولار) بلا المرفوعِ ولا صناديقِ الدخل بالعقود.</li>
                <li>ثمّ المسار: صاعدٌ أو هابطٌ واضح، والخبرُ القويُّ المعاكسُ يُسقط الصفقة.</li>
                <li>طويلُ الأجل وحده: تختار من «عقود الخيارات» وتنفّذ من بطاقتها بأوامرك (‏D778) — والتداولُ الآليُّ <b>{s.settings?.auto ? "يعمل" : "موقوف"}</b>
                  {s.settings?.auto ? <>، يشتري ممّا يفحصه صقرٌ في الجلسة حتى <Num v={`${s.rules.max_new_day}`} /> صفقاتٍ يومياً</> : null}.</li>
                <li>العقد: أجلُ <Num v={`${s.rules.dte[0]}–${s.rules.dte[1]}`} /> يوماً، وكلفتُه ضمن ميزانية العقد، وعرضٌ وطلبٌ حقيقيّان بفارقٍ ≤ <Num v={`${s.rules.max_spread}%`} />،
                  ودلتا <Num v={`${s.rules.delta[0]}–${s.rules.delta[1]}`} />، ونقطةُ تعادلٍ دون الهدف الفنيّ، وربحٌ عنده <Num v="75%" /> من الكلفة فأكثر.</li>
                <li>لكلّ عقدٍ إيجابياتُه وسلبياتُه بأرقامها (المسار · الزخم · الأساس · الخبر · الربح والاحتمال · الفارق · السيولة · الأجل) — وما زادت سلبياتُه على إيجابياته لا يدخل القائمة،
                  ومعه سعرُ السهم الذي يربح عنده العقدُ <Num v="30%" />.</li>
                <li>ثمّ فريقُ صقر (‏D776) — ستّةُ أعضاءٍ يحكم كلٌّ بسطر: الأساس · الفنّ · خبرُ الشركة نفسِها · اليونانيات (الدلتا والتآكلُ الأسبوعيّ) ·
                  المخاطر (الفارق والسيولة وموعدُ الأرباح) · الاحتمال؛ ورفضُ واحدٍ يُسقط العقد. ونسبةُ النجاح احتمالُ بلوغ <Num v="+30%" /> قبل الوقف
                  وقبل الخروج كما يسعّرها التذبذبُ الضمنيّ — تقديرٌ لا وعد، والفعليُّ في «سجلّ الفريق».</li>
                <li>التداولُ الآليُّ إن شغّلته: في الجلسة الرسمية وحدها، لا في أوّل ربع ساعةٍ ولا آخرِ عشرين دقيقة، ولا حول حدثٍ اقتصاديٍّ عالي الأثر، ولا بعد خسارة <Num v={`${s.rules.day_loss}%`} /> في اليوم.</li>
              </ul>
            </div>
            <div className="sq-card card card-rise" data-role="sq-rules-exit">
              <h4>كيف يخرج</h4>
              <ul className="sq-gl">
                <li>ما نفّذتَه بأوامرك: يبيعه صقر عند أمر جني الربح أو أمر الوقف كما كتبتهما، أو حين تضغط «إغلاق» بسعر السوق — وقبل الانتهاء بـ<Num v={`${s.rules.exit_dte}`} /> يوماً.</li>
                <li>وما اشتراه آلياً: وقفٌ عند <Num v={`${Math.round(s.rules.stop * 100)}%`} /> من سعر الشراء.</li>
                <li>من <Num v={`+${Math.round((s.rules.trail[0] - 1) * 100)}%`} /> يرتفع الوقفُ إلى الدخول، ومن <Num v={`+${Math.round((s.rules.trail[1] - 1) * 100)}%`} /> إلى <Num v={`${Math.round(s.rules.trail[2] * 100)}%`} /> من القمّة.</li>
                <li>بلوغُ هدف اليوم يحمي كلَّ رابحٍ عند سعر دخوله، والصيدُ مستمرٌّ بلا سقف.</li>
                <li>جنيٌ عند تضاعف العقد أو بلوغِ السهم الهدف.</li>
                <li>خروجٌ قبل <Num v={`${s.rules.exit_dte}`} /> يوماً من الانتهاء، وعند انكسار الأطروحة.</li>
              </ul>
            </div>
            <div className="sq-card card card-rise" data-role="sq-rules-size">
              <h4>حجمُ الصفقة</h4>
              {s.settings?.per_trade ? (
                <p className="sq-gl" data-role="sq-unit">ميزانيةُ الصفقة <b><Num v={usd(s.settings.per_trade, 0)} /></b> بأمرك، ومقعدٌ لكلّ <Num v={usd(s.settings.per_trade, 0)} /> في رأس المال
                  (<Num v={`${s.tier.seats}`} /> {s.tier.seats === 1 ? "مقعد" : "مقاعد"} الآن) — وكلّما كبر رأسُ المال كثرت الصفقاتُ معاً.</p>
              ) : (
              <div className="sq-tiers">
                {s.rules.tiers.map(([lim, f, n]: [number | null, number, number], i: number) => (
                  <span key={i} className={s.tier.frac === f ? "on" : ""}>
                    <small>{lim == null ? "فوق 10,000" : <>دون <Num v={usd(lim, 0)} /></>}</small>
                    <b><Num v={`${Math.round(f * 100)}%`} /> · <Num v={`${n}`} /> مراكز</b>
                  </span>
                ))}
              </div>
              )}
              <small className="sq-muted">العمولة <Num v={usd(s.rules.fee)} /> للعقد في كلّ اتّجاه · الشراءُ بالعرض والبيعُ بالطلب.</small>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
