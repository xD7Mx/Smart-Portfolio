/* حاكمُ عرضِ حالة السوق — موضعٌ واحدٌ تقرأ منه كلُّ شاشة.
 *
 * ══ لماذا موضعٌ واحد ══ (‏D302 · ثم بأمر المالك)
 * حُذفت الحالةُ من بطاقة «نبض السوق» بأمر المالك لأنّها كانت من
 * **مصدرَين** يتناقضان: وسمٌ مشتقٌّ من طور خلاصة الذكاء («جلسة مباشرة»)
 * ونقطةٌ من حاكم الأطوار («السوق مغلق») — ورآهما المالكُ يتناقضان بعينه.
 *
 * ثم أمر بإعادتها إلى النبض «مثل الساعة». والإعادةُ صوابٌ الآن لأنّ
 * المصدرَ صار واحداً (‏`/settings/server-time` ← `market_state`)، لكنّ
 * الخطرَ القديمَ يعود لو نُسخت **الأسماءُ والألوان** في كلّ شاشة: تُعدَّل
 * واحدةٌ وتُنسى أختُها فيختلف اللفظُ للحال نفسِها. فالخريطةُ هنا وحدَها،
 * وتقرأ منها الساعةُ والنبضُ معاً.
 *
 * ══ وفرقٌ بين «مغلق» و«عطلة» ══ (بأمر المالك)
 * المغلقُ حالٌ طبيعيةٌ في يوم تداولٍ — يفتح بعد ساعات. والعطلةُ يومٌ
 * كاملٌ لا جلسةَ فيه. والفرقُ خبرٌ يحتاجه المستثمر، فلا يُخلطان في لفظ.
 */

export type MarketStatusKey =
  | "open" | "pre" | "preclose" | "closed" | "holiday";

export interface MarketStatusView {
  key: MarketStatusKey;
  label: string;
  color: string;
}

export const MARKET_STATUS: Record<MarketStatusKey, MarketStatusView> = {
  open:     { key: "open",     label: "السوق مفتوح",  color: "var(--st-open)" },
  pre:      { key: "pre",      label: "قبل الافتتاح", color: "var(--st-pre)" },
  preclose: { key: "preclose", label: "قبل الإغلاق",  color: "var(--st-preclose)" },
  closed:   { key: "closed",   label: "السوق مغلق",   color: "var(--st-idle)" },
  holiday:  { key: "holiday",  label: "عطلة — لا جلسة اليوم",
              color: "var(--st-idle)" },
};

/** حالةٌ من الخادم ← عرضُها. وما لا يُعرَف يُعاد `null` ولا يُخمَّن. */
export function statusView(s: string | null | undefined): MarketStatusView | null {
  if (!s) return null;
  return MARKET_STATUS[s as MarketStatusKey] ?? null;
}

/** أيُّ الحالات لا تداولَ فيها — للنبض والاستطلاع معاً. */
export function isDormant(s: string | null | undefined): boolean {
  return s === "closed" || s === "holiday";
}
