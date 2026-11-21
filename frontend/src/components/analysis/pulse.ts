/* ══ لوحتا القوّة: الاتجاهُ والسيولة ══ (‏D782 · بأمر المالك 2026-11-21)

   «نحن في الأسهم نحتاج نعرف حاجتين: الاتجاه والسيولة… لوحتان: قوّةُ الاتجاه وقوّةُ السيولة — هل السيولةُ ذاهبةٌ للصعود أو للهبوط، هل
   الاتجاهُ ذاهبٌ للصعود أو للهبوط… شيءٌ بسيطٌ وواضح». فالحسابُ من شموع الإطار المعروض وحدها، ولكلّ لوحةٍ شواهدُ تصوّت:

   · الاتجاه — ستةُ شواهد: السعرُ ومتوسّطُ 50 · متوسّطُ 20 و50 · متوسّطُ 50 و200 · ‏+DI و‏−DI · ميلُ متوسّط 50 · القممُ والقيعان
     (آخرُ عشرين شمعةً مقابل العشرين قبلها). صاعدٌ إن رجحت بشاهدين فأكثر، وهابطٌ كذلك، وإلّا فعرضيّ. وقوّتُه من ‏ADX (‏15 ⇐ صفر ·
     40 ⇐ تمام) واتّفاقِ الشواهد.
   · السيولة — ثلاثةُ شواهد للمال: تدفّقُ تشايكن (‏CMF 20) · نصيبُ حجم الشموع الصاعدة من حجم العشرين · ميلُ ‏OBV في عشر شموع.
     داخلةٌ للصعود إن رجحت، وخارجةٌ للهبوط إن رجحت ضدّه، وإلّا فمتوازنة. وقوّتُها من رجحانها ومن الحجم النسبيّ (آخرُ خمس شموعٍ إلى
     العشرين قبلها). وبلا أحجامٍ من المصدر «غير متوفّر» — لا رقمٌ مختلَق. */
import { ema, dmi, liquidity, type VBar } from "./d7m";

export type Side = "up" | "down" | "flat" | "na";
export type Force = {
  side: Side; word: string; level: string; strength: number; stat: string | null;
  /** الشواهدُ بترتيبها: ‏+1 مع الصعود · ‏−1 مع الهبوط */
  why: [number, string][];
  /** راصدُ الحيتان على الشمعة الأخيرة (اندفاعٌ شرائيّ · تجميعٌ خفيّ · انهيارٌ بيعيّ · تصريفٌ بيعيّ · جفاف) — للسيولة وحدها */
  tag?: string | null;
};

const clip = (v: number, lo = -1, hi = 1) => Math.max(lo, Math.min(hi, v));
/** درجةُ القوّة بالفصحى — مذكّرةً للاتجاه ومؤنّثةً للسيولة */
export const levelWord = (s: number, fem = false) =>
  s >= 75 ? (fem ? "قويّةٌ جدّاً" : "قويٌّ جدّاً") : s >= 55 ? (fem ? "قويّة" : "قويّ") : s >= 35 ? (fem ? "متوسّطة" : "متوسّط") : (fem ? "ضعيفة" : "ضعيف");

export function trendForce(bars: VBar[]): Force | null {
  const n = bars.length, i = n - 1;
  if (n < 30) return null;
  const c = bars.map(b => b.close);
  const e20 = ema(c, 20), e50 = ema(c, 50), e200 = ema(c, 200);
  const { plus, minus, adx } = dmi(bars, 14, 14);
  const why: [number, string][] = [];
  const vote = (up: boolean, u: string, d: string) => { why.push(up ? [1, u] : [-1, d]); };
  const E20 = e20[i], E50 = e50[i], E200 = e200[i];
  if (E50 != null && c[i] !== E50) vote(c[i] > E50, "السعرُ فوق متوسّط 50", "السعرُ تحت متوسّط 50");
  if (E20 != null && E50 != null && E20 !== E50) vote(E20 > E50, "متوسّطُ 20 فوق متوسّط 50", "متوسّطُ 20 تحت متوسّط 50");
  if (E50 != null && E200 != null && E50 !== E200) vote(E50 > E200, "متوسّطُ 50 فوق متوسّط 200", "متوسّطُ 50 تحت متوسّط 200");
  const P = plus[i], M = minus[i];
  if (P != null && M != null && P !== M) vote(P > M, "المشترون أقوى (‏+DI)", "البائعون أقوى (‏−DI)");
  const E50p = i >= 5 ? e50[i - 5] : null;
  if (E50 != null && E50p != null && E50 !== E50p) vote(E50 > E50p, "متوسّطُ 50 يصعد", "متوسّطُ 50 يهبط");
  if (n >= 40) {
    let h1 = -Infinity, h0 = -Infinity, l1 = Infinity, l0 = Infinity;
    for (let k = n - 40; k < n; k++) {
      const b = bars[k];
      if (k >= n - 20) { h1 = Math.max(h1, b.high); l1 = Math.min(l1, b.low); } else { h0 = Math.max(h0, b.high); l0 = Math.min(l0, b.low); }
    }
    if (h1 > h0 && l1 > l0) why.push([1, "قممٌ وقيعانٌ أعلى"]);
    else if (h1 < h0 && l1 < l0) why.push([-1, "قممٌ وقيعانٌ أدنى"]);
  }
  const score = why.reduce((s, v) => s + v[0], 0);
  const A = adx[i];
  const side: Side = score >= 2 ? "up" : score <= -2 ? "down" : "flat";
  const adxN = A == null ? 0 : clip((A - 15) / 25, 0, 1);
  let strength = Math.round(100 * (0.55 * adxN + 0.45 * Math.abs(score) / 6));
  if (side === "flat") strength = Math.min(strength, 34);
  return { side, word: side === "up" ? "صاعد" : side === "down" ? "هابط" : "عرضيّ", level: levelWord(strength), strength,
    stat: A == null ? null : `ADX ${Math.round(A)}`, why };
}

