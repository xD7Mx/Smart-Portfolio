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

