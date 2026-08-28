import { useEffect } from "react";
import { useAuthStore } from "../store/authStore";
import { authApi } from "../services/api";

const KEY = "sp_idle_minutes";

/** خيارات القفل التلقائي بعد الخمول — 0 تعني «بلا قفل مطلقاً». */
export const IDLE_OPTIONS: { label: string; minutes: number }[] = [
  { label: "دقيقة واحدة", minutes: 1 },
  { label: "5 دقائق", minutes: 5 },
  { label: "15 دقيقة", minutes: 15 },
  { label: "30 دقيقة", minutes: 30 },
  { label: "ساعة", minutes: 60 },
  { label: "بلا قفل مطلقاً", minutes: 0 },
];

export const getIdleMinutes = (): number => {
  const v = Number(localStorage.getItem(KEY));
  return Number.isFinite(v) && v >= 0 ? v : 15; // الافتراضي: ربع ساعة
};
export const setIdleMinutes = (m: number) => {
  localStorage.setItem(KEY, String(m));
  // بثّ للتبويبات الأخرى + إعادة تشغيل المؤقّت في هذا التبويب فوراً
  window.dispatchEvent(new Event("sp-idle-change"));
};

/** يُركَّب مرة واحدة على مستوى التطبيق: يُسجّل خروج المالك تلقائياً بعد مدة
 * الخمول المختارة. النشاط (حركة/لمس/مفتاح/تمرير) يعيد ضبط العدّاد. عند اختيار
 * «بلا قفل» لا يعمل أي مؤقّت. يعمل فقط أثناء وجود جلسة مالك. */
export function useIdleLock() {
  const isOwner = useAuthStore(s => s.isOwner);
  const logout = useAuthStore(s => s.logout);

  useEffect(() => {
    if (!isOwner) return;

    let timer: ReturnType<typeof setTimeout> | null = null;

    const doLock = () => {
      authApi.logout().catch(() => {}).finally(logout);
    };

    const reset = () => {
      if (timer) clearTimeout(timer);
      const mins = getIdleMinutes();
      if (mins <= 0) return; // بلا قفل
      timer = setTimeout(doLock, mins * 60 * 1000);
    };

    const events = ["mousemove", "mousedown", "keydown", "touchstart", "scroll", "visibilitychange"];
    events.forEach(e => window.addEventListener(e, reset, { passive: true }));
    window.addEventListener("sp-idle-change", reset);
    reset();

    return () => {
      if (timer) clearTimeout(timer);
      events.forEach(e => window.removeEventListener(e, reset));
      window.removeEventListener("sp-idle-change", reset);
    };
  }, [isOwner, logout]);
}
