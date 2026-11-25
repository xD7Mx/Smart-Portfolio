/* ‏D828 (المالك 2026-11-25): «عرضُ التقرير على الكمبيوتر ممتازٌ ولا غلطة، أمّا على الجوال فيحتاج توحيدَ المقاسات مع مراعاة صغر شاشة الجوال —
   لازم يكون واضحاً على الجوال». كانت الورقةُ (‏A4 بعرض الحاسوب) تُصغَّر إلى عرض الهاتف (‏≈39٪) فيصير الخطُّ نحو 4px لا يُقرأ.
   فقارئٌ بملء الشاشة بالورقة نفسِها (الشكلُ ذاتُه — لا تخطيطَ آخر): تبدأ بعرض الشاشة، وتُكبَّر بإصبعين أو بنقرتين حيث تقرأ (حتى مقاس الطباعة
   وأكبر) أو بالأزرار، وتُسحب في الاتّجاهين؛ والفتحُ والإغلاقُ والتكبيرُ بانسيابية تحترم تقليلَ الحركة. */
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

type Props = { html: string; width: number; title: string; onClose: () => void; fit: (d: Document) => void };

const MAX_Z = 1.6;
const reduced = () => { try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; } };

export default function PaperReader({ html, width, title, onClose, fit }: Props) {
  const box = useRef<HTMLDivElement | null>(null);
  const frame = useRef<HTMLIFrameElement | null>(null);
  const [vw, setVw] = useState(() => window.innerWidth);
  const fitZ = Math.min(1, Math.max(0.2, (vw - 12) / width));
  const [z, setZ] = useState(fitZ);
  const zRef = useRef(z);
  const [h, setH] = useState(1200);
  const [shown, setShown] = useState(false);
  const pendingScroll = useRef<{ l: number; t: number } | null>(null);
  const anim = useRef(0);

  /* التكبيرُ حول نقطة: النقطةُ من الورقة تحت الإصبع تبقى تحته */
  const zoomTo = useCallback((nz: number, ax?: number, ay?: number, z0?: number, sl?: number, st?: number) => {
    const el = box.current;
    if (!el) return;
    const from = z0 ?? zRef.current;
    const to = Math.max(fitZ, Math.min(MAX_Z, nz));
    const cx = ax ?? el.clientWidth / 2, cy = ay ?? el.clientHeight / 2;
    const px = ((sl ?? el.scrollLeft) + cx) / from, py = ((st ?? el.scrollTop) + cy) / from;
    zRef.current = to;
    pendingScroll.current = { l: px * to - cx, t: py * to - cy };
    setZ(to);
  }, [fitZ]);
  const animateTo = useCallback((nz: number, ax?: number, ay?: number) => {
    const el = box.current;
    if (!el) return;
    cancelAnimationFrame(anim.current);
    const z0 = zRef.current, sl = el.scrollLeft, st = el.scrollTop, t0 = performance.now(), D = reduced() ? 0 : 200;
    const step = (t: number) => {
      const k = D ? Math.min(1, (t - t0) / D) : 1, e = 1 - Math.pow(1 - k, 3);
      zoomTo(z0 + (nz - z0) * e, ax, ay, z0, sl, st);
      if (k < 1) anim.current = requestAnimationFrame(step);
    };
    anim.current = requestAnimationFrame(step);
  }, [zoomTo]);

  useLayoutEffect(() => {
    const el = box.current, p = pendingScroll.current;
    if (el && p) { el.scrollLeft = p.l; el.scrollTop = p.t; pendingScroll.current = null; }
  }, [z]);

  /* الفتحُ: ظهورٌ بانسيابية، والصفحةُ خلفه لا تتحرّك، و«Esc» يغلق */
  const close = useCallback(() => { setShown(false); window.setTimeout(onClose, reduced() ? 0 : 200); }, [onClose]);
  useEffect(() => {
    const r = requestAnimationFrame(() => setShown(true));
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopImmediatePropagation(); close(); } };
    const rs = () => setVw(window.innerWidth);
    window.addEventListener("keydown", k, true);
    window.addEventListener("resize", rs);
    return () => { cancelAnimationFrame(r); document.body.style.overflow = prev; window.removeEventListener("keydown", k, true); window.removeEventListener("resize", rs); };
  }, [close]);
  useEffect(() => { if (zRef.current < fitZ) { zRef.current = fitZ; setZ(fitZ); } }, [fitZ]);

  /* الإصبعان يكبّران، والنقرتان تبدّلان بين عرض الشاشة ومقاس الطباعة حيث نُقر؛ والإصبعُ الواحدُ يسحب (تمريرُ المتصفّح نفسِه) */
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    let pinch: { d: number; z: number; cx: number; cy: number; sl: number; st: number } | null = null;
    let tap: { x: number; y: number; t: number } | null = null, moved = false, sx = 0, sy = 0;
    const dist = (t: TouchList) => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
    const onStart = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        cancelAnimationFrame(anim.current);
        const r = el.getBoundingClientRect();
        pinch = { d: dist(e.touches), z: zRef.current, cx: (e.touches[0].clientX + e.touches[1].clientX) / 2 - r.left,
                  cy: (e.touches[0].clientY + e.touches[1].clientY) / 2 - r.top, sl: el.scrollLeft, st: el.scrollTop };
      } else if (e.touches.length === 1) { moved = false; sx = e.touches[0].clientX; sy = e.touches[0].clientY; }
    };
    const onMove = (e: TouchEvent) => {
      if (pinch && e.touches.length === 2) { e.preventDefault(); zoomTo(pinch.z * dist(e.touches) / pinch.d, pinch.cx, pinch.cy, pinch.z, pinch.sl, pinch.st); }
      else if (e.touches.length === 1 && Math.hypot(e.touches[0].clientX - sx, e.touches[0].clientY - sy) > 8) moved = true;
    };
    const onEnd = (e: TouchEvent) => {
      if (e.touches.length < 2) pinch = null;
      if (e.touches.length || moved || e.changedTouches.length !== 1) return;
      const c = e.changedTouches[0], r = el.getBoundingClientRect(), now = performance.now();
      if (tap && now - tap.t < 320 && Math.hypot(c.clientX - tap.x, c.clientY - tap.y) < 30) {
        e.preventDefault();
        animateTo(zRef.current > fitZ + 0.05 ? fitZ : 1, c.clientX - r.left, c.clientY - r.top);
        tap = null;
      } else tap = { x: c.clientX, y: c.clientY, t: now };
    };
    el.addEventListener("touchstart", onStart, { passive: false });
    el.addEventListener("touchmove", onMove, { passive: false });
    el.addEventListener("touchend", onEnd, { passive: false });
    return () => { el.removeEventListener("touchstart", onStart); el.removeEventListener("touchmove", onMove); el.removeEventListener("touchend", onEnd); };
  }, [zoomTo, animateTo, fitZ]);

  const onLoad = () => {
    const d = frame.current?.contentDocument;
    if (!d?.body) return;
    fit(d);
    setH(Math.max(400, d.documentElement.scrollHeight));
  };
  const pct = Math.round(z * 100);

  return createPortal(
    <div className="prd" data-shown={shown ? "1" : "0"} role="dialog" aria-modal="true" aria-label={`قارئ ${title}`} data-role="rl-reader" data-z={z.toFixed(3)}>
      <div className="prd-bar" dir="rtl">
        <b className="prd-t">{title}</b>
        <span className="prd-zoom">
          <button type="button" className="prd-btn" onClick={() => animateTo(zRef.current / 1.3)} disabled={z <= fitZ + 0.001} aria-label="تصغير" data-role="rl-zout"><ZoomOut size={17} /></button>
          <b className="prd-pct" dir="ltr" data-role="rl-zpct">{pct}%</b>
          <button type="button" className="prd-btn" onClick={() => animateTo(zRef.current * 1.3)} disabled={z >= MAX_Z - 0.001} aria-label="تكبير" data-role="rl-zin"><ZoomIn size={17} /></button>
          <button type="button" className="prd-btn" onClick={() => animateTo(fitZ)} aria-label="بعرض الشاشة" data-role="rl-zfit"><Maximize2 size={16} /></button>
        </span>
        <button type="button" className="prd-btn prd-x" onClick={close} aria-label="إغلاق" data-role="rl-reader-close"><X size={18} /></button>
      </div>
      <div ref={box} className="prd-box" dir="ltr" data-role="rl-reader-box">
        <div className="prd-sheet" style={{ width: Math.ceil(width * z), height: Math.ceil(h * z) }}>
          <iframe ref={frame} title={title} srcDoc={html} sandbox="allow-same-origin" onLoad={onLoad} scrolling="no"
            style={{ width, height: h, transform: `scale(${z})` }} />
          <div className="prd-catch" aria-hidden="true" />
        </div>
      </div>
    </div>,
    document.body,
  );
}
