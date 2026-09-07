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

/** ما يبقى نقداً حين لا يكون المجموعُ المستهدف مئةً. */
export function retainedCashPct(deployTarget: number): number {
  const t = Number(deployTarget) || 0;
  return t > 0 ? Math.max(0, 100 - t) : 0;
}
