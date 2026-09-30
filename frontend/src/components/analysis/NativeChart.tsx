import { autoFib, autoChannel, autoTrend, vwapAnchored, ema as ema7, dashboard, macdSmart, tradeTool,
  D7M_DEFAULTS, D7MSettings } from "./d7m";
import D7MPanel from "./D7MPanel";
import { D7M_COLORS } from "./d7m";
import React, { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { marketApi } from "../../services/api";

/**
 * Native candlestick chart powered by TradingView's open-source
 * Lightweight-Charts (loaded from CDN) and fed with OUR Yahoo OHLC data — so it
 * works reliably for Saudi (Tadawul) symbols and the TASI index, unlike the
 * free TradingView embed which has no Tadawul data. Indicators (SMA 20/50/200,
 * RSI) are computed locally and togggleable.
 */
let _libPromise: Promise<any> | null = null;
function loadLib(): Promise<any> {
  if ((window as any).LightweightCharts) return Promise.resolve((window as any).LightweightCharts);
  if (_libPromise) return _libPromise;
  _libPromise = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js";
    s.async = true;
    s.onload = () => resolve((window as any).LightweightCharts);
    s.onerror = reject;
    document.head.appendChild(s);
  });
  return _libPromise;
}

function sma(data: number[], p: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    sum += data[i];
    if (i >= p) sum -= data[i - p];
    out.push(i >= p - 1 ? sum / p : null);
  }
  return out;
}
function ema(data: number[], p: number): (number | null)[] {
  const out: (number | null)[] = Array(data.length).fill(null);
  const k = 2 / (p + 1);
  let prev: number | null = null;
  for (let i = 0; i < data.length; i++) {
    if (prev == null) {
      if (i >= p - 1) {
        const seed = data.slice(i - p + 1, i + 1).reduce((a, b) => a + b, 0) / p;
        prev = seed;
        out[i] = seed;
      }
    } else {
      prev = data[i] * k + prev * (1 - k);
      out[i] = prev;
    }
  }
  return out;
}
function macd(data: number[]): { line: (number | null)[]; signal: (number | null)[]; hist: (number | null)[] } {
  const e12 = ema(data, 12), e26 = ema(data, 26);
  const line = data.map((_, i) => (e12[i] == null || e26[i] == null ? null : (e12[i] as number) - (e26[i] as number)));
  const lineValues = line.filter((v): v is number => v != null);
  const signalOnValues = ema(lineValues, 9);
  const signal: (number | null)[] = Array(data.length).fill(null);
  let j = 0;
  for (let i = 0; i < line.length; i++) {
    if (line[i] != null) { signal[i] = signalOnValues[j] ?? null; j++; }
  }
  const hist = line.map((v, i) => (v == null || signal[i] == null ? null : v - (signal[i] as number)));
  return { line, signal, hist };
}
function rsi(data: number[], p = 14): (number | null)[] {
  const out: (number | null)[] = Array(data.length).fill(null);
  if (data.length < p + 1) return out;
  let g = 0, l = 0;
  for (let i = 1; i <= p; i++) { const d = data[i] - data[i - 1]; g += Math.max(d, 0); l += Math.max(-d, 0); }
  g /= p; l /= p;
  out[p] = l === 0 ? 100 : 100 - 100 / (1 + g / l);
  for (let i = p + 1; i < data.length; i++) {
    const d = data[i] - data[i - 1];
    g = (g * (p - 1) + Math.max(d, 0)) / p;
    l = (l * (p - 1) + Math.max(-d, 0)) / p;
    out[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l);
  }
  return out;
}

/* تاريخٌ يوميّ «2026-09-22» يُمرَّر كما هو، ونقطةٌ داخل الجلسة
   «2026-09-22 10:00» (تاسي من مولّد «تداول») تصير ثوانيَ بتوقيت الرياض —
   فالمكتبةُ لا تقبل التاريخَ بساعته نصّاً. */
const tkey = (d: string): any =>
  d && d.length > 10 ? Math.floor(Date.parse(d.replace(" ", "T") + ":00+03:00") / 1000) : d;

const RANGES: [string, string][] = [["1mo", "شهر"], ["3mo", "3 أشهر"], ["6mo", "6 أشهر"], ["1y", "سنة"], ["2y", "سنتان"], ["5y", "5 سنوات"]];

const IND = [["sma20", "SMA20", "var(--chart-1)"], ["sma50", "SMA50", "var(--warn-ink)"], ["sma200", "SMA200", "var(--chart-4)"],
  ["macd", "MACD", "var(--chart-1)"], ["rsi", "RSI", "var(--chart-5)"], ["d7m", "D7M", "var(--brand-ink)"]] as const;

