/* ══ الرسمُ البيانيّ الاحترافيّ — غرفةُ التداول ══ (بأمر المالك 2026-11-15 · D736)

   «سخّر كلَّ الإمكانيات لجعل الرسم البيانيّ وطريقةِ عرضه وجمالِه وثباتِه وتحريكِ السهم ومؤشّرِ D7M والدعوم شبيهاً بتريدنق فيو
   سلاسةً ودقّةً وثباتاً… الشموعُ كأنها ديكور… المؤشّراتُ رسومُها فارغة… أبغى شغلاً حقيقياً احترافياً يغنيني عن تريدنق فيو».

   ما كان (‏NativeChart): كلُّ الشموع تُحشر في عرض الشاشة (‏fitContent) فتصير خيوطاً؛ وعجلةُ الفأرة معطَّلة؛ والرسمُ يُهدم ويُبنى
   مع كلّ تغييرٍ فيضيع الموضعُ والتكبير؛ والمؤشّراتُ السفلى هوامشُ على مقياسٍ واحد بلا محورٍ لها؛ والمستوياتُ والوسومُ عناصرُ
   صفحةٍ تتأخّر عن الشموع. وما صار:
     · رسمٌ واحدٌ يُنشأ مرّةً — البياناتُ والمؤشّراتُ تُحدَّث فيه، والشمعةُ الجاريةُ تتحرّك في مكانها، والموضعُ يبقى.
     · شموعٌ بعرضٍ مقروء (آخرُ ما يسعه الرسم)، والسحبُ والعجلةُ والقرصُ والمحوران كتريدنق فيو، وزرٌّ يعود إلى آخر شمعة.
     · لكلّ مؤشّرٍ سفليٍّ لوحةٌ حقيقيةٌ بمحورها وفاصلٍ يُسحب (المكتبةُ الخامسة)، ووسيلةُ إيضاحٍ بقيمه تتبع خطَّ التقاطع.
     · المستوياتُ والخطوطُ والفرشاةُ تُرسم في دورة رسم الشموع نفسِها (‏lib/chartOverlay) فلا تتأخّر ولا ترتجف.
     · أيُّ إطار: الجاهزُ والمخصَّص (عددٌ + وحدة)، وأنواعُ رسم، ولقطةٌ، وملءُ الشاشة. والمكتبةُ مع التطبيق لا تُنزَّل عند الفتح. */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  createChart, CandlestickSeries, BarSeries, LineSeries, AreaSeries, HistogramSeries, createSeriesMarkers, CrosshairMode, LineStyle,
  PriceScaleMode, type IChartApi, type ISeriesApi, type MouseEventParams, type Logical,
} from "lightweight-charts";
import {
  CandlestickChart, LineChart, AreaChart, BarChart3, Activity, Brush, TrendingUp, Minus, Trash2, Undo2, Camera, Maximize2, Minimize2,
  Settings2, ChevronDown, Check, MousePointer2, ChevronsRight,
} from "lucide-react";
import { marketApi } from "../../services/api";
import {
  sanitizeBars, CBar, TF_BAR, TF_PRESETS, TF_UNITS, TfUnit, parseTf, tfKey, tfShort, tfLong, tfIntraday, tickLabel, crossLabel, fmtPrice, fmtVol,
  TZ_LIST, exchangeTz, tzOffsetMin, fmtOffset, displayTimes,
} from "../../lib/chartData";
import { researchInd } from "../../lib/researchIndicator";
import { ChartOverlay, BandFill, Level, Segment, Path, Note, Band } from "../../lib/chartOverlay";
import { cvdD7M, CVD_DEFAULTS, CvdCfg, stochRsi, STOCHRSI_DEFAULTS, StochRsiCfg, source } from "../../lib/indicators";
import IndSettings from "./IndSettings";
import {
  autoFib, autoChannel, autoTrend, vwapAnchored, ema as emaD7, dashboard, macdSmart, tradeTool, D7M_DEFAULTS, D7MSettings, D7M_COLORS,
} from "../analysis/d7m";
import D7MPanel from "../analysis/D7MPanel";
import D7MStrip from "./D7MStrip";

/* ‏D744 (المالك 2026-11-15): «لا أريد كثرةَ المؤشّرات — أريد CVD ومؤشّرَ الدحم وStoch RSI المدمج». فهي الثلاثة مع الحجم، ولكلٍّ إعداداتُه
   كتريدنق فيو (ترسٌ واحدٌ يفتح نافذةَ كلّ مؤشّر). كانت معها: SMA 20/50/200 وRSI وStochastic وMACD. */
/* ‏D753 (المالك 2026-11-16): «مؤشّرُ الأبحاث — مطابقٌ لمؤشّر الجزيرة كابيتال»: متوسّطا 20 و50 وفيبوناتشي وخطّا الاتجاه وأسهمُ الإشارة فوق،
   ولوحتا الكمّية وRSI 14 تحت — بشيفرة ورقة التقرير اليوميّ نفسِها (‏lib/researchIndicator). */
type IndKey = "vol" | "stochrsi" | "cvd" | "d7m" | "research";
const IND: [IndKey, string, string][] = [
  ["vol", "الحجم", "--ink-muted"], ["stochrsi", "Stoch RSI", "--info-ink"], ["cvd", "CVD D7M", "--chart-3"], ["d7m", "D7M", "--brand-ink"],
  ["research", "مؤشر الأبحاث", "--ri-fib"]];
const OSC: IndKey[] = ["stochrsi", "cvd", "research"];
const IND_DEF: Record<IndKey, boolean> = { vol: true, stochrsi: true, cvd: true, d7m: true, research: false };
type ChartType = "candles" | "hollow" | "bars" | "line" | "area";
const TYPES: [ChartType, string, any][] = [["candles", "شموع", CandlestickChart], ["hollow", "شموعٌ مفرَّغة", CandlestickChart],
  ["bars", "أعمدة", BarChart3], ["line", "خطّ", LineChart], ["area", "منطقة", AreaChart]];
type Tool = null | "trend" | "hline" | "brush";
/* أزرارُ المدى أسفلَ الرسم كتريدنق فيو: كلٌّ يختار إطارَه ويعرض مدّتَه */
const RANGES: [string, number | "ytd" | "all", string][] = [["يوم", 1, "1m"], ["5 أيام", 5, "5m"], ["شهر", 30, "30m"], ["3 أشهر", 91, "1h"],
  ["6 أشهر", 182, "2h"], ["منذ بداية العام", "ytd", "1d"], ["سنة", 365, "1d"], ["5 سنوات", 1826, "1wk"], ["الكل", "all", "1mo"]];

const lsGet = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const lsSet = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* وضعُ التصفّح الخاصّ */ } };
const lsJson = <T,>(k: string, def: T): T => { try { return { ...def, ...(JSON.parse(lsGet(k) || "{}") || {}) }; } catch { return def; } };

