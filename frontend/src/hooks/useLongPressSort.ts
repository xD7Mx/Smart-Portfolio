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

  const disarm = () => { if (timer.current) { clearTimeout(timer.current); timer.current = null; } };
  const finish = (commit: boolean) => {
    disarm();
    if (dragRef.current == null) return;
    const next = listRef.current;
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
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => { document.removeEventListener("touchmove", stop); cancelAnimationFrame(raf); };
  }, [dragKey]);

  /* FLIP: كلُّ بطاقةٍ غيرِ المرفوعة تنزلق من موضعها القديم — بإزاحتها داخل الشبكة لا في الشاشة، فلا يحرّكها التمرير */
  useLayoutEffect(() => {
    const box = boxRef.current;
    if (!box) return;
    const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    box.querySelectorAll<HTMLElement>("[data-sort-key]").forEach(el => {
      const k = el.dataset.sortKey as string;
      const now: [number, number] = [el.offsetLeft, el.offsetTop];
      const was = pos.current.get(k);
      if (was && !reduce && dragRef.current != null && k !== dragRef.current && (was[0] !== now[0] || was[1] !== now[1])) {
        el.animate?.([{ transform: `translate(${was[0] - now[0]}px, ${was[1] - now[1]}px)` }, { transform: "none" }],
                     { duration: 180, easing: "cubic-bezier(.2,.8,.2,1)" });
      }
      pos.current.set(k, now);
    });
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
        const over = (document.elementFromPoint(e.clientX, e.clientY) as HTMLElement | null)?.closest("[data-sort-key]") as HTMLElement | null;
        const target = over && boxRef.current?.contains(over) ? over.dataset.sortKey : null;
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
          ? { position: "relative", zIndex: 20, transform: "scale(1.04)", cursor: "grabbing",
              boxShadow: "0 14px 32px -12px color-mix(in srgb, var(--ink) 35%, transparent), 0 0 0 1.5px var(--brand)",
              borderRadius: 16, transition: "transform .15s, box-shadow .15s" }
          : { transition: "transform .15s" }),
      } as React.CSSProperties,
    };
  };

  return { list, dragKey, boxRef, itemProps };
}
