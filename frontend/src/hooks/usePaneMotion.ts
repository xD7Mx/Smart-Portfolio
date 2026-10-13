import { useLayoutEffect, useRef } from "react";

/* ══ حركةُ تبديل التبويب ══ (‏D689 — «الحركةُ جزءٌ من هويّة التصميم»، المالك 2026-10-13)
   كان المحتوى يتبدّل تحت شريط التبويبات قفزاً. فعند كلّ تبديلٍ يطلع ما بعد الشريط من عناصر ظاهرة صعوداً خفيفاً متتابعاً.
   بالحركة على العناصر نفسِها لا بغلافٍ يُعاد تركيبُه — فلوحةُ التحكّم التي تبقى مركّبةً مخفيّةً (للسرعة) لا تُبنى من جديد.
   ولا حركةَ عند أوّل ظهور (للصفحة حركتُها)، ولا لمن يفضّل تقليلَ الحركة. */
export function usePaneMotion(anchor: { current: HTMLElement | null }, dep: unknown) {
  const first = useRef(true);
  useLayoutEffect(() => {
    if (first.current) { first.current = false; return; }
    if (typeof window === "undefined" || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    let el = anchor.current?.nextElementSibling as HTMLElement | null;
    for (let i = 0, n = 0; el && i < 14; i++, el = el.nextElementSibling as HTMLElement | null) {
      if (!el.getClientRects().length || getComputedStyle(el).position === "fixed") continue;
      el.animate?.([{ opacity: 0, transform: "translateY(8px)" }, { opacity: 1, transform: "none" }],
                   { duration: 260, easing: "cubic-bezier(.2,.8,.2,1)", delay: Math.min(n++, 4) * 30, fill: "backwards" });
    }
  }, [dep]);
}
