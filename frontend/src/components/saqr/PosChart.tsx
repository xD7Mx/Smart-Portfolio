/* ══ رسمُ المركز داخل بطاقته ══ (‏D839 بأمر المالك 2026-11-25)
   «في المراكز المفتوحة — حتى أراقب شكلَ العقد مباشرةً — هل تستطيع وضعَ الرسم نفسِه في بطاقة المركز؟ بياناتُ المركز فوق، وفي الأسفل الرسمُ
   البيانيّ للعقد نفسِه أو للسهم». فرسمٌ مدمَجٌ بمكتبة الرسم نفسِها وذاكرتها (‏["bars", الرمز, الإطار] — ما يُفتح في «الرسم» لا يُجلب مرّتين):
   العقدُ افتراضاً وزرٌّ إلى سهمه، وخطوطُ الدخول والوقف والجني (أو هدفُ السهم ومستواه عند الدخول)، وعلامةٌ عند فتح المركز. لا تمريرَ ولا
   تكبيرَ داخل البطاقة (فالصفحةُ تُمرَّر بالإصبع على الجوال)، والرسمُ الكاملُ بزرّ «فتح في الرسم». */
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createChart, AreaSeries, createSeriesMarkers, LineStyle, CrosshairMode, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { marketApi } from "../../services/api";
import { useAppStore } from "../../store/appStore";
import { sanitizeBars, displayTimes, exchangeTz, tickLabel, crossLabel } from "../../lib/chartData";
import type { SPos } from "./saqr";