export function liquidityForce(bars: VBar[], volOk: boolean): Force | null {
  const n = bars.length;
  if (n < 30) return null;
  if (!volOk) return { side: "na", word: "غير متوفّر", level: "", strength: 0, stat: "لا أحجامَ من المصدر", why: [] };
  const v = bars.map(b => b.volume || 0);
  let mfv = 0, vs = 0, upV = 0;
  for (let k = n - 20; k < n; k++) {
    const b = bars[k], r = b.high - b.low, m = r > 0 ? ((b.close - b.low) - (b.high - b.close)) / r : 0;
    mfv += m * v[k]; vs += v[k];
    const prev = bars[k - 1].close;
    upV += b.close > prev ? v[k] : b.close === prev ? v[k] / 2 : 0;
  }
  if (vs <= 0) return { side: "na", word: "غير متوفّر", level: "", strength: 0, stat: "لا أحجامَ من المصدر", why: [] };
  const cmf = mfv / vs, upR = upV / vs;
  let obv = 0, v10 = 0;
  for (let k = n - 10; k < n; k++) { const p = bars[k - 1].close; obv += bars[k].close > p ? v[k] : bars[k].close < p ? -v[k] : 0; v10 += v[k]; }
  const obvS = v10 > 0 ? obv / v10 : 0;
  const parts = [clip(cmf / 0.2), clip((upR - 0.5) / 0.2), clip(obvS / 0.5)];
  const flow = parts.reduce((s, x) => s + x, 0) / 3;
  const recent = v.slice(n - 5).reduce((s, x) => s + x, 0) / 5;
  const base = v.slice(n - 25, n - 5).reduce((s, x) => s + x, 0) / 20;
  const rv = base > 0 ? recent / base : null;
  const side: Side = flow >= 0.15 ? "up" : flow <= -0.15 ? "down" : "flat";
  const rvN = rv == null ? 0 : clip((rv - 0.8) / 1.2, 0, 1);
  let strength = Math.round(100 * clip(0.65 * Math.abs(flow) + 0.35 * rvN, 0, 1));
  if (side === "flat") strength = Math.min(strength, 34);
  const pc = (x: number) => `${Math.round(x * 100)}%`;
  const why: [number, string][] = [
    [cmf >= 0 ? 1 : -1, cmf >= 0 ? `تدفّقُ المال موجب (‏CMF ${cmf.toFixed(2)})` : `تدفّقُ المال سالب (‏CMF ${cmf.toFixed(2)})`],
    [upR >= 0.5 ? 1 : -1, `حجمُ الشموع الصاعدة ${pc(upR)} من حجم العشرين`],
    [obvS >= 0 ? 1 : -1, obvS >= 0 ? "‏OBV يصعد في عشر شموع" : "‏OBV يهبط في عشر شموع"],
  ];
  const L = liquidity(bars, 20, false);
  return { side, word: side === "up" ? "داخلةٌ للصعود" : side === "down" ? "خارجةٌ للهبوط" : "متوازنة", level: levelWord(strength, true), strength,
    stat: rv == null ? null : `الحجم ${rv.toFixed(1)}×`, why, tag: L.state !== "محايد" && L.state !== "—" ? L.state : null };
}
