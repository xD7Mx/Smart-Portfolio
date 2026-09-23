/* نبضُ التحديث يتبع السوقَ لا رقماً ثابتاً (D288).
 *
 * طلب المالك أسعاراً لحظيةً وسوقاً مباشراً. وكانت الشاشةُ تسأل الخادمَ
 * كلَّ دقيقةٍ **دائماً**: بطيئةٌ في الجلسة (لقطةُ «تداول» تتجدّد كلَّ
 * دقيقة، فالسعرُ يتأخّر نصفَ دقيقةٍ بلا سبب)، ومُسرِفةٌ في العطلة (تسأل
 * ألفَ مرّةٍ عن رقمٍ لا يتحرّك).
 *
 * فالحاكمُ الواحدُ لطور السوق (`/settings/server-time`) هو من يقول النبض:
 *   · الجلسةُ ومزادُها  → 15 ثانية
 *   · قبل الافتتاح      → 30 ثانية (الأرقامُ تتغيّر قبل الجرس)
 *   · مغلق              → 10 دقائق (آخرُ إغلاقٍ لا يتحرّك)
 *
 * ولا ساعةَ ثانيةً في الواجهة: الطورُ يُقرأ من الخادم — وهو عطبُ D283
 * الذي جعل البطاقةَ تقول «قبل الافتتاح» يومَ السبت.
 */
import { useQuery } from "@tanstack/react-query";

import { settingsApi } from "../services/api";

export type Phase = "pre" | "open" | "preclose" | "closed";

/* ══ ثلاثُ ثوانٍ في الجلسة ══ (D289)
   قال المالك: «لا أقبل بتأخير 15 ثانية». وقد صار المصدرُ نفسُه يتجدّد
   عند الطلب بسقفِ خمس ثوانٍ (`tadawul_market.ensure_fresh`)، فسؤالٌ كلَّ
   ثلاثِ ثوانٍ يلتقط كلَّ تغيّرٍ يبلغنا — ولا معنى لأسرعَ منه: تحتَه تُسأل
   الشاشةُ عن رقمٍ لم يتغيّر بعد. وخارجَ الجلسة لا شيءَ يتحرّك أصلاً. */
export const LIVE_MS: Record<Phase, number> = {
  open: 3_000,
  preclose: 3_000,
  pre: 15_000,
  closed: 10 * 60_000,
};

export function useMarketPhase(): Phase {
  const { data } = useQuery({
    // نفسُ مفتاح اللسان: استعلامٌ واحدٌ يتشاركه الجميعُ في الذاكرة —
    // ولا نداءان لحقيقةٍ واحدة (وهو عطبُ «منتِجَين لمعنًى واحد»).
    queryKey: ["server-time"],
    queryFn: () => settingsApi.serverTime().then(r => r.data.data),
    refetchInterval: 20_000,
    staleTime: 10_000,
  });
  const st = String(data?.market_status || "closed");
  // و«عطلة» ليست طوراً في جدول المهل: نبضُها نبضُ المغلق (لا استطلاعَ
  // متسارعٌ في يومٍ بلا جلسة)، والتمييزُ بينهما للعرض لا للمهلة.
  return (["pre", "open", "preclose", "closed"].includes(st) ? st : "closed") as Phase;
}

/** الحالةُ كما يقولها الخادمُ **بلا تحويل** — ومعها سببُها إن زاد على
 *  ما يعرفه التقويم. تقرؤها الشاشاتُ التي تَعرض الحالةَ نفسَها (الساعةُ
 *  والنبض) من هذا الاستعلام الواحد — لا نداءَ ثانٍ ولا مصدرَ ثانٍ. */
export function useMarketStatus(): { status: string | null; why: string | null } {
  const { data } = useQuery({
    queryKey: ["server-time"],
    queryFn: () => settingsApi.serverTime().then(r => r.data.data),
    refetchInterval: 20_000,
    staleTime: 10_000,
  });
  return {
    status: (data?.market_status as string) ?? null,
    why: (data?.market_status_evidence as string) ?? null,
  };
}

/** مهلةُ التحديث المناسبةُ للطور الحاضر — تُمرَّر إلى `refetchInterval`. */
export function useLiveInterval(): number {
  return LIVE_MS[useMarketPhase()];
}