const tok = (name: string, fb: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fb;
const tokA = (name: string, fb: string, a: number) => {
  const c = tok(name, fb);
  const m = /^#([0-9a-f]{6})$/i.exec(c);
  if (m) { const n = parseInt(m[1], 16); return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`; }
  const p = c.match(/[\d.]+/g);
  return p && p.length >= 3 ? `rgba(${p[0]}, ${p[1]}, ${p[2]}, ${a})` : c;
};
const BARS_GC = 30 * 60_000;
const reduced = () => { try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; } };

export default function PosChart({ p, market }: { p: SPos; market: "us" | "sa" }) {
  const stock = p.kind === "stock";
  const [view, setView] = useState<"c" | "s">("c");
  const sym = stock || view === "s" ? (market === "sa" ? `${p.symbol}.SR` : p.symbol) : p.contract;
  /* ‏D842 — قيس على الخادم: المصدرُ لا يعطي العقدَ شموعاً دون اليوم (‏NIO271217P00003000: صفرٌ بـ15د و1س و4س، و146 شمعةً يومية) — فكان الرسمُ
     «لا شموعَ له». فالساعةُ أوّلاً (للسهم وللعقد السائل)، وإن خلت فاليوميّ */
  const hq = useQuery({
    queryKey: ["bars", sym, "1h"],
    queryFn: () => marketApi.bars(sym, "1h").then(r => (Array.isArray(r.data?.data) ? r.data.data : [])),
    staleTime: 60_000, gcTime: BARS_GC, refetchInterval: 120_000, retry: 1,
  });
  const daily = hq.isSuccess && !(hq.data || []).length;
  const dq = useQuery({
    queryKey: ["bars", sym, "1d"], enabled: daily,
    queryFn: () => marketApi.bars(sym, "1d").then(r => (Array.isArray(r.data?.data) ? r.data.data : [])),
    staleTime: 300_000, gcTime: BARS_GC, retry: 1,
  });
  const q = daily ? dq : hq;
  const tf = daily ? "1d" : "1h";
  const bars = useMemo(() => sanitizeBars(q.data || []), [q.data]);
  const box = useRef<HTMLDivElement | null>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<ISeriesApi<"Area"> | null>(null);
  const [shown, setShown] = useState(false);
  const theme = useAppStore(s => s.theme);   // ‏D841: ألوانُ الرسم تتبع المظهرَ إن تبدّل والبطاقةُ مفتوحة

  /* السطورُ المرجعية: للعقد — الدخولُ والوقفُ والجني؛ وللسهم — مستواه عند الدخول وهدفُه */
  const lines = useMemo(() => {
    const out: { v: number; t: string; c: string }[] = [];
    const onContract = !stock && view === "c";
    if (stock || onContract) {
      out.push({ v: p.entry_px, t: "الدخول", c: "--ink-muted" });
      if (p.stop) out.push({ v: p.stop, t: "الوقف", c: "--neg-ink" });
      const tp = p.tp_px ?? (p.take_x ? p.entry_px * p.take_x : null);
      if (tp) out.push({ v: tp, t: "الجني", c: "--pos-ink" });
      if (stock && p.target) out.push({ v: p.target, t: "الهدف", c: "--brand-ink" });
    } else {
      if (p.S0) out.push({ v: p.S0, t: "عند الدخول", c: "--ink-muted" });
      if (p.target) out.push({ v: p.target, t: "الهدف", c: "--brand-ink" });
    }
    return out;
  }, [p, stock, view]);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const font = getComputedStyle(document.body).fontFamily || "sans-serif";
    const c = createChart(el, {
      autoSize: true,
      layout: { background: { color: "transparent" }, textColor: tok("--ink-muted", "#6b7280"), fontFamily: font, fontSize: 10, attributionLogo: false },
      grid: { vertLines: { visible: false }, horzLines: { color: tokA("--hairline", "#dcdcdc", 0.55) } },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.14, bottom: 0.1 } },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false, fixLeftEdge: true, fixRightEdge: true,
                   tickMarkFormatter: (t: any, type: number) => tickLabel(t, type) },
      localization: { locale: "en-US", timeFormatter: (t: any) => crossLabel(t) },
      crosshair: { mode: CrosshairMode.Magnet, vertLine: { labelVisible: false }, horzLine: { labelVisible: true } },
      handleScroll: false, handleScale: false,
    });
    const brand = tok("--brand-ink", "#5b52d3");
    series.current = c.addSeries(AreaSeries, { lineColor: brand, lineWidth: 2, topColor: tokA("--brand-ink", "#5b52d3", 0.26), bottomColor: tokA("--brand-ink", "#5b52d3", 0.02),
      priceLineVisible: false, lastValueVisible: true, crosshairMarkerRadius: 3 });
    chart.current = c;
    return () => { c.remove(); chart.current = null; series.current = null; };
  }, []);

  useEffect(() => {
    const c = chart.current, s = series.current;
    if (!c || !s) return;
    const brand = tok("--brand-ink", "#5b52d3");
    c.applyOptions({ layout: { textColor: tok("--ink-muted", "#6b7280") }, grid: { horzLines: { color: tokA("--hairline", "#dcdcdc", 0.55) } } });
    s.applyOptions({ lineColor: brand, topColor: tokA("--brand-ink", "#5b52d3", 0.26), bottomColor: tokA("--brand-ink", "#5b52d3", 0.02) });
  }, [theme]);

  useEffect(() => {
    const s = series.current, c = chart.current;
    if (!s || !c) return;
    const tz = exchangeTz(sym);
    const T = displayTimes(bars, tz);
    s.setData(bars.map((b, i) => ({ time: T[i] as any, value: b.close })));
    /* مستوى الدخول في المدى دائماً — به يُقرأ الربحُ والخسارةُ بنظرة (والوقفُ والجني يُريان إن قرُبا، فلا يُسحق الرسم) */
    const anchor = stock || view === "c" ? p.entry_px : (p.S0 ?? null);
    s.applyOptions({ autoscaleInfoProvider: (orig: () => any) => { const r = orig(); if (!r || anchor == null) return r;
      return { ...r, priceRange: { minValue: Math.min(r.priceRange.minValue, anchor), maxValue: Math.max(r.priceRange.maxValue, anchor) } }; } });
    for (const pl of (s as any).__pls || []) s.removePriceLine(pl);
    (s as any).__pls = lines.map(l => s.createPriceLine({ price: l.v, color: tok(l.c, tok("--ink-muted", "#6b7280")), lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: l.t }));
    /* علامةُ فتح المركز: أوّلُ شمعةٍ عند الفتح أو بعده */
    const opened = Date.parse(p.opened) / 1000;
    const iOpen = bars.findIndex(b => (typeof b.time === "number" ? b.time : Date.parse(String(b.time) + "T00:00:00Z") / 1000) >= opened - (tf === "1d" ? 86400 : 3600));
    (s as any).__mk?.detach?.();
    if (iOpen >= 0) (s as any).__mk = createSeriesMarkers(s, [{ time: T[iOpen] as any, position: "belowBar", color: tok("--brand-ink", "#5b52d3"), shape: "arrowUp", text: "فُتح" }]);
    if (bars.length) {
      /* المدى: من قبيل فتح المركز بقليلٍ إلى الآن — لا الأشهرُ كلُّها */
      const from = Math.max(0, (iOpen >= 0 ? iOpen : bars.length - 1) - (tf === "1d" ? 20 : 24));
      c.timeScale().setVisibleLogicalRange({ from, to: bars.length - 1 });
    }
    const r = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(r);
  }, [bars, lines, sym, tf, p.opened, p.entry_px, p.S0, stock, view, theme]);

  const swap = (v: "c" | "s") => { if (v === view) return; if (reduced()) { setView(v); return; } setShown(false); window.setTimeout(() => setView(v), 140); };
  return (
    <div className="sp-chart" data-role="sp-chartbox" data-view={stock ? "s" : view} data-tf={tf} data-shown={shown ? "1" : "0"}>
      {!stock && (
        <span className="sp-chart-seg seg inline-flex" role="group" aria-label="رسمُ العقد أو سهمه" data-role="sp-chart-view">
          <button type="button" className={"seg-btn chip" + (view === "c" ? " on" : "")} aria-pressed={view === "c"} onClick={() => swap("c")} data-v="c">العقد</button>
          <button type="button" className={"seg-btn chip" + (view === "s" ? " on" : "")} aria-pressed={view === "s"} onClick={() => swap("s")} data-v="s">السهم</button>
        </span>
      )}
      <div ref={box} className="sp-chart-c" aria-label={`رسمُ ${stock || view === "s" ? "السهم" : "العقد"} منذ فتح المركز`} role="img" />
      {(hq.isLoading || (daily && dq.isLoading)) && <span className="sp-chart-note" data-role="sp-chart-wait">يُحمَّل الرسم…</span>}
      {!hq.isLoading && !(daily && dq.isLoading) && !bars.length && <span className="sp-chart-note" data-role="sp-chart-empty">لا شموعَ له بعد — {q.isError ? "تعذّر الجلب" : "لم يُتداول بعد"}</span>}
    </div>
  );
}
