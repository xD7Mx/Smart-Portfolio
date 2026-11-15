/* مؤشّراتُ اللوحات السفلى — دوالُّ خالصةٌ يفحصها الحارسُ بنفسها (‏scripts/audit/trade_room_d732.mjs).
   ══ ‏D732 (المالك 2026-11-14): «ستوكاستيك، RSI، الماكد، و… Cumulative Volume» في غرفة التداول ══ */
/** متوسّطٌ بسيطٌ يتخطّى الفراغ: نافذةٌ من ‏p قيمٍ متّصلة، وإلّا فراغ. */
function smaN(a: (number | null)[], p: number): (number | null)[] {
  const out: (number | null)[] = Array(a.length).fill(null);
  for (let i = 0; i < a.length; i++) {
    if (i < p - 1) continue;
    let sum = 0, ok = true;
    for (let j = i - p + 1; j <= i; j++) { const v = a[j]; if (v == null) { ok = false; break; } sum += v; }
    if (ok) out[i] = sum / p;
  }
  return out;
}
/** ستوكاستيك (14 · 3 · 3): ‏%K الخامُ = موضعُ الإغلاق بين أدنى قاعٍ وأعلى قمّةٍ في 14 شمعة، ثمّ يُنعَّم بثلاث،
 *  و‏%D متوسّطُ ‏%K لثلاث. ونطاقٌ صفريّ (قمّةٌ = قاع) فراغٌ لا رقمٌ مختلَق. */
export function stochastic(bars: { high: number; low: number; close: number }[], kP = 14, kS = 3, dP = 3) {
  const raw: (number | null)[] = bars.map((_, i) => {
    if (i < kP - 1) return null;
    let hh = -Infinity, ll = Infinity;
    for (let j = i - kP + 1; j <= i; j++) { hh = Math.max(hh, bars[j].high); ll = Math.min(ll, bars[j].low); }
    return hh > ll ? (bars[i].close - ll) / (hh - ll) * 100 : null;
  });
  const k = smaN(raw, kS);
  return { k, d: smaN(k, dP) };
}
/* ══ CVD D7M — مؤشّرُ المالك بنصّه (Pine v4 · «CVD D7M» عن LonesomeTheBlue) ══ (بأمر المالك 2026-11-14)
   دلتا كلّ شمعةٍ من فتائلها وجسمها لا من صفقاتها: نسبةُ الشراء = ½ × (فتيلٌ علويّ + سفليّ + (صاعدة ? 2 × الجسم : 0))
   ÷ (الفتيلين + الجسم) — ونسبةٌ صفرٌ أو غيرُ معرّفةٍ تصير ½. فالدلتا = الحجم × نسبةُ اتّجاهها، موجبةً للصاعدة وسالبةً
   للهابطة، وتُجمع. وتُرسم شموعاً (فتحُها تراكمُ الأمس وإغلاقُها تراكمُ اليوم) بهايكن آشي اختياراً، أو خطّاً؛ والمقياسُ
   «احجام» كما هي، أو «مستويات» 0–100، أو «نسبة» −100..100 على أعلى وأدنى ‏len شمعة؛ ومتوسّطاتٌ على الإغلاق. */
export type CvdCfg = {
  style: "candle" | "line"; scale: "volume" | "pct" | "levels"; len: number; ha: boolean;
  sma1: boolean; sma1Len: number; sma2: boolean; sma2Len: number;
  ema1: boolean; ema1Len: number; ema2: boolean; ema2Len: number;
};
export const CVD_DEFAULTS: CvdCfg = {
  style: "candle", scale: "levels", len: 200, ha: true,
  sma1: false, sma1Len: 50, sma2: false, sma2Len: 200, ema1: false, ema1Len: 50, ema2: true, ema2Len: 200,
};
type Bar = { open: number; high: number; low: number; close: number; volume?: number };
const mx = (...v: (number | null)[]) => v.some(x => x == null) ? null : Math.max(...(v as number[]));
const mn = (...v: (number | null)[]) => v.some(x => x == null) ? null : Math.min(...(v as number[]));

/** الدلتا التراكميّة بمعادلة السكربت حرفاً. */
export function cvdCum(bars: Bar[]): number[] {
  let acc = 0;
  return bars.map(b => {
    const v = Number(b.volume) || 0;
    const tw = b.high - Math.max(b.open, b.close), bw = Math.min(b.open, b.close) - b.low, body = Math.abs(b.close - b.open);
    const rate = (cond: boolean) => {
      const r = 0.5 * (tw + bw + (cond ? 2 * body : 0)) / (tw + bw + body);
      return !isFinite(r) || r === 0 ? 0.5 : r;              // nz(ret) == 0 ? 0.5
    };
    acc += b.close >= b.open ? v * rate(b.open <= b.close) : -v * rate(b.open > b.close);
    return acc;
  });
}

