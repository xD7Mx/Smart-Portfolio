import React, { useEffect, useLayoutEffect, useRef, useState } from "react";

/* ══ إعادةُ الترتيب بالضغط المطوّل ثمّ السحب ══ (بأمر المالك · D683)
   «اجعل البطاقات قابلةً للتحريك ولا تظهر أزرارُ التحريك — ضغطٌ مطوّل ثمّ تحريك». فلا مقبضَ ولا سهم: الضغطةُ المطوّلة
   (‏420 مل.ث بلا حركةٍ قاصدة) ترفع البطاقة، وما تمرّ عليه تأخذ موضعَه، والإفلاتُ يحفظ.
   على نمط سحب صفوف المحفظة (PortfolioPage) — وزاد عليه ثلاثة:
   · منعُ تمرير الصفحة أثناء السحب على الجوال بمستمعِ `touchmove` غيرِ سلبيّ: `touch-action` يُقرأ عند بدء اللمسة،
     فتغييرُه بعد الرفع لا يوقف تمريراً بدأ — فيُلغى التمريرُ نفسُه.
   · انزلاقُ البطاقات الأخرى إلى مواضعها الجديدة (FLIP) بدل القفز — ويُحترم تفضيلُ تقليل الحركة.
   · لا نقرةَ بعد الرفع: الضغطةُ المطوّلة ليست فتحاً للبطاقة.
   ولوحةُ المفاتيح: ‏Alt مع الأسهم تنقل البطاقةَ المركَّزة — بديلٌ بلا زرٍّ ظاهر. */
