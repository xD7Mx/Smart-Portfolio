/* علامةُ حالة السوق — شكلٌ واحدٌ ترسمه كلُّ شاشة.
 *
 * ══ نجمةٌ رماديةٌ للعطلة ══ (بأمر المالك · D413)
 * «اعتمد أيقونة العطلة نجمةً رماديةً مثل تريدنق فيو». والعطلةُ صنفٌ
 * مختلفٌ عن «مغلق»: المغلقُ حالٌ من حالات اليوم التداوليّ فتناسبه
 * الحلقةُ المشطوبة، والعطلةُ **يومٌ خارج الجدول** فتناسبها علامةٌ
 * مختلفةُ الشكل لا مختلفةُ اللون فقط — فتُقرأ بلمحةٍ بلا نصّ.
 *
 * وهي هنا وحدَها: الساعةُ والنبضُ يرسمان منها، فلا تُنسَخ فتختلف —
 * وهو الشرطُ نفسُه الذي منع عودةَ عطب D302 في الأسماء والألوان.
 */
import React from "react";
import { statusView } from "../../lib/marketStatus";

/** نجمةُ العطلة — خماسيةٌ صلبةٌ بلونِ الحالة الخافت. */
export function HolidayStar({ size = 11, color }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true"
      className="shrink-0"
      style={{ display: "block" }}>
      <path
        d="M12 2.6l2.9 6.05 6.6.9-4.8 4.6 1.18 6.55L12 17.6l-5.88 3.1L7.3 14.15l-4.8-4.6 6.6-.9z"
        fill={color || "var(--st-idle)"} />
    </svg>
  );
}

/** علامةُ أيّ حالة: نجمةٌ للعطلة، ونقطةٌ لما سواها. */
export function StatusMark({ status, size = 9 }:
  { status: string | null | undefined; size?: number }) {
  const v = statusView(status);
  if (!v) return null;
  if (v.key === "holiday") return <HolidayStar size={size + 2} color={v.color} />;
  return (
    <span className="inline-block rounded-full shrink-0"
      style={{ width: size - 2, height: size - 2, background: v.color }} />
  );
}

export default StatusMark;
