/* ══ مؤشّر D7M — ترجمةُ سكربت المالك (Pine v6) إلى حسابٍ على شموع التطبيق ══
 *
 * يُنقل منه ما يُبنى على شموع السهم نفسِها:
 *   · الفيبوناتشي التلقائي من الزجزاج (انحرافٌ = ATR(10)÷السعر×100×3 · عمق 7)
 *     بمستوياته وألوانه ونصوص مناطقه كما في السكربت.
 *   · القناة السعرية التلقائية (آخرُ ثلاث قممٍ/قيعانٍ للزجزاج بعمق 20).
 * ولا يُنقل ما يحتاج إطاراتٍ لحظيةً أو بياناتٍ أمريكية (لوحةُ الاتجاه وأداةُ
 * الصفقة وVIX والأخبار) — لا تُختلق بياناتٌ لا نملكها.
 */

export type Bar = { date: string; open: number; high: number; low: number; close: number };
export type Pivot = { index: number; price: number; isHigh: boolean };

/** ATR بطريقة Pine (RMA لمدى الحقيقيّ). */
export function atr(bars: Bar[], len = 10): number[] {
  const out: number[] = [];
  let prev: number | null = null;
  bars.forEach((b, i) => {
    const pc = i > 0 ? bars[i - 1].close : b.close;
    const tr = Math.max(b.high - b.low, Math.abs(b.high - pc), Math.abs(b.low - pc));
    prev = prev == null ? tr : (prev * (len - 1) + tr) / len;
    out.push(prev);
  });
  return out;
}

/**
 * زجزاجُ TradingView (مكتبة ZigZag/7) مبسّطاً بأمانة:
 *   · القمّةُ/القاعُ محوريٌّ بـ`depth` شمعةً على كلّ جانبٍ نصفاً.
 *   · يُقبل المحورُ الجديدُ إذا خالف اتجاهَ السابق وابتعد عنه بنسبة الانحراف،
 *     ويُستبدَل السابقُ إذا كان من جنسه وأشدَّ منه.
 */
export function zigzag(bars: Bar[], mult: number, depth: number): Pivot[] {
  const n = bars.length;
  if (n < depth + 2) return [];
  const a = atr(bars, 10);
  const half = Math.max(1, Math.floor(depth / 2));
  const piv: Pivot[] = [];
  for (let i = half; i < n - half; i++) {
    let isH = true, isL = true;
    for (let k = i - half; k <= i + half; k++) {
      if (k === i) continue;
      if (bars[k].high > bars[i].high) isH = false;
      if (bars[k].low < bars[i].low) isL = false;
    }
    const dev = (a[i] / bars[i].close) * 100 * mult;
    for (const [ok, price, isHigh] of [[isH, bars[i].high, true], [isL, bars[i].low, false]] as const) {
      if (!ok) continue;
      const last = piv[piv.length - 1];
      if (!last) { piv.push({ index: i, price, isHigh }); continue; }
      if (last.isHigh === isHigh) {
        if (isHigh ? price > last.price : price < last.price) piv[piv.length - 1] = { index: i, price, isHigh };
        continue;
      }
      if (Math.abs(price - last.price) / last.price * 100 >= dev) piv.push({ index: i, price, isHigh });
    }
  }
  return piv;
}

/** مستوياتُ السكربت الظاهرةُ افتراضاً: [القيمة، اللون، النصّ]. */
/* دورُ اللون لا قيمتُه — يُترجَم إلى رموز التطبيق عند الرسم. */
const WHITE = "white", YELLOW = "yellow";
export const FIB_LEVELS: [number, string][] = [
  [0, WHITE], [0.5, WHITE], [0.618, YELLOW], [-0.5, WHITE], [1.5, WHITE], [1, WHITE],
  [-1, WHITE], [-0.618, YELLOW], [1.618, YELLOW], [-0.1, WHITE], [1.1, WHITE], [2, WHITE],
  [2.1, WHITE], [-1.1, WHITE],
];

export type FibLine = { price: number; level: number; color: string; title: string };
export type FibZone = { price: number; title: string };

/** الفيبوناتشي التلقائي: آخرُ ضلعٍ للزجزاج (بلا عكس) ومستوياتُه ومناطقُه. */
export function autoFib(bars: Bar[], mult = 3, depth = 7): { lines: FibLine[]; zones: FibZone[] } | null {
  const p = zigzag(bars, mult, depth);
  if (p.length < 2) return null;
  const start = p[p.length - 2], end = p[p.length - 1];
  const startPrice = end.price, endPrice = start.price;          // fibo_reverse = false
  const height = (startPrice > endPrice ? -1 : 1) * Math.abs(startPrice - endPrice);
  const lines = FIB_LEVELS.map(([lv, color]) => {
    const price = startPrice + height * lv;
    const name = lv === 0.618 ? "اتجاه معاكس" : lv === 0.5 ? "دعــم قـوي" : "";
    return { price, level: lv, color, title: name };
  });
  // مناطقُ السكربت بين المستويات الرئيسية 0 · 1 · 1.1 · -0.1
  const main = [0, 1, 1.1, -0.1].map(lv => startPrice + height * lv).sort((x, y) => x - y);
  const mid = (startPrice + endPrice) / 2;
  const zones: FibZone[] = [];
  for (let i = 0; i < main.length - 1; i++) {
    const lo = main[i], hi = main[i + 1], mz = (lo + hi) / 2;
    const upper = mz >= mid;
    const isRes = upper && lo === main[main.length - 2];
    const isLowSup = mz < mid && hi === main[1];
    const isUpSup = upper && !isRes;
    if (isRes) zones.push({ price: mz, title: "الــمــقــاومــة" });
    else if (isUpSup) zones.push({ price: mz, title: "لاتطمع - لاتعكس" });
    else if (isLowSup) zones.push({ price: mz, title: "الـــدعـــم" });
  }
  return { lines, zones };
}

export type Channel = { base: [number, number][]; parallel: [number, number][] };

/** القناةُ التلقائية: قاعدةٌ بين المحورين المتجانسين الأخيرين، وموازيةٌ من الأوسط. */
export function autoChannel(bars: Bar[], mult = 3, depth = 20): Channel | null {
  const p = zigzag(bars, mult, depth);
  if (p.length < 3) return null;
  const a = p[p.length - 3], b = p[p.length - 2], c = p[p.length - 1];
  if (a.isHigh !== c.isHigh || a.index === c.index) return null;
  const slope = (c.price - a.price) / (c.index - a.index);
  const icBase = a.price - slope * a.index;
  const icPar = b.price - slope * b.index;
  const xEnd = bars.length - 1;
  return {
    base: [[a.index, a.price], [xEnd, slope * xEnd + icBase]],
    parallel: [[b.index, b.price], [xEnd, slope * xEnd + icPar]],
  };
}
