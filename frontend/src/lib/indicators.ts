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
/** ‏CVD — دلتا الحجم التراكميّة. البيانُ صفقةً صفقةً (من البائع ومن المشتري) لا يصلنا، فتُقدَّر دلتا كلّ شمعةٍ من
 *  موضع إغلاقها في مداها: حجمٌ × ((الإغلاق − القاع) − (القمّة − الإغلاق)) ÷ (القمّة − القاع) — إغلاقٌ عند القمّة كلُّه
 *  شراء، وعند القاع كلُّه بيع — ثمّ تُجمع. تقديرٌ من الشموع يُسمّى كذلك في الرسم، لا دلتا صفقاتٍ حقيقية. */
export function cvdApprox(bars: { high: number; low: number; close: number; volume?: number }[]): number[] {
  let acc = 0;
  return bars.map(b => {
    const r = b.high - b.low, v = Number(b.volume) || 0;
    acc += r > 0 ? v * ((b.close - b.low) - (b.high - b.close)) / r : 0;
    return acc;
  });
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

