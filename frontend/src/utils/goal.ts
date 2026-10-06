/* ‏D609: سنواتُ الوصول إلى الهدف بعائدٍ مركّبٍ ثابت — الحسابُ نفسُه في مؤشرات المحفظة ونجوم تاسي والمستشار.
   null حين لا يُعرف العائدُ أو كان صفراً فما دونه: لا وعدَ بموعدٍ لا يُبلغ. */
export function yearsToGoal(current?: number | null, target?: number | null, cagrPct?: number | null): number | null {
  if (!current || !target || current <= 0 || target <= 0) return null;
  if (current >= target) return 0;
  if (cagrPct == null || cagrPct <= 0) return null;
  return Math.log(target / current) / Math.log(1 + cagrPct / 100);
}
export const yearsLabel = (y: number | null) =>
  y == null ? "—" : y === 0 ? "بُلغ" : `${y.toFixed(1)} سنة`;
