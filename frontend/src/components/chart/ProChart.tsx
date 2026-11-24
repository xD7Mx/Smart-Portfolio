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
  Settings2, ChevronDown, ChevronRight, Check, MousePointer2, ChevronsRight, Eye, EyeOff, Palette, Star,
} from "lucide-react";
import { marketApi } from "../../services/api";
import {
  sanitizeBars, CBar, TF_BAR, TF_PRESETS, TF_UNITS, TfUnit, parseTf, tfKey, tfShort, tfLong, tfIntraday, tickLabel, crossLabel, fmtPrice, fmtVol,
  TZ_LIST, exchangeTz, tzOffsetMin, fmtOffset, displayTimes,
} from "../../lib/chartData";
import { ChartOverlay, BandFill, Level, Segment, Path, Note, Band } from "../../lib/chartOverlay";
import { cvdD7M, CVD_DEFAULTS, CvdCfg, stochRsi, STOCHRSI_DEFAULTS, StochRsiCfg, source, macd as macdCalc } from "../../lib/indicators";
import IndSettings from "./IndSettings";
import {
  autoFib, autoChannel, autoTrend, vwapAnchored, ema as emaD7, zigzag, D7M_DEFAULTS, D7MSettings, D7M_COLORS, FIB_SIX,
} from "../analysis/d7m";
import D7MPanel from "../analysis/D7MPanel";
import ForcePanels from "./ForcePanels";
import { type ReadFrame } from "./ChartRead";
import { trendForce, liquidityForce } from "../analysis/pulse";
import LiveQuote, { useLive } from "./LiveQuote";

/* ‏D744 (المالك 2026-11-15): «لا أريد كثرةَ المؤشّرات — أريد CVD ومؤشّرَ الدحم وStoch RSI المدمج». فهي الثلاثة مع الحجم، ولكلٍّ إعداداتُه
   كتريدنق فيو (ترسٌ واحدٌ يفتح نافذةَ كلّ مؤشّر). كانت معها: SMA 20/50/200 وRSI وStochastic وMACD. */
/* ‏D756 (المالك 2026-11-16): «لم أجد مؤشّر الماكد — لازم يكون موجوداً» — ‏MACD 12 26 9 بلوحته كتريدنق فيو */
type IndKey = "vol" | "stochrsi" | "cvd" | "macd" | "d7m";
const IND: [IndKey, string, string][] = [
  ["vol", "الحجم", "--ink-muted"], ["stochrsi", "Stoch RSI", "--info-ink"], ["cvd", "CVD D7M", "--chart-3"], ["macd", "MACD", "--info-ink"],
  ["d7m", "D7M", "--brand-ink"]];
const OSC: IndKey[] = ["stochrsi", "cvd", "macd"];
const IND_DEF: Record<IndKey, boolean> = { vol: true, stochrsi: true, cvd: true, macd: false, d7m: true };
type ChartType = "candles" | "hollow" | "bars" | "line" | "area";
const TYPES: [ChartType, string, any][] = [["candles", "شموع", CandlestickChart], ["hollow", "شموعٌ مفرَّغة", CandlestickChart],
  ["bars", "أعمدة", BarChart3], ["line", "خطّ", LineChart], ["area", "منطقة", AreaChart]];
type Tool = null | "trend" | "hline" | "brush";
/* أزرارُ المدى أسفلَ الرسم كتريدنق فيو: كلٌّ يختار إطارَه ويعرض مدّتَه */
const RANGES: [string, number | "ytd" | "all", string][] = [["يوم", 1, "1m"], ["5 أيام", 5, "5m"], ["شهر", 30, "30m"], ["3 أشهر", 91, "1h"],
  ["6 أشهر", 182, "2h"], ["منذ بداية العام", "ytd", "1d"], ["سنة", 365, "1d"], ["5 سنوات", 1826, "1wk"], ["الكل", "all", "1mo"]];

/* ‏D795 (المالك 2026-11-24) ينقض «أكثرَ ثلاثةٍ استخداماً» (‏D782): «الثلاثةُ أطرٍ تُنتخب بالتفضيل — ساعةٌ وأربعُ ساعات لا يستحقّون البقاءَ هنا إذا لم
   أفضّلها أنا… نجمةٌ بجانب الإطار… تظهر بالترتيب حسب الضغط: يوم، أسبوع، شهر… والإطارُ المخصَّص بالتفضيل». فالشريطُ مفضّلاتُ المالك بترتيب نجماتها
   (واحدةٌ لكلّ الشاشات، في المتصفّح)، والجاري إن لم يكن منها، وكلُّ الإطارات في السهم المنبثق بنجمةٍ لكلٍّ. */
const FAV_KEY = "sp_chart_tf_fav";
const readFav = (): string[] => { try { const v = JSON.parse(lsGetRaw(FAV_KEY) || "[]"); return Array.isArray(v) ? [...new Set(v.map(String).filter(x => parseTf(x)))] : []; } catch { return []; } };
function useTfFav() {
  const [fav, setFav] = useState<string[]>(readFav);
  useEffect(() => {
    const on = () => setFav(readFav());
    window.addEventListener("sp-tf-fav", on); window.addEventListener("storage", on);
    return () => { window.removeEventListener("sp-tf-fav", on); window.removeEventListener("storage", on); };
  }, []);
  const toggle = (k: string) => {
    const cur = readFav(), nx = cur.includes(k) ? cur.filter(x => x !== k) : [...cur, k];
    try { localStorage.setItem(FAV_KEY, JSON.stringify(nx)); } catch { /* خاصّ */ }
    setFav(nx); window.dispatchEvent(new Event("sp-tf-fav"));
  };
  return [fav, toggle] as const;
}
function lsGetRaw(k: string) { try { return localStorage.getItem(k); } catch { return null; } }
/* ‏D782: الشاشاتُ المتعدّدة — لكلّ شاشةٍ إطارُها ومؤشّراتُها (الأولى كما هي، والبقيّةُ أربعُ ساعاتٍ فساعةٌ فربعُ ساعةٍ افتراضاً) */
const SLOT_TF = ["1wk", "4h", "1h", "15m"];

const lsGet = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const lsSet = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* وضعُ التصفّح الخاصّ */ } };
const lsJson = <T,>(k: string, def: T): T => { try { return { ...def, ...(JSON.parse(lsGet(k) || "{}") || {}) }; } catch { return def; } };

