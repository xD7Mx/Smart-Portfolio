/* ══ فواصلُ الشاشات تُسحب ══ (‏D803 — المالك 2026-11-24)
   «أبغى خيار تكبير وتمديد — أتحكّم في النافذة: إذا خلّيتُها ثلاثاً أمدّد واحدةً وأنقص، أكبّرها إلى الأسفل والأعلى واليمين واليسار… مرونة».
   فاصلٌ رأسيٌّ بين العمودين وأفقيٌّ بين الصفّين، يُسحب بالفأرة (أو بالأسهم من لوحة المفاتيح) فيتغيّر نصيبُ كلّ شاشة، ويُحفظ عند الإفلات؛
   والنقرُ المزدوج يعيده إلى الأصل. موضعُه يُقاس من الشاشات نفسِها (لا يُخمَّن)، وعلى الحاسوب وحده — الجوالُ شاشاتٌ متتالية. */
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Var3 } from "./LayoutMenu";

type Geo = { v?: { x: number; y: number; h: number }; h?: { x: number; y: number; w: number } };
const clampR = (v: number) => Math.min(0.75, Math.max(0.25, v));

export default function PaneSplitters({ grid, n, v3, a, b, onChange, onCommit, onReset }: {
  grid: React.RefObject<HTMLDivElement | null>; n: number; v3: Var3; a: number; b: number;
  onChange: (part: { a?: number; b?: number }) => void; onCommit: () => void; onReset: () => void;
}) {
  const [geo, setGeo] = useState<Geo | null>(null);
  const [drag, setDrag] = useState<"v" | "h" | null>(null);
  const raf = useRef(0);
  useLayoutEffect(() => {
    const g = grid.current;
    if (!g) return;
    const measure = () => {
      if (window.innerWidth < 1024) { setGeo(null); return; }
      const gr = g.getBoundingClientRect();
      const ps = [...g.querySelectorAll<HTMLElement>(':scope > [data-role="troom-pane"]')].map(p => p.getBoundingClientRect());
      if (ps.length < n) return;
      const X = (r: DOMRect) => Math.round(r.left - gr.left), Y = (r: DOMRect) => Math.round(r.bottom - gr.top);
      const out: Geo = {};
      if (n === 2) out.v = { x: X(ps[0]), y: 0, h: Math.round(gr.height) };
      if (n === 4) { out.v = { x: X(ps[0]), y: 0, h: Math.round(gr.height) }; out.h = { x: 0, y: Y(ps[0]), w: Math.round(gr.width) }; }
      if (n === 3 && v3 === "side") {
        out.v = { x: X(ps[0]), y: 0, h: Math.round(gr.height) };
        out.h = { x: Math.round(ps[1].left - gr.left), y: Y(ps[1]), w: Math.round(ps[1].width) };
      }
      if (n === 3 && v3 === "top") {
        out.h = { x: 0, y: Y(ps[0]), w: Math.round(gr.width) };
        out.v = { x: X(ps[1]), y: Math.round(ps[1].top - gr.top), h: Math.round(ps[1].height) };
      }
      setGeo(o => (JSON.stringify(o) === JSON.stringify(out) ? o : out));
    };
    measure();
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(measure) : null;
    ro?.observe(g);
    g.querySelectorAll(':scope > [data-role="troom-pane"]').forEach(p => ro?.observe(p));
    window.addEventListener("resize", measure);
    return () => { ro?.disconnect(); window.removeEventListener("resize", measure); };
  }, [grid, n, v3, a, b]);
  useEffect(() => () => cancelAnimationFrame(raf.current), []);
  if (!geo || n < 2) return null;

  const ratioAt = (kind: "v" | "h", e: { clientX: number; clientY: number }) => {
    const g = grid.current!;
    const gr = g.getBoundingClientRect();
    if (kind === "v") return clampR((gr.right - e.clientX) / gr.width);                    // العمودُ الأوّلُ يمينٌ في العربية
    if (n === 3 && v3 === "side") {
      const ps = g.querySelectorAll<HTMLElement>(':scope > [data-role="troom-pane"]');
      const t = ps[1].getBoundingClientRect().top, bt = ps[2].getBoundingClientRect().bottom;
      return clampR((e.clientY - t) / Math.max(1, bt - t));
    }
    return clampR((e.clientY - gr.top) / gr.height);
  };
  const down = (kind: "v" | "h") => (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    setDrag(kind);
  };
  const move = (kind: "v" | "h") => (e: React.PointerEvent<HTMLDivElement>) => {
    if (drag !== kind) return;
    const r = ratioAt(kind, e);
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(() => onChange(kind === "v" ? { a: r } : { b: r }));
  };
  const up = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!drag) return;
    try { (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId); } catch { /* */ }
    setDrag(null); onCommit();
  };
  const key = (kind: "v" | "h") => (e: React.KeyboardEvent<HTMLDivElement>) => {
    const step = 0.05, cur = kind === "v" ? a : b;
    const d = kind === "v" ? (e.key === "ArrowLeft" ? step : e.key === "ArrowRight" ? -step : 0) : (e.key === "ArrowDown" ? step : e.key === "ArrowUp" ? -step : 0);
    if (!d) return;
    e.preventDefault();
    onChange(kind === "v" ? { a: clampR(cur + d) } : { b: clampR(cur + d) }); onCommit();
  };
  const one = (kind: "v" | "h") => {
    const g = kind === "v" ? geo.v : geo.h;
    if (!g) return null;
    const style = kind === "v" ? { left: g.x - 6, top: g.y, height: (g as any).h } : { left: g.x, top: (g as any).y - 6, width: (g as any).w };
    return (
      <div key={kind} className={`troom-split ${kind}` + (drag === kind ? " on" : "")} style={style} role="separator" tabIndex={0}
        aria-orientation={kind === "v" ? "vertical" : "horizontal"} aria-valuemin={25} aria-valuemax={75}
        aria-valuenow={Math.round((kind === "v" ? a : b) * 100)} aria-label={kind === "v" ? "اسحب لتغيير عرض الشاشات" : "اسحب لتغيير ارتفاع الشاشات"}
        title="اسحب للتكبير والتصغير — نقرتان تعيدانه" data-role={`troom-split-${kind}`}
        onPointerDown={down(kind)} onPointerMove={move(kind)} onPointerUp={up} onPointerCancel={up} onKeyDown={key(kind)}
        onDoubleClick={() => onReset()}>
        <i aria-hidden />
      </div>
    );
  };
  return <>{one("v")}{one("h")}</>;
}