export function useLongPressSort<T>(items: T[], keyOf: (x: T) => string, onCommit: (next: T[]) => void,
                                    opts: { enabled?: boolean; delay?: number } = {}) {
  const { enabled = true, delay = 420 } = opts;
  const [order, setOrder] = useState<T[] | null>(null);
  const [dragKey, setDragKey] = useState<string | null>(null);
  const list = order ?? items;
  const listRef = useRef(list); listRef.current = list;
  const dragRef = useRef<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const start = useRef<{ x: number; y: number } | null>(null);
  const suppress = useRef(false);
  const edgeY = useRef(0);
  const boxRef = useRef<HTMLDivElement | null>(null);
  const pos = useRef(new Map<string, [number, number]>());
  /* ‏D687 (بأمر المالك: «ضع حركةً عند تمرير البطاقات لأنها قاسية»): البطاقةُ المرفوعة تتبع الإصبعَ نفسَه — كانت تقفز
     من خانةٍ إلى خانة — وتهبط إلى موضعها بانزلاقٍ عند الإفلات. والإزاحةُ تُكتب مباشرةً في العنصر (لا في حالة React)
     فلا يُعاد رسمُ الشبكة مع كلّ حركة، ويُحسب مركزُ البطاقة في الشبكة بطرح إزاحتها الحاليّة */
  const liftEl = useRef<HTMLElement | null>(null);
  const shift = useRef<[number, number]>([0, 0]);
  const grab = useRef<[number, number]>([0, 0]);
  const lastPt = useRef<[number, number] | null>(null);
  const centerOf = (el: HTMLElement): [number, number] => {
    const r = el.getBoundingClientRect();
    return [r.left + r.width / 2 - shift.current[0], r.top + r.height / 2 - shift.current[1]];
  };
  const place = () => {
    const el = liftEl.current, p = lastPt.current;
    if (!el || !p) return;
    const c = centerOf(el);
    shift.current = [p[0] - grab.current[0] - c[0], p[1] - grab.current[1] - c[1]];
    el.style.transform = `translate(${shift.current[0]}px, ${shift.current[1]}px) scale(1.04)`;
  };
  const land = () => {
    const el = liftEl.current;
    liftEl.current = null;
    if (!el) return;
    el.style.transition = "transform .24s cubic-bezier(.2,.8,.2,1)";
    el.style.transform = "";
    shift.current = [0, 0];
    setTimeout(() => { el.style.transition = ""; }, 260);
  };

  const disarm = () => { if (timer.current) { clearTimeout(timer.current); timer.current = null; } };
  const finish = (commit: boolean) => {
    disarm();
    if (dragRef.current == null) return;
    const next = listRef.current;
    land();
    dragRef.current = null;
    setDragKey(null);
    if (commit && next.map(keyOf).join("|") !== items.map(keyOf).join("|")) onCommit(next);
    setOrder(null);
  };

  /* التمريرُ يُلغى ما دامت البطاقةُ مرفوعة — ويُمرَّر الحاويةُ آلياً قرب حافّتيها */
  useEffect(() => {
    if (dragKey == null) return;
    const stop = (e: TouchEvent) => { if (e.cancelable) e.preventDefault(); };
    document.addEventListener("touchmove", stop, { passive: false });
    const box = (document.querySelector(".app-main") || document.scrollingElement) as HTMLElement | null;
    let raf = 0;
    const step = () => {
      const r = box?.getBoundingClientRect();
      const top = r ? r.top : 0, bottom = r ? r.bottom : window.innerHeight;
      const y = edgeY.current, m = 70;
      if (y > 0 && y - top < m) box?.scrollBy(0, -Math.ceil((m - (y - top)) / 5));
      else if (y > 0 && bottom - y < m) box?.scrollBy(0, Math.ceil((m - (bottom - y)) / 5));
      place();                                   // والتمريرُ الآليّ لا يفصل البطاقةَ عن الإصبع
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => { document.removeEventListener("touchmove", stop); cancelAnimationFrame(raf); };
  }, [dragKey]);

  /* FLIP: كلُّ بطاقةٍ غيرِ المرفوعة تنزلق من موضعها القديم — بإزاحتها داخل الشبكة لا في الشاشة، فلا يحرّكها التمرير */
  useLayoutEffect(() => {
    const box = boxRef.current;
    if (!box) return;
    // الشبكةُ مرجعُ إزاحات بطاقاتها (offsetParent) — فتُقاس الخاناتُ منها لا من أبٍ بعيد
    if (getComputedStyle(box).position === "static") box.style.position = "relative";
    const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    box.querySelectorAll<HTMLElement>("[data-sort-key]").forEach(el => {
      const k = el.dataset.sortKey as string;
      const now: [number, number] = [el.offsetLeft, el.offsetTop];
      const was = pos.current.get(k);
      if (was && !reduce && dragRef.current != null && k !== dragRef.current && (was[0] !== now[0] || was[1] !== now[1])) {
        el.animate?.([{ transform: `translate(${was[0] - now[0]}px, ${was[1] - now[1]}px)` }, { transform: "none" }],
                     { duration: 240, easing: "cubic-bezier(.2,.8,.2,1)" });
      }
      pos.current.set(k, now);
    });
    place();                                     // موضعُها في الشبكة تغيّر — وتبقى تحت الإصبع
  }, [list]);

  const move = (k: string, to: number) => {
    const cur = [...listRef.current];
    const i = cur.findIndex(x => keyOf(x) === k);
    if (i < 0 || to < 0 || to >= cur.length || i === to) return cur;
    cur.splice(to, 0, cur.splice(i, 1)[0]);
    return cur;
  };

  const itemProps = (k: string): React.HTMLAttributes<HTMLDivElement> & { "data-sort-key": string } => {
    if (!enabled) return { "data-sort-key": k };
    const lifted = dragKey === k;
    return {
      "data-sort-key": k,
      onPointerDown: (e) => {
        if (e.button !== 0 || order) return;
        disarm();
        suppress.current = false;
        start.current = { x: e.clientX, y: e.clientY };
        const el = e.currentTarget, id = e.pointerId;
        timer.current = setTimeout(() => {
          dragRef.current = k;
          suppress.current = true;
          liftEl.current = el;
          shift.current = [0, 0];
          const c = centerOf(el), p0 = start.current || { x: c[0], y: c[1] };
          grab.current = [p0.x - c[0], p0.y - c[1]];
          lastPt.current = [p0.x, p0.y];
          el.style.transition = "transform .15s";
          place();
          setTimeout(() => { if (liftEl.current === el) el.style.transition = ""; }, 160);
          setOrder(listRef.current);
          setDragKey(k);
          // أسرُ المؤشّر: تبقى الحركةُ تصل هذه البطاقة ولو خرج الإصبعُ عنها
          try { el.setPointerCapture(id); } catch { /* لا يدعمه كلُّ متصفّح */ }
          if (navigator.vibrate) navigator.vibrate(12);
        }, delay);
      },
      onPointerMove: (e) => {
        if (dragRef.current == null) {
          // اهتزازُ الإصبع الطبيعيّ لا يُلغي الضغطةَ المطوّلة — تُلغيها حركةٌ قاصدة (تمرير)
          const p = start.current;
          if (p && Math.hypot(e.clientX - p.x, e.clientY - p.y) > 10) disarm();
          return;
        }
        e.preventDefault();
        edgeY.current = e.clientY;
        lastPt.current = [e.clientX, e.clientY];
        place();
        // يُقرأ ما تحت الإصبع من **خانات الشبكة** لا من مواضع الرسم: البطاقةُ المرفوعة نفسُها تحته، والأخرى تنزلق
        // بحركتها (FLIP) — فاختبارُ المرسوم يقرأ بطاقةً في منتصف انزلاقها ويضعها خانةً قبل موضعها (قِيس)
        const box = boxRef.current;
        let target: string | null = null;
        if (box) {
          const br = box.getBoundingClientRect();
          for (const el of box.querySelectorAll<HTMLElement>("[data-sort-key]")) {
            if (el.dataset.sortKey === dragRef.current || el.offsetParent !== box) continue;
            const l = br.left + el.offsetLeft - box.scrollLeft, t = br.top + el.offsetTop - box.scrollTop;
            if (e.clientX >= l && e.clientX <= l + el.offsetWidth && e.clientY >= t && e.clientY <= t + el.offsetHeight) {
              target = el.dataset.sortKey as string; break;
            }
          }
        }
        if (!target || target === dragRef.current) return;
        const j = listRef.current.findIndex(x => keyOf(x) === target);
        setOrder(move(dragRef.current, j));
      },
      onPointerUp: () => { disarm(); finish(true); },
      onPointerCancel: () => { disarm(); finish(false); },
      onContextMenu: (e) => { if (timer.current || dragRef.current) e.preventDefault(); },
      onClickCapture: (e) => { if (suppress.current) { suppress.current = false; e.preventDefault(); e.stopPropagation(); } },
      onKeyDown: (e) => {
        if (!e.altKey) return;
        const i = listRef.current.findIndex(x => keyOf(x) === k);
        const d = e.key === "ArrowUp" || e.key === "ArrowRight" ? -1 : e.key === "ArrowDown" || e.key === "ArrowLeft" ? 1 : 0;
        if (!d) return;
        e.preventDefault();
        const next = move(k, i + d);
        if (next.map(keyOf).join("|") !== items.map(keyOf).join("|")) onCommit(next);
      },
      // لا تحديدَ نصٍّ ولا قائمةَ النظام عند الضغطة المطوّلة — فهي إشارةُ رفعٍ لا نسخ
      style: {
        WebkitTouchCallout: "none", WebkitUserSelect: "none", userSelect: "none",
        ...(lifted
          ? { position: "relative", zIndex: 20, cursor: "grabbing", willChange: "transform",
              boxShadow: "0 18px 36px -14px color-mix(in srgb, var(--ink) 40%, transparent), 0 0 0 1.5px var(--brand)",
              borderRadius: 16 }
          : {}),
      } as React.CSSProperties,
    };
  };

  return { list, dragKey, boxRef, itemProps };
}
