import { autoFib, autoChannel, autoTrend, vwapAnchored, ema as ema7, dashboard, macdSmart, tradeTool,
  bar10, D7M_DEFAULTS, D7MSettings } from "./d7m";
import D7MPanel from "./D7MPanel";
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

export default function NativeChart({ symbol, theme = "dark" }: { symbol: string; theme?: "dark" | "light" }) {
  const el = useRef<HTMLDivElement>(null);
  // المدّةُ الافتراضيّةُ خمسُ سنوات للسوقين (بأمر المالك)
  const [range, setRange] = useState("5y");
  const [ind, setInd] = useState({ sma20: true, sma50: true, sma200: false, macd: true, rsi: false, d7m: false });
  const [err, setErr] = useState(false);
  // ══ إعداداتُ مؤشّر D7M — تُحفظ في المتصفّح (بأمر المالك: زرُّ إعدادات) ══
  const [cfg, setCfg] = useState<D7MSettings>(() => {
    try { return { ...D7M_DEFAULTS, ...JSON.parse(localStorage.getItem("sp_d7m_cfg") || "{}") }; }
    catch { return D7M_DEFAULTS; }
  });
  const saveCfg = (c: D7MSettings) => { setCfg(c); try { localStorage.setItem("sp_d7m_cfg", JSON.stringify(c)); } catch {} };
  const [showCfg, setShowCfg] = useState(false);
  const [zones, setZones] = useState<{ y: number; title: string }[]>([]);
  // ══ الرسمُ اليدويّ: خطُّ ترند وقناة — محفوظان لكلّ رمز ══
  const dKey = `sp_draw_${symbol}`;
  const [draws, setDraws] = useState<any[]>(() => { try { return JSON.parse(localStorage.getItem(dKey) || "[]"); } catch { return []; } });
  const [tool, setTool] = useState<null | "line" | "channel">(null);
  const pending = useRef<any[]>([]);
  useEffect(() => { try { setDraws(JSON.parse(localStorage.getItem(dKey) || "[]")); } catch { setDraws([]); } }, [dKey]);
  const saveDraws = (d: any[]) => { setDraws(d); try { localStorage.setItem(dKey, JSON.stringify(d)); } catch {} };

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
    enabled: ind.d7m && isUS, staleTime: 15 * 60 * 1000,
  });
  const vix = isUS && vixBars.length ? vixBars[vixBars.length - 1].close : null;
  const today = new Date().toISOString().slice(0, 10);
  const newsDay = isUS && cfg.news && cfg.newsDates.split(",").map((x: string) => x.trim()).includes(today);
  const dash = ind.d7m && cfg.dashboard ? dashboard(bars as any, { bull: cfg.bull, bear: cfg.bear, vix,
    vixWarn: cfg.vixWarn, vixBlock: cfg.vixBlock, newsDates: newsDay ? [today] : [], today }) : null;
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
        const ink = tok("--ink", "#e5e7eb");
        const yellow = tok("--gauge-warn", "#d97706");
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
          const shown: { y: number; title: string }[] = [];
          zoneList.map(z => ({ y: candle.priceToCoordinate(z.price) ?? -999, title: z.title }))
            .sort((a, b) => a.y - b.y)
            .forEach(z => { if (z.y > 0 && shown.every(o => Math.abs(o.y - z.y) >= 14)) shown.push(z); });
          setZones(shown);
        };
        chart.timeScale().subscribeVisibleLogicalRangeChange(() => requestAnimationFrame(placeZones));
        setTimeout(placeZones, 60);
        // ٢) الترند التلقائي
        if (cfg.trend) {
          const tr = autoTrend(bars, cfg.trendPP);
          for (const l of tr.lines) if (l.x2 > l.x1) addLine([[l.x1, l.y1], [l.x2, l.y2]], ink, l.major ? 2 : 1, 0);
          if (cfg.trendShapes && tr.signals.length) {
            candle.setMarkers(tr.signals.map(sg => ({ time: T(sg.index),
              position: sg.kind === "breakDown" || sg.kind === "reactDown" ? "aboveBar" : "belowBar",
              shape: sg.kind === "breakDown" || sg.kind === "reactDown" ? "arrowDown" : "arrowUp", color: ink }))
              .sort((a: any, b: any) => (a.time > b.time ? 1 : -1)));
          }
        }
        // ٣) القناة السعرية التلقائية
        const ch = cfg.channel ? autoChannel(bars, cfg.chDev, cfg.chDepth) : null;
        if (ch) for (const seg of [ch.base, ch.parallel]) addLine(seg as any, tokA("--ink", "#e5e7eb", .55));
        // ٤) VWAP ونطاقه
        if (cfg.vwap || cfg.vwapBand) {
          const vw = vwapAnchored(bars, cfg.vwapAnchor, cfg.vwapMult);
          if (cfg.vwap) addLine(vw.vwap.map((v, i) => [i, v]) as any, tok("--chart-1", "#2962FF"), 1);
          if (cfg.vwapBand) { addLine(vw.upper.map((v, i) => [i, v]) as any, tok("--pos-ink", "#16a34a"), 1);
            addLine(vw.lower.map((v, i) => [i, v]) as any, tok("--pos-ink", "#16a34a"), 1); }
        }
        // ٥) المتوسّطات الأسية
        const cl = bars.map((b: any) => b.close);
        ([["ema20", 20, "--chart-1"], ["ema50", 50, "--pos-ink"], ["ema100", 100, "--gauge-warn"],
          ["ema200", 200, "--neg-ink"], ["ema400", 400, "--ink"]] as const).forEach(([k, n, c]) => {
          if (!(cfg as any)[k] || bars.length < n) return;
          addLine(ema7(cl, n).map((v, i) => v == null ? null : [i, v]).filter(Boolean) as any, tok(c, "#000"), 2);
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
        const a = tIndex(d.a.t), b = tIndex(d.b.t);
        if (a < 0 || b < 0 || a === b) continue;
        const [i1, v1, i2, v2] = a < b ? [a, d.a.p, b, d.b.p] : [b, d.b.p, a, d.a.p];
        const mk = (y1: number, y2: number) => { const l = chart.addLineSeries({ color: tok("--brand-ink", "#5b52d3"), lineWidth: 2,
          priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
          l.setData([{ time: tkey(bars[i1].date), value: y1 }, { time: tkey(bars[i2].date), value: y2 }]); };
        mk(v1, v2);
        if (d.c) { const ci = tIndex(d.c.t); if (ci >= 0) { const slope = (v2 - v1) / (i2 - i1);
          const off = d.c.p - (v1 + slope * (ci - i1)); mk(v1 + off, v2 + off); } }
      }
      if (tool) {
        chart.subscribeClick((param: any) => {
          if (!param?.time || !param.point) return;
          const p = candle.coordinateToPrice(param.point.y); if (p == null) return;
          pending.current.push({ t: param.time, p });
          const need = tool === "line" ? 2 : 3;
          if (pending.current.length >= need) {
            const [a, b, c] = pending.current; pending.current = [];
            saveDraws([...draws, tool === "line" ? { a, b } : { a, b, c }]); setTool(null);
          }
        });
      }
      chart.timeScale().fitContent();
      ro = new ResizeObserver(() => chart && chart.applyOptions({}));
      ro.observe(el.current);
    }).catch(() => setErr(true));
    return () => { cancelled = true; try { ro && ro.disconnect(); chart && chart.remove(); } catch {} };
  }, [bars, theme, ind, range, cfg, draws, tool]);

  const toggle = (k: keyof typeof ind) => setInd(s => ({ ...s, [k]: !s[k] }));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex gap-1.5 flex-wrap">
          {RANGES.map(([id, lbl]) => (
            <button key={id} onClick={() => setRange(id)}
              className={"px-2.5 py-1 min-h-[32px] rounded-lg text-[11px] font-bold border transition-all " +
                (range === id ? " text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)] hover:text-[var(--ink)]")}>
              {lbl}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {([["sma20", "SMA20", "var(--chart-1)"], ["sma50", "SMA50", "var(--warn-ink)"], ["sma200", "SMA200", "var(--chart-4)"], ["macd", "MACD", "var(--chart-1)"], ["rsi", "RSI", "var(--chart-5)"], ["d7m", "D7M", "var(--brand-ink)"]] as const).map(([k, lbl, c]) => (
            <button key={k} onClick={() => toggle(k)}
              className={"px-2.5 py-1 min-h-[32px] rounded-lg text-[11px] font-bold border transition-all " + (ind[k] ? "text-[var(--ink)]" : "text-[var(--ink-muted)]")}
              /* ══ لا تُلحَق شفافيةٌ برمز ══
                 كان `c + "22"` ينتج `var(--chart-1)22` — نصٌّ غير صالح
                 يسقطه المتصفّح، فتظهر الشارة المفعَّلة بلا أرضيةٍ ولا
                 إطار: لا يُفرَّق المفعَّل من المطفأ إلا بحبرٍ خافت.
                 و`color-mix` هي التي تخلط رمزاً بشفافية. */
              style={ind[k]
                ? { background: `color-mix(in srgb, ${c} 14%, transparent)`,
                    borderColor: `color-mix(in srgb, ${c} 42%, transparent)` }
                : { borderColor: "var(--hairline)" }}>
              {lbl}
            </button>
          ))}
          {ind.d7m && (
            <button onClick={() => setShowCfg(true)} title="إعدادات المؤشّر" aria-label="إعدادات المؤشّر"
              className="px-2.5 py-1 min-h-[32px] rounded-lg text-[11px] font-bold border border-[var(--hairline)] text-[var(--ink)]">⚙ إعدادات D7M</button>
          )}
          <button onClick={() => { pending.current = []; setTool(tool === "line" ? null : "line"); }}
            className={"px-2.5 py-1 min-h-[32px] rounded-lg text-[11px] font-bold border transition-all " + (tool === "line" ? "text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)]")}>
            ╱ خطّ</button>
          <button onClick={() => { pending.current = []; setTool(tool === "channel" ? null : "channel"); }}
            className={"px-2.5 py-1 min-h-[32px] rounded-lg text-[11px] font-bold border transition-all " + (tool === "channel" ? "text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)]")}>
            ▱ قناة</button>
          {draws.length > 0 && (
            <button onClick={() => saveDraws([])}
              className="px-2.5 py-1 min-h-[32px] rounded-lg text-[11px] font-bold border border-[var(--hairline)] text-[var(--ink-muted)]">مسح الرسم</button>
          )}
        </div>
      </div>
      {tool && (
        <p className="text-[11px] text-[var(--brand-ink)]">
          {tool === "line" ? "انقر نقطتين على الرسم لخطّ الترند" : "انقر نقطتين للخطّ ثمّ نقطةً ثالثة للموازي"}
        </p>
      )}
      {showCfg && <D7MPanel cfg={cfg} onChange={saveCfg} onClose={() => setShowCfg(false)} />}
      {err ? (
        <div className="h-[420px] flex items-center justify-center text-[var(--ink-muted)] text-sm">تعذّر تحميل مكتبة الرسم — تأكد من الاتصال بالإنترنت.</div>
      ) : isLoading ? (
        <div className="h-[420px] skeleton rounded-xl" />
      ) : !bars.length ? (
        <div className="h-[420px] flex items-center justify-center text-[var(--ink-muted)] text-sm">لا توجد بيانات سعرية تاريخية لهذا الرمز حالياً.</div>
      ) : (
        <div className="relative">
        <div className="relative" style={{ height: "62vh", minHeight: 420, width: "100%" }}>
          <div ref={el} style={{ position: "absolute", inset: 0 }} />
          {ind.d7m && zones.filter(z => z.y > 0).map((z, k) => (
            <div key={k} className="d7m-zone" style={{ top: z.y - 8 }}>{z.title}</div>
          ))}
        </div>
          {ind.d7m && (dash || msmart || tt || alertsSt) && (
            <div className="d7m-panels" dir="rtl">
              {dash && (
                <table className="d7m-table">
                  <thead><tr><th>الإطار</th><th>الحالة</th><th>المؤشرات الفنية</th></tr></thead>
                  <tbody>
                    {dash.rows.map((r, k) => (
                      <tr key={k}><td>{r.tf}</td>
                        <td className={r.up == null ? "" : r.up ? "d7m-pos" : "d7m-neg"}>{r.up == null ? "—" : r.up ? "صعود" : "هبوط"}</td>
                        <td className={k === 0 ? "" : k === 1 ? `d7m-${dash.liq.color}` : `d7m-${dash.trend.tone}`}>
                          {k === 0 ? "راصد الحيتان" : k === 1 ? dash.liq.state : `قوة الاتجاه: ${dash.trend.state}`}</td></tr>
                    ))}
                    {dash.vixWarn && <tr><td colSpan={3} className="d7m-warnrow">{dash.vixWarn}</td></tr>}
                    {dash.newsWarn && <tr><td colSpan={3} className="d7m-warnrow">⚠ يوم خبر اقتصادي</td></tr>}
                    <tr><th colSpan={3}>قرار الدخول</th></tr>
                    <tr><td colSpan={3} className={`d7m-${dash.tone} d7m-decision`}>
                      {dash.decision}<br /><span className="d7m-bar">{bar10(dash.power)}</span><br />
                      <span className="d7m-bar">{bar10(dash.trust)}</span><br />الثقة</td></tr>
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
                    <tr><td>القرار</td><td className={tt.call ? "d7m-pos" : tt.put ? "d7m-neg" : "d7m-warn"}>{tt.dec}<br /><span className="d7m-bar">{bar10(tt.conf)}</span></td></tr>
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
