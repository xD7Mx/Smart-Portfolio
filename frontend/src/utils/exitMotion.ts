/* ‏D616: حركةُ الإغلاق — بلاغُ المالك: القوائمُ المنسدلة ومفاتيحُ التفعيل وأزرارُ الإغلاق «قاسية».
   React يحذف النافذةَ أو القائمةَ من الصفحة فوراً، فتختفي بلا حركة. ولا يُعالَج ذلك في كلّ نافذةٍ
   على حدة (إحدى عشرةَ نافذةً وخمسُ قوائم): طبقةٌ واحدة ترقب الحذف، فتضع في موضع المحذوف نسخةً
   صامتةً منه (لا تُلمس ولا تُقرأ) تتلاشى في ١٧٠ م.ث ثمّ تزول. ويُحترم «تقليلُ الحركة». */
const IN_PLACE = ".modal-overlay, .menu-pop, .date-pop, .clock-pop, .drawer-pop";
const MS = 170;

export function installExitMotion(): () => void {
  if (typeof window === "undefined" || typeof MutationObserver === "undefined") return () => {};
  const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)");
  const ghost = (node: Element, parent: Node, before: Node | null) => {
    const c = node.cloneNode(true) as HTMLElement;
    c.classList.add("exit-anim");
    c.setAttribute("aria-hidden", "true");
    c.setAttribute("inert", "");
    try { parent.insertBefore(c, before && before.parentNode === parent ? before : null); } catch { return; }
    window.setTimeout(() => c.remove(), MS + 30);
  };
  const obs = new MutationObserver(muts => {
    if (reduced?.matches) return;
    for (const m of muts) {
      m.removedNodes.forEach(n => {
        if (!(n instanceof HTMLElement) || n.classList.contains("exit-anim")) return;
        if (n.matches(IN_PLACE)) { if (m.target.isConnected) ghost(n, m.target, m.nextSibling); return; }
        // النافذةُ داخل غلافٍ حُذف معها: تُنسخ وحدها إلى جسم الصفحة (هي ثابتةُ الموضع أصلاً)
        const ov = n.querySelector?.(".modal-overlay");
        if (ov && n.childElementCount <= 3) ghost(ov, document.body, null);
      });
    }
  });
  obs.observe(document.body, { childList: true, subtree: true });
  return () => obs.disconnect();
}