/** زرٌّ يُظهر المختارَ وحدَه، وعند الضغط تنسدل الخيارات ثمّ تُطوى. */
function Drop({ label, children }: { label: string; children: (close: () => void) => React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const away = (e: Event) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);
  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen(o => !o)} aria-expanded={open}
        className={"inline-flex items-center gap-1 px-2.5 py-1 min-h-[32px] max-w-[62vw] rounded-lg text-[11px] font-bold border transition-all " +
          (open ? "text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink)]")}>
        <span className="truncate">{label}</span>
        <span aria-hidden className={"text-[var(--ink-muted)] transition-transform duration-200 " + (open ? "rotate-180" : "")}>▾</span>
      </button>
      {open && (
        <div className="sp-menu absolute z-30 top-full mt-1 start-0 min-w-[140px] rounded-xl overflow-hidden shadow-2xl py-1">
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}

/** شريطُ السكربت █░: عشرُ خاناتٍ، الممتلئةُ بلون القرار والباقيةُ منقَّطة. */
function Meter({ v, solid = false }: { v: number; solid?: boolean }) {
  const f = Math.min(Math.round(Math.abs(v)), 10);
  return (
    <div className={"d7m-meter" + (solid ? " d7m-meter-solid" : "")} role="img" aria-label={`${f} من 10`}>
      {Array.from({ length: 10 }, (_, k) => <span key={k} className={k < f ? "on" : ""} />)}
    </div>
  );
}

export default function NativeChart({ symbol, theme = "dark", identity }: { symbol: string; theme?: "dark" | "light"; identity?: React.ReactNode }) {
  const el = useRef<HTMLDivElement>(null);
  // المدّةُ الافتراضيّةُ خمسُ سنوات للسوقين (بأمر المالك)
  const [range, setRange] = useState("5y");
  const [ind, setInd] = useState({ sma20: true, sma50: true, sma200: false, macd: true, rsi: false, d7m: false });
  const [err, setErr] = useState(false);
  // ══ إعداداتُ مؤشّر D7M — تُحفظ في المتصفّح (بأمر المالك: زرُّ إعدادات) ══
  const [cfg, setCfg] = useState<D7MSettings>(() => {
    // v2: حدّا اللوحة صارا 6 / −6 كما في السكربت، فلا تُورَث قيمُ النسخة السابقة
    try { const sv = JSON.parse(localStorage.getItem("sp_d7m_cfg_v2") || "{}");
      if (sv && sv.dashPos === "tr") sv.dashPos = "tl";   // النقلُ إلى أعلى اليسار بأمر المالك
      return { ...D7M_DEFAULTS, ...sv, colors: { ...D7M_DEFAULTS.colors, ...(sv.colors || {}) } }; }
    catch { return D7M_DEFAULTS; }
  });
  const saveCfg = (c: D7MSettings) => { setCfg(c); try { localStorage.setItem("sp_d7m_cfg_v2", JSON.stringify(c)); } catch {} };
  const [showCfg, setShowCfg] = useState(false);
  const [zones, setZones] = useState<{ y: number; x: number; title: string }[]>([]);
  const [psw, setPsw] = useState(64);   // عرضُ محور الأسعار — تجلس اللوحةُ بجانبه كما في تريدنق فيو
  // ══ الرسمُ اليدويّ: خطُّ ترند وقناة — محفوظان لكلّ رمز ══
  const dKey = `sp_draw_${symbol}`;
  const [draws, setDraws] = useState<any[]>(() => { try { return JSON.parse(localStorage.getItem(dKey) || "[]"); } catch { return []; } });
  const [tool, setTool] = useState<null | "line" | "free">(null);
  const pending = useRef<any[]>([]);
  // ══ الرسمُ الحرّ (D529) — يُحفظ نقاطاً بزمن الشمعة وسعرها فيتبع الرسمَ حين يُسحب ويُكبَّر ══
  const chartRef = useRef<any>(null);
  const candleRef = useRef<any>(null);
  const [tick, setTick] = useState(0);
  const stroke = useRef<{ t: any; p: number }[] | null>(null);
  const [live, setLive] = useState<{ x: number; y: number }[]>([]);
  const [hy, setHy] = useState<number | null>(null);      // موضعُ الخطّ الأفقيّ قبل اعتماده (D550)
  /* ══ الرسمُ يبقى للشركة حتى يمسحه المالك (بأمر المالك · D496) ══ يُحفظ على
     الخادم لكلّ رمزٍ على حدة، والنسخةُ المحلّيةُ للعرض الفوريّ وحين يتعذّر الخادم. */
  useEffect(() => {
    let alive = true;
    try { setDraws(JSON.parse(localStorage.getItem(dKey) || "[]")); } catch { setDraws([]); }
    marketApi.drawings(symbol).then(r => {
      const items = Array.isArray(r.data?.data) ? r.data.data : null;
      if (alive && items && items.length) {
        setDraws(items);
        try { localStorage.setItem(dKey, JSON.stringify(items)); } catch {}
      }
    }).catch(() => {});
    return () => { alive = false; };
  }, [dKey]);
  const saveDraws = (d: any[]) => {
    setDraws(d);
    try { localStorage.setItem(dKey, JSON.stringify(d)); } catch {}
    marketApi.saveDrawings(symbol, d).catch(() => {});
  };

  const { data: bars = [], isLoading } = useQuery({
    queryKey: ["ohlc", symbol, range],
    queryFn: () => marketApi.history(symbol, range).then(r => (Array.isArray(r.data?.data) ? r.data.data : [])),
    enabled: !!symbol,
    retry: 0,
  });

  // VIX للأسواق الأمريكية وحدَها — كما في السكربت
  const isUS = !!symbol && !/^\d{4}(\.SR)?$/.test(symbol) && !/TASI/i.test(symbol);
  const { data: vixBars = [] } = useQuery({
    queryKey: ["ohlc", "^VIX", "1mo"],
    queryFn: () => marketApi.history("^VIX", "1mo").then(r => (Array.isArray(r.data?.data) ? r.data.data : [])),
    enabled: false, staleTime: 15 * 60 * 1000,   // VIX محذوفٌ بأمر المالك
  });
  const vix = null;
  // إطاراتُ اللوحة كما يطلبها السكربت: يوميٌّ لـEMA200 وشموعُ 15د لـ4H · 1H · 15M
  const { data: frames } = useQuery({
    queryKey: ["frames", symbol],
    queryFn: () => marketApi.frames(symbol).then(r => r.data?.data || null),
    enabled: ind.d7m && (cfg.dashboard || cfg.alertsDash) && !!symbol,
    staleTime: 5 * 60 * 1000, refetchInterval: 5 * 60 * 1000, retry: 0,
  });
  const today = new Date().toISOString().slice(0, 10);
  const newsDay = false;   // (بأمر المالك) حُذفت الأخبار وVIX من المؤشّر
  const dash = ind.d7m && cfg.dashboard ? dashboard(bars as any, { bull: cfg.bull, bear: cfg.bear, vix,
    vixWarn: 25, vixBlock: 35, newsDates: newsDay ? [today] : [], today,
    daily: frames?.daily, m15: frames?.m15 }) : null;
  const msmart = ind.d7m && cfg.macdDash && bars.length > 40 ? macdSmart(bars as any) : null;
  const tt = ind.d7m && cfg.tradeTool ? tradeTool(bars as any, vix, newsDay) : null;
  const alertsSt = (() => {
    if (!ind.d7m || !cfg.alertsDash || bars.length < 40) return null;
    const vw = vwapAnchored(bars as any, cfg.vwapAnchor).vwap, i = bars.length - 1;
    const m = macdSmart(bars as any); const h = m?.hist[i] ?? 0;
    const c = bars[i].close;
    const f = autoFib(bars as any, cfg.fibDev, cfg.fibDepth, cfg.fibReverse);
    const f0 = f?.lines.find(x => x.level === 0)?.price, f1 = f?.lines.find(x => x.level === 1)?.price;
    const longUp = dash ? dash.rows[0].up : null;
    return {
      mom: c > vw[i] && h > 0 ? "شراء" : c < vw[i] && h < 0 ? "بيع" : "انتظار",
      rev: dash ? (dash.score >= cfg.bull ? "شراء" : dash.score <= cfg.bear ? "بيع" : "انتظار") : "انتظار",
      bounce: f1 != null && longUp === false && bars[i].low <= f1 ? "شراء" : f0 != null && longUp === true && bars[i].high >= f0 ? "بيع" : "انتظار",
    };
  })();

  useEffect(() => {
    if (!el.current || !bars.length) return;
    let chart: any, ro: ResizeObserver;
    let cancelled = false;
    loadLib().then((LW) => {
      if (cancelled || !el.current) return;
      el.current.innerHTML = "";
      /* الرسم على لوحة canvas لا في DOM، ومكتبة الرسم لا تفهم `var()` —
         تُمرَّر لها قيمةٌ محسوبة. الرمز يبقى مصدر الحقيقة، ويُقرأ منه هنا
         مرّةً عند الرسم. */
      const tok = (name: string, fallback: string) =>
        getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
      /* ونفسُه بشفافية. الحجم وأعمدة MACD كانت على ‎rgba(16,185,129) و
         ‎rgba(244,63,94) — درجاتٌ مكتوبةٌ باليد هجرها التطبيق، فتظهر في
         الرسم ألوانٌ لا يعرفها باقي الشاشة ولا تتبدّل متى بدّل المالك
         درجته. و`color-mix` لا تصلح هنا: اللوحة لا تفهمها كما لا تفهم
         `var()`. فيُقرأ الرمز ثمّ تُركّب الشفافية على قيمته. */
      const tokA = (name: string, fallback: string, a: number) => {
        const c = tok(name, fallback);
        const m = /^#([0-9a-f]{6})$/i.exec(c);
        if (m) {
          const n = parseInt(m[1], 16);
          return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
        }
        const p = c.match(/[\d.]+/g);
        return p && p.length >= 3 ? `rgba(${p[0]}, ${p[1]}, ${p[2]}, ${a})` : c;
      };
      const light = theme === "light";
      chart = LW.createChart(el.current, {
        autoSize: true,
        /* ══ `var()` لا تصل لوحةَ الرسم ══
           هذه القيم تُمرَّر إلى مكتبةٍ ترسم على `canvas`، وهي لا تفهم رموز
           التصميم — تتوقّع لوناً محسوباً. فكان `textColor: "var(--hairline)"`
           يصل حرفياً فتسقط المكتبة إلى لونها الافتراضي: **أرقام المحاور
           بلونٍ لا علاقة له بالمظهر**. وهو عطبُ `fill="var(--x)"` نفسه
           الذي أخفى أرقام الرسوم من قبل، عاد في موضعٍ آخر.
           فتُقرأ الرموز هنا قيماً محسوبة عبر `tok` قبل التمرير. */
        layout: { background: { color: "transparent" }, textColor: tok("--ink-muted", "#4a4a4a"), fontFamily: "inherit" },
        grid: { vertLines: { color: tok("--hairline", "#dcdcdc") }, horzLines: { color: tok("--hairline", "#dcdcdc") } },
        rightPriceScale: { borderColor: tok("--hairline", "#dcdcdc"), scaleMargins: { top: 0.06, bottom: (ind.rsi || ind.macd) ? 0.28 : 0.14 } },
        timeScale: { borderColor: tok("--hairline", "#dcdcdc"), timeVisible: bars.some((b: any) => String(b.date || "").length > 10) },
        crosshair: { mode: 0 },
        /* ══ الإصبعُ العموديُّ للصفحة لا للرسم ══ (بأمر المالك)
           «عند تمرير الشاشة تتوقّف الصفحة ويظهر التعليق»: كان الرسمُ يأسر
           كلَّ لمسةٍ وعجلة. فالسحبُ الأفقيُّ يحرّك الرسم، والعموديُّ
           والعجلةُ يمرّران الصفحة، والقرصُ يكبّر. */
        handleScroll: { mouseWheel: false, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
        handleScale: { mouseWheel: false, pinch: true, axisPressedMouseMove: true, axisDoubleClickReset: true },
      });
      // الاحتياطيّ يُحدَّث مع الرمز لا يُترك خلفه: هو الذي يظهر لو غاب
      // الرمز، فبقاؤه على درجةٍ قديمة يعني شمعةً بلونٍ هجره التطبيق.
      const up = tok("--pos-ink", "#16a34a");
      const down = tok("--neg-ink", "#dc2626");
      const candle = chart.addCandlestickSeries({
        upColor: up, downColor: down, borderVisible: false,
        wickUpColor: up, wickDownColor: down,
      });
      candle.setData(bars.map((b: any) => ({ time: tkey(b.date), open: b.open, high: b.high, low: b.low, close: b.close })));

      // volume
      const vol = chart.addHistogramSeries({ priceScaleId: "", priceFormat: { type: "volume" } });
      vol.priceScale().applyOptions({ scaleMargins: { top: 0.86, bottom: 0 } });
      vol.setData(bars.map((b: any) => ({ time: tkey(b.date), value: b.volume, color: b.close >= b.open ? tokA("--pos-ink", "#16a34a", .4) : tokA("--neg-ink", "#dc2626", .4) })));

      const closes = bars.map((b: any) => b.close);
      const addSMA = (period: number, color: string) => {
        const s = chart.addLineSeries({ color, lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false });
        s.setData(sma(closes, period).map((v, i) => v == null ? null : ({ time: tkey(bars[i].date), value: v })).filter(Boolean));
      };
      if (ind.sma20) addSMA(20, tok("--chart-1", "#5b52d3"));
      if (ind.sma50) addSMA(50, tok("--warn-ink", "#92400e"));
      if (ind.sma200) addSMA(200, tok("--chart-4", "#4a8fbd"));

      const bothPanes = ind.rsi && ind.macd;
      if (ind.rsi) {
        const rs = chart.addLineSeries({ color: tok("--chart-5", "#c08a45"), lineWidth: 1.5, priceScaleId: "rsi", priceLineVisible: false, lastValueVisible: false });
        chart.priceScale("rsi").applyOptions({
          scaleMargins: bothPanes ? { top: 0.74, bottom: 0.14 } : { top: 0.74, bottom: 0.02 },
          borderColor: tok("--hairline", "#dcdcdc"),
        });
        rs.setData(rsi(closes).map((v, i) => v == null ? null : ({ time: tkey(bars[i].date), value: v })).filter(Boolean));
      }
      if (ind.macd) {
        const { line, signal, hist } = macd(closes);
        const macdMargins = bothPanes ? { top: 0.88, bottom: 0 } : { top: 0.74, bottom: 0.02 };
        const macdHist = chart.addHistogramSeries({ priceScaleId: "macd", priceLineVisible: false, lastValueVisible: false });
        chart.priceScale("macd").applyOptions({ scaleMargins: macdMargins, borderColor: tok("--hairline", "#dcdcdc") });
        macdHist.setData(hist.map((v, i) => v == null ? null : ({ time: tkey(bars[i].date), value: v, color: v >= 0 ? tokA("--pos-ink", "#16a34a", .5) : tokA("--neg-ink", "#dc2626", .5) })).filter(Boolean));
        const macdLine = chart.addLineSeries({ color: tok("--chart-1", "#5b52d3"), lineWidth: 1.3, priceScaleId: "macd", priceLineVisible: false, lastValueVisible: false });
        macdLine.setData(line.map((v, i) => v == null ? null : ({ time: tkey(bars[i].date), value: v })).filter(Boolean));
        const signalLine = chart.addLineSeries({ color: tok("--warn-ink", "#92400e"), lineWidth: 1.3, priceScaleId: "macd", priceLineVisible: false, lastValueVisible: false });
        signalLine.setData(signal.map((v, i) => v == null ? null : ({ time: tkey(bars[i].date), value: v })).filter(Boolean));
      }
      /* ══ مؤشّرُ D7M — فيبوناتشي تلقائيّ وقناةٌ سعرية (سكربت المالك) ══
         «الأبيض» في السكربت مصمَّمٌ لخلفيةٍ داكنة؛ فيُرسم بحبر النصّ ليُقرأ في
         المظهرين، والأصفرُ يبقى كما هو. */
      if (ind.d7m) {
        // لونُ المالك من الإعدادات إن اختاره، وإلا لونُ المظهر
        const C = (k: string) => cfg.colors?.[k] || tok((D7M_COLORS.find(x => x[0] === k) || ["", "", "--ink"])[2], "#000");
        const ink = C("fib");
        const yellow = C("fibGold");
        const T = (i: number) => tkey(bars[Math.max(0, Math.min(i, bars.length - 1))].date);
        const addLine = (pts: [number, number][], color: string, width = 1, style = 0) => {
          const l = chart.addLineSeries({ color, lineWidth: width, lineStyle: style, priceLineVisible: false,
            lastValueVisible: false, crosshairMarkerVisible: false });
          const seen = new Set();
          l.setData(pts.filter(([i]) => { const k = String(T(i)); if (seen.has(k)) return false; seen.add(k); return true; })
            .map(([i, v]) => ({ time: T(i), value: v })));
          return l;
        };
        // ١) الفيبوناتشي التلقائي
        const fib = cfg.fib ? autoFib(bars, cfg.fibDev, cfg.fibDepth, cfg.fibReverse) : null;
        if (fib) {
          for (const l of fib.lines) {
            if (cfg.fibLevels[String(l.level)] === false) continue;
            candle.createPriceLine({ price: l.price, color: l.color === "yellow" ? yellow : ink, lineWidth: 1,
              lineStyle: 0, axisLabelVisible: true, title: l.title });
          }
        }
        const zoneList = fib && cfg.fibZones ? fib.zones : [];
        const placeZones = () => {
          // لا تتراكب النصوص: يُسقَط ما يقع على بُعد أقلّ من 14px من نصٍّ ظاهر
          const shown: { y: number; x: number; title: string }[] = [];
          // بين خطَّي المنطقة رأسياً، وقربَ آخر سعرٍ أفقياً (بأمر المالك)
          const mid = Math.max(0, bars.length - 12);
          const x = chart.timeScale().logicalToCoordinate(mid) ?? 200;
          try { setPsw(chart.priceScale("right").width() || 64); } catch {}
          zoneList.map(z => ({ y: candle.priceToCoordinate(z.price) ?? -999, x, title: z.title }))
            .sort((a, b) => a.y - b.y)
            .forEach(z => { if (z.y > 0 && shown.every(o => Math.abs(o.y - z.y) >= 14)) shown.push(z); });
          setZones(shown);
        };
        chart.timeScale().subscribeVisibleLogicalRangeChange(() => requestAnimationFrame(placeZones));
        setTimeout(placeZones, 60);
        // ٢) الترند التلقائي
        if (cfg.trend) {
          const tr = autoTrend(bars, cfg.trendPP);
          for (const l of tr.lines) if (l.x2 > l.x1) addLine([[l.x1, l.y1], [l.x2, l.y2]], l.up ? C("trendUp") : C("trendDown"), l.major ? 2 : 1, l.major ? 0 : 2);
          if (cfg.trendShapes && tr.signals.length) {
            candle.setMarkers(tr.signals.map(sg => ({ time: T(sg.index),
              position: sg.kind === "breakDown" || sg.kind === "reactDown" ? "aboveBar" : "belowBar",
              shape: sg.kind === "breakDown" || sg.kind === "reactDown" ? "arrowDown" : "arrowUp", color: ink }))
              .sort((a: any, b: any) => (a.time > b.time ? 1 : -1)));
          }
        }
        // ٣) القناة السعرية التلقائية
        const ch = cfg.channel ? autoChannel(bars, cfg.chDev, cfg.chDepth) : null;
        if (ch) for (const seg of [ch.base, ch.parallel]) addLine(seg as any, C("channel"), 1, 2);
        // ٤) VWAP ونطاقه
        if (cfg.vwap || cfg.vwapBand) {
          const vw = vwapAnchored(bars, cfg.vwapAnchor, cfg.vwapMult);
          if (cfg.vwap) addLine(vw.vwap.map((v, i) => [i, v]) as any, C("vwap"), 1);
          if (cfg.vwapBand) { addLine(vw.upper.map((v, i) => [i, v]) as any, C("band"), 1);
            addLine(vw.lower.map((v, i) => [i, v]) as any, C("band"), 1); }
        }
        // ٥) المتوسّطات الأسية
        const cl = bars.map((b: any) => b.close);
        ([["ema20", 20, "--chart-1"], ["ema50", 50, "--pos-ink"], ["ema100", 100, "--gauge-warn"],
          ["ema200", 200, "--neg-ink"], ["ema400", 400, "--ink"]] as const).forEach(([k, n, c]) => {
          if (!(cfg as any)[k] || bars.length < n) return;
          addLine(ema7(cl, n).map((v, i) => v == null ? null : [i, v]).filter(Boolean) as any, cfg.colors?.[k] || tok(c, "#000"), 2);
        });
        // ٦) مستوياتُ اليوم السابق
        ([["pdh", (i: number) => bars[i - 1]?.high, "--neg-ink"], ["pdl", (i: number) => bars[i - 1]?.low, "--pos-ink"],
          ["pdc", (i: number) => bars[i - 1]?.close, "--ink-muted"], ["dOpen", (i: number) => bars[i]?.open, "--gauge-warn"]] as const)
          .forEach(([k, f, c]) => {
            if (!(cfg as any)[k]) return;
            const s3 = chart.addLineSeries({ color: tok(c, "#000"), lineVisible: false, pointMarkersVisible: true,
              pointMarkersRadius: 1.5, priceLineVisible: false, lastValueVisible: false });
            s3.setData(bars.map((_: any, i: number) => f(i)).map((v: any, i: number) => v == null ? null : { time: T(i), value: v }).filter(Boolean));
          });
      }
      // ══ الرسمُ اليدويّ (خطٌّ · قناة) ══
      const tIndex = (t: any) => bars.findIndex((b: any) => String(tkey(b.date)) === String(t));
      for (const d of draws) {
        if (!d.a || !d.b) continue;
        const a = tIndex(d.a.t), b = tIndex(d.b.t);
        if (a < 0 || b < 0 || a === b) continue;
        const [i1, v1, i2, v2] = a < b ? [a, d.a.p, b, d.b.p] : [b, d.b.p, a, d.a.p];
        const mk = (y1: number, y2: number) => { const l = chart.addLineSeries({ color: cfg.colors?.draw || tok("--brand-ink", "#5b52d3"), lineWidth: 2,
          priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
          l.setData([{ time: tkey(bars[i1].date), value: y1 }, { time: tkey(bars[i2].date), value: y2 }]); };
        mk(v1, v2);
        if (d.c) { const ci = tIndex(d.c.t); if (ci >= 0) { const slope = (v2 - v1) / (i2 - i1);
          const off = d.c.p - (v1 + slope * (ci - i1)); mk(v1 + off, v2 + off); } }
      }
      // ══ خطٌّ أفقيٌّ مثبَّت (D550) — كخطّ التقاطع العرضيّ على امتداد الرسم، يُعتمد بـ«+» ══
      for (const d of draws) {
        if (typeof d.h !== "number") continue;
        candle.createPriceLine({ price: d.h, color: cfg.colors?.draw || tok("--brand-ink", "#5b52d3"), lineWidth: 2,
          lineStyle: 0, axisLabelVisible: true, title: "" });
      }
      chart.timeScale().fitContent();
      chartRef.current = chart; candleRef.current = candle;
      chart.timeScale().subscribeVisibleLogicalRangeChange(() => setTick(t => t + 1));
      setTick(t => t + 1);
      ro = new ResizeObserver(() => { chart && chart.applyOptions({}); setTick(t => t + 1); });
      ro.observe(el.current);
    }).catch(() => setErr(true));
    return () => { cancelled = true; chartRef.current = null; candleRef.current = null;
      try { ro && ro.disconnect(); chart && chart.remove(); } catch {} };
  }, [bars, theme, ind, range, cfg, draws, tool]);

  const normT = (tm: any) => (tm && typeof tm === "object" && "year" in tm)
    ? `${tm.year}-${String(tm.month).padStart(2, "0")}-${String(tm.day).padStart(2, "0")}` : tm;
  const toXY = (pt: { t: any; p: number }) => {
    const c = chartRef.current, k = candleRef.current;
    if (!c || !k) return null;
    const x = c.timeScale().timeToCoordinate(pt.t), y = k.priceToCoordinate(pt.p);
    return x == null || y == null ? null : { x, y };
  };
  const freePaths = React.useMemo(() => {
    void tick;
    return draws.filter((d: any) => Array.isArray(d.free)).map((d: any) =>
      d.free.map(toXY).filter(Boolean).map((q: any, i: number) => `${i ? "L" : "M"}${q.x.toFixed(1)},${q.y.toFixed(1)}`).join(""));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draws, tick]);
  const onDown = (e: React.PointerEvent<SVGSVGElement>) => {
    if (tool !== "free") return;
    (e.target as Element).setPointerCapture?.(e.pointerId);
    stroke.current = []; setLive([]); onMove(e);
  };
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (!stroke.current || !chartRef.current || !candleRef.current) return;
    const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    const t = normT(chartRef.current.timeScale().coordinateToTime(x));
    const p = candleRef.current.coordinateToPrice(y);
    if (t == null || p == null) return;
    stroke.current.push({ t, p });
    setLive(l => [...l, { x, y }]);
  };
  const onUp = () => {
    const pts = stroke.current; stroke.current = null; setLive([]);
    if (pts && pts.length > 1) { saveDraws([...draws, { free: pts }]); setTool(null); }
  };

  useEffect(() => {
    if (tool !== "line") { setHy(null); return; }
    const k = candleRef.current, last = bars[bars.length - 1];
    const y = k && last ? k.priceToCoordinate(last.close) : null;
    setHy(y == null ? 180 : y);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tool]);
  const hyPrice = hy != null && candleRef.current ? candleRef.current.coordinateToPrice(hy) : null;
  const moveH = (e: React.PointerEvent<HTMLDivElement>) => {
    const r = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
    setHy(Math.max(4, Math.min(r.height - 4, e.clientY - r.top)));
  };
  const commitH = () => {
    if (hyPrice == null) return;
    saveDraws([...draws, { h: Math.round(hyPrice * 100) / 100 }]); setTool(null);
  };

  const toggle = (k: keyof typeof ind) => setInd(s => ({ ...s, [k]: !s[k] }));

  return (
    <div className="space-y-2">
      {/* ══ قوائمُ منسدلةٌ يظهر عليها المختارُ وحدَه ══ (بأمر المالك · D521)
         كانت المدّةُ ستَّ أزرارٍ والمؤشراتُ ستّاً تملأ سطرين على الجوال. */}
      {bars.length > 1 && (() => {
        const last = bars[bars.length - 1], prev = bars[bars.length - 2];
        const ch = prev?.close ? (last.close / prev.close - 1) * 100 : null;
        return (
          <div className="flex items-center gap-2 flex-wrap">
            {identity}
            <span className="text-xl font-bold tabular-nums text-[var(--ink)]" dir="ltr">{last.close.toFixed(2)}</span>
            {ch != null && (
              <span className={"text-[13px] font-bold tabular-nums " + (ch >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")} dir="ltr">
                {(last.close - prev.close >= 0 ? "+" : "") + (last.close - prev.close).toFixed(2)} ({(ch >= 0 ? "+" : "") + ch.toFixed(2)}%)
              </span>
            )}
            <span className="text-[11px] text-[var(--ink-muted)] tabular-nums" dir="ltr">{String(last.date).slice(0, 16)}</span>
          </div>
        );
      })()}
      <div className="flex items-center gap-1.5 flex-wrap">
        <Drop label={(RANGES.find(r => r[0] === range) || RANGES[0])[1]}>
          {close => RANGES.map(([id, lbl]) => (
            <button key={id} type="button" onClick={() => { setRange(id); close(); }}
              className={"w-full text-start px-3 min-h-[32px] text-[12px] font-bold " + (range === id ? "text-[var(--brand-ink)]" : "text-[var(--ink)]")}>
              {lbl}
            </button>
          ))}
        </Drop>
        <Drop label={IND.filter(([k]) => ind[k]).map(x => x[1]).join(" · ") || "المؤشرات"}>
          {() => IND.map(([k, lbl, c]) => (
            <button key={k} type="button" onClick={() => toggle(k)} aria-pressed={ind[k]}
              className="w-full flex items-center gap-2 px-3 min-h-[32px] text-[12px] font-bold text-[var(--ink)]" dir="ltr">
              <span className="w-3 h-3 rounded-sm border" style={ind[k]
                ? { background: c, borderColor: c } : { borderColor: "var(--hairline)" }} />
              {lbl}
            </button>
          ))}
        </Drop>
        {ind.d7m && (
          <button onClick={() => setShowCfg(true)} title="إعدادات المؤشّر" aria-label="إعدادات المؤشّر"
            className="px-2.5 py-1 min-h-[32px] rounded-lg text-[11px] font-bold border border-[var(--hairline)] text-[var(--ink)]">⚙ D7M</button>
        )}
        <Drop label={tool === "free" ? "رسم · حرّ" : tool === "line" ? "رسم · خطّ" : "رسم"}>
          {close => ([["free", "حرّ"], ["line", "خطّ"]] as const).map(([k, lbl]) => (
            <button key={k} type="button" onClick={() => { pending.current = []; setTool(tool === k ? null : k); close(); }}
              className={"w-full text-start px-3 min-h-[32px] text-[12px] font-bold " + (tool === k ? "text-[var(--brand-ink)]" : "text-[var(--ink)]")}>
              {lbl}
            </button>
          ))}
        </Drop>
        {draws.length > 0 && (
          <button onClick={() => saveDraws([])}
            className="px-2.5 py-1 min-h-[32px] rounded-lg text-[11px] font-bold border border-[var(--hairline)] text-[var(--ink-muted)]">مسح الرسم</button>
        )}
      </div>
      {showCfg && <D7MPanel cfg={cfg} onChange={saveCfg} onClose={() => setShowCfg(false)} />}
      {err ? (
        <div className="h-[420px] flex items-center justify-center text-[var(--ink-muted)] text-sm">تعذّر تحميل مكتبة الرسم — تأكد من الاتصال بالإنترنت.</div>
      ) : isLoading ? (
        <div className="h-[420px] skeleton rounded-xl" />
      ) : !bars.length ? (
        <div className="h-[420px] flex items-center justify-center text-[var(--ink-muted)] text-sm">لا توجد بيانات سعرية تاريخية لهذا الرمز حالياً.</div>
      ) : (
        <div className="relative">
        <div className="relative chart-frame" style={{ height: 440, width: "100%" }}>
          <div ref={el} style={{ position: "absolute", inset: 0 }} />
          <svg className="absolute inset-0 w-full h-full" style={{ pointerEvents: tool === "free" ? "auto" : "none",
               touchAction: tool === "free" ? "none" : undefined, cursor: tool === "free" ? "crosshair" : undefined, zIndex: 3 }}
               onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
            {freePaths.map((d: string, k: number) => d && (
              <path key={k} d={d} fill="none" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"
                style={{ stroke: cfg.colors?.draw || "var(--brand-ink)" }} />
            ))}
            {live.length > 1 && (
              <path d={live.map((q, i) => `${i ? "L" : "M"}${q.x.toFixed(1)},${q.y.toFixed(1)}`).join("")} fill="none"
                strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={{ stroke: cfg.colors?.draw || "var(--brand-ink)" }} />
            )}
          </svg>
          {tool === "line" && hy != null && (
            <div className="absolute inset-0" style={{ zIndex: 4, touchAction: "none", cursor: "row-resize" }}
              onPointerDown={e => { (e.target as Element).setPointerCapture?.(e.pointerId); moveH(e); }}
              onPointerMove={moveH}>
              <div className="absolute inset-x-0" style={{ top: hy, borderTop: `2px dashed ${cfg.colors?.draw || "var(--brand-ink)"}` }} />
              {hyPrice != null && (
                <span className="absolute text-[11px] font-bold tabular-nums px-1.5 py-0.5 rounded"
                  style={{ top: hy - 11, right: 4, background: cfg.colors?.draw || "var(--brand-ink)", color: "var(--bg)" }} dir="ltr">
                  {hyPrice.toFixed(2)}</span>
              )}
              <button type="button" aria-label="اعتماد الخطّ" title="اعتماد الخطّ"
                onPointerDown={e => e.stopPropagation()} onClick={commitH}
                className="absolute flex items-center justify-center rounded-full text-[20px] font-bold leading-none"
                style={{ top: hy - 16, left: 8, width: 32, height: 32, background: cfg.colors?.draw || "var(--brand-ink)", color: "var(--bg)" }}>+</button>
            </div>
          )}
          {ind.d7m && zones.filter(z => z.y > 0).map((z, k) => (
            <div key={k} className="d7m-zone" style={{ top: z.y - 8, left: z.x, color: cfg.colors?.zone || undefined }}>{z.title}</div>
          ))}
        </div>
          {ind.d7m && (dash || msmart || tt || alertsSt) && (
            <div className={`d7m-panels d7m-at-${cfg.dashPos}`} dir="rtl"
              style={{ ["--d7m-axis" as any]: `${psw + 6}px` }}>
              {dash && (
                <table className="d7m-table d7m-dash">
                  <thead><tr><th>الإطار</th><th>الحالة</th><th>المؤشرات الفنية</th></tr></thead>
                  <tbody>
                    {dash.rows.map((r, k) => (
                      <tr key={r.tf}>
                        <td className="d7m-tf" dir="ltr">{r.tf}</td>
                        <td className={r.up == null ? "d7m-muted" : r.up ? "d7m-pos" : "d7m-neg"}>{r.up == null ? "—" : r.up ? "صعود" : "هبوط"}</td>
                        <td className={k === 1 ? `d7m-${dash.liq.color}` : k === 3 ? `d7m-${dash.trend.tone}` : "d7m-muted"}>
                          {k === 0 ? "راصد الحيتان" : k === 1 ? dash.liq.state : k === 2 ? "قوة الاتجاه" : dash.trend.state}</td>
                      </tr>
                    ))}
                    <tr><th colSpan={3}>قرار الدخول</th></tr>
                    <tr><td colSpan={3} className={`d7m-decision d7m-tone-${dash.tone}`}>
                      <div className="d7m-dec-text">{dash.decision}</div>
                      <Meter v={dash.power} solid />
                      <Meter v={dash.trust} />
                      <div className="d7m-dec-cap">الثقة</div>
                    </td></tr>
                  </tbody>
                </table>
              )}
              {msmart && (
                <table className="d7m-table">
                  <thead><tr><th>المحلل الذكي</th></tr></thead>
                  <tbody>
                    <tr><td className={`d7m-${msmart.readingTone}`}>{msmart.reading}</td></tr>
                    <tr><td>{msmart.divergence}</td></tr>
                    <tr><td className={msmart.summary === "صعود" ? "d7m-pos" : msmart.summary === "هبوط" ? "d7m-neg" : "d7m-warn"}>{msmart.summary}</td></tr>
                  </tbody>
                </table>
              )}
              {alertsSt && (
                <table className="d7m-table">
                  <thead><tr><th colSpan={2}>التنبيهات</th></tr></thead>
                  <tbody>
                    {([["الزخم", alertsSt.mom], ["انعكاس", alertsSt.rev], ["ارتداد", alertsSt.bounce]] as const).map(([k, v]) => (
                      <tr key={k}><td>{k}</td><td className={v === "شراء" ? "d7m-pos" : v === "بيع" ? "d7m-neg" : ""}>{v}</td></tr>
                    ))}
                  </tbody>
                </table>
              )}
              {tt && (
                <table className="d7m-table">
                  <thead><tr><th colSpan={2}>أداة الصفقة 📋</th></tr></thead>
                  <tbody>
                    <tr><td>القرار</td><td className={tt.call ? "d7m-pos" : tt.put ? "d7m-neg" : "d7m-warn"}>{tt.dec}<Meter v={tt.conf} solid /></td></tr>
                    <tr><td>السترايك</td><td>{tt.call || tt.put ? `$${Math.round(tt.strike)}` : "—"}</td></tr>
                    <tr><td>الهدف</td><td className="d7m-pos">{tt.call || tt.put ? `$${tt.target.toFixed(2)}` : "—"}</td></tr>
                    <tr><td>الوقف</td><td className="d7m-neg">{tt.call || tt.put ? `$${tt.stop.toFixed(2)}` : "—"}</td></tr>
                    <tr><td>R : R</td><td>{tt.call || tt.put ? `1 : ${tt.rr.toFixed(1)}` : "—"}</td></tr>
                    <tr><td>الدخول</td><td>{tt.entry}</td></tr>
                    <tr><td>Gap اليوم</td><td className={tt.gap > 0.2 ? "d7m-pos" : tt.gap < -0.2 ? "d7m-neg" : ""}>{(tt.gap >= 0 ? "+" : "") + tt.gap.toFixed(2)}%</td></tr>
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
