/* ══ منتقي الألوان كتريدنق فيو ══ (‏D798 · المالك 2026-11-24)
   «خلّ في إعدادات المؤشّرات ألواناً رئيسيةً — الأبيض والأصفر والأحمر والأخضر والمتشبّعة — نفسَ اللي في تريدنق فيو، عشان يكون سهلاً نختار منها».
   لوحةٌ من أربعة صفوف (رماديّات · مشبعة · فاتحة · داكنة) من رموز ‏globals.css (‏--tvp-*، واحدةٌ في المظهرين كلوحة الرسم)، و«مخصَّص» لمن أراد
   غيرها، و«الافتراضيّ» يعيد لونَ المظهر. والنافذةُ تنفتح تحت زرّها وتُطوى بالنقر خارجها أو بـEsc — بانسياب.
   ‏D798ب (لجنةُ الكشف): كانت اللوحةُ محمولةً تحت زرّها داخل نافذة الإعدادات (‏overflow: auto) — فزرُّ العمود الأيمن يفتحها خارج النافذة فتُقصّ
   ألوانُها اليسرى ولا تُلمس. فصارت فوق كلّ شيء (‏portal) بموضعٍ يُحسب من زرّها ويُحصر داخل الشاشة، فوقه إن ضاق ما تحته، ويتبعه إن مُرِّرت النافذة. */
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Check, RotateCcw } from "lucide-react";

export const PALETTE: string[] = Array.from({ length: 40 }, (_, i) => `--tvp-${i + 1}`);

/** قيمةُ الرمز بصيغة ‏#rrggbb — اللونُ المحفوظُ قيمةٌ لا رمز، فيُرسم على اللوحة (‏canvas) كما اختير */
export function tokenHex(name: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (/^#[0-9a-f]{6}$/i.test(v)) return v.toLowerCase();
  if (/^#[0-9a-f]{3}$/i.test(v)) return ("#" + v.slice(1).split("").map(c => c + c).join("")).toLowerCase();
  const m = v.match(/\d+(\.\d+)?/g);
  return m && m.length >= 3 ? "#" + m.slice(0, 3).map(n => Math.round(+n).toString(16).padStart(2, "0")).join("") : "#000000";
}

export default function ColorPick({ label, value, fallback, onChange }: {
  label: string; value: string; fallback: string; onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null), btn = useRef<HTMLButtonElement>(null), pop = useRef<HTMLSpanElement>(null);
  const [at, setAt] = useState<{ left: number; top: number } | null>(null);
  const place = useCallback(() => {
    const b = btn.current?.getBoundingClientRect(), p = pop.current;
    if (!b || !p) return;
    const vw = document.documentElement.clientWidth, vh = window.innerHeight, w = p.offsetWidth, h = p.offsetHeight, M = 8;
    const left = Math.min(Math.max(M, b.right - w), Math.max(M, vw - w - M));          // حافّتُها اليمنى على حافّة الزرّ — داخل الشاشة
    const below = b.bottom + 6, above = b.top - 6 - h;
    const top = below + h <= vh - M ? below : above >= M ? above : Math.max(M, vh - h - M);
    setAt(o => (o && o.left === left && o.top === top ? o : { left, top }));
  }, []);
  useLayoutEffect(() => { if (open) place(); else setAt(null); }, [open, place]);
  useEffect(() => {
    if (!open) return;
    const away = (e: Event) => { const t = e.target as Node; if (!ref.current?.contains(t) && !pop.current?.contains(t)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); setOpen(false); } };
    document.addEventListener("pointerdown", away);
    window.addEventListener("keydown", esc, true);
    window.addEventListener("resize", place);
    document.addEventListener("scroll", place, true);
    return () => { document.removeEventListener("pointerdown", away); window.removeEventListener("keydown", esc, true);
      window.removeEventListener("resize", place); document.removeEventListener("scroll", place, true); };
  }, [open, place]);
  const cur = (value || fallback || "#000000").toLowerCase();
  return (
    <span ref={ref} className="cp" data-role="color-pick">
      <button ref={btn} type="button" className="cp-btn" aria-label={`${label}: ${cur}`} aria-expanded={open} title={label}
        onClick={() => setOpen(o => !o)} data-role="color-pick-btn">
        <i style={{ background: cur }} aria-hidden />
      </button>
      {open && createPortal(
        <span ref={pop} className="cp-pop" role="dialog" aria-label={label} data-role="color-pick-pop" dir="rtl"
          style={at ? { left: at.left, top: at.top } : { left: 0, top: 0, visibility: "hidden" }}>
          <span className="cp-grid">
            {PALETTE.map(t => {
              const hx = tokenHex(t), on = hx === cur;
              return (
                <button key={t} type="button" className={"cp-sw" + (on ? " on" : "")} aria-pressed={on} aria-label={hx}
                  onClick={() => { onChange(hx); setOpen(false); }} data-hex={hx}>
                  <i style={{ background: `var(${t})` }} aria-hidden />{on && <Check size={12} strokeWidth={3} />}
                </button>
              );
            })}
          </span>
          <span className="cp-foot">
            <label className="cp-custom">
              <input type="color" value={cur} aria-label={`${label} — لونٌ مخصَّص`} onChange={e => onChange(e.target.value.toLowerCase())} />
              <span>مخصَّص</span>
            </label>
            {value && (
              <button type="button" className="cp-reset" onClick={() => { onChange(""); setOpen(false); }} data-role="color-pick-reset">
                <RotateCcw size={13} /> الافتراضيّ
              </button>
            )}
          </span>
        </span>,
        document.body,
      )}
    </span>
  );
}

/** نقرُ الخلفية يُغلق النافذةَ إن بدأ الضغطُ عليها وانتهى عليها — لا لمسةٌ بدأت داخلها (سحبٌ أو منتقٍ أصيلٌ يُغلَق) فانتهت خارجها */
export function useBackdropClose(onClose: () => void) {
  const down = useRef(false);
  return {
    onPointerDown: (e: React.PointerEvent) => { down.current = e.target === e.currentTarget; },
    onClick: (e: React.MouseEvent) => { if (down.current && e.target === e.currentTarget) onClose(); down.current = false; },
  };
}
