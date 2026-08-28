/**
 * تسجيل Service Worker + تدفّق التحديث.
 *
 * فلسفة التحديث: لا نُحدّث تحت قدم المستخدم أثناء عمله (قد يكون في منتصف
 * إدخال صفقة). نكتشف النسخة الجديدة، ونُبلغه بإشعار لطيف، والتفعيل لا يقع
 * إلا بموافقته — ثم تُعاد الصفحة مرّة واحدة.
 *
 * ملاحظة أمان بيانات: الـSW لا يُخزّن أي طلب /api/ إطلاقاً (انظر public/sw.js)،
 * فلا يمكن أن يعرض رصيداً أو سعراً قديماً كأنه حيّ.
 */

const UPDATE_EVENT = "sp:update-ready";

export function registerSW() {
  if (!("serviceWorker" in navigator)) return;
  // التسجيل بعد اكتمال التحميل كي لا ينافس أول رسم للصفحة.
  window.addEventListener("load", async () => {
    try {
      const reg = await navigator.serviceWorker.register("/sw.js");

      // نسخة جديدة تنتظر التفعيل
      const notify = () => window.dispatchEvent(new CustomEvent(UPDATE_EVENT, { detail: reg }));
      if (reg.waiting) notify();
      reg.addEventListener("updatefound", () => {
        const sw = reg.installing;
        if (!sw) return;
        sw.addEventListener("statechange", () => {
          // "installed" مع وجود controller ⇒ تحديث لا تثبيت أول.
          if (sw.state === "installed" && navigator.serviceWorker.controller) notify();
        });
      });

      // إعادة تحميل واحدة عند تبديل النسخة (بعد موافقة المستخدم).
      // ولا تقع الإعادة والصفحةُ معروضة: كان تبديلُ النسخة يُعيد التحميل
      // متى وقع، ومنه ما يقع عند العودة من رابطٍ خارجيّ — فيجد المالك
      // تطبيقه قد أُقلع من أوّله وفقد موضعه بلا سبب يراه. فتُؤجَّل
      // الإعادة إلى أن تُخفى الصفحة: عندها لا يرى أحدٌ إعادةً ولا يفقد
      // موضعاً، ويكون التطبيق حين يعود على النسخة الجديدة.
      let reloaded = false;
      const reloadWhenHidden = () => {
        if (reloaded) return;
        if (document.visibilityState === "hidden") {
          reloaded = true;
          window.location.reload();
        }
      };
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        if (reloaded) return;
        reloadWhenHidden();
        document.addEventListener("visibilitychange", reloadWhenHidden);
      });

      // فحص دوري لوجود نسخة أحدث (كل ساعة) — بلا إزعاج.
      setInterval(() => reg.update().catch(() => {}), 60 * 60 * 1000);
    } catch {
      /* التسجيل اختياري: التطبيق يعمل كاملاً بدونه */
    }
  });
}

export { UPDATE_EVENT };
