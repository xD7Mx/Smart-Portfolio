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

const RANGES: [string, string][] = [["1mo", "شهر"], ["3mo", "3 أشهر"], ["6mo", "6 أشهر"], ["1y", "سنة"], ["2y", "سنتان"], ["5y", "5 سنوات"]];

export default function NativeChart({ symbol, theme = "dark" }: { symbol: string; theme?: "dark" | "light" }) {
  const el = useRef<HTMLDivElement>(null);
  const [range, setRange] = useState("6mo");
  const [ind, setInd] = useState({ sma20: true, sma50: true, sma200: false, macd: true, rsi: false });
  const [err, setErr] = useState(false);

  const { data: bars = [], isLoading } = useQuery({
    queryKey: ["ohlc", symbol, range],
    queryFn: () => marketApi.history(symbol, range).then(r => (Array.isArray(r.data?.data) ? r.data.data : [])),
    enabled: !!symbol,
    retry: 0,
  });

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
        timeScale: { borderColor: tok("--hairline", "#dcdcdc"), timeVisible: false },
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
      candle.setData(bars.map((b: any) => ({ time: b.date, open: b.open, high: b.high, low: b.low, close: b.close })));

      // volume
      const vol = chart.addHistogramSeries({ priceScaleId: "", priceFormat: { type: "volume" } });
      vol.priceScale().applyOptions({ scaleMargins: { top: 0.86, bottom: 0 } });
      vol.setData(bars.map((b: any) => ({ time: b.date, value: b.volume, color: b.close >= b.open ? tokA("--pos-ink", "#16a34a", .4) : tokA("--neg-ink", "#dc2626", .4) })));

      const closes = bars.map((b: any) => b.close);
      const addSMA = (period: number, color: string) => {
        const s = chart.addLineSeries({ color, lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false });
        s.setData(sma(closes, period).map((v, i) => v == null ? null : ({ time: bars[i].date, value: v })).filter(Boolean));
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
        rs.setData(rsi(closes).map((v, i) => v == null ? null : ({ time: bars[i].date, value: v })).filter(Boolean));
      }
      if (ind.macd) {
        const { line, signal, hist } = macd(closes);
        const macdMargins = bothPanes ? { top: 0.88, bottom: 0 } : { top: 0.74, bottom: 0.02 };
        const macdHist = chart.addHistogramSeries({ priceScaleId: "macd", priceLineVisible: false, lastValueVisible: false });
        chart.priceScale("macd").applyOptions({ scaleMargins: macdMargins, borderColor: tok("--hairline", "#dcdcdc") });
        macdHist.setData(hist.map((v, i) => v == null ? null : ({ time: bars[i].date, value: v, color: v >= 0 ? tokA("--pos-ink", "#16a34a", .5) : tokA("--neg-ink", "#dc2626", .5) })).filter(Boolean));
        const macdLine = chart.addLineSeries({ color: tok("--chart-1", "#5b52d3"), lineWidth: 1.3, priceScaleId: "macd", priceLineVisible: false, lastValueVisible: false });
        macdLine.setData(line.map((v, i) => v == null ? null : ({ time: bars[i].date, value: v })).filter(Boolean));
        const signalLine = chart.addLineSeries({ color: tok("--warn-ink", "#92400e"), lineWidth: 1.3, priceScaleId: "macd", priceLineVisible: false, lastValueVisible: false });
        signalLine.setData(signal.map((v, i) => v == null ? null : ({ time: bars[i].date, value: v })).filter(Boolean));
      }
      chart.timeScale().fitContent();
      ro = new ResizeObserver(() => chart && chart.applyOptions({}));
      ro.observe(el.current);
    }).catch(() => setErr(true));
    return () => { cancelled = true; try { ro && ro.disconnect(); chart && chart.remove(); } catch {} };
  }, [bars, theme, ind, range]);

  const toggle = (k: keyof typeof ind) => setInd(s => ({ ...s, [k]: !s[k] }));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex gap-1.5 flex-wrap">
          {RANGES.map(([id, lbl]) => (
            <button key={id} onClick={() => setRange(id)}
              className={"px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all " +
                (range === id ? " text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)] hover:text-[var(--ink)]")}>
              {lbl}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {([["sma20", "SMA20", "var(--chart-1)"], ["sma50", "SMA50", "var(--warn-ink)"], ["sma200", "SMA200", "var(--chart-4)"], ["macd", "MACD", "var(--chart-1)"], ["rsi", "RSI", "var(--chart-5)"]] as const).map(([k, lbl, c]) => (
            <button key={k} onClick={() => toggle(k)}
              className={"px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all " + (ind[k] ? "text-[var(--ink)]" : "text-[var(--ink-muted)]")}
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
        </div>
      </div>
      {err ? (
        <div className="h-[420px] flex items-center justify-center text-[var(--ink-muted)] text-sm">تعذّر تحميل مكتبة الرسم — تأكد من الاتصال بالإنترنت.</div>
      ) : isLoading ? (
        <div className="h-[420px] skeleton rounded-xl" />
      ) : !bars.length ? (
        <div className="h-[420px] flex items-center justify-center text-[var(--ink-muted)] text-sm">لا توجد بيانات سعرية تاريخية لهذا الرمز حالياً.</div>
      ) : (
        <div ref={el} style={{ height: "62vh", minHeight: 420, width: "100%" }} />
      )}
    </div>
  );
}
