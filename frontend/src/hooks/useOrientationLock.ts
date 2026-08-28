import { useEffect } from "react";

/** قفل دوران الشاشة (اختياري من الإعدادات ← التخصيص).
 * تغطية مزدوجة حتى يعمل فعلياً في كل بيئة:
 *   1) Screen Orientation API الأصلي — يعمل في التطبيق المثبّت (PWA) وأندرويد
 *      ملء الشاشة فقط، ويحتاج غالباً وضع ملء الشاشة، ولا يدعمه iOS Safari.
 *   2) قفل CSS احتياطي (فئة html.orient-lock في globals.css): عند تدوير الجهاز
 *      أفقياً يُدوّر المحتوى برمجياً ليبقى عمودياً — يعمل في كل المتصفحات بما
 *      فيها iOS Safari والمتصفح العادي حيث يفشل الـ API الأصلي بصمت. */
const KEY = "sp_orientation_lock";

export const getOrientationLock = (): boolean => localStorage.getItem(KEY) === "1";

export const setOrientationLock = (on: boolean) => {
  localStorage.setItem(KEY, on ? "1" : "0");
  window.dispatchEvent(new Event("sp-orientation-change"));
  // Called from the settings toggle click → a user gesture is available, so a
  // fullscreen request (needed for the native lock to succeed on Android) is
  // allowed here. Best-effort; the CSS fallback covers everything else.
  apply(on, true);
};

function apply(on: boolean, fromGesture = false) {
  // 1) CSS fallback — always toggled; the media query only acts on
  //    touch devices in landscape, so desktop is never affected.
  document.documentElement.classList.toggle("orient-lock", on);

  // 2) Native API — best effort, never throws to the caller.
  const so: any = (screen as any).orientation;
  try {
    if (on) {
      const doLock = () => { if (so?.lock) so.lock("portrait").catch(() => {}); };
      const el: any = document.documentElement;
      // The native lock needs fullscreen on most Android browsers; only
      // attempt it from a real user gesture to avoid a console error spam.
      if (fromGesture && !document.fullscreenElement && el.requestFullscreen) {
        el.requestFullscreen().then(doLock).catch(doLock);
      } else {
        doLock();
      }
    } else {
      if (so?.unlock) so.unlock();
      if (document.fullscreenElement && document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
    }
  } catch { /* غير مدعوم — القفل CSS يكفي */ }
}

export function useOrientationLock() {
  useEffect(() => {
    // On mount (no gesture): apply the CSS fallback + a best-effort native
    // lock without requesting fullscreen.
    const sync = () => apply(getOrientationLock(), false);
    sync();
    window.addEventListener("sp-orientation-change", sync);
    return () => window.removeEventListener("sp-orientation-change", sync);
  }, []);
}