/* الرموزُ لا تصل لوحةَ الرسم (‏canvas لا تفهم var) — تُقرأ قيمُها المحسوبة عند الرسم، والرمزُ يبقى مصدرَ الحقيقة */
const tok = (name: string, fb: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fb;
/** رمزٌ يُعرف اسمُه وقتَ التشغيل (ألوانُ D7M من جدولها) — واحتياطُه حبرُ النصّ الثانويّ. */
const tokv = (name: string) => tok(name, "") || tok("--ink-muted", "#6b7280");
const tokA = (name: string, fb: string, a: number) => {
  const c = tok(name, fb);
  const m = /^#([0-9a-f]{6})$/i.exec(c);
  if (m) { const n = parseInt(m[1], 16); return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`; }
  const p = c.match(/[\d.]+/g);
  return p && p.length >= 3 ? `rgba(${p[0]}, ${p[1]}, ${p[2]}, ${a})` : c;
};

/** قائمةٌ تنسدل تحت زرّها وتُطوى بالنقر خارجها. */
function Menu({ label, title, children, role, wide, up }: {
  label: React.ReactNode; title: string; role?: string; wide?: boolean; up?: boolean; children: (close: () => void) => React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const away = (e: Event) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);
  return (
    <div ref={ref} className="pc-menu-wrap">
      <button type="button" className={"pc-btn" + (open ? " on" : "")} title={title} aria-label={title} aria-expanded={open}
        data-role={role} onClick={() => setOpen(o => !o)}>{label}</button>
      {open && <div className={"sp-menu pc-menu" + (wide ? " pc-menu-wide" : "") + (up ? " pc-menu-up" : "")} data-role={role ? role + "-menu" : undefined}>{children(() => setOpen(false))}</div>}
    </div>
  );
}

/* ‏preset «stock»: صفحةُ السهم (‏D739 — كانت على الرسم القديم): الرسمُ نفسُه بإطارٍ أسبوعيٍّ وD7M افتراضاً، واختياراتُها محفوظةٌ
   لها وحدها فلا تمسّ غرفةَ التداول، وبلا لوحة القرار فوقه (‏D652). والرسمُ اليدويُّ واحدٌ للرمز في المكانين كتريدنق فيو. */
const IND_STOCK: Record<IndKey, boolean> = { vol: true, stochrsi: false, cvd: false, d7m: true, research: false };

export default function ProChart({ symbol, identity, theme = "dark", preset }: {
  symbol: string; identity?: React.ReactNode; theme?: "dark" | "light"; preset?: "stock";
}) {
  /* ── الاختيارات المحفوظة ── */
  const KT = preset ? "sp_stock_tf" : "sp_chart_tf", KI = preset ? "sp_stock_ind_v3" : "sp_chart_ind_v3";
  const [tf, setTfState] = useState(() => { const v = lsGet(KT); return v && parseTf(v) ? v : "1wk"; });
  const setTf = (v: string) => { if (parseTf(v)) { setTfState(v); lsSet(KT, v); } };
  const [customTfs, setCustomTfs] = useState<string[]>(() => { try { return (JSON.parse(lsGet("sp_chart_tf_custom") || "[]") as string[]).filter(x => parseTf(x)).slice(0, 4); } catch { return []; } });
  const [ctype, setCtypeState] = useState<ChartType>(() => (TYPES.some(t => t[0] === lsGet("sp_chart_type")) ? lsGet("sp_chart_type") as ChartType : "candles"));
  const setCtype = (v: ChartType) => { setCtypeState(v); lsSet("sp_chart_type", v); };
  const [ind, setIndState] = useState<Record<IndKey, boolean>>(() => lsJson(KI, preset ? IND_STOCK : IND_DEF));
  const toggleInd = (k: IndKey) => setIndState(s => { const n = { ...s, [k]: !s[k] }; lsSet(KI, JSON.stringify(n)); return n; });
  const [cvdCfg, setCvdState] = useState<CvdCfg>(() => lsJson("sp_cvd_cfg", CVD_DEFAULTS));
  const setCvd = (p: Partial<CvdCfg>) => setCvdState(c => { const n = { ...c, ...p }; lsSet("sp_cvd_cfg", JSON.stringify(n)); return n; });
  const [srCfg, setSrState] = useState<StochRsiCfg>(() => lsJson("sp_stochrsi_cfg", STOCHRSI_DEFAULTS));
  const [cfgFor, setCfgFor] = useState<null | "stochrsi" | "cvd">(null);
  const setSr = (p: Partial<StochRsiCfg>) => setSrState(c => { const n = { ...c, ...p }; lsSet("sp_stochrsi_cfg", JSON.stringify(n)); return n; });
  const [cfg, setCfgState] = useState<D7MSettings>(() => {
    try { const sv = JSON.parse(lsGet("sp_d7m_cfg_v2") || "{}");
      return { ...D7M_DEFAULTS, ...sv, colors: { ...D7M_DEFAULTS.colors, ...(sv.colors || {}) } }; } catch { return D7M_DEFAULTS; }
  });
  const saveCfg = (c: D7MSettings) => { setCfgState(c); lsSet("sp_d7m_cfg_v2", JSON.stringify(c)); };
  const [showCfg, setShowCfg] = useState(false);
  const [tool, setTool] = useState<Tool>(null);
  const [railOpen, setRailOpen] = useState(false);
  const [full, setFull] = useState(false);
  /* المنطقةُ الزمنيةُ ومقياسُ السعر — كتريدنق فيو، ويُحفظان لكلّ الرموز */
  const [tzPref, setTzState] = useState(() => lsGet("sp_chart_tz") || "exchange");
  const setTz = (v: string) => { setTzState(v); lsSet("sp_chart_tz", v); };
  const [scaleMode, setScaleState] = useState<number>(() => { const v = Number(lsGet("sp_chart_scale")); return v === 1 || v === 2 ? v : 0; });
  const setScale = (v: number) => { setScaleState(v); lsSet("sp_chart_scale", String(v)); };
  const pendRange = useRef<number | "ytd" | "all" | null>(null);
  const clockRef = useRef<HTMLSpanElement>(null);
  const [away, setAway] = useState(false);            // آخرُ شمعةٍ خارج المشهد ⇒ زرُّ العودة إليها
  const [manual, setManual] = useState(false);        // مقياسُ السعر سُحب يدوياً ⇒ الزرُّ نفسُه يعيده تلقائياً
  const [paneTops, setPaneTops] = useState<Record<string, number>>({});
  const [axisW, setAxisW] = useState(64);
  const [mainH, setMainH] = useState(0);
  const [winH, setWinH] = useState(() => window.innerHeight);
  const [vw, setVw] = useState(() => window.innerWidth);
  const wide = vw >= 1024, narrow = vw < 768;
  const topRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  /* ── البيانات ── */
  const { data: raw, isError, isPending } = useQuery({
    queryKey: ["bars", symbol, tf],
    queryFn: () => marketApi.bars(symbol, tf).then(r => (Array.isArray(r.data?.data) ? r.data.data : [])),
    enabled: !!symbol, retry: 1, staleTime: 10_000,
    /* الشمعةُ الجاريةُ تتحرّك مع التداول — الخادمُ يكتبها من جلسة «تداول» الرسمية ومن شموع المصدر */
    refetchInterval: tfIntraday(tf) ? 30_000 : 60_000,
  });
  const bars = useMemo(() => sanitizeBars(raw), [raw]);
  /* الشموعُ بالتوقيت العالميّ الحقيقيّ، والعرضُ بمنطقة المالك: «توقيتُ البورصة» افتراضاً أو ما اختاره (‏D739) */
  const tzName = tzPref === "exchange" ? exchangeTz(symbol) : tzPref;
  const disp = useMemo(() => displayTimes(bars, tzName), [bars, tzName]);
  /* الحجمُ مرسومٌ حين يكون للمصدر حجمٌ فعلاً (‏≥80% من الشموع) — وإلّا فهو «غير متوفّر» لا أعمدةٌ صفرية (يوميُّ تاسي · ساعاتُ البتكوين) */
  const volRef = useRef(true);
  const volOk = useMemo(() => {
    if (raw !== undefined) volRef.current = bars.length > 0 && bars.filter(b => b.volume > 0).length >= bars.length * 0.8;
    return volRef.current;
  }, [raw, bars]);
  const eff = useMemo(() => ({ ...ind, vol: ind.vol && volOk, cvd: ind.cvd && volOk }), [ind, volOk]);
  const isUS = !!symbol && !/^\d{4}(\.SR)?$/.test(symbol) && !/TASI/i.test(symbol);
  const { data: frames } = useQuery({
    queryKey: ["frames", symbol],
    queryFn: () => marketApi.frames(symbol).then(r => r.data?.data || null),
    enabled: ind.d7m && (cfg.dashboard || cfg.alertsDash) && !!symbol,
    staleTime: 5 * 60_000, refetchInterval: 5 * 60_000, retry: 0,
  });

  /* ── الرسمُ اليدويّ: محفوظٌ لكلّ رمزٍ على الخادم، والنسخةُ المحلّيةُ للعرض الفوريّ ── */
  const dKey = `sp_draw_${symbol}`;
  const [draws, setDraws] = useState<any[]>([]);
  useEffect(() => {
    let alive = true;
    try { setDraws(JSON.parse(lsGet(dKey) || "[]")); } catch { setDraws([]); }
    marketApi.drawings(symbol).then(r => {
      const items = Array.isArray(r.data?.data) ? r.data.data : null;
      if (alive && items && items.length) { setDraws(items); lsSet(dKey, JSON.stringify(items)); }
    }).catch(() => {});
    return () => { alive = false; };
  }, [dKey, symbol]);
  const saveDraws = (d: any[]) => { setDraws(d); lsSet(dKey, JSON.stringify(d)); marketApi.saveDrawings(symbol, d).catch(() => {}); };

  /* ── الحساب ── مرّةً لكلّ تغيّرٍ في الشموع أو الإعدادات، ويقرؤه الرسمُ ووسيلةُ الإيضاح معاً */
  const calc = useMemo(() => {
    const closes = bars.map(b => b.close);
    return { closes, stochrsi: stochRsi(source(bars, srCfg.src), srCfg), cvd: cvdD7M(bars, cvdCfg),
             research: ind.research ? researchInd(bars.map(b => ({ o: b.open, h: b.high, l: b.low, c: b.close, v: b.volume }))) : null };
  }, [bars, cvdCfg, srCfg, ind.research]);
  const d7m = useMemo(() => {
    if (!ind.d7m || bars.length < 5) return null;
    const b: any = bars;
    return {
      fib: cfg.fib ? autoFib(b, cfg.fibDev, cfg.fibDepth, cfg.fibReverse) : null,
      trend: cfg.trend ? autoTrend(b, cfg.trendPP) : null,
      channel: cfg.channel ? autoChannel(b, cfg.chDev, cfg.chDepth) : null,
      vwap: cfg.vwap || cfg.vwapBand ? vwapAnchored(b, cfg.vwapAnchor, cfg.vwapMult) : null,
    };
  }, [bars, ind.d7m, cfg]);
  const dash = ind.d7m && cfg.dashboard ? dashboard(bars as any, { bull: cfg.bull, bear: cfg.bear, vix: null, vixWarn: 25, vixBlock: 35,
    newsDates: [], today: new Date().toISOString().slice(0, 10), daily: frames?.daily, m15: frames?.m15 }) : null;
  const msmart = ind.d7m && cfg.macdDash && bars.length > 40 ? macdSmart(bars as any) : null;
  const tt = ind.d7m && cfg.tradeTool && isUS ? tradeTool(bars as any, null, false) : null;
  const alerts = (() => {
    if (!ind.d7m || !cfg.alertsDash || bars.length < 40) return null;
    const vw = vwapAnchored(bars as any, cfg.vwapAnchor).vwap, i = bars.length - 1;
    const h = macdSmart(bars as any)?.hist[i] ?? 0, c = bars[i].close;
    const f = autoFib(bars as any, cfg.fibDev, cfg.fibDepth, cfg.fibReverse);
    const f0 = f?.lines.find(x => x.level === 0)?.price, f1 = f?.lines.find(x => x.level === 1)?.price;
    const longUp = dash ? dash.rows[0].up : null;
    return {
      mom: c > vw[i] && h > 0 ? "شراء" : c < vw[i] && h < 0 ? "بيع" : "انتظار",
      rev: dash ? (dash.score >= cfg.bull ? "شراء" : dash.score <= cfg.bear ? "بيع" : "انتظار") : "انتظار",
      bounce: f1 != null && longUp === false && bars[i].low <= f1 ? "شراء" : f0 != null && longUp === true && bars[i].high >= f0 ? "بيع" : "انتظار",
    };
  })();

  /* ── مراجعُ الرسم ── */
  const boxRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainRef = useRef<ISeriesApi<any> | null>(null);
  const markRef = useRef<any>(null);
  const overlay = useRef(new ChartOverlay());
  const reg = useRef(new Map<string, { sig: string; series: ISeriesApi<any>[] }>());
  const sigRef = useRef({ main: "", key: "", n: 0, first: null as any, panes: "" });
  const legend = useRef<Record<string, HTMLElement | null>>({});
  const pend = useRef<any>(null);                 // أوّلُ نقطتَي خطّ الاتجاه
  const preview = useRef<Segment | null>(null);
  const stroke = useRef<{ x: number; y: number }[] | null>(null);
  const S = useRef({ bars, calc, tool, d7m, cfg, draws, ind, ctype, theme, cvdCfg, disp });
  S.current = { bars, calc, tool, d7m, cfg, draws, ind, ctype, theme, cvdCfg, disp };

  /* الارتفاع: الرسمُ كلُّه داخل الشاشة كتريدنق فيو — اللوحاتُ السفلى تقتسم ارتفاعَه ولا تدفعه تحت الطيّ، إلّا إن ضاقت الرئيسةُ عن حدّها */
  const oscOn = OSC.filter(k => eff[k]);
  const oscPx = wide ? 104 : 88;
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
  const chromeH = (topRef.current?.offsetHeight ?? 50) + (narrow && (railOpen || tool) ? 42 : 0);
  const stripH = ind.d7m && !preset ? 47 : 0;                                    // شريطُ D7M فوق الرسم (‏D744)
  const baseH = full ? Math.max(300, winH - chromeH - 2) : preset ? (wide ? 480 : 400) : wide ? clamp(winH - 345 - stripH, 400, 740) : clamp(winH - 380, 340, 460);
  const oscN = oscOn.length + (eff.research ? 1 : 0);                            // مؤشّرُ الأبحاث لوحتان: الكمّيةُ وRSI
  const mainPx = Math.max(full ? 200 : wide ? 300 : 250, baseH - oscN * oscPx);
  const stageH = mainPx + oscN * oscPx;

  /* ── نقطةُ رسمٍ محفوظة ← موضعٌ منطقيّ: بزمن شمعتها وكسرها، فتتبع الرسمَ في أيّ إطار ── */
  const secs = useMemo(() => bars.map(b => (typeof b.time === "number" ? b.time : Date.parse(b.time + "T00:00:00Z") / 1000)), [bars]);
  const secsRef = useRef(secs); secsRef.current = secs;
  const toX = (pt: any, ver: number): number | null => {
    const sc = secsRef.current;
    if (!sc.length || pt == null) return null;
    const s = typeof pt.t === "number" ? (ver === 2 ? pt.t - 10800 : pt.t) : Date.parse(String(pt.t) + "T00:00:00Z") / 1000;
    if (!isFinite(s)) return null;
    let lo = 0, hi = sc.length - 1;
    while (lo < hi) { const m = (lo + hi + 1) >> 1; if (sc[m] <= s) lo = m; else hi = m - 1; }
    return lo + (Number(pt.o) || 0);
  };
  /* موضعُ المؤشّر بين الشموع بكسره — المكتبةُ تعيد رقمَ أقرب شمعةٍ صحيحاً، فيخرج خطُّ الفرشاة سلالمَ؛ فيُضاف ما بين المؤشّر ومركزها */
  const fracLogical = (x: number): number | null => {
    const ts = chartRef.current?.timeScale();
    if (!ts) return null;
    const k = ts.coordinateToLogical(x);
    if (k == null) return null;
    const xr = ts.logicalToCoordinate(k), sp = ts.options().barSpacing;
    return xr == null || !sp ? (k as number) : (k as number) + (x - (xr as number)) / sp;
  };
  const prec4 = (v: number) => (Math.abs(v) >= 1 ? 2 : 4);
  const mkPt = (lg: number, price: number) => {
    const b = S.current.bars, i = Math.max(0, Math.min(b.length - 1, Math.floor(lg)));
    return { t: b[i].time, o: +(lg - i).toFixed(3), p: +price.toFixed(4) };
  };

  /* ── طبقةُ الرسم: المستوياتُ والخطوطُ والفرشاة — خفيفةٌ تُستدعى مباشرةً من الإيماءات بلا إعادة رسم الصفحة ── */
  const paint = () => {
    const st = S.current, b = st.bars;
    const up = tok("--pos-ink", "#16a34a"), down = tok("--neg-ink", "#dc2626");
    const drawC = st.cfg.colors?.draw || tok("--brand-ink", "#5b52d3");
    const levels: Level[] = [], segments: Segment[] = [], paths: Path[] = [], notes: Note[] = [], bands: Band[] = [];
    const last = b[b.length - 1];
    if (last) levels.push({ price: last.close, color: last.close >= last.open ? up : down, tag: true, bold: true, rank: 0, dash: [2, 3] });
    const D = st.d7m;
    if (D) {
      const C = (k: string) => st.cfg.colors?.[k] || tokv((D7M_COLORS.find(x => x[0] === k) || ["", "", "--ink"])[2]);
      const ink = st.cfg.colors?.fib || tokA("--ink-muted", "#6b7280", 0.6);
      /* ‏D744 (المالك): «شِل الكلام — المقاومة والدعم ولا تطمع — الشارتُ نظيف»: لا نصَّ على الرسم إلا رقمُ المستوى، والمناطقُ الثلاث
         تظليلٌ خفيف (المقاومة · الوسط: الاتجاهُ المعاكس والدعمُ القويّ · الدعم). و«مختصر» ستةُ خطوطها وحدها، و«الكل» كلُّ المستويات */
      if (D.fib) {
        const SIX = new Set([0, -0.1, 0.5, 0.618, 1, 1.1]), compact = (st.cfg.fibMode || "compact") === "compact";
        for (const l of D.fib.lines) {
          if (compact ? !SIX.has(l.level) : st.cfg.fibLevels[String(l.level)] === false) continue;
          const gold = l.color === "yellow";
          levels.push({ price: l.price, color: gold ? C("fibGold") : ink, text: String(l.level), tag: true, rank: gold ? 2 : 3, width: 1 });
        }
        if (st.cfg.fibZones) {
          const at = (lv: number) => D.fib!.lines.find(x => x.level === lv)?.price;
          const pairs = [[0, -0.1], [1, 1.1]].map(([u, v]) => [at(u), at(v)]).filter(([u, v]) => u != null && v != null) as [number, number][];
          pairs.sort((x, y) => (y[0] + y[1]) - (x[0] + x[1]));
          if (pairs[0]) bands.push({ p1: pairs[0][0], p2: pairs[0][1], color: tokA("--neg-ink", "#dc2626", 0.07) });
          if (pairs[1]) bands.push({ p1: pairs[1][0], p2: pairs[1][1], color: tokA("--pos-ink", "#16a34a", 0.07) });
          const m1 = at(0.5), m2 = at(0.618);
          if (m1 != null && m2 != null) bands.push({ p1: m1, p2: m2, color: tokA("--gauge-warn", "#d97706", 0.09) });
        }
      }
      if (D.trend) for (const l of D.trend.lines) if (l.x2 > l.x1)
        segments.push({ x1: l.x1, y1: l.y1, x2: l.x2, y2: l.y2, color: l.up ? C("trendUp") : C("trendDown"), width: l.major ? 2 : 1, dash: l.major ? [] : [5, 4] });
      if (D.channel) {
        const chC = st.cfg.colors?.channel || tokA("--brand-ink", "#5b52d3", 0.65);
        for (const seg of [D.channel.base, D.channel.parallel]) if (seg.length >= 2)
          segments.push({ x1: seg[0][0], y1: seg[0][1], x2: seg[seg.length - 1][0], y2: seg[seg.length - 1][1], color: chC, width: 1 });
        const [b0, b1] = [D.channel.base[0], D.channel.base[D.channel.base.length - 1]], [q0, q1] = [D.channel.parallel[0], D.channel.parallel[D.channel.parallel.length - 1]];
        segments.push({ x1: b0[0], y1: (b0[1] + q0[1]) / 2, x2: b1[0], y2: (b1[1] + q1[1]) / 2, color: chC, width: 1, dash: [3, 4] });   // منتصفُ القناة كتريدنق فيو
      }
    }
    /* ‏D753 مؤشّرُ الأبحاث: فيبوناتشي بتسمياته كأداة تريدنق فيو («1.618 (10,490.82)»)، وخطّا الاتجاه */
    const RI = st.ind.research ? st.calc.research : null;
    if (RI) {
      const fc = tok("--ri-fib", "#2962ff");
      if (RI.fib) for (const l of RI.fib.levels)
        levels.push({ price: l.p, color: fc, text: `${l.k} (${l.p.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })})`, rank: 4, width: 1 });
      for (const t of [RI.trend.res, RI.trend.sup]) if (t) segments.push({ x1: t.x1, y1: t.y1, x2: t.x2, y2: t.y2, color: tok("--ri-trend", "#131722"), width: 1 });
    }
    for (const d of st.draws) {
      const v2 = Number(d.v) || 1;
      if (typeof d.h === "number") levels.push({ price: d.h, color: drawC, tag: true, rank: 1, width: 1.5 });
      else if (d.a && d.b) {
        const x1 = toX(d.a, v2), x2 = toX(d.b, v2);
        if (x1 != null && x2 != null && x1 !== x2) segments.push({ x1, y1: d.a.p, x2, y2: d.b.p, color: drawC, width: 2 });
      } else if (Array.isArray(d.free)) {
        const pts = d.free.map((q: any) => ({ x: toX(q, v2), y: q.p })).filter((q: any) => q.x != null);
        if (pts.length > 1) paths.push({ pts, color: drawC, width: 2 });
      }
    }
    if (preview.current) segments.push(preview.current);
    if (stroke.current && stroke.current.length > 1) paths.push({ pts: stroke.current, color: drawC, width: 2 });
    overlay.current.set({ levels, segments, paths, notes, bands, font: getComputedStyle(document.body).fontFamily || "sans-serif", bg: tok("--card", "#ffffff"), textTop: 50 });
    // سماتُ تشخيص: ما رُسم على اللوحة (لا يُقرأ من الـDOM) — آخرُ سعرٍ موسوم، وعددُ المستويات المسمّاة والوسوم والرسوم اليدوية
    const root = rootRef.current;
    if (root) {
      root.dataset.last = last ? fmtPrice(last.close) : ""; root.dataset.lv = String(levels.filter(l => l.text).length);
      root.dataset.tags = String(levels.filter(l => l.tag).length); root.dataset.draws = String(st.draws.length);
      root.dataset.segs = String(segments.length);
      root.dataset.ri = RI ? `${RI.fib?.levels.length || 0}·${[RI.trend.res, RI.trend.sup].filter(Boolean).length}·${RI.signals.length}` : "";
    }
  };

  /* ── وسيلةُ الإيضاح: أرقامُها تُكتب مباشرةً مع حركة خطّ التقاطع ── */
  const fill = (i: number) => {
    const st = S.current, b = st.bars, L = legend.current, c = st.calc;
    const set = (k: string, v: string, color?: string) => { const e = L[k]; if (e) { e.textContent = v; if (color) e.style.color = color; } };
    const r = b[i];
    if (!r) { ["o", "h", "l", "c", "chg", "vol"].forEach(k => set(k, "—")); return; }
    const prev = b[i - 1], up = r.close >= r.open;
    const col = up ? "var(--pos-ink)" : "var(--neg-ink)";
    set("o", fmtPrice(r.open), col); set("h", fmtPrice(r.high), col); set("l", fmtPrice(r.low), col); set("c", fmtPrice(r.close), col);
    if (prev) {
      const d = r.close - prev.close, p = prev.close ? d / prev.close * 100 : 0;
      const dp = Math.abs(r.close) >= 1 ? 2 : 4;
      set("chg", `${d >= 0 ? "+" : ""}${d.toFixed(dp)} (${p >= 0 ? "+" : ""}${p.toFixed(2)}%)`, d >= 0 ? "var(--pos-ink)" : "var(--neg-ink)");
    } else set("chg", "");
    set("vol", fmtVol(r.volume));
    // ‏D739: شمعةٌ من الإغلاقات الرسمية وحدها (تاريخُ تاسي القديم) يُقال عنها ذلك — لا يُوهَم أنّ لها أعلى وأدنى رسميّين
    set("basis", (r as any).basis === "close" ? "من الإغلاقات اليومية — الأعلى والأدنى غيرُ متوفّرَين" : "");
    const f = (v: number | null | undefined, dp = 2) => (v == null || !isFinite(v) ? "—" : v.toFixed(dp));
    set("srK", f(c.stochrsi.k[i])); set("srD", f(c.stochrsi.d[i]));
    if (c.research) { set("ri20", f(c.research.sma20[i])); set("ri50", f(c.research.sma50[i])); set("riRsi", f(c.research.rsi[i])); set("riV", fmtVol(r.volume)); }
    const cv = st.cvdCfg.style === "line" ? c.cvd.line[i] : c.cvd.c[i];
    set("cvd", st.cvdCfg.scale === "volume" ? fmtVol(Math.abs(cv ?? 0)) : f(cv, 1)); set("cvdE", f(c.cvd.ema2[i], 1));
  };

  /* مواضعُ اللوحات السفلى (لوسائل إيضاحها) وعرضُ محور الأسعار وارتفاعُ اللوحة الرئيسة — تُقرأ من الرسم نفسِه، فتتبع سحبَ الفواصل */
  const readLayout = () => {
    const chart = chartRef.current;
    if (!chart) return;
    try {
      const tops: Record<string, number> = {};
      let y = 0;
      const idx = new Map<number, string>();
      reg.current.forEach((e, k) => {
        if (OSC.includes(k as IndKey) && e.series[0]) idx.set(e.series[0].getPane().paneIndex(), k);
        if (k === "research" && e.series[1]) idx.set(e.series[1].getPane().paneIndex(), "researchRsi");
      });
      chart.panes().forEach((_, i) => { if (idx.has(i)) tops[idx.get(i)!] = y; y += chart.paneSize(i).height + 1; });
      setPaneTops(o => (JSON.stringify(o) === JSON.stringify(tops) ? o : tops));
      const h0 = chart.paneSize(0).height; if (h0) setMainH(o => (o === h0 ? o : h0));
      const w = chart.priceScale("right").width(); if (w) setAxisW(o => (o === w ? o : w));
      const auto = chart.priceScale("right").options().autoScale !== false; setManual(o => (o === !auto ? o : !auto));
      // سماتُ تشخيصٍ على الجذر — عددُ الشموع والمعروضُ منها وعرضُ الشمعة وعددُ اللوحات: يقرؤها الحارسُ فيقيس الرسمَ نفسَه لا شكلَه
      const root = rootRef.current, vr = chart.timeScale().getVisibleLogicalRange();
      if (root) {
        root.dataset.bars = String(S.current.bars.length); root.dataset.panes = String(chart.panes().length);
        root.dataset.vis = vr ? String(Math.round(vr.to - vr.from)) : ""; root.dataset.to = vr ? vr.to.toFixed(1) : "";
        root.dataset.spacing = chart.timeScale().options().barSpacing.toFixed(2);
        const D = S.current.disp;
        root.dataset.lastT = D.length ? crossLabel(D[D.length - 1]) : "";
        root.dataset.scale = String(chart.priceScale("right").options().mode);
      }
    } catch { /* لم يُرسم بعد */ }
  };

  /* ── إنشاءُ الرسم مرّةً واحدة ── */
  useEffect(() => {
    const box = boxRef.current;
    if (!box) return;
    const chart = createChart(box, {
      autoSize: true,
      layout: { background: { color: "transparent" }, attributionLogo: true, panes: { enableResize: true } },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.08, bottom: 0.2 } },
      timeScale: { borderVisible: false, rightOffset: 6, barSpacing: 9, minBarSpacing: 0.5, secondsVisible: false,
                   tickMarkFormatter: (t: any, type: number) => tickLabel(t, type), lockVisibleTimeRangeOnResize: true },
      crosshair: { mode: CrosshairMode.Normal },
      /* كتريدنق فيو: السحبُ يحرّك، والعجلةُ والقرصُ يكبّران، والمحوران يُسحبان؛ وعلى اللمس الإصبعُ العموديُّ للصفحة لا للرسم */
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
      handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: { time: true, price: true }, axisDoubleClickReset: { time: true, price: true } },
      kineticScroll: { touch: true, mouse: true },
      localization: { locale: "en-US", timeFormatter: (t: any) => crossLabel(t) },
    });
    chartRef.current = chart;
    const onCross = (p: MouseEventParams) => {
      const st = S.current, n = st.bars.length;
      const i = p.time === undefined || p.logical == null ? n - 1 : Math.max(0, Math.min(n - 1, Math.round(p.logical as number)));
      fill(i);
    };
    const onRange = (r: any) => { if (r) setAway(r.to < S.current.bars.length - 1.5); };
    chart.subscribeCrosshairMove(onCross);
    chart.timeScale().subscribeVisibleLogicalRangeChange(onRange);
    return () => {
      chart.remove();
      chartRef.current = null; mainRef.current = null; markRef.current = null;
      reg.current.clear(); sigRef.current = { main: "", key: "", n: 0, first: null, panes: "" };
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── المزامنة: المظهرُ ثمّ السلسلةُ الرئيسة ثمّ البياناتُ ثمّ المؤشّراتُ ثمّ اللوحات — كلُّ خطوةٍ تفعل ما تغيّر وحده ── */
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const up = tok("--pos-ink", "#16a34a"), down = tok("--neg-ink", "#dc2626"), hair = tok("--hairline", "#dcdcdc");
    const muted = tok("--ink-muted", "#6b7280"), ink = tok("--ink", "#111111"), brand = tok("--brand-ink", "#5b52d3");
    const font = getComputedStyle(document.body).fontFamily || "sans-serif";
    chart.applyOptions({
      layout: { textColor: muted, fontFamily: font, fontSize: 11,
                panes: { separatorColor: hair, separatorHoverColor: tokA("--brand-ink", "#5b52d3", 0.25) } },
      grid: { vertLines: { color: tokA("--hairline", "#dcdcdc", 0.55) }, horzLines: { color: tokA("--hairline", "#dcdcdc", 0.55) } },
      timeScale: { timeVisible: tfIntraday(tf) },
      crosshair: { vertLine: { color: muted, width: 1, style: LineStyle.Dashed, labelBackgroundColor: ink },
                   horzLine: { color: muted, width: 1, style: LineStyle.Dashed, labelBackgroundColor: ink } },
    });

    /* ١ السلسلةُ الرئيسة — تُبنى حين يتغيّر نوعُ الرسم أو المظهر وحدهما */
    const mainSig = `${ctype}|${theme}`;
    if (sigRef.current.main !== mainSig || !mainRef.current) {
      if (mainRef.current) { try { mainRef.current.detachPrimitive(overlay.current); } catch { /* لم تُلحق */ } chart.removeSeries(mainRef.current); }
      const common = { priceLineVisible: false, lastValueVisible: false };
      const m = ctype === "line" ? chart.addSeries(LineSeries, { ...common, color: brand, lineWidth: 2, crosshairMarkerRadius: 4 }, 0)
        : ctype === "area" ? chart.addSeries(AreaSeries, { ...common, lineColor: brand, lineWidth: 2, topColor: tokA("--brand-ink", "#5b52d3", 0.28),
                                                           bottomColor: tokA("--brand-ink", "#5b52d3", 0.02) }, 0)
        : ctype === "bars" ? chart.addSeries(BarSeries, { ...common, upColor: up, downColor: down, thinBars: false }, 0)
        : chart.addSeries(CandlestickSeries, { ...common, upColor: ctype === "hollow" ? "rgba(0,0,0,0)" : up, downColor: down,
                                               borderVisible: true, borderUpColor: up, borderDownColor: down, wickUpColor: up, wickDownColor: down }, 0);
      m.attachPrimitive(overlay.current);
      markRef.current = createSeriesMarkers(m, []);
      mainRef.current = m;
      sigRef.current = { ...sigRef.current, main: mainSig, key: "" };
    }
    const main = mainRef.current!;
    const lineLike = ctype === "line" || ctype === "area";
    /* لكلّ لوحةٍ صياغةُ أرقامها: السعرُ بدقّته (هللتان، أو أدقّ لما دون الريال)، والمؤشّراتُ بدقّتها */
    const lastC = bars.length ? bars[bars.length - 1].close : 10;
    const prec = lastC >= 1 ? 2 : lastC >= 0.01 ? 4 : 6;
    main.applyOptions({ priceFormat: { type: "custom", minMove: 1 / 10 ** prec, formatter: (v: number) => fmtPrice(v) } });
    const D = disp;
    const toMain = (b: CBar, i: number) => (lineLike ? { time: D[i] as any, value: b.close } : { time: D[i] as any, open: b.open, high: b.high, low: b.low, close: b.close });
    chart.priceScale("right").applyOptions({ mode: scaleMode === 1 ? PriceScaleMode.Logarithmic : scaleMode === 2 ? PriceScaleMode.Percentage : PriceScaleMode.Normal });

    /* ٢ البيانات: إطارٌ أو رمزٌ جديد ⇒ سلسلةٌ جديدةٌ ومشهدٌ على آخر الشموع؛ وإلّا فالشمعةُ الجاريةُ تُحدَّث في مكانها والموضعُ يبقى */
    const n = bars.length, key = `${symbol}|${tf}|${mainSig}|${tzName}`, view = `${symbol}|${tf}`;
    const prev = sigRef.current;
    /* أثناء الجلب (إطارٌ أو رمزٌ جديد) تبقى الصورةُ السابقةُ كما هي تحت غلالةٍ خفيفة — لا وميضَ فراغٍ بين إطارَين */
    if (raw === undefined) return;
    let resetView = false;
    {
      const same = prev.key === key && n > 0 && n - prev.n >= 0 && n - prev.n <= 1 && prev.first === bars[0]?.time;
      if (same) {
        if (n > prev.n && n >= 2) main.update(toMain(bars[n - 2], n - 2));
        main.update(toMain(bars[n - 1], n - 1));
      } else {
        main.setData(bars.map(toMain));
        resetView = !prev.key.startsWith(view + "|") && n > 0;
      }
      sigRef.current = { ...sigRef.current, key, n, first: bars[0]?.time ?? null };
    }

    /* ٣ المؤشّرات: لكلٍّ توقيعٌ (المظهرُ + إعداداتُه)؛ ما تغيّر توقيعُه يُبنى في لوحته نفسِها، وما أُطفئ يُزال */
    const c = calc;
    const pts = (vals: (number | null | undefined)[]) => {
      const out: any[] = [];
      for (let i = 0; i < vals.length && i < n; i++) { const v = vals[i]; if (v != null && isFinite(v)) out.push({ time: D[i] as any, value: v }); }
      return out;
    };
    const ln = (pane: number, color: string, width: 1 | 2 | 3 | 4 = 1, extra: any = {}) =>
      chart.addSeries(LineSeries, { color, lineWidth: width, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, ...extra }, pane);
    const fixed = (lo: number, hi: number) => ({ autoscaleInfoProvider: () => ({ priceRange: { minValue: lo, maxValue: hi } }) });
    const guide = (s: ISeriesApi<any>, vals: number[]) => vals.forEach(v =>
      s.createPriceLine({ price: v, color: tokA("--ink-muted", "#888888", 0.5), lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: "" }));
    const build: Record<IndKey, (pane: number) => ISeriesApi<any>[]> = {
      vol: () => {
        const s = chart.addSeries(HistogramSeries, { priceScaleId: "vol", priceFormat: { type: "volume" }, priceLineVisible: false, lastValueVisible: false }, 0);
        s.priceScale().applyOptions({ scaleMargins: { top: 0.84, bottom: 0 } });
        return [s];
      },
      /* ‏Stoch RSI بسكربت تريدنق فيو: ‏K أزرق و‏D برتقاليّ، وحدودُ 80 و50 و20، وخلفيةٌ بين 80 و20 (ألوانُه من رموز التطبيق) */
      stochrsi: p => {
        const k = ln(p, tok("--info-ink", "#2563eb"), 1, fixed(0, 100)), d = ln(p, tok("--gauge-warn", "#d97706"), 1);
        const band = (v: number, a: number) => k.createPriceLine({ price: v, color: tokA("--ink-muted", "#787b86", a), lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: "" });
        band(srCfg.upper, 1); band(srCfg.middle, 0.5); band(srCfg.lower, 1);
        k.attachPrimitive(new BandFill(srCfg.upper, srCfg.lower, tokA("--info-ink", "#2196f3", 0.1)));
        return [k, d];
      },
      cvd: p => {
        const fmt = cvdCfg.scale === "volume" ? { type: "volume" as const } : { type: "price" as const, precision: 1, minMove: 0.1 };
        const rng = cvdCfg.scale === "levels" ? fixed(0, 100) : cvdCfg.scale === "pct" ? fixed(-100, 100) : {};
        if (cvdCfg.style === "line") return [ln(p, tok("--chart-4", "#4a8fbd"), 2, { priceFormat: fmt, ...rng })];
        /* ألوانُ سكربت المالك من رموز التطبيق: الصاعدةُ بيضاءُ لخلفيةٍ داكنة — فبحبر النصّ ليُقرأ في المظهرين — والهابطةُ برمز الهبوط */
        const cs = chart.addSeries(CandlestickSeries, { priceLineVisible: false, lastValueVisible: false, priceFormat: fmt, ...rng,
          upColor: ink, downColor: down, borderUpColor: ink, borderDownColor: down, wickUpColor: ink, wickDownColor: down }, p);
        const out: ISeriesApi<any>[] = [cs];
        (["sma1", "sma2", "ema1", "ema2"] as const).forEach(k => { if (cvdCfg[k]) out.push(ln(p, k === "sma2" ? down : ink, 1, { priceFormat: fmt })); });
        return out;
      },
      /* ‏D753 مؤشّرُ الأبحاث: الكمّيةُ في لوحتها ثمّ RSI 14 بحدَّي 30 و70 ونطاقِه، والمتوسّطان على الأسعار — ألوانُ رسم التقرير من رموزها */
      research: p => {
        const v = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceLineVisible: false, lastValueVisible: false }, p);
        const r = ln(p + 1, tok("--ri-rsi", "#2962ff"), 1, fixed(0, 100));
        guide(r, [30, 70]);
        r.attachPrimitive(new BandFill(70, 30, tok("--ri-band", "rgba(41,98,255,0.08)")));
        return [v, r, ln(0, tok("--ri-sma20", "#ef9a9a"), 2), ln(0, tok("--ri-sma50", "#a5d6a7"), 2)];
      },
      d7m: () => {
        const out: ISeriesApi<any>[] = [];
        const C = (k: string) => cfg.colors?.[k] || tokv((D7M_COLORS.find(x => x[0] === k) || ["", "", "--ink"])[2]);
        if (cfg.vwap) out.push(ln(0, C("vwap"), 1));
        if (cfg.vwapBand) out.push(ln(0, C("band"), 1), ln(0, C("band"), 1));
        ([["ema20", "--chart-1"], ["ema50", "--pos-ink"], ["ema100", "--gauge-warn"], ["ema200", "--neg-ink"], ["ema400", "--chart-4"]] as const)
          .forEach(([k, t]) => { if ((cfg as any)[k]) out.push(ln(0, cfg.colors?.[k] || tokv(t), 2)); });
        ([["pdh", "--neg-ink"], ["pdl", "--pos-ink"], ["pdc", "--ink-muted"], ["dOpen", "--gauge-warn"]] as const)
          .forEach(([k, t]) => { if ((cfg as any)[k]) out.push(ln(0, tokv(t), 1, { lineVisible: false, pointMarkersVisible: true, pointMarkersRadius: 1.5 })); });
        return out;
      },
    };
    const feed: Record<IndKey, (s: ISeriesApi<any>[]) => void> = {
      vol: s => s[0].setData(bars.map((b, i) => ({ time: D[i] as any, value: b.volume || 0,
        color: b.close >= b.open ? tokA("--pos-ink", "#16a34a", 0.42) : tokA("--neg-ink", "#dc2626", 0.42) }))),
      stochrsi: s => { s[0].setData(pts(c.stochrsi.k)); s[1].setData(pts(c.stochrsi.d)); },
      research: s => {
        const R = c.research;
        if (!R) { s.forEach(x => x.setData([])); return; }
        s[0].setData(bars.map((b, i) => ({ time: D[i] as any, value: b.volume || 0,
          color: b.close >= b.open ? tokA("--pos-ink", "#16a34a", 0.5) : tokA("--neg-ink", "#dc2626", 0.5) })));
        s[1].setData(pts(R.rsi)); s[2].setData(pts(R.sma20)); s[3].setData(pts(R.sma50));
      },
      cvd: s => {
        const v = c.cvd;
        if (cvdCfg.style === "line") { s[0].setData(pts(v.line)); return; }
        const rows: any[] = [];
        for (let i = 0; i < n; i++) if (v.o[i] != null && v.h[i] != null && v.l[i] != null && v.c[i] != null)
          rows.push({ time: D[i] as any, open: v.o[i], high: v.h[i], low: v.l[i], close: v.c[i] });
        s[0].setData(rows);
        let j = 1;
        (["sma1", "sma2", "ema1", "ema2"] as const).forEach(k => { if (cvdCfg[k] && s[j]) s[j++].setData(pts(v[k])); });
      },
      d7m: s => {
        let j = 0;
        const cl = c.closes, vw = d7m?.vwap;
        if (cfg.vwap) s[j++]?.setData(pts(vw ? vw.vwap : []));
        if (cfg.vwapBand) { s[j++]?.setData(pts(vw ? vw.upper : [])); s[j++]?.setData(pts(vw ? vw.lower : [])); }
        ([["ema20", 20], ["ema50", 50], ["ema100", 100], ["ema200", 200], ["ema400", 400]] as const)
          .forEach(([k, len]) => { if ((cfg as any)[k]) s[j++]?.setData(n >= len ? pts(emaD7(cl, len)) : []); });
        ([["pdh", (i: number) => bars[i - 1]?.high], ["pdl", (i: number) => bars[i - 1]?.low], ["pdc", (i: number) => bars[i - 1]?.close],
          ["dOpen", (i: number) => bars[i]?.open]] as const)
          .forEach(([k, f]) => { if ((cfg as any)[k]) s[j++]?.setData(pts(bars.map((_, i) => f(i)))); });
      },
    };
    const sigOf = (k: IndKey) => `${theme}|${k === "cvd" ? JSON.stringify(cvdCfg) : k === "d7m" ? JSON.stringify(cfg) : k === "stochrsi" ? JSON.stringify(srCfg) : ""}`;
    const R = reg.current;
    for (const [k] of IND) {
      const cur = R.get(k);
      if (!eff[k]) { if (cur) { cur.series.forEach(s => chart.removeSeries(s)); R.delete(k); } continue; }
      const sig = sigOf(k);
      if (!cur || cur.sig !== sig) {
        // اللوحةُ نفسُها إن وُجدت (فلا يقفز المؤشّرُ إلى الأسفل حين تتغيّر إعداداتُه)، وإلّا لوحةٌ جديدةٌ آخرَ الرسم
        const pane = OSC.includes(k) ? (cur?.series[0] ? cur.series[0].getPane().paneIndex() : chart.panes().length) : 0;
        const fresh = build[k](pane);
        if (cur) cur.series.forEach(s => chart.removeSeries(s));
        R.set(k, { sig, series: fresh });
      }
      feed[k](R.get(k)!.series);
    }
    main.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: eff.vol ? 0.2 : 0.06 } });
    /* المشهدُ الأوّل لإطارٍ أو رمزٍ جديد: آخرُ الشموع بعرضٍ مقروء (لا الكلُّ محشوراً) — بعد أن تستقرّ السلاسلُ كلُّها على الزمن الجديد */
    if (pendRange.current != null && n) { const pr = pendRange.current; pendRange.current = null; rangeTo(pr); }
    else if (resetView) {
      const vis = Math.min(n, wide ? 150 : 64);
      chart.timeScale().setVisibleLogicalRange({ from: n - vis - 0.5, to: n + 5.5 });
      chart.priceScale("right").applyOptions({ autoScale: true });
    }

    /* ٤ علاماتُ D7M (كسرُ الترند وارتدادُه) */
    const sigs = d7m?.trend && cfg.trendShapes ? d7m.trend.signals : [];
    const marks: { i: number; m: any }[] = sigs.filter(sg => bars[sg.index]).map(sg => {
      const dn = sg.kind === "breakDown" || sg.kind === "reactDown";
      return { i: sg.index, m: { time: D[sg.index] as any, position: dn ? "aboveBar" : "belowBar", shape: dn ? "arrowDown" : "arrowUp", color: muted } };
    });
    /* ‏D753 أسهمُ مؤشّر الأبحاث: عبورُ RSI حدَّ 30 صعوداً شراءٌ، وحدَّ 70 هبوطاً بيع */
    if (eff.research && c.research) for (const sg of c.research.signals) if (bars[sg.i]) marks.push({ i: sg.i, m: { time: D[sg.i] as any,
      position: sg.side === "sell" ? "aboveBar" : "belowBar", shape: sg.side === "sell" ? "arrowDown" : "arrowUp",
      color: tok(sg.side === "sell" ? "--ri-sell" : "--ri-buy", sg.side === "sell" ? "#f23645" : "#089981") } });
    markRef.current?.setMarkers(marks.sort((a, b) => a.i - b.i).map(x => x.m));

    /* ٥ اللوحات: الرئيسةُ بارتفاعها والسفلى بارتفاعٍ واحد — تُضبط حين يتغيّر عددُها أو ارتفاعُ الرسم وحدهما، فما سحبه المالكُ
       من فواصلها يبقى ولا يرتدّ مع كلّ تحديثٍ للسعر */
    const panes = chart.panes(), pSig = `${panes.length}|${mainPx}|${oscPx}`;
    if (sigRef.current.panes !== pSig) { panes.forEach((p, i) => p.setStretchFactor(i === 0 ? mainPx : oscPx)); sigRef.current.panes = pSig; }
    paint();
    fill(n - 1);
    requestAnimationFrame(readLayout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [raw, bars, disp, tzName, eff, scaleMode, calc, d7m, ind, ctype, cvdCfg, cfg, theme, tf, symbol, mainPx, oscPx, wide]);

  /* لوحةٌ سفلى ظهرت للتوّ: وسيلةُ إيضاحها تُركَّب بعد أن يُعرف موضعُها — فتُملأ قيمُها حينها، لا عند أوّل حركةٍ للمؤشّر (كانت «———») */
  useEffect(() => { fill(S.current.bars.length - 1); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [paneTops]);

  /* الرسمُ اليدويُّ والأداة: طبقةُ الرسم وحدها */
  useEffect(() => { if (tool !== "trend") { pend.current = null; preview.current = null; } paint(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [draws, tool]);

  useEffect(() => {
    readLayout();
    const t = window.setInterval(readLayout, 350);
    return () => window.clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    /* على الجوال شريطُ العنوان يظهر ويختفي مع التمرير فيتغيّر ارتفاعُ النافذة قليلاً — لا يُعاد قياسُ الرسم لذلك فيرتجف */
    const on = () => { setVw(window.innerWidth); setWinH(h => (Math.abs(window.innerHeight - h) > 120 || window.innerWidth >= 1024 ? window.innerHeight : h)); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") { setFull(false); setTool(null); } };
    window.addEventListener("resize", on); window.addEventListener("keydown", esc);
    return () => { window.removeEventListener("resize", on); window.removeEventListener("keydown", esc); };
  }, []);

  /* ── أدواتُ الرسم: طبقةٌ فوق اللوحة الرئيسة تلتقط الإصبعَ والفأرةَ بنفسها ──
     كانت نقرتا خطّ الاتجاه تُقرآن من «نقرة» المكتبة، وهي تبتلع الثانيةَ إن جاءت خلال نصف ثانيةٍ من الأولى (تحسبها نصفَ نقرةٍ
     مزدوجة) فيضيع الخطّ. فهنا: خطُّ الاتجاه نقرتان أو سحبةٌ واحدة، والأفقيُّ نقرة، والفرشاةُ سحب — والنقطةُ بزمن شمعتها
     وكسرها وسعرها، فتتبع الرسمَ حين يُسحب ويُكبَّر وحين يتبدّل الإطار. */
  const press = useRef<{ x: number; y: number; fresh: boolean } | null>(null);
  const drawPt = (e: React.PointerEvent) => {
    const main = mainRef.current;
    if (!main) return null;
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const lg = fracLogical(e.clientX - r.left), price = main.coordinateToPrice(e.clientY - r.top);
    return lg == null || price == null ? null : { x: lg, y: price as number };
  };
  const drawColor = () => S.current.cfg.colors?.draw || tok("--brand-ink", "#5b52d3");
  const drawDown = (e: React.PointerEvent) => {
    const p = drawPt(e), t = S.current.tool;
    if (!p || !S.current.bars.length) return;
    (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
    press.current = { x: e.clientX, y: e.clientY, fresh: false };
    if (t === "brush") stroke.current = [p];
    else if (t === "trend" && !pend.current) { pend.current = mkPt(p.x, p.y); press.current.fresh = true; }
  };
  const drawMove = (e: React.PointerEvent) => {
    const t = S.current.tool;
    if (t === "brush") { if (stroke.current) { const p = drawPt(e); if (p) { stroke.current.push(p); paint(); } } return; }
    if (t !== "trend" || !pend.current) return;
    const p = drawPt(e), x1 = toX(pend.current, 3);
    if (p && x1 != null) { preview.current = { x1, y1: pend.current.p, x2: p.x, y2: p.y, color: drawColor(), width: 2, dash: [4, 4] }; paint(); }
  };
  const drawUp = (e: React.PointerEvent) => {
    const t = S.current.tool, pr = press.current, p = drawPt(e);
    press.current = null;
    if (t === "brush") {
      const pts = stroke.current; stroke.current = null;
      if (pts && pts.length > 1) saveDraws([...S.current.draws, { free: pts.map(q => mkPt(q.x, q.y)), v: 3 }]); else paint();
      return;
    }
    if (!pr || !p) return;
    if (t === "hline") { saveDraws([...S.current.draws, { h: +p.y.toFixed(prec4(p.y)) }]); setTool(null); return; }
    if (t === "trend" && pend.current) {
      // الضغطةُ التي وضعت البدايةَ ثمّ أُفلتت في مكانها نقرةٌ أولى — تنتظر الثانية؛ وإن سُحبت فإفلاتُها النهاية
      if (pr.fresh && Math.hypot(e.clientX - pr.x, e.clientY - pr.y) < 8) return;
      const a = pend.current, b = mkPt(p.x, p.y);
      pend.current = null; preview.current = null;
      saveDraws([...S.current.draws, { a, b, v: 3 }]); setTool(null);
    }
  };
  const drawCancel = () => {
    press.current = null;
    if (stroke.current) { const pts = stroke.current; stroke.current = null; if (pts.length > 1) saveDraws([...S.current.draws, { free: pts.map(q => mkPt(q.x, q.y)), v: 3 }]); else paint(); }
  };

  const shot = () => {
    try {
      const cv = chartRef.current?.takeScreenshot();
      cv?.toBlob(b => { if (!b) return; const a = document.createElement("a"); a.href = URL.createObjectURL(b);
        a.download = `${symbol.replace(/[^\w.-]/g, "")}-${tf}.png`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); });
    } catch { /* لا لقطة */ }
  };
  /* زرُّ المدى: يختار إطارَه، ثمّ يعرض المدّةَ من آخر شمعة */
  const rangeTo = (days: number | "ytd" | "all") => {
    const c = chartRef.current, D = S.current.disp, n = D.length;
    if (!c || !n) return;
    const sec = (t: any) => (typeof t === "number" ? t : Date.parse(t + "T00:00:00Z") / 1000);
    const end = sec(D[n - 1]);
    const from = days === "all" ? -Infinity : days === "ytd" ? Date.UTC(new Date(end * 1000).getUTCFullYear(), 0, 1) / 1000 : end - days * 86400;
    let i = 0;
    while (i < n - 1 && sec(D[i]) < from) i++;
    c.timeScale().setVisibleLogicalRange({ from: i - 0.5, to: n + 2.5 });
    c.priceScale("right").applyOptions({ autoScale: true });
  };
  const goRange = (days: number | "ytd" | "all", rtf: string) => {
    if (rtf === tf && raw !== undefined) { rangeTo(days); return; }
    pendRange.current = days; setTf(rtf);
  };
  useEffect(() => {
    let f: Intl.DateTimeFormat;
    try { f = new Intl.DateTimeFormat("en-GB", { timeZone: tzName, hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }); }
    catch { f = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }); }
    const tick = () => { if (clockRef.current) clockRef.current.textContent = f.format(new Date()); };
    tick();
    const t = window.setInterval(tick, 1000);
    return () => window.clearInterval(t);
  }, [tzName]);
  const nowS = Date.now() / 1000;
  const tzItems: [string, string, number][] = [["exchange", "توقيت البورصة", tzOffsetMin(exchangeTz(symbol), nowS)], ["UTC", "UTC", 0],
    ...TZ_LIST.map(([k, n]) => [k, n, tzOffsetMin(k, nowS)] as [string, string, number]).sort((a, b) => a[2] - b[2])];
  const goLive = () => {
    const c = chartRef.current, n = bars.length;
    if (!c || !n) return;
    const r = c.timeScale().getVisibleLogicalRange(), w = r ? r.to - r.from : 120;
    c.timeScale().setVisibleLogicalRange({ from: n + 5.5 - w, to: n + 5.5 });
    c.priceScale("right").applyOptions({ autoScale: true });
    setManual(false);
  };

  /* ── الإطارُ المخصَّص ── */
  const [cn, setCn] = useState("6");
  const [cu, setCu] = useState<TfUnit>("h");
  const customKey = tfKey(Number(cn) || 0, cu), customOk = !!parseTf(customKey);
  const applyCustom = (close: () => void) => {
    const p = parseTf(customKey);
    if (!p) return;
    const k = tfKey(p.n, p.unit);
    if (!TF_PRESETS.includes(k)) { const next = [k, ...customTfs.filter(x => x !== k)].slice(0, 4); setCustomTfs(next); lsSet("sp_chart_tf_custom", JSON.stringify(next)); }
    setTf(k); close();
  };
  const barTfs = [...TF_BAR, ...customTfs.filter(x => !TF_BAR.includes(x))];
  const TypeIcon = (TYPES.find(t => t[0] === ctype) || TYPES[0])[2];
  const lv = (k: string) => (e: HTMLElement | null) => { legend.current[k] = e; };
  const chip = (k: IndKey, body: React.ReactNode) => <span className="pc-chip" data-ind={k}>{body}</span>;
  const empty = raw !== undefined && !bars.length;

  return (
    <div ref={rootRef} className={"pc" + (full ? " pc-full" : "")} data-role="pro-chart" data-tf={tf} data-type={ctype} data-symbol={symbol}>
      {/* ══ الشريطُ العلويّ — كتريدنق فيو: الرمزُ · الإطارات · نوعُ الرسم · المؤشّرات · الرسم · لقطة · ملءُ الشاشة ══ */}
      <div ref={topRef} className="pc-top" data-role="pc-top">
        {identity && <div className="pc-ident">{identity}</div>}
        <div className="pc-group" role="group" aria-label="الإطار الزمني" data-role="pc-tfs">
          {barTfs.map(k => (
            <button key={k} type="button" className={"pc-tf" + (tf === k ? " on" : "")} aria-pressed={tf === k} title={tfLong(k)} onClick={() => setTf(k)}>{tfShort(k)}</button>
          ))}
          {!barTfs.includes(tf) && <span className="pc-tf on" aria-current="true" title={tfLong(tf)}>{tfShort(tf)}</span>}
          <Menu label={<ChevronDown size={15} />} title="كلُّ الإطارات وإطارٌ مخصَّص" role="pc-tf-more" wide>
            {close => (
              <div className="pc-tfmenu">
                <div className="pc-tfgrid">
                  {TF_PRESETS.map(k => (
                    <button key={k} type="button" className={"pc-tf" + (tf === k ? " on" : "")} onClick={() => { setTf(k); close(); }}>{tfLong(k)}</button>
                  ))}
                </div>
                <div className="pc-custom" data-role="pc-custom">
                  <span className="pc-cap">إطارٌ مخصَّص</span>
                  <div className="pc-custom-row">
                    <input className="input tabular-nums" type="text" inputMode="numeric" lang="en" dir="ltr" aria-label="العدد" value={cn}
                      onChange={e => setCn(e.target.value.replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 0x0660)).replace(/[^\d]/g, "").slice(0, 3))}
                      onKeyDown={e => { if (e.key === "Enter") applyCustom(close); }} />
                    <div className="seg inline-flex">
                      {TF_UNITS.map(([u, name]) => (
                        <button key={u} type="button" className={"seg-btn chip" + (cu === u ? " on" : "")} onClick={() => setCu(u)}>{name}</button>
                      ))}
                    </div>
                  </div>
                  <button type="button" className="btn-primary pc-apply" disabled={!customOk} onClick={() => applyCustom(close)} data-role="pc-custom-apply">
                    {customOk ? `اعرض ${tfLong(customKey)}` : "عددٌ خارج الحدّ"}
                  </button>
                </div>
              </div>
            )}
          </Menu>
        </div>
        <span className="pc-sep" aria-hidden />
        <Menu label={<TypeIcon size={17} />} title="نوع الرسم" role="pc-type">
          {close => TYPES.map(([k, name, Ic]) => (
            <button key={k} type="button" className={"pc-item" + (ctype === k ? " on" : "")} onClick={() => { setCtype(k); close(); }}>
              <Ic size={15} /> <span>{name}</span>{ctype === k && <Check size={14} className="pc-check" />}
            </button>
          ))}
        </Menu>
        <Menu label={<><Activity size={17} /><span className="pc-btn-txt">المؤشرات</span></>} title="المؤشرات" role="pc-ind">
          {() => IND.map(([k, name, t]) => (
            <button key={k} type="button" className={"pc-item" + (ind[k] ? " on" : "")} aria-pressed={ind[k]} onClick={() => toggleInd(k)} data-ind={k}>
              <span className="pc-dot" style={{ background: `var(${t})` }} /> <span dir={k === "vol" ? undefined : "ltr"}>{name}</span>
              {ind[k] && <Check size={14} className="pc-check" />}
            </button>
          ))}
        </Menu>
        <button type="button" className={"pc-btn" + (railOpen || tool ? " on" : "")} title="أدوات الرسم" aria-label="أدوات الرسم" aria-pressed={railOpen}
          data-role="pc-draw" onClick={() => setRailOpen(o => !o)}><Brush size={17} /></button>
        {(ind.stochrsi || ind.cvd || ind.d7m) && (
          <Menu label={<><Settings2 size={16} /><span className="pc-btn-txt">الإعدادات</span></>} title="إعدادات المؤشرات" role="pc-cfg">
            {close => IND.filter(([k]) => k !== "vol" && k !== "research" && ind[k]).map(([k, name]) => (
              <button key={k} type="button" className="pc-item" data-cfg={k} onClick={() => { close(); if (k === "d7m") setShowCfg(true); else setCfgFor(k as "stochrsi" | "cvd"); }}>
                <Settings2 size={14} /> <span dir="ltr">{name}</span>
              </button>
            ))}
          </Menu>
        )}
        {ind.d7m && cfg.fib && (
          <span className="seg inline-flex pc-fibmode" role="group" aria-label="مستويات D7M" data-role="pc-fibmode">
            {([["compact", "مختصر"], ["all", "الكل"]] as const).map(([v, t]) => (
              <button key={v} type="button" className={"seg-btn chip" + ((cfg.fibMode || "compact") === v ? " on" : "")} aria-pressed={(cfg.fibMode || "compact") === v}
                title={v === "compact" ? "ستةُ خطوط: المقاومةُ والوسطُ والدعم" : "كلُّ المستويات"} onClick={() => saveCfg({ ...cfg, fibMode: v })}>{t}</button>
            ))}
          </span>
        )}
        <span className="pc-grow" />
        <button type="button" className="pc-btn" title="لقطةٌ للرسم" aria-label="لقطةٌ للرسم" onClick={shot}><Camera size={17} /></button>
        <button type="button" className="pc-btn" title={full ? "خروج من ملء الشاشة" : "ملء الشاشة"} aria-label="ملء الشاشة" aria-pressed={full}
          data-role="pc-full" onClick={() => setFull(f => !f)}>{full ? <Minimize2 size={17} /> : <Maximize2 size={17} />}</button>
      </div>
      {showCfg && <D7MPanel cfg={cfg} onChange={saveCfg} onClose={() => setShowCfg(false)} />}
      {cfgFor && <IndSettings kind={cfgFor} sr={srCfg} cvd={cvdCfg} onSr={setSr} onCvd={setCvd} onClose={() => setCfgFor(null)} />}

      {ind.d7m && !preset && <D7MStrip dash={dash} msmart={msmart} tt={tt} alerts={alerts} />}
      <div className="pc-body">
        {/* ══ سكّةُ أدوات الرسم — على يسار الرسم كتريدنق فيو (وصفٌّ فوقه على الجوال) ══ */}
        {(railOpen || tool) && (
          <div className="pc-rail" role="toolbar" aria-label="أدوات الرسم" data-role="pc-rail">
            {([[null, "مؤشّر", MousePointer2], ["trend", "خطُّ اتجاه", TrendingUp], ["hline", "خطٌّ أفقيّ", Minus], ["brush", "فرشاة", Brush]] as const).map(([k, name, Ic]) => (
              <button key={String(k)} type="button" className={"pc-btn" + (tool === k ? " on" : "")} title={name} aria-label={name} aria-pressed={tool === k}
                data-tool={String(k)} onClick={() => setTool(k as Tool)}><Ic size={17} /></button>
            ))}
            <span className="pc-rail-sep" aria-hidden />
            <button type="button" className="pc-btn" title="تراجع عن آخر رسم" aria-label="تراجع عن آخر رسم" disabled={!draws.length}
              data-role="pc-undo" onClick={() => saveDraws(draws.slice(0, -1))}><Undo2 size={17} /></button>
            <button type="button" className="pc-btn pc-danger" title="مسح كلّ الرسم" aria-label="مسح كلّ الرسم" disabled={!draws.length}
              data-role="pc-clear" onClick={() => saveDraws([])}><Trash2 size={17} /></button>
          </div>
        )}

        <div className="pc-main">
        <div className="pc-stage chart-lock" style={{ height: stageH }} data-role="pc-stage" data-noswipe>
          <div ref={boxRef} className="pc-box" />

          {/* وسيلةُ الإيضاح — قيمُ الشمعة تحت خطّ التقاطع، ثمّ مؤشّراتُ اللوحة الرئيسة */}
          <div className="pc-legend" dir="ltr" data-role="pc-legend">
            <div className="pc-ohlc">
              <span className="pc-k">O</span><b ref={lv("o")} data-k="o">—</b><span className="pc-k">H</span><b ref={lv("h")} data-k="h">—</b>
              <span className="pc-k">L</span><b ref={lv("l")} data-k="l">—</b><span className="pc-k">C</span><b ref={lv("c")} data-k="c">—</b>
              <b ref={lv("chg")} className="pc-chg" data-k="chg" />
              <b ref={lv("basis")} className="pc-dim pc-basis" data-k="basis" />
            </div>
            <div className="pc-chips">
              {ind.vol && (volOk ? chip("vol", <><span className="pc-k">Vol</span><b ref={lv("vol")}>—</b></>)
                : chip("vol", <><span className="pc-k">Vol</span><b className="pc-dim">غير متوفّر</b></>))}
              {ind.cvd && !volOk && chip("cvd", <><span className="pc-k" style={{ color: "var(--chart-3)" }}>CVD D7M</span><b className="pc-dim">غير متوفّر — لا حجم</b></>)}
              {ind.d7m && chip("d7m", <span className="pc-k" style={{ color: "var(--brand-ink)" }}>D7M</span>)}
              {ind.research && chip("research", <><span className="pc-k" style={{ color: "var(--ri-fib)" }}>مؤشر الأبحاث</span>
                <span className="pc-k" style={{ color: "var(--ri-sma20)" }}>20 SMA</span><b ref={lv("ri20")} style={{ color: "var(--ri-sma20)" }}>—</b>
                <span className="pc-k" style={{ color: "var(--ri-sma50)" }}>50 SMA</span><b ref={lv("ri50")} style={{ color: "var(--ri-sma50)" }}>—</b></>)}
            </div>
          </div>
          {eff.research && paneTops.researchRsi != null && (
            <div className="pc-legend pc-pane-legend" dir="ltr" style={{ top: paneTops.researchRsi + 4 }} data-role="pane-tag" data-ind="researchRsi">
              {chip("research", <><span className="pc-k" style={{ color: "var(--ri-rsi)" }}>RSI 14 close</span><b ref={lv("riRsi")} style={{ color: "var(--ri-rsi)" }}>—</b></>)}
            </div>
          )}
          {oscOn.map(k => paneTops[k] != null && (
            <div key={k} className="pc-legend pc-pane-legend" dir="ltr" style={{ top: paneTops[k] + 4 }} data-role="pane-tag" data-ind={k}>
              {k === "research" && chip("research", <><span className="pc-k" style={{ color: "var(--ri-fib)" }}>مؤشر الأبحاث · Volume</span><b ref={lv("riV")}>—</b></>)}
              {k === "stochrsi" && chip("stochrsi", <><span className="pc-k" style={{ color: "var(--info-ink)" }}>Stoch RSI {srCfg.k} {srCfg.d} {srCfg.rsiLen} {srCfg.stochLen} {srCfg.src}</span>
                <b ref={lv("srK")} style={{ color: "var(--info-ink)" }}>—</b><b ref={lv("srD")} style={{ color: "var(--gauge-warn)" }}>—</b></>)}
              {k === "cvd" && chip("cvd", <><span className="pc-k" style={{ color: "var(--chart-3)" }}>
                CVD D7M · {cvdCfg.scale === "levels" ? "مستويات" : cvdCfg.scale === "pct" ? "نسبة" : "احجام"} {cvdCfg.len}</span><b ref={lv("cvd")}>—</b>
                {cvdCfg.ema2 && cvdCfg.style === "candle" && <b ref={lv("cvdE")} className="pc-dim">—</b>}</>)}
            </div>
          ))}

          {tool && (
            <div className="pc-draw-layer" style={{ right: axisW, height: (mainH || mainPx) - 2 }} data-role="pc-draw-layer" data-mode={tool}
              onPointerDown={drawDown} onPointerMove={drawMove} onPointerUp={drawUp} onPointerCancel={drawCancel} />
          )}
          {(away || manual) && bars.length > 0 && (
            <button type="button" className="pc-live" style={{ right: axisW + 10, top: (mainH || mainPx) - 46 }} title="إلى آخر شمعة" aria-label="إلى آخر شمعة"
              data-role="pc-live" onClick={goLive}><ChevronsRight size={17} /></button>
          )}
          {(isPending || isError || empty) && (
            <div className={"pc-cover" + (isPending ? " pc-loading" : "")} data-role="pc-cover" role="status">
              {isPending ? <span className="pc-progress" aria-label="جارٍ الجلب" /> : isError ? "تعذّر جلبُ الشموع." : `لا شموعَ لهذا الرمز على إطار ${tfLong(tf)}.`}
            </div>
          )}
        </div>
        {/* ══ الشريطُ السفليّ تحت الرسم مباشرةً كتريدنق فيو: المدى · الساعةُ بمنطقتها الزمنية · مقياسُ السعر ══ */}
        <div className="pc-foot" data-role="pc-foot">
          <div className="pc-ranges" role="group" aria-label="المدى" data-role="pc-ranges">
            {RANGES.map(([lbl, d, rtf]) => (
              <button key={lbl} type="button" className="pc-tf" title={`${lbl} · ${tfLong(rtf)}`} onClick={() => goRange(d, rtf)}>{lbl}</button>
            ))}
          </div>
          <span className="pc-grow" />
          <Menu up role="pc-tz" title="المنطقة الزمنية" label={<span dir="ltr" className="pc-clockwrap"><span ref={clockRef} className="tabular-nums" data-role="pc-clock" />
            <span className="pc-dim"> ({fmtOffset(tzOffsetMin(tzName, nowS))})</span></span>}>
            {close => tzItems.map(([k, name, off]) => (
              <button key={k} type="button" className={"pc-item" + (tzPref === k ? " on" : "")} data-tz={k} onClick={() => { setTz(k); close(); }}>
                <span className="pc-off tabular-nums" dir="ltr">{fmtOffset(off)}</span><span>{name}</span>
                {tzPref === k && <Check size={14} className="pc-check" />}
              </button>
            ))}
          </Menu>
          <span className="pc-sep" aria-hidden />
          <button type="button" className={"pc-btn" + (scaleMode === 2 ? " on" : "")} aria-pressed={scaleMode === 2} title="مقياسٌ نسبيّ" aria-label="مقياسٌ نسبيّ"
            data-role="pc-pct" onClick={() => setScale(scaleMode === 2 ? 0 : 2)}>%</button>
          <button type="button" className={"pc-btn" + (scaleMode === 1 ? " on" : "")} aria-pressed={scaleMode === 1} title="مقياسٌ لوغاريتميّ" aria-label="مقياسٌ لوغاريتميّ"
            data-role="pc-log" onClick={() => setScale(scaleMode === 1 ? 0 : 1)}>log</button>
          <button type="button" className={"pc-btn" + (!manual ? " on" : "")} aria-pressed={!manual} title="مقياسٌ تلقائيّ" aria-label="مقياسٌ تلقائيّ"
            data-role="pc-auto" onClick={() => { chartRef.current?.priceScale("right").applyOptions({ autoScale: true }); setManual(false); }}>تلقائي</button>
        </div>
        </div>
      </div>
    </div>
  );
}