/* الرموزُ لا تصل لوحةَ الرسم (‏canvas لا تفهم var) — تُقرأ قيمُها المحسوبة عند الرسم، والرمزُ يبقى مصدرَ الحقيقة */
const tok = (name: string, fb: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fb;
/** لونُ الرمز بصيغة ‏#rrggbb لمنتقي اللون (‏D756) */
const hexTok = (name: string) => {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (/^#[0-9a-f]{6}$/i.test(v)) return v;
  const m = v.match(/\d+(\.\d+)?/g);
  return m && m.length >= 3 ? "#" + m.slice(0, 3).map(x => Math.round(+x).toString(16).padStart(2, "0")).join("") : "#000000";
};
/* ‏D772 (المالك 2026-11-20 بصورةٍ من تريدنق فيو): «الألوانُ باهتة — نبغى ألواناً مشبعةً نظيفة، وخلفيةُ الشارت سوداء حتى يعطي عكساً للألوان»:
   فللرسم رموزُه (‏--pc-*) واحدةً في المظهرين — لوحةٌ سوداء، وشموعٌ بيضاءُ وحمراءُ افتراضاً، وخطوطٌ مُصمَتةٌ مشبعة — وتبقى رموزُ D7M لغيره */
const PC: Record<string, string> = {
  fib: "--pc-fib", fibGold: "--pc-fib-gold", zone: "--pc-text", trendUp: "--pc-trend-up", trendDown: "--pc-trend-down", channel: "--pc-channel",
  vwap: "--pc-vwap", band: "--pc-band", ema20: "--pc-ema20", ema50: "--pc-ema50", ema100: "--pc-ema100", ema200: "--pc-ema200", ema400: "--pc-ema400",
  draw: "--pc-draw",
};
/* ‏D772: «أقدر أغيّر ألوانَ الشموع — أخضر وأسود، أبيض وأحمر» — قوالبُ جاهزة ولوحتا ألوانٍ مشبعة؛ والأسودُ على اللوحة السوداء بحافّةٍ تُظهره */
const CANDLE_PRESETS: [string, string, string][] = [["أبيض · أحمر", "--pc-up", "--pc-down"], ["أخضر · أحمر", "--pc-green", "--pc-down"],
  ["أخضر · أسود", "--pc-green", "--pc-black"], ["أبيض · أسود", "--pc-up", "--pc-black"]];
const SWATCHES = ["--pc-sw-1", "--pc-sw-2", "--pc-sw-3", "--pc-sw-4", "--pc-sw-5", "--pc-sw-6", "--pc-sw-7", "--pc-sw-8", "--pc-sw-9"];
const dark = (c: string) => { const m = /^#([0-9a-f]{6})$/i.exec(c); if (!m) return false; const n = parseInt(m[1], 16);
  return (0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) < 40; };
/** رمزٌ يُعرف اسمُه وقتَ التشغيل (ألوانُ D7M من جدولها) — واحتياطُه حبرُ النصّ الثانويّ. */
const tokv = (name: string) => tok(name, "") || tok("--ink-muted", "#6b7280");
const tokA = (name: string, fb: string, a: number) => {
  const c = tok(name, fb);
  const m = /^#([0-9a-f]{6})$/i.exec(c);
  if (m) { const n = parseInt(m[1], 16); return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`; }
  const p = c.match(/[\d.]+/g);
  return p && p.length >= 3 ? `rgba(${p[0]}, ${p[1]}, ${p[2]}, ${a})` : c;
};

/** لونُ المالك (‏#rrggbb) بشفافية — لخلفية Stoch RSI (‏D784) */
const hexA = (c: string, a: number) => { const m = /^#([0-9a-f]{6})$/i.exec(c); if (!m) return c; const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`; };

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
const IND_STOCK: Record<IndKey, boolean> = { vol: true, stochrsi: false, cvd: false, macd: false, d7m: true };

export default function ProChart({ symbol, theme = "dark", preset, slot = 0, mini = false, rows = 1, share, snaps, fit, embedded = false, fillH = null, tools }: {
  symbol: string; theme?: "dark" | "light"; preset?: "stock";
  /* ‏D782: الشاشاتُ المتعدّدة — رقمُ الشاشة (لحفظ إطارها ومؤشّراتها)، وشكلُها المختصر، وصفوفُها، ومبدّلُ عددها، وسجلُّ لقطاتها لـ«تحليل الرسم» */
  slot?: number; mini?: boolean; rows?: number;
  snaps?: React.MutableRefObject<Map<number, () => ReadFrame | null>>;
  /* ‏D794 (المالك 2026-11-24): «صفٌّ خارجيٌّ أساسيّ — الأحداثُ وتحليلُ الرسم وبجانبها تقسيمُ الشاشة والتكبيرُ والتصغير — خارجَ الشاشات»: في غرفة
     التداول (‏embedded) لا هويّةَ ولا ملءَ شاشةٍ ولا مبدّلَ شاشاتٍ داخل الرسم — كلُّها في الصفّ الخارجيّ؛ و‏fillH ارتفاعُ الرسم في «التكبير» يقيسه الصفّ */
  embedded?: boolean; fillH?: number | null;
  /* ‏D787: ما فوق الشاشات المختصرة من الصفحة (‏top) ورأسُ كلّ شاشة (‏head) — وفي «تكبير الشاشات» يقلّ ما فوقها فتكبر */
  fit?: { top: number; head: number };
  /* ‏D803 (المالك 2026-11-24: «أبغى أمدّد واحدةً وأنقص… مرونة»): نصيبُ الشاشة من ارتفاع الشبكة (يُسحب الفاصلُ فيتغيّر) — بديلُ ‏1/rows */
  share?: number;
  /* ‏D801 (المالك 2026-11-24: «زرُّ تقسيم الشاشات بجانب الإطارات — لا آخرَ شيءٍ على اليسار»): ما تضعه الغرفةُ بعد أزرار الإطارات مباشرة */
  tools?: React.ReactNode;
}) {
  /* ── الاختيارات المحفوظة ── */
  const KT = preset ? "sp_stock_tf" : slot ? `sp_chart_tf_s${slot}` : "sp_chart_tf", KI = preset ? "sp_stock_ind_v3" : slot ? `sp_chart_ind_v3_s${slot}` : "sp_chart_ind_v3";
  const [tf, setTfState] = useState(() => { const v = lsGet(KT); return v && parseTf(v) ? v : SLOT_TF[slot] || "1wk"; });
  const [fav, toggleFav] = useTfFav();
  const setTf = (v: string) => {
    if (!parseTf(v)) return;
    setTfState(v); lsSet(KT, v);
  };
  const [customTfs, setCustomTfs] = useState<string[]>(() => { try { return (JSON.parse(lsGet("sp_chart_tf_custom") || "[]") as string[]).filter(x => parseTf(x)).slice(0, 4); } catch { return []; } });
  const [ctype, setCtypeState] = useState<ChartType>(() => (TYPES.some(t => t[0] === lsGet("sp_chart_type")) ? lsGet("sp_chart_type") as ChartType : "candles"));
  const setCtype = (v: ChartType) => { setCtypeState(v); lsSet("sp_chart_type", v); };
  const [ind, setIndState] = useState<Record<IndKey, boolean>>(() => lsJson(KI, preset || slot ? IND_STOCK : IND_DEF));
  const toggleInd = (k: IndKey) => setIndState(s => { const n = { ...s, [k]: !s[k] }; lsSet(KI, JSON.stringify(n)); return n; });
  const [cvdCfg, setCvdState] = useState<CvdCfg>(() => lsJson("sp_cvd_cfg", CVD_DEFAULTS));
  const setCvd = (p: Partial<CvdCfg>) => setCvdState(c => { const n = { ...c, ...p }; lsSet("sp_cvd_cfg", JSON.stringify(n)); return n; });
  const [srCfg, setSrState] = useState<StochRsiCfg>(() => lsJson("sp_stochrsi_cfg", STOCHRSI_DEFAULTS));
  const [cfgFor, setCfgFor] = useState<null | "stochrsi" | "cvd">(null);
  /* ‏D756: عينُ الإخفاء لكلّ مؤشّرٍ ولها كلِّها، وألوانُ الشموع — تُحفظ في المتصفّح */
  const [hid, setHidState] = useState<Record<string, boolean>>(() => lsJson("sp_chart_hid", {}));
  const toggleHid = (k: string) => setHidState(s => { const nx = { ...s, [k]: !s[k] }; lsSet("sp_chart_hid", JSON.stringify(nx)); return nx; });
  const [hideAll, setHideAll] = useState(() => lsGet("sp_chart_hideall") === "1");
  const [cc, setCcState] = useState<{ up?: string; down?: string }>(() => lsJson("sp_chart_candle", {}));
  const setCc = (v: { up?: string; down?: string }) => { setCcState(v); lsSet("sp_chart_candle", JSON.stringify(v)); };
  const setSr = (p: Partial<StochRsiCfg>) => setSrState(c => { const n = { ...c, ...p }; lsSet("sp_stochrsi_cfg", JSON.stringify(n)); return n; });
  const [cfg, setCfgState] = useState<D7MSettings>(() => {
    try { const sv = JSON.parse(lsGet("sp_d7m_cfg_v2") || "{}");
      const m = { ...D7M_DEFAULTS, ...sv, colors: { ...D7M_DEFAULTS.colors, ...(sv.colors || {}) } };
      /* ‏D783 (المالك 2026-11-21): «الفيبو أربعَ عشرةَ مستوىً — عددتُها في تريدنق فيو — وعندنا ناقصة»: الثلاثةُ المخفيّةُ بأمر ‏D756 (1.1 · 0.618 · 0.5)
         تُخفى من «مختصر» وحده وتعود إلى «الكل» — مرّةً واحدة، وما أخفاه المالكُ بيده بعدها يبقى */
      if ((Number(sv.fibV) || 1) < 4) m.fibLevels = { ...m.fibLevels, ...Object.fromEntries([1.1, 0.618, 0.5].map(lv => [String(lv), true])) };
      /* ‏D772: الرقمُ فوق خطّه كتريدنق فيو (كان «على الخطّ» بفُسحةٍ تقطعه) — مرّةً واحدة، وما اختاره المالكُ بعدها يبقى */
      if ((Number(sv.fibV) || 1) < 3) m.fibLabelPos = "above";
      /* ‏D784 (المالك 2026-11-22): «مختصر ستّةُ خطوطٍ لا ثلاثة — كلُّ خطّين منطقة… وتُطبَّق على الجميع»: الستّةُ ظاهرةٌ مرّةً واحدة */
      if ((Number(sv.fibV) || 1) < 5) m.fibLevels = { ...m.fibLevels, ...Object.fromEntries(FIB_SIX.map(lv => [String(lv), true])) };
      return { ...m, fibV: 5 }; } catch { return D7M_DEFAULTS; }
  });
  const saveCfg = (c: D7MSettings) => { setCfgState(c); lsSet("sp_d7m_cfg_v2", JSON.stringify(c)); };
  const [showCfg, setShowCfg] = useState(false);
  /* ‏D783: منتقي اللون في الإعدادات يعرض اللونَ المرسومَ فعلاً — رموزُ الرسم (‏--pc-*)، والقناةُ والرسمُ اليدويُّ بلون الهويّة كما يُرسمان */
  const colorDefaults = () => Object.fromEntries(D7M_COLORS.map(([k, , t]) => [k, hexTok(k === "channel" || k === "draw" ? "--brand-ink" : PC[k] || t)]));
  /* ‏D781 (المالك): «كتريدنق فيو — سهمٌ في اليسار يطوي أسماءَ المؤشّرات (ويُبقي عددَها)، والضغطُ على المؤشّر نفسِه في الرسم يفتح إعداداته» */
  const [legFold, setLegFold] = useState(() => lsGet("sp_chart_legfold") === "1");
  const foldLeg = () => setLegFold(v => { lsSet("sp_chart_legfold", v ? "0" : "1"); return !v; });
  const hasCfg = (k: string) => k === "d7m" || k === "stochrsi" || k === "cvd";
  const openCfg = (k: string) => { if (k === "d7m") setShowCfg(true); else if (k === "stochrsi" || k === "cvd") setCfgFor(k); };
  const openCfgRef = useRef(openCfg);
  openCfgRef.current = openCfg;
  const [tool, setTool] = useState<Tool>(null);
  /* ‏D810 (المالك): «النقرتان على أيّ مؤشّرٍ في أيّ شاشة تكبّره وحده فيأخذ مكانَ الباقي — والنقرتان مرّةً أخرى تعيدان الكلّ»:
     ‏"main" للرسم نفسِه، أو مفتاحُ لوحةٍ سفلى (‏stochrsi · cvd · macd) */
  const [solo, setSolo] = useState<string | null>(null);
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
    /* ‏D756 (المالك: «CVD لا يعمل — يقول لا أحجام»): الحكمُ على آخر ثلاثمئة شمعة — يوميُّ تاسي منذ 2007 بلا كمّيةٍ قبل مدى ساعاته */
    if (raw !== undefined) { const tl = bars.slice(-300); volRef.current = tl.length > 0 && tl.filter(b => b.volume > 0).length >= tl.length * 0.8; }
    return volRef.current;
  }, [raw, bars]);
  const eff = useMemo(() => ({ ...ind, vol: ind.vol && volOk, cvd: ind.cvd && volOk }), [ind, volOk]);
  /* ‏D761 (المالك): «أريد الأرقام تتحرّك — حيويةً كتريدنق فيو»: السعرُ الحيُّ وحالةُ السوق كلَّ خمس ثوانٍ في الجلسة */
  const { data: live } = useLive(symbol);

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
  /* ‏D782: الرسمُ اليدويُّ للرمز واحدٌ في الشاشات المتعدّدة — ما يُرسم في شاشةٍ يظهر في أخواتها فوراً، ولا تكتب إحداها فوق الأخرى */
  const uid = useRef(Math.random());
  const saveDraws = (d: any[]) => {
    setDraws(d); lsSet(dKey, JSON.stringify(d)); marketApi.saveDrawings(symbol, d).catch(() => {});
    window.dispatchEvent(new CustomEvent("sp-draws", { detail: { symbol, items: d, from: uid.current } }));
  };
  useEffect(() => {
    const on = (e: Event) => { const d = (e as CustomEvent).detail; if (d && d.symbol === symbol && d.from !== uid.current) setDraws(d.items || []); };
    window.addEventListener("sp-draws", on);
    return () => window.removeEventListener("sp-draws", on);
  }, [symbol]);

  /* ── الحساب ── مرّةً لكلّ تغيّرٍ في الشموع أو الإعدادات، ويقرؤه الرسمُ ووسيلةُ الإيضاح معاً */
  const calc = useMemo(() => {
    const closes = bars.map(b => b.close);
    return { closes, stochrsi: stochRsi(source(bars, srCfg.src), srCfg), cvd: cvdD7M(bars, cvdCfg), macd: macdCalc(closes, 12, 26, 9) };
  }, [bars, cvdCfg, srCfg]);
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
  /* ‏D782 (المالك): «لوحتان مهمّتان: قوّةُ الاتجاه وقوّةُ السيولة — بسيطٌ وواضح» — بدل شريط D7M (القرار · الأطر الأربعة · الحيتان ·
     ‏ADX · المحلّل · التنبيهات · الصفقة) — من شموع هذا الإطار نفسِه (‏analysis/pulse) */
  const force = useMemo(() => (ind.d7m && cfg.dashboard && !preset && bars.length >= 30
    ? { trend: trendForce(bars as any), liq: liquidityForce(bars as any, volOk) } : null), [bars, volOk, ind.d7m, cfg.dashboard, preset]);

  /* ── مراجعُ الرسم ── */
  const boxRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainRef = useRef<ISeriesApi<any> | null>(null);
  const markRef = useRef<any>(null);
  const overlay = useRef(new ChartOverlay());
  const reg = useRef(new Map<string, { sig: string; series: ISeriesApi<any>[]; vis?: boolean[] }>());
  const sigRef = useRef({ main: "", key: "", n: 0, first: null as any, panes: "" });
  const legend = useRef<Record<string, HTMLElement | null>>({});
  const pend = useRef<any>(null);                 // أوّلُ نقطتَي خطّ الاتجاه
  const preview = useRef<Segment | null>(null);
  const stroke = useRef<{ x: number; y: number }[] | null>(null);
  const S = useRef({ bars, calc, tool, d7m, cfg, draws, ind, ctype, theme, cvdCfg, disp, hid, hideAll, cc });
  S.current = { bars, calc, tool, d7m, cfg, draws, ind, ctype, theme, cvdCfg, disp, hid, hideAll, cc };

  /* الارتفاع: الرسمُ كلُّه داخل الشاشة كتريدنق فيو — اللوحاتُ السفلى تقتسم ارتفاعَه ولا تدفعه تحت الطيّ، إلّا إن ضاقت الرئيسةُ عن حدّها */
  const oscOn = OSC.filter(k => eff[k]);
  const soloK = oscOn.length && (solo === "main" || oscOn.includes(solo as IndKey)) ? solo : null;   // مؤشّرٌ أُطفئ وهو مكبَّر ⇒ يعود الكلّ
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
  const chromeH = (topRef.current?.offsetHeight ?? 50) + (narrow && (railOpen || tool) ? 42 : 0);
  const stripH = force ? (mini ? 36 : 66) : 0;                                   // لوحتا الاتجاه والسيولة فوق الرسم (‏D782)
  const baseH = fillH != null ? Math.max(240, fillH) : full ? Math.max(300, winH - chromeH - 2) : mini ? (narrow ? 300 : clamp((winH - (fit?.top ?? 250)) * (share ?? 1 / Math.max(1, rows)) - 84 - stripH - (fit?.head ?? 0), 180, 1400))
    : preset ? (wide ? 480 : 400) : wide ? clamp(winH - 345 - stripH - (embedded ? 46 : 0), 400, 740) : clamp(winH - 380, 340, 460);
  /* ‏D782: الشاشةُ المختصرة تقتسم ارتفاعَها — و‏D803: لوحاتُ المؤشّرات فيها تتبع نصيبَها (لا 70px ثابتة) وحدُّ الرسم الأدنى 96، فسحبُ الفاصل
     يكبّر الرسمَ ومؤشّراتِه معاً؛ كانت المؤشّراتُ الثابتةُ وحدُّ 140 يمتصّان السحبَ كلَّه في شاشةٍ عاديّة الارتفاع */
  const oscPx = mini ? clamp(Math.round(baseH * 0.22), 44, 80) : wide ? 104 : 88;
  const mainPx = Math.max(full || fillH != null ? 200 : mini ? 96 : wide ? 300 : 250, baseH - oscOn.length * oscPx);
  const stageH = mainPx + oscOn.length * oscPx;

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
    const up = st.cc.up || tok("--pc-up", "#ffffff"), down = st.cc.down || tok("--pc-down", "#f23645");
    const drawC = st.cfg.colors?.draw || tok("--brand-ink", "#5b52d3");
    const levels: Level[] = [], segments: Segment[] = [], paths: Path[] = [], notes: Note[] = [], bands: Band[] = [];
    const last = b[b.length - 1];
    if (last) levels.push({ price: last.close, color: last.close >= last.open ? up : down, tag: true, bold: true, rank: 0, dash: [2, 3] });
    const D = st.hideAll || st.hid.d7m ? null : st.d7m;           // ‏D756: عينُ الإخفاء
    if (D) {
      const C = (k: string) => st.cfg.colors?.[k] || tokv(PC[k] || (D7M_COLORS.find(x => x[0] === k) || ["", "", "--ink"])[2]);
      /* ‏D772: كان الخطُّ رمادياً بشفافية 0.6 والرقمُ مُصمَتاً — فاختفى الخطُّ على اللوحة الداكنة وبقي رقمُه «بلا خطّ»: الخطُّ والرقمُ لونٌ واحدٌ مُصمَت */
      const ink = C("fib");
      /* ‏D744 (المالك): «شِل الكلام — المقاومة والدعم ولا تطمع — الشارتُ نظيف»: لا نصَّ على الرسم إلا رقمُ المستوى، والمناطقُ الثلاث
         تظليلٌ خفيف (المقاومة · الوسط: الاتجاهُ المعاكس والدعمُ القويّ · الدعم). و«مختصر» ستةُ خطوطها وحدها، و«الكل» كلُّ المستويات */
      if (D.fib) {
        /* ‏D784 (المالك 2026-11-22): «مختصر ستّةُ خطوطٍ لا ثلاثة — كلُّ خطّين منطقة: خطّان للدعم وخطّان للمقاومة وخطّان في الوسط حيث يتحرّك السهم»
           (مثالُه على تاسي: 11486 · 11293 · 10558 · 10330 · 9367 · 9175 ⇐ المستويات 1.1 · 1 · 0.618 · 0.5 · 0 · −0.1)؛ و«الكل» الأربعَ عشرةَ
           كتريدنق فيو (‏D783) — إلّا ما أخفاه المالكُ من الإعدادات */
        const SIX = new Set(FIB_SIX), compact = (st.cfg.fibMode || "compact") === "compact";
        const shown = (lv: number) => st.cfg.fibLevels[String(lv)] !== false && (!compact || SIX.has(lv));
        /* ‏D761 (المالك): «الرقمُ نفسُه سادةً — السعرُ على الخطّ بلا نسبةٍ ولا دائرة، ولونُه لونُ الخطّ» — والنصُّ بلون الخطّ مُصمَتاً ليُقرأ */
        const lx = b.length - 1 + 3, lpos = st.cfg.fibLabelPos || "above", inkTxt = ink;
        /* ‏D799: «ثابتةٌ على الشموع» (الافتراض) تبدأ من أوّل نقطتَي موجتها — و«تتبع الشاشة» على عرضها كما كانت */
        const x0 = (st.cfg.fibAnchor || "fixed") === "fixed" ? D.fib.startIndex : undefined;
        for (const l of D.fib.lines) {
          if (!shown(l.level)) continue;
          const gold = l.color === "yellow";
          levels.push({ price: l.price, color: gold ? C("fibGold") : ink, label: fmtPrice(l.price), lx, lpos, lcolor: gold ? C("fibGold") : inkTxt,
                        rank: gold ? 2 : 3, width: 1, x0 });
        }
        if (st.cfg.fibZones) {
          const at = (lv: number) => (shown(lv) ? D.fib!.lines.find(x => x.level === lv)?.price : undefined);
          const pairs = [[0, -0.1], [1, 1.1]].map(([u, v]) => [at(u), at(v)]).filter(([u, v]) => u != null && v != null) as [number, number][];
          pairs.sort((x, y) => (y[0] + y[1]) - (x[0] + x[1]));
          if (pairs[0]) bands.push({ p1: pairs[0][0], p2: pairs[0][1], color: tokA("--neg-ink", "#dc2626", 0.07), x0 });
          if (pairs[1]) bands.push({ p1: pairs[1][0], p2: pairs[1][1], color: tokA("--pos-ink", "#16a34a", 0.07), x0 });
          const m1 = at(0.5), m2 = at(0.618);
          if (m1 != null && m2 != null) bands.push({ p1: m1, p2: m2, color: tokA("--gauge-warn", "#d97706", 0.09), x0 });
        }
      }
      if (D.trend) for (const l of D.trend.lines) if (l.x2 > l.x1 && (l.major ? st.cfg.trendMajor !== false : st.cfg.trendMinor !== false))
        segments.push({ x1: l.x1, y1: l.y1, x2: l.x2, y2: l.y2, color: l.up ? C("trendUp") : C("trendDown"), width: l.major ? 2 : 1, dash: l.major ? [] : [5, 4] });
      if (D.channel) {
        const chC = st.cfg.colors?.channel || tokA("--brand-ink", "#5b52d3", 0.65);
        for (const seg of [D.channel.base, D.channel.parallel]) if (seg.length >= 2)
          segments.push({ x1: seg[0][0], y1: seg[0][1], x2: seg[seg.length - 1][0], y2: seg[seg.length - 1][1], color: chC, width: 1 });
        const [b0, b1] = [D.channel.base[0], D.channel.base[D.channel.base.length - 1]], [q0, q1] = [D.channel.parallel[0], D.channel.parallel[D.channel.parallel.length - 1]];
        if (st.cfg.chMid) segments.push({ x1: b0[0], y1: (b0[1] + q0[1]) / 2, x2: b1[0], y2: (b1[1] + q1[1]) / 2, color: chC, width: 1, dash: [3, 4] });   // ‏D756: خيارٌ لا افتراض
      }
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
    overlay.current.set({ levels, segments, paths, notes, bands, font: getComputedStyle(document.body).fontFamily || "sans-serif", bg: tok("--pc-bg", "#000000"), textTop: 50,
      leaders: false });   /* ‏D805 (المالك 2026-11-24): «النقاطُ المتّصلةُ بالأرقام ظهرت على الكمبيوتر أيضاً — بعد ثلاث شاشاتٍ ولمّا يصغر الشارت»: كان ‏D799
                              يطفئ المِهمازَ دون 600px وحدها، والشاشةُ الكبيرةُ في الثلاث أعرضُ منها والتصغيرُ يزاحم الأرقام — فلا مِهمازَ في أيّ عرض */
    // سماتُ تشخيص: ما رُسم على اللوحة (لا يُقرأ من الـDOM) — آخرُ سعرٍ موسوم، وعددُ المستويات المسمّاة والوسوم والرسوم اليدوية
    const root = rootRef.current;
    if (root) {
      root.dataset.last = last ? fmtPrice(last.close) : ""; root.dataset.lv = String(levels.filter(l => l.text || l.label).length);
      root.dataset.tags = String(levels.filter(l => l.tag).length); root.dataset.draws = String(st.draws.length);
      root.dataset.segs = String(segments.length);
      root.dataset.fibX0 = String(levels.find(l => l.x0 != null)?.x0 ?? ""); root.dataset.leaders = overlay.current.leaders ? "1" : "0";   // ‏D799
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
    set("mH", f(c.macd.hist[i])); set("mM", f(c.macd.line[i])); set("mS", f(c.macd.signal[i]));
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
      reg.current.forEach((e, k) => { if (OSC.includes(k as IndKey) && e.series[0]) idx.set(e.series[0].getPane().paneIndex(), k); });
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
        root.dataset.paneH = chart.panes().map((_, i) => Math.round(chart.paneSize(i).height)).join(",");   // ‏D810: ارتفاعُ كلّ لوحة
        root.dataset.lines = [...reg.current].map(([k, e]) => `${k}:${e.series.map(s => (s.options().visible ? 1 : 0)).join("")}`).join(" ");   // ‏D813: الظاهرُ من خطوط كلّ مؤشّر
      }
    } catch { /* لم يُرسم بعد */ }
  };

  /* ‏D810: ضبطُ نصيب اللوحات — بانتقالٍ قصيرٍ من ارتفاعاتها الحاليّة إلى المطلوبة (‏ease-out)، وفوراً لمن يفضّل تقليلَ الحركة */
  const soloAnim = useRef(0);
  const setFactors = (chart: IChartApi, want: number[], morph: boolean) => {
    cancelAnimationFrame(soloAnim.current);
    const panes = chart.panes();
    const calm = typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!morph || calm) { panes.forEach((p, i) => p.setStretchFactor(want[i] ?? 1)); return; }
    const tot = want.reduce((a, b) => a + b, 0);
    const now = panes.map((_, i) => { try { return chart.paneSize(i).height; } catch { return 0; } });
    const nTot = now.reduce((a, b) => a + b, 0) || 1;
    const from = now.map(h => (h / nTot) * tot);
    const t0 = performance.now(), dur = 240;
    const step = (ts: number) => {
      const k = Math.min(1, (ts - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      chart.panes().forEach((p, i) => p.setStretchFactor(Math.max(0.0001, from[i] + ((want[i] ?? 1) - from[i]) * e)));
      readLayout();
      soloAnim.current = requestAnimationFrame(k < 1 ? step : () => readLayout());
    };
    soloAnim.current = requestAnimationFrame(step);
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
    /* ‏D781: الضغطُ على خطّ المؤشّر نفسِه في الرسم يفتح إعداداته — السلسلةُ تحت المؤشّر تُعرف بسجلّ المؤشّرات */
    /* ‏D810: والنقرةُ الأولى من نقرتين لا تفتح الإعدادات — تنتظر لحظةً، فإن تلتها الثانيةُ فهي تكبيرٌ لا إعداد */
    let clickT = 0, lastDbl = 0;
    const onClick = (p: MouseEventParams) => {
      const hit = (p as any).hoveredInfo?.series ?? p.hoveredSeries;
      if (!hit) return;
      for (const [k, e] of reg.current) if (e.series.includes(hit as any)) {
        window.clearTimeout(clickT);
        clickT = window.setTimeout(() => { if (Date.now() - lastDbl > 400) openCfgRef.current(k); }, 300);
        return;
      }
    };
    chart.subscribeClick(onClick);
    /* ‏D810: النقرتان على لوحةٍ تكبّرانها وحدها (والرسمُ نفسُه لوحة) — ومرّةً أخرى تعيدان الكلّ؛ ولا تكبيرَ وأداةُ رسمٍ مختارة */
    const onDbl = (p: MouseEventParams) => {
      lastDbl = Date.now(); window.clearTimeout(clickT);
      const pi = (p as any).paneIndex as number | undefined;
      if (S.current.tool || pi == null || chart.panes().length < 2) return;
      let key: string | null = pi === 0 ? "main" : null;
      reg.current.forEach((e, k) => { if (pi > 0 && OSC.includes(k as IndKey) && e.series[0]?.getPane().paneIndex() === pi) key = k; });
      if (key) setSolo(s => (s === key ? null : key));
    };
    chart.subscribeDblClick(onDbl);
    return () => {
      window.clearTimeout(clickT); cancelAnimationFrame(soloAnim.current);
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
    const pcText = tok("--pc-text", "#b2b5be"), pcCross = tok("--pc-cross", "#9598a1"), pcLab = tok("--pc-label", "#363a45");
    chart.applyOptions({
      layout: { background: { color: tok("--pc-bg", "#000000") }, textColor: pcText, fontFamily: font, fontSize: 11,
                panes: { separatorColor: tok("--pc-sep", "#2a2e39"), separatorHoverColor: tokA("--brand-ink", "#5b52d3", 0.35) } },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      timeScale: { timeVisible: tfIntraday(tf) },
      crosshair: { vertLine: { color: pcCross, width: 1, style: LineStyle.Dashed, labelBackgroundColor: pcLab },
                   horzLine: { color: pcCross, width: 1, style: LineStyle.Dashed, labelBackgroundColor: pcLab } },
    });

    /* ١ السلسلةُ الرئيسة — تُبنى حين يتغيّر نوعُ الرسم أو المظهر وحدهما */
    const cu = cc.up || tok("--pc-up", "#ffffff"), cd = cc.down || tok("--pc-down", "#f23645");   // ‏D756 · D772: «خيارُ تغيير لون الشموع»
    const edge = tok("--pc-black-edge", "#b2b5be"), eu = dark(cu) ? edge : cu, ed = dark(cd) ? edge : cd;
    const mainSig = `${ctype}|${theme}|${cu}|${cd}`;
    if (sigRef.current.main !== mainSig || !mainRef.current) {
      if (mainRef.current) { try { mainRef.current.detachPrimitive(overlay.current); } catch { /* لم تُلحق */ } chart.removeSeries(mainRef.current); }
      const common = { priceLineVisible: false, lastValueVisible: false };
      const m = ctype === "line" ? chart.addSeries(LineSeries, { ...common, color: brand, lineWidth: 2, crosshairMarkerRadius: 4 }, 0)
        : ctype === "area" ? chart.addSeries(AreaSeries, { ...common, lineColor: brand, lineWidth: 2, topColor: tokA("--brand-ink", "#5b52d3", 0.28),
                                                           bottomColor: tokA("--brand-ink", "#5b52d3", 0.02) }, 0)
        : ctype === "bars" ? chart.addSeries(BarSeries, { ...common, upColor: eu, downColor: ed, thinBars: false }, 0)
        : chart.addSeries(CandlestickSeries, { ...common, upColor: ctype === "hollow" ? "rgba(0,0,0,0)" : cu, downColor: cd,
                                               borderVisible: true, borderUpColor: eu, borderDownColor: ed, wickUpColor: eu, wickDownColor: ed }, 0);
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
      /* ‏Stoch RSI بسكربت تريدنق فيو: ‏K أزرق و‏D برتقاليّ، وحدودُ 80 و50 و20، وخلفيةٌ بين 80 و20 (ألوانُه من رموز التطبيق) —
         ‏D784: ونمطُ كلٍّ بيد المالك (إظهارٌ ولونٌ وسُمكٌ ونوعُ خطّ، والحدودُ والخلفيةُ وشفافيتُها) */
      stochrsi: p => {
        const st = (x: string) => (x === "dashed" ? LineStyle.Dashed : x === "dotted" ? LineStyle.Dotted : LineStyle.Solid);
        const w = (x: number) => Math.min(4, Math.max(1, Math.round(x) || 1)) as 1 | 2 | 3 | 4;
        const k = ln(p, srCfg.kColor || tok("--info-ink", "#2563eb"), w(srCfg.kWidth), { ...fixed(0, 100), lineStyle: st(srCfg.kStyle), visible: srCfg.kOn !== false });
        const d = ln(p, srCfg.dColor || tok("--gauge-warn", "#d97706"), w(srCfg.dWidth), { ...fixed(0, 100), lineStyle: st(srCfg.dStyle), visible: srCfg.dOn !== false });
        // الحدودُ والخلفيةُ على خطٍّ ظاهر — فإخفاءُ ‏K لا يُخفيها معه
        const host = srCfg.kOn !== false || srCfg.dOn === false ? k : d;
        const bc = (a: number) => (srCfg.bandColor ? srCfg.bandColor : tokA("--ink-muted", "#787b86", a));
        const band = (v: number, a: number, on: boolean) => { if (on) host.createPriceLine({ price: v, color: bc(a), lineWidth: 1, lineStyle: st(srCfg.bandStyle || "dashed"), axisLabelVisible: false, title: "" }); };
        band(srCfg.upper, 1, srCfg.upOn !== false); band(srCfg.middle, 0.5, srCfg.midOn !== false); band(srCfg.lower, 1, srCfg.loOn !== false);
        if (srCfg.bgOn !== false) {
          const a = Math.min(100, Math.max(0, Number(srCfg.bgOpacity ?? 10))) / 100;
          host.attachPrimitive(new BandFill(srCfg.upper, srCfg.lower, srCfg.bgColor ? hexA(srCfg.bgColor, a) : tokA("--info-ink", "#2196f3", a)));
        }
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
      /* ‏D756 ‏MACD كتريدنق فيو: الخطُّ والإشارةُ والمدرّجُ بلونيه (الأقوى حين يتّسع) وخطُّ الصفر */
      macd: p => {
        const h = chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false, priceFormat: { type: "price", precision: 2, minMove: 0.01 } }, p);
        guide(h, [0]);
        return [h, ln(p, tok("--info-ink", "#2962ff"), 1), ln(p, tok("--gauge-warn", "#ff6d00"), 1)];
      },
      d7m: () => {
        const out: ISeriesApi<any>[] = [];
        const C = (k: string) => cfg.colors?.[k] || tokv(PC[k] || (D7M_COLORS.find(x => x[0] === k) || ["", "", "--ink"])[2]);
        if (cfg.vwap) out.push(ln(0, C("vwap"), 1));
        if (cfg.vwapBand) out.push(ln(0, C("band"), 1), ln(0, C("band"), 1));
        ([["ema20", "--pc-ema20"], ["ema50", "--pc-ema50"], ["ema100", "--pc-ema100"], ["ema200", "--pc-ema200"], ["ema400", "--pc-ema400"]] as const)
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
      macd: s => {
        const M = c.macd, rows: any[] = [];
        for (let i = 0; i < n; i++) {
          const v = M.hist[i];
          if (v == null) continue;
          const pv = M.hist[i - 1] ?? v;
          rows.push({ time: D[i] as any, value: v, color: v >= 0 ? tokA("--pos-ink", "#26a69a", v >= pv ? 0.85 : 0.4) : tokA("--neg-ink", "#ff5252", v <= pv ? 0.85 : 0.4) });
        }
        s[0].setData(rows); s[1].setData(pts(M.line)); s[2].setData(pts(M.signal));
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
        // ‏D813: ظهورُ كلّ خطٍّ كما بُني (‏K و‏D في إعدادات ستوكاستيك) — يُحفظ فلا تمحوه العينُ ولا التكبير
        R.set(k, { sig, series: fresh, vis: fresh.map(s => s.options().visible !== false) });
      }
      feed[k](R.get(k)!.series);
    }
    /* ‏D756 (المالك: «علامةُ العين لإخفاء المؤشّرات أو إظهارها»): المخفيُّ يبقى بإعداداته ولوحته، ولا يُرسم —
       و‏D813: كان هذا السطرُ يُظهر كلَّ خطوط المؤشّر فيمحو إخفاءَ ‏K أو ‏D من إعدادات ستوكاستيك (يُحفظ الإعدادُ ويبقى الخطُّ مرسوماً) */
    /* ‏D810: والمؤشّرُ المكبَّرُ وحده يُرسم — اللوحاتُ المطويّةُ (سطرٌ من بكسلين) كانت تُظهر شريحةً من الشموع والنطاقات فوقه */
    const soloIdx = soloK == null ? -1 : soloK === "main" ? 0 : (R.get(soloK)?.series[0]?.getPane().paneIndex() ?? -1);
    const shown = (x: ISeriesApi<any>) => soloIdx < 0 || x.getPane().paneIndex() === soloIdx;
    R.forEach((e, k) => e.series.forEach((x, i) => x.applyOptions({ visible: (e.vis?.[i] ?? true) && !(hideAll || hid[k]) && shown(x) })));
    main.applyOptions({ visible: shown(main) });
    main.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: eff.vol ? 0.2 : 0.06 } });
    /* المشهدُ الأوّل لإطارٍ أو رمزٍ جديد: آخرُ الشموع بعرضٍ مقروء (لا الكلُّ محشوراً) — بعد أن تستقرّ السلاسلُ كلُّها على الزمن الجديد */
    if (pendRange.current != null && n) { const pr = pendRange.current; pendRange.current = null; rangeTo(pr); }
    else if (resetView) {
      const vis = Math.min(n, wide ? 150 : 64);
      chart.timeScale().setVisibleLogicalRange({ from: n - vis - 0.5, to: n + 5.5 });
      chart.priceScale("right").applyOptions({ autoScale: true });
    }

    /* ٤ علاماتُ D7M (كسرُ الترند وارتدادُه) */
    const sigs = d7m?.trend && cfg.trendShapes && !(hideAll || hid.d7m) ? d7m.trend.signals : [];
    markRef.current?.setMarkers(sigs.filter(sg => bars[sg.index]).sort((a, b) => a.index - b.index).map(sg => {
      const dn = sg.kind === "breakDown" || sg.kind === "reactDown";
      return { time: D[sg.index] as any, position: dn ? "aboveBar" : "belowBar", shape: dn ? "arrowDown" : "arrowUp", color: muted };
    }));

    /* ٥ اللوحات: الرئيسةُ بارتفاعها والسفلى بارتفاعٍ واحد — تُضبط حين يتغيّر عددُها أو ارتفاعُ الرسم وحدهما، فما سحبه المالكُ
       من فواصلها يبقى ولا يرتدّ مع كلّ تحديثٍ للسعر */
    /* ‏D810: والمكبَّرُ وحده يأخذ الارتفاعَ كلَّه والباقي يُطوى (سطرٌ لا يُرى) — بانتقالٍ لا قفزة، والعودةُ كذلك */
    const panes = chart.panes(), pSig = `${panes.length}|${mainPx}|${oscPx}|${soloK ?? ""}`;
    if (sigRef.current.panes !== pSig) {
      const prev = sigRef.current.panes;
      const want = panes.map((_, i) => (soloIdx < 0 ? (i === 0 ? mainPx : oscPx) : i === soloIdx ? stageH : 0.0001));
      const morph = prev.split("|")[0] === String(panes.length) && prev.split("|")[3] !== (soloK ?? "");
      setFactors(chart, want, morph);
      sigRef.current.panes = pSig;
    }
    paint();
    fill(n - 1);
    requestAnimationFrame(readLayout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [raw, bars, disp, tzName, eff, scaleMode, calc, d7m, ind, ctype, cvdCfg, cfg, theme, tf, symbol, mainPx, oscPx, wide, hid, hideAll, cc, soloK]);

  /* ‏D810: أداةُ رسمٍ تُختار ولوحةٌ سفلى مكبَّرة ⇒ يعود الكلّ، فالرسمُ اليدويُّ على الرسم نفسِه */
  useEffect(() => { if (tool && soloK && soloK !== "main") setSolo(null); }, [tool, soloK]);

  /* لوحةٌ سفلى ظهرت للتوّ: وسيلةُ إيضاحها تُركَّب بعد أن يُعرف موضعُها — فتُملأ قيمُها حينها، لا عند أوّل حركةٍ للمؤشّر (كانت «———») */
  useEffect(() => { fill(S.current.bars.length - 1); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [paneTops, legFold]);   // ‏D781: وبعد فكّ الطيّ تُملأ القيمُ فوراً

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
  /* ‏D761: الشمعةُ الجاريةُ تتحرّك مع السعر الحيّ في الجلسة الرسمية — في مكانها (‏update) بلا إعادة حسابٍ للمؤشّرات، وما دام زمنُ السعر
     داخلَ مدّة الشمعة الأخيرة؛ والشمعةُ التالية يكتبها جلبُ الشموع نفسُه */
  useEffect(() => {
    const main = mainRef.current, L = live, n = bars.length;
    if (!main || !L || L.price == null || L.session?.state !== "open" || n < 2 || raw === undefined) return;
    const b = bars[n - 1];
    // زمنُ الشمعة ثوانٍ، أو يومُ جلسةٍ نصّاً (‏«2026-11-17») فيُقرأ بدايةَ يومه بالتوقيت العالميّ
    const ts = (x: string | number) => (typeof x === "number" ? x : Date.parse(`${x}T00:00:00Z`) / 1000);
    const per = Math.min(...[1, 2, 3].filter(k => n - k - 1 >= 0).map(k => ts(bars[n - k].time) - ts(bars[n - k - 1].time)).filter(x => x > 0), 86400 * 31);
    const t = L.time ? Date.parse(L.time) / 1000 : Date.now() / 1000, t0 = ts(b.time);
    if (!(t >= t0 && t < t0 + per)) return;
    const px = L.price, hi = Math.max(b.high, px), lo = Math.min(b.low, px);
    try {
      main.update(ctype === "line" || ctype === "area" ? { time: disp[n - 1] as any, value: px } : { time: disp[n - 1] as any, open: b.open, high: hi, low: lo, close: px });
    } catch { /* سلسلةٌ تُبنى */ }
  }, [live, bars, disp, ctype, raw]);
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

  /* ── ‏D782 لقطةُ «تحليل الرسم»: صورةُ الرسم كما يراه المالك، وأرقامُه — آخرُ 120 شمعة، وقيمُ المؤشّرات الظاهرة وحدها، والمستوياتُ المرسومة
     (فيبوناتشي بما يظهر منه · خطوطُ الاتجاه والقناة عند آخر شمعة · ‏VWAP · المتوسّطاتُ المفعّلة · مستوياتُ الشمعة السابقة)، والقممُ والقيعان،
     ولوحتا الاتجاه والسيولة. لا رقمَ في اللقطة إلّا ممّا على الرسم، والخادمُ لا يقبل من القراءة رقماً ليس فيها ── */
  const snapFrame = (): ReadFrame | null => {
    const b = bars, n = b.length, i = n - 1;
    if (n < 30) return null;
    const r = (v: number | null | undefined) => (v == null || !isFinite(Number(v)) ? null : +Number(v).toFixed(Math.abs(Number(v)) >= 1 ? 2 : 4));
    const ts = (t: any) => (typeof t === "number" ? new Date(t * 1000).toISOString().slice(0, 16).replace("T", " ") : String(t));
    const vis = (k: IndKey) => !!ind[k] && !hideAll && !hid[k] && ((k !== "vol" && k !== "cvd") || volOk);
    const shown = (["vol", "stochrsi", "cvd", "macd", "d7m"] as IndKey[]).filter(vis);
    const out: Record<string, any> = {};
    if (shown.includes("vol")) {
      const v = b.slice(-21, -1).map(x => x.volume || 0), avg = v.reduce((a, x) => a + x, 0) / Math.max(1, v.length);
      out.volume = { last: Math.round(b[i].volume || 0), avg20: Math.round(avg), rvol: avg ? r((b[i].volume || 0) / avg) : null };
    }
    if (shown.includes("stochrsi")) out["Stoch RSI"] = { k: r(calc.stochrsi.k[i]), d: r(calc.stochrsi.d[i]), k_prev: r(calc.stochrsi.k[i - 1]),
      d_prev: r(calc.stochrsi.d[i - 1]), overbought: srCfg.upper, oversold: srCfg.lower };
    if (shown.includes("macd")) out.MACD = { macd: r(calc.macd.line[i]), signal: r(calc.macd.signal[i]), hist: r(calc.macd.hist[i]), hist_prev: r(calc.macd.hist[i - 1]) };
    if (shown.includes("cvd")) {
      const L = (cvdCfg.style === "line" ? calc.cvd.line : calc.cvd.c) as (number | null)[];
      out["CVD D7M"] = { scale: cvdCfg.scale, value: r(L[i]), value_10_bars_ago: r(L[i - 10]) };
    }
    const levels: { kind: string; label: string; price: number }[] = [];
    const add = (kind: string, label: string, v: number | null | undefined) => { const x = r(v); if (x != null && x > 0) levels.push({ kind, label, price: x }); };
    const D = shown.includes("d7m") ? d7m : null;
    if (D) {
      const SIX = new Set(FIB_SIX), compact = (cfg.fibMode || "compact") === "compact";
      for (const l of D.fib?.lines || []) if (cfg.fibLevels[String(l.level)] !== false && (!compact || SIX.has(l.level)))
        add("fib", `فيبوناتشي ${l.level}`, l.price);
      for (const t of D.trend?.lines || []) if (t.x2 !== t.x1) add("trend", t.up ? "خطُّ اتجاهٍ صاعد" : "خطُّ اتجاهٍ هابط", t.y1 + (t.y2 - t.y1) * (i - t.x1) / (t.x2 - t.x1));
      if (D.channel) {
        const at = (q: [number, number][]) => (q.length > 1 && q[1][0] !== q[0][0] ? q[0][1] + (q[1][1] - q[0][1]) * (i - q[0][0]) / (q[1][0] - q[0][0]) : null);
        const a = at(D.channel.base), c2 = at(D.channel.parallel);
        if (a != null && c2 != null) { add("channel", "أعلى القناة", Math.max(a, c2)); add("channel", "أسفل القناة", Math.min(a, c2)); }
      }
      if (D.vwap) { add("vwap", "VWAP", D.vwap.vwap[i]); if (cfg.vwapBand) { add("vwap", "VWAP العلويّ", D.vwap.upper[i]); add("vwap", "VWAP السفليّ", D.vwap.lower[i]); } }
      for (const len of [20, 50, 100, 200, 400]) if ((cfg as any)[`ema${len}`]) add("ema", `EMA ${len}`, emaD7(calc.closes, len)[i]);
      if (cfg.pdh) add("pd", "أعلى الشمعة السابقة", b[i - 1]?.high);
      if (cfg.pdl) add("pd", "أدنى الشمعة السابقة", b[i - 1]?.low);
      if (cfg.pdc) add("pd", "إغلاق الشمعة السابقة", b[i - 1]?.close);
    }
    for (const pv of zigzag(b as any, cfg.fibDev || 3, cfg.fibDepth || 7).slice(-6)) add("swing", pv.isHigh ? "قمّة" : "قاع", pv.price);
    let img: string | undefined;
    try {
      const cv = chartRef.current?.takeScreenshot();
      if (cv && cv.width > 0 && cv.height > 0) {
        const W = Math.min(960, cv.width), H = Math.round(cv.height * W / cv.width), o = document.createElement("canvas");
        o.width = W; o.height = H; o.getContext("2d")?.drawImage(cv, 0, 0, W, H);
        img = o.toDataURL("image/jpeg", 0.72);
      }
    } catch { /* بلا صورة — الأرقامُ تكفي */ }
    const fz = (f: any) => (f ? { word: f.word, level: f.level, strength: f.strength, stat: f.stat, why: (f.why || []).map((w: any) => w[1]), tag: f.tag || null } : null);
    return {
      tf, tf_ar: tfLong(tf), price: r(live?.price ?? b[i].close), chg_pct: r(live?.change_pct ?? null),
      bars: b.slice(-120).map(x => [ts(x.time), r(x.open), r(x.high), r(x.low), r(x.close), Math.round(x.volume || 0)]),
      ind: out, levels, shown: shown.map(k => (k === "vol" ? "volume" : k)), force: force ? { trend: fz(force.trend), liquidity: fz(force.liq) } : null, img,
    };
  };
  const snapRef = useRef(snapFrame);
  snapRef.current = snapFrame;
  useEffect(() => {
    if (!snaps) return;
    const m = snaps.current, f = () => snapRef.current();
    m.set(slot, f);
    return () => { if (m.get(slot) === f) m.delete(slot); };
  }, [snaps, slot]);

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
  const TypeIcon = (TYPES.find(t => t[0] === ctype) || TYPES[0])[2];
  const lv = (k: string) => (e: HTMLElement | null) => { legend.current[k] = e; };
  const chip = (k: IndKey, body: React.ReactNode) => {
    const off = hideAll || !!hid[k];
    return (
      <span className={"pc-chip" + (off ? " pc-off" : "")} data-ind={k}>
        {hasCfg(k) ? <button type="button" className="pc-chip-name" onClick={() => openCfg(k)} title="إعداداتُ المؤشّر" data-role="pc-chip-cfg" data-ind={k}>{body}</button> : body}
        <button type="button" className="pc-eye" data-role="pc-eye" data-eye={k} aria-pressed={off} onClick={() => toggleHid(k)}
          title={off ? "إظهار المؤشّر" : "إخفاء المؤشّر"} aria-label={off ? "إظهار المؤشّر" : "إخفاء المؤشّر"}>{off ? <EyeOff size={13} /> : <Eye size={13} />}</button>
      </span>
    );
  };
  const empty = raw !== undefined && !bars.length;
  const nMain = (ind.vol ? 1 : 0) + (ind.cvd && !volOk ? 1 : 0) + (ind.d7m ? 1 : 0);

  /* ‏D810: زرُّ العودة في رأس المكبَّر — للّمس ولمن لا يعرف النقرتين؛ والنقرتان مرّةً أخرى تفعلان الشيءَ نفسَه */
  const soloBack = (
    <button type="button" className="pc-fold pc-solo-back" onClick={() => setSolo(null)} data-role="pc-solo-back"
      title="إظهارُ كلِّ اللوحات" aria-label="إظهارُ كلِّ اللوحات"><Minimize2 size={14} /></button>
  );

  return (
    <div ref={rootRef} className={"pc" + (full ? " pc-full" : "") + (mini ? " pc-mini" : "")} data-role="pro-chart" data-tf={tf} data-type={ctype} data-symbol={symbol}
      data-slot={slot} data-solo={soloK ?? ""}>
      {/* ══ الشريطُ العلويّ — كتريدنق فيو: الرمزُ · الإطارات · نوعُ الرسم · المؤشّرات · الرسم · لقطة · ملءُ الشاشة ══ */}
      <div ref={topRef} className="pc-top" data-role="pc-top">
        {!mini && !embedded && live?.session && (
          <div className="pc-ident"><LiveQuote symbol={symbol} live={live} badge /></div>
        )}
        <div className="pc-group" role="group" aria-label="الإطار الزمني" data-role="pc-tfs">
          {fav.map(k => (
            <button key={k} type="button" className={"pc-tf" + (tf === k ? " on" : "")} aria-pressed={tf === k} title={tfLong(k)} onClick={() => setTf(k)}
              data-tf={k} data-fav="1">{tfShort(k)}</button>
          ))}
          {!fav.includes(tf) && <span className="pc-tf on" aria-current="true" title={tfLong(tf)} data-role="pc-tf-cur">{tfShort(tf)}</span>}
          <Menu label={<ChevronDown size={15} />} title="كلُّ الإطارات وإطارٌ مخصَّص" role="pc-tf-more" wide>
            {close => (
              <div className="pc-tfmenu">
                <span className="pc-cap pc-favcap">النجمةُ تضع الإطارَ في الشريط — بترتيب ضغطك</span>
                <div className="pc-tfgrid" data-role="pc-tfgrid">
                  {[...TF_PRESETS, ...customTfs.filter(x => !TF_PRESETS.includes(x)), ...fav.filter(x => !TF_PRESETS.includes(x) && !customTfs.includes(x))].map(k => {
                    const on = fav.includes(k);
                    return (
                      <span key={k} className="pc-tfopt" data-tfopt={k}>
                        <button type="button" className={"pc-tf" + (tf === k ? " on" : "")} onClick={() => { setTf(k); close(); }} data-tf={k}>{tfLong(k)}</button>
                        <button type="button" className={"pc-star" + (on ? " on" : "")} aria-pressed={on} onClick={() => toggleFav(k)} data-star={k}
                          title={on ? "أزِله من المفضّلة" : "أضِفه إلى المفضّلة"} aria-label={on ? `أزِل ${tfLong(k)} من المفضّلة` : `أضِف ${tfLong(k)} إلى المفضّلة`}>
                          <Star size={14} fill={on ? "currentColor" : "none"} /></button>
                      </span>
                    );
                  })}
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
        {tools}
        <span className="pc-sep" aria-hidden />
        {!mini && <>
        <Menu label={<TypeIcon size={17} />} title="نوع الرسم" role="pc-type">
          {close => <>
            {TYPES.map(([k, name, Ic]) => (
              <button key={k} type="button" className={"pc-item" + (ctype === k ? " on" : "")} onClick={() => { setCtype(k); close(); }}>
                <Ic size={15} /> <span>{name}</span>{ctype === k && <Check size={14} className="pc-check" />}
              </button>
            ))}
          </>}
        </Menu>
        {/* ‏D772 (المالك): «خلّ فيه إمكانيةَ أن أغيّر ألوانَ الشموع — أخضر وأسود، أبيض وأحمر» */}
        <Menu label={<Palette size={17} />} title="ألوان الشموع" role="pc-colors">
          {close => (
            <div className="pc-cc" data-role="pc-candle-colors">
              <span className="pc-cc-t">ألوان الشموع</span>
              <div className="pc-cc-pre">
                {CANDLE_PRESETS.map(([name, u, d]) => {
                  const on = (cc.up || hexTok("--pc-up")) === hexTok(u) && (cc.down || hexTok("--pc-down")) === hexTok(d);
                  return (
                    <button key={name} type="button" className={"pc-item pc-cc-p" + (on ? " on" : "")} aria-pressed={on} onClick={() => { setCc({ up: hexTok(u), down: hexTok(d) }); close(); }}
                      data-role="pc-cc-preset">
                      <span className="pc-cc-duo" aria-hidden><i style={{ background: `var(${u})` }} /><i style={{ background: `var(${d})` }} /></span>{name}
                    </button>
                  );
                })}
              </div>
              {(["up", "down"] as const).map(side => (
                <div key={side} className="pc-cc-row" data-role={`pc-cc-${side}`}>
                  <span>{side === "up" ? "صعود" : "هبوط"}</span>
                  <span className="pc-cc-sw">
                    {SWATCHES.map(t => {
                      const v = hexTok(t), on = (cc[side] || hexTok(side === "up" ? "--pc-up" : "--pc-down")) === v;
                      return <button key={t} type="button" className={"pc-sw" + (on ? " on" : "")} aria-pressed={on}
                        aria-label={`${side === "up" ? "لون الصعود" : "لون الهبوط"} ${v}`} onClick={() => setCc({ ...cc, [side]: v })}>
                        <i aria-hidden style={{ background: `var(${t})` }} /></button>;
                    })}
                  </span>
                </div>
              ))}
              {(cc.up || cc.down) && <button type="button" className="pc-item" onClick={() => { setCc({}); close(); }} data-role="pc-cc-reset">الافتراضيّ (أبيض · أحمر)</button>}
            </div>
          )}
        </Menu>
        </>}
        <Menu label={<><Activity size={17} /><span className="pc-btn-txt">المؤشرات</span></>} title="المؤشرات" role="pc-ind">
          {() => IND.map(([k, name, t]) => (
            <button key={k} type="button" className={"pc-item" + (ind[k] ? " on" : "")} aria-pressed={ind[k]} onClick={() => toggleInd(k)} data-ind={k}>
              <span className="pc-dot" style={{ background: `var(${t})` }} /> <span dir={k === "vol" ? undefined : "ltr"}>{name}</span>
              {ind[k] && <Check size={14} className="pc-check" />}
            </button>
          ))}
        </Menu>
        {!mini && <button type="button" className={"pc-btn" + (hideAll ? " on" : "")} aria-pressed={hideAll} data-role="pc-eye-all"
          title={hideAll ? "إظهار المؤشرات" : "إخفاء المؤشرات"} aria-label={hideAll ? "إظهار المؤشرات" : "إخفاء المؤشرات"}
          onClick={() => { const v = !hideAll; setHideAll(v); lsSet("sp_chart_hideall", v ? "1" : "0"); }}>{hideAll ? <EyeOff size={17} /> : <Eye size={17} />}</button>}
        <button type="button" className={"pc-btn" + (railOpen || tool ? " on" : "")} title="أدوات الرسم" aria-label="أدوات الرسم" aria-pressed={railOpen}
          data-role="pc-draw" onClick={() => setRailOpen(o => !o)}><Brush size={17} /></button>
        {!mini && (ind.stochrsi || ind.cvd || ind.d7m) && (
          <Menu label={<><Settings2 size={16} /><span className="pc-btn-txt">الإعدادات</span></>} title="إعدادات المؤشرات" role="pc-cfg">
            {close => IND.filter(([k]) => k !== "vol" && k !== "macd" && ind[k]).map(([k, name]) => (
              <button key={k} type="button" className="pc-item" data-cfg={k} onClick={() => { close(); if (k === "d7m") setShowCfg(true); else setCfgFor(k as "stochrsi" | "cvd"); }}>
                <Settings2 size={14} /> <span dir="ltr">{name}</span>
              </button>
            ))}
          </Menu>
        )}
        <span className="pc-grow" />
        {!mini && <button type="button" className="pc-btn" title="لقطةٌ للرسم" aria-label="لقطةٌ للرسم" onClick={shot}><Camera size={17} /></button>}
        {!embedded && <button type="button" className="pc-btn" title={full ? "خروج من ملء الشاشة" : "ملء الشاشة"} aria-label="ملء الشاشة" aria-pressed={full}
          data-role="pc-full" onClick={() => setFull(f => !f)}>{full ? <Minimize2 size={17} /> : <Maximize2 size={17} />}</button>}
      </div>
      {showCfg && <D7MPanel cfg={cfg} onChange={saveCfg} onClose={() => setShowCfg(false)} colorDefaults={colorDefaults()} />}
      {cfgFor && <IndSettings kind={cfgFor} sr={srCfg} cvd={cvdCfg} onSr={setSr} onCvd={setCvd} onClose={() => setCfgFor(null)} />}

      {force && <ForcePanels trend={force.trend} liq={force.liq} compact={mini} />}
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
          <div className={"pc-legend" + (soloK && soloK !== "main" ? " pc-leg-off" : "")} dir="ltr" data-role="pc-legend">
            <div className="pc-ohlc">
              {/* ‏D810: أوّلَ السطر لا آخرَه — قيمُ الشمعة تتغيّر عرضاً مع حركة المؤشّر فكان الزرُّ يزحف تحت المؤشّر قبل أن يُضغط */}
              {soloK === "main" && soloBack}
              <span className="pc-k">O</span><b ref={lv("o")} data-k="o">—</b><span className="pc-k">H</span><b ref={lv("h")} data-k="h">—</b>
              <span className="pc-k">L</span><b ref={lv("l")} data-k="l">—</b><span className="pc-k">C</span><b ref={lv("c")} data-k="c">—</b>
              <b ref={lv("chg")} className="pc-chg" data-k="chg" />
              <b ref={lv("basis")} className="pc-dim pc-basis" data-k="basis" />
            </div>
            {nMain > 0 && (
              <div className={"pc-chips" + (legFold ? " pc-folded" : "")}>
                <button type="button" className="pc-fold" onClick={foldLeg} aria-expanded={!legFold} data-role="pc-fold"
                  title={legFold ? "إظهارُ أسماء المؤشّرات" : "طيُّ أسماء المؤشّرات"} aria-label={legFold ? "إظهارُ أسماء المؤشّرات" : "طيُّ أسماء المؤشّرات"}>
                  {legFold ? <ChevronRight size={14} /> : <ChevronDown size={14} />}{legFold && <b className="pc-fold-n" data-role="pc-fold-n">{nMain}</b>}</button>
                {!legFold && <>
                  {ind.vol && (volOk ? chip("vol", <><span className="pc-k">Vol</span><b ref={lv("vol")}>—</b></>)
                    : chip("vol", <><span className="pc-k">Vol</span><b className="pc-dim">غير متوفّر</b></>))}
                  {ind.cvd && !volOk && chip("cvd", <><span className="pc-k" style={{ color: "var(--chart-3)" }}>CVD D7M</span><b className="pc-dim">غير متوفّر — لا حجم</b></>)}
                  {ind.d7m && chip("d7m", <span className="pc-k" style={{ color: "var(--brand-ink)" }}>D7M</span>)}
                </>}
              </div>
            )}
          </div>
          {oscOn.map(k => paneTops[k] != null && (!soloK || soloK === k) && (
            <div key={k} className={"pc-legend pc-pane-legend" + (soloK === k ? " pc-solo" : "")} dir="ltr" style={{ top: paneTops[k] + 4 }} data-role="pane-tag" data-ind={k}>
              {soloK === k && soloBack}
              {legFold ? <button type="button" className="pc-fold" onClick={foldLeg} aria-expanded={false} title="إظهارُ أسماء المؤشّرات" aria-label="إظهارُ أسماء المؤشّرات"
                data-role="pc-fold-pane"><ChevronRight size={14} /></button> : <>
              {k === "macd" && chip("macd", <><span className="pc-k" style={{ color: "var(--info-ink)" }}>MACD 12 26 close 9</span>
                <b ref={lv("mH")}>—</b><b ref={lv("mM")} style={{ color: "var(--info-ink)" }}>—</b><b ref={lv("mS")} style={{ color: "var(--gauge-warn)" }}>—</b></>)}
              {k === "stochrsi" && chip("stochrsi", <><span className="pc-k" style={{ color: "var(--info-ink)" }}>Stoch RSI {srCfg.k} {srCfg.d} {srCfg.rsiLen} {srCfg.stochLen} {srCfg.src}</span>
                <b ref={lv("srK")} style={{ color: srCfg.kColor || "var(--info-ink)" }}>—</b><b ref={lv("srD")} style={{ color: srCfg.dColor || "var(--gauge-warn)" }}>—</b></>)}
              {k === "cvd" && chip("cvd", <><span className="pc-k" style={{ color: "var(--chart-3)" }}>
                CVD D7M · {cvdCfg.scale === "levels" ? "مستويات" : cvdCfg.scale === "pct" ? "نسبة" : "احجام"} {cvdCfg.len}</span><b ref={lv("cvd")}>—</b>
                {cvdCfg.ema2 && cvdCfg.style === "candle" && <b ref={lv("cvdE")} className="pc-dim">—</b>}</>)}
              </>}
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
        {!mini && <div className="pc-foot" data-role="pc-foot">
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
        </div>}
        </div>
      </div>
    </div>
  );
}
