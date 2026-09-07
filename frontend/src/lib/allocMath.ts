/* حسابُ صفّ المجموع في جدول التوزيع — دالّةٌ واحدةٌ تُستدعى وتُفحص.
   كانت ستُكتب داخل المكوّن فلا يبلغها فحصٌ إلا بمتصفّح، ونسخُها في سكربت
   فحصٍ يفحص النسخةَ لا الشيفرة. فأُخرجت لتُستورد في الموضعين. */

export type AllocRow = { dividend_yield?: number | null };

/** معدّلُ عائد التوزيعات مرجّحاً بالأوزان المستهدفة.
 *
 *  الوزنُ صفراً أو سالباً لا يدخل — الشركةُ خارج التوزيع أصلاً.
 *  والعائدُ المجهول يخرج من **البسط والمقام معاً**: إدخالُه صفراً في المقام
 *  يخفض المعدّلَ بشركةٍ لا نعرف عائدها، وهو اختلاقٌ بصيغة حساب.
 *  وإن لم يُعرف عائدُ أيّ شركةٍ فالجواب null — «غير متوفّر» لا صفر. */
export function weightedDividendYield(
  rows: AllocRow[], weightOf: (r: AllocRow, i: number) => number,
): { value: number | null; known: number; unknown: number } {
  let num = 0, den = 0, known = 0, unknown = 0;
  rows.forEach((r, i) => {
    const w = Number(weightOf(r, i)) || 0;
    if (w <= 0) return;
    const dy = r.dividend_yield;
    if (typeof dy === "number" && isFinite(dy)) { num += w * dy; den += w; known += 1; }
    else unknown += 1;
  });
  return { value: den > 0 ? num / den : null, known, unknown };
}

/** إعادةُ توزيع الأوزان على مجموعٍ جديد، بنسبها بينها.
 *
 *  هذا هو معنى «المجموع المستهدف»: من أراد سبعين للمحفظة وثلاثين نقداً
 *  لا يريد وسماً يتلوّن، بل أوزاناً تنزل بنسبةٍ واحدةٍ فتتبعها المبالغُ
 *  والأسهم. والنسبةُ بين الشركات لا تتغيّر — من كان ضعفَ أخيه بقي ضعفَه.
 *
 *  والكسورُ تُجبر على الأكبر: تقريبُ كلّ وزنٍ إلى منزلةٍ واحدة يترك بقيّةً
 *  (‏0.1٪ أو 0.2٪) فلا يبلغ المجموعُ هدفَه ويبقى الوسمُ برتقالياً بعد عملٍ
 *  صحيح. تُحمَّل البقيّةُ على أكبر وزنٍ حيث أثرُها النسبيُّ أصغر.
 *
 *  مجموعٌ حاليٌّ صفرٌ لا يُقسَم عليه — تُعاد الأوزانُ كما هي، فلا شيءَ
 *  يُوزَّع بنسبةٍ من عدم. */
export function rescaleWeights(weights: number[], target: number): number[] {
  const w = weights.map(v => (Number(v) > 0 ? Number(v) : 0));
  const sum = w.reduce((a, b) => a + b, 0);
  const t = Number(target);
  if (!(sum > 0) || !isFinite(t) || t < 0) return w.map(v => round1(v));
  const scaled = w.map(v => round1(v * t / sum));
  const drift = round1(t - scaled.reduce((a, b) => a + b, 0));
  if (drift !== 0) {
    let big = 0;
    for (let i = 1; i < scaled.length; i++) if (scaled[i] > scaled[big]) big = i;
    if (scaled[big] + drift >= 0) scaled[big] = round1(scaled[big] + drift);
  }
  return scaled;
}

const round1 = (v: number) => Math.round(v * 10) / 10;

/** ما يبقى نقداً حين لا يكون المجموعُ المستهدف مئةً. */
export function retainedCashPct(deployTarget: number): number {
  const t = Number(deployTarget) || 0;
  return t > 0 ? Math.max(0, 100 - t) : 0;
}