function emaN(a: (number | null)[], p: number): (number | null)[] {
  const out: (number | null)[] = Array(a.length).fill(null);
  const k = 2 / (p + 1);
  let prev: number | null = null;
  for (let i = 0; i < a.length; i++) {
    const v = a[i];
    if (v == null) continue;
    prev = prev == null ? v : k * v + (1 - k) * prev;    // كدالّة Pine: أوّلُ قيمةٍ بذرةٌ ثمّ التنعيم
    out[i] = prev;
  }
  return out;
}

export function cvdD7M(bars: Bar[], cfg: CvdCfg = CVD_DEFAULTS) {
  const n = bars.length, cum = cvdCum(bars);
  const o: (number | null)[] = cum.map((_, i) => i > 0 ? cum[i - 1] : null);
  const h = cum.map((v, i) => mx(v, o[i])), l = cum.map((v, i) => mn(v, o[i])), c: (number | null)[] = cum.slice();   // الإغلاقُ معرّفٌ من أوّل شمعة
  let O = o, H = h, L = l, C = c;
  if (cfg.ha) {
    const hc: (number | null)[] = Array(n).fill(null), ho: (number | null)[] = Array(n).fill(null);
    for (let i = 0; i < n; i++) {
      if (o[i] == null) continue;
      hc[i] = ((o[i] as number) + (h[i] as number) + (l[i] as number) + (c[i] as number)) / 4;
      ho[i] = i === 0 || ho[i - 1] == null ? ((o[i] as number) + (c[i] as number)) / 2 : ((ho[i - 1] as number) + (hc[i - 1] as number)) / 2;
    }
    O = ho; C = hc; H = h.map((v, i) => mx(v, ho[i], hc[i])); L = l.map((v, i) => mn(v, ho[i], hc[i]));
  }
  // الحدّان على آخر ‏len شمعة — للشموع من قممها وقيعانها، وللخطّ من الخطّ نفسِه (في السكربت يُقاس الخطُّ على شموعٍ
  // غيرِ مرسومة فيستوي صفراً؛ فقِيس على ما يُرسم). وأوّلُ الرسم بما توفّر قبل اكتمال الفترة — لا خطّاً مستوياً.
  const line = cfg.style === "line";
  const hiSrc = line ? cum : H, loSrc = line ? cum : L;
  const len = Math.max(10, Math.floor(Number(cfg.len) || 200));
  const hb: (number | null)[] = Array(n).fill(null), lb: (number | null)[] = Array(n).fill(null);
  for (let i = 0; i < n; i++) {
    let a = -Infinity, b = Infinity;
    for (let j = Math.max(0, i - len + 1); j <= i; j++) {
      const x = hiSrc[j], y = loSrc[j];
      if (x != null && x > a) a = x;
      if (y != null && y < b) b = y;
    }
    if (a > -Infinity) hb[i] = a;
    if (b < Infinity) lb[i] = b;
  }
  const sc = (v: number | null, i: number): number | null => {
    if (v == null) return null;
    if (cfg.scale === "volume") return v;
    const r = hb[i] != null && lb[i] != null ? (hb[i] as number) - (lb[i] as number) : 0;
    const norm = r === 0 ? 0 : (v - (lb[i] ?? 0)) / r;
    return cfg.scale === "levels" ? norm * 100 : norm * 200 - 100;
  };
  const scaled = (a: (number | null)[]) => a.map((v, i) => sc(v, i));
  return {
    o: line ? [] : scaled(O), h: line ? [] : scaled(H), l: line ? [] : scaled(L), c: line ? [] : scaled(C),
    line: line ? scaled(cum) : [],
    sma1: !line && cfg.sma1 ? scaled(smaN(C, cfg.sma1Len)) : [], sma2: !line && cfg.sma2 ? scaled(smaN(C, cfg.sma2Len)) : [],
    ema1: !line && cfg.ema1 ? scaled(emaN(C, cfg.ema1Len)) : [], ema2: !line && cfg.ema2 ? scaled(emaN(C, cfg.ema2Len)) : [],
  };
}

/** مواضعُ اللوحات السفلى: كلُّ مؤشّرٍ ذبذبيٍّ لوحةٌ لا تتداخل مع أخرى، والحجمُ فوقها، والسعرُ فوق الجميع. */
export function paneLayout(n: number) {
  const osc = n <= 0 ? 0 : [0, 0.2, 0.32, 0.42, 0.5][Math.min(n, 4)];
  const h = n > 0 ? osc / n : 0, gap = 0.012;
  return {
    price: { top: 0.06, bottom: osc + 0.12 },
    volume: { top: 1 - osc - 0.11, bottom: osc + 0.005 },
    panes: Array.from({ length: n }, (_, i) => ({ top: 1 - osc + i * h + gap, bottom: Math.max(0, osc - (i + 1) * h) + (i === n - 1 ? 0.005 : gap) })),
  };
}

/* ── المتوسّطاتُ وRSI وMACD — كما كانت في الرسم القديم، هنا ليقرأها الرسمُ الاحترافيّ (‏D736) ويفحصها الحارس ── */
export function sma(data: number[], p: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    sum += data[i];
    if (i >= p) sum -= data[i - p];
    out.push(i >= p - 1 ? sum / p : null);
  }
  return out;
}
export function ema(data: number[], p: number): (number | null)[] {
  const out: (number | null)[] = Array(data.length).fill(null);
  const k = 2 / (p + 1);
  let prev: number | null = null;
  for (let i = 0; i < data.length; i++) {
    if (prev == null) {
      if (i >= p - 1) { prev = data.slice(i - p + 1, i + 1).reduce((a, b) => a + b, 0) / p; out[i] = prev; }
    } else { prev = data[i] * k + prev * (1 - k); out[i] = prev; }
  }
  return out;
}
export function rsi(data: number[], p = 14): (number | null)[] {
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
export function macd(data: number[], fast = 12, slow = 26, sig = 9) {
  const ef = ema(data, fast), es = ema(data, slow);
  const line = data.map((_, i) => (ef[i] == null || es[i] == null ? null : (ef[i] as number) - (es[i] as number)));
  const vals = line.filter((v): v is number => v != null);
  const sv = ema(vals, sig);
  const signal: (number | null)[] = Array(data.length).fill(null);
  let j = 0;
  for (let i = 0; i < line.length; i++) if (line[i] != null) { signal[i] = sv[j] ?? null; j++; }
  const hist = line.map((v, i) => (v == null || signal[i] == null ? null : v - (signal[i] as number)));
  return { line, signal, hist };
}

/* ══ Stoch RSI — سكربتُ تريدنق فيو بنصّه (‏Pine v6 «Stochastic RSI» · أرسله المالك 2026-11-15 · D741) ══
   rsi1 = ta.rsi(close, lengthRSI) · k = ta.sma(ta.stoch(rsi1, rsi1, rsi1, lengthStoch), smoothK) · d = ta.sma(k, smoothD).
   ‏ta.rsi بمتوسّط وايلدر (‏RMA) المبذور بمتوسّطٍ بسيط — كدالّة rsi أعلاه؛ و‏ta.stoch = ‏100 × (الحاليّ − الأدنى) ÷ (الأعلى − الأدنى) على
   ‏lengthStoch شمعة، ومدًى صفريٌّ ‏na لا رقمٌ مختلَق؛ و‏ta.sma على نافذةٍ فيها ‏na ‏na. */
export type SrcKey = "close" | "open" | "high" | "low" | "hl2" | "hlc3" | "ohlc4";
export type StochRsiCfg = { k: number; d: number; rsiLen: number; stochLen: number; src: SrcKey; upper: number; middle: number; lower: number };
/* مدخلاتُ السكربت كلُّها كما في نافذة تريدنق فيو: ‏K · D · طولُ RSI · طولُ الستوكاستيك · مصدرُ RSI — وحدودُ النمط 80 · 50 · 20 */
export const STOCHRSI_DEFAULTS: StochRsiCfg = { k: 3, d: 3, rsiLen: 14, stochLen: 14, src: "close", upper: 80, middle: 50, lower: 20 };
export function source(bars: { open: number; high: number; low: number; close: number }[], src: SrcKey = "close"): number[] {
  return bars.map(b => src === "open" ? b.open : src === "high" ? b.high : src === "low" ? b.low : src === "hl2" ? (b.high + b.low) / 2
    : src === "hlc3" ? (b.high + b.low + b.close) / 3 : src === "ohlc4" ? (b.open + b.high + b.low + b.close) / 4 : b.close);
}
export function stochRsi(series: number[], cfg: StochRsiCfg = STOCHRSI_DEFAULTS) {
  const r = rsi(series, cfg.rsiLen), n = r.length, L = cfg.stochLen;
  const raw: (number | null)[] = Array(n).fill(null);
  for (let i = L - 1; i < n; i++) {
    let hh = -Infinity, ll = Infinity, ok = true;
    for (let j = i - L + 1; j <= i; j++) { const v = r[j]; if (v == null) { ok = false; break; } if (v > hh) hh = v; if (v < ll) ll = v; }
    if (ok && hh > ll) raw[i] = 100 * ((r[i] as number) - ll) / (hh - ll);
  }
  const k = smaN(raw, cfg.k);
  return { k, d: smaN(k, cfg.d) };
}
