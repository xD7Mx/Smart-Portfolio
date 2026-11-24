/* ══ مبدّلُ الشاشات ══ (‏D801 · ‏D803 · ‏D804 — المالك 2026-11-24)
   «زرُّ تقسيم الشاشات بجانب الإطارات — لا آخرَ شيءٍ على اليسار»: يوضع في شريط الرسم بعد أزرار الإطارات مباشرة.
   «الثلاثُ: واحدةٌ بالعرض فوق واثنتان تحت بجانب بعض — أجملُ: الشارتُ الكبيرُ فوق وتحته العقدُ كول أو بوت»: ترتيبان للثلاث.
   «أحفظ إعداداً مخصّصاً (ثلاثُ شاشاتٍ لشركاتٍ معيّنة) ثابتاً في المفضّلة — مكانُه شاشةُ الإطارات هذه: شاشتان… تخصيص، ثمّ المفضّلةُ مع زرّ مسح».
   النافذةُ فوق كلّ شيء (‏portal) تحت زرّها داخل الشاشة، وتُطوى بالنقر خارجها أو بـEsc — بانسياب. */
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Check, Columns2, Grid2x2, LayoutPanelLeft, LayoutPanelTop, Square, Trash2, BookmarkPlus, Bookmark } from "lucide-react";

export type Var3 = "side" | "top";
export type Preset = { id: string; name: string; n: number; v3: Var3; syms: (string | null)[]; tfs: (string | null)[]; a: number; b: number };

const ITEMS: { n: number; v3?: Var3; name: string; Ic: typeof Square; flip?: boolean }[] = [
  { n: 1, name: "شاشةٌ واحدة", Ic: Square },
  { n: 2, name: "شاشتان", Ic: Columns2 },
  { n: 3, v3: "side", name: "ثلاثٌ — كبيرةٌ وبجانبها اثنتان", Ic: LayoutPanelLeft, flip: true },
  { n: 3, v3: "top", name: "ثلاثٌ — كبيرةٌ فوق واثنتان تحت", Ic: LayoutPanelTop },
  { n: 4, name: "أربعُ شاشات", Ic: Grid2x2 },
];

export default function LayoutMenu({ n, v3, onPick, presets, onApply, onDelete, onSave, suggest }: {
  n: number; v3: Var3; onPick: (n: number, v3?: Var3) => void;
  presets: Preset[]; onApply: (p: Preset) => void; onDelete: (id: string) => void; onSave: (name: string) => void; suggest: () => string;
}) {
  const [open, setOpen] = useState(false);
  const [naming, setNaming] = useState<string | null>(null);
  const wrap = useRef<HTMLSpanElement>(null), btn = useRef<HTMLButtonElement>(null), pop = useRef<HTMLDivElement>(null), inp = useRef<HTMLInputElement>(null);
  const [at, setAt] = useState<{ left: number; top: number; maxH: number } | null>(null);
  const place = useCallback(() => {
    const b = btn.current?.getBoundingClientRect(), p = pop.current;
    if (!b || !p) return;
    const vw = document.documentElement.clientWidth, vh = window.innerHeight, w = p.offsetWidth, M = 8;
    const left = Math.min(Math.max(M, b.right - w), Math.max(M, vw - w - M));
    const top = Math.min(b.bottom + 6, Math.max(M, vh - 160));
    setAt({ left, top, maxH: Math.max(160, vh - top - M) });
  }, []);
  useLayoutEffect(() => { if (open) place(); else { setAt(null); setNaming(null); } }, [open, place, presets.length, naming != null]);
  useEffect(() => {
    if (!open) return;
    const away = (e: Event) => { const t = e.target as Node; if (!wrap.current?.contains(t) && !pop.current?.contains(t)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); setOpen(false); } };
    document.addEventListener("pointerdown", away);
    window.addEventListener("keydown", esc, true);
    window.addEventListener("resize", place);
    document.addEventListener("scroll", place, true);
    return () => { document.removeEventListener("pointerdown", away); window.removeEventListener("keydown", esc, true);
      window.removeEventListener("resize", place); document.removeEventListener("scroll", place, true); };
  }, [open, place]);
  useEffect(() => { if (naming != null) inp.current?.focus(); }, [naming != null]);
  const cur = ITEMS.find(i => i.n === n && (n !== 3 || i.v3 === v3)) || ITEMS[0];
  const save = () => { const nm = (naming || "").trim() || suggest(); onSave(nm); setNaming(null); };

  return (
    <span ref={wrap} className="troom-layw">
      <button ref={btn} type="button" className={"pc-btn troom-lay-btn" + (open ? " on" : "")} aria-expanded={open} aria-haspopup="menu"
        onClick={() => setOpen(v => !v)} data-role="troom-layout" title="تقسيمُ الشاشة" aria-label="تقسيمُ الشاشة">
        <cur.Ic size={15} className={cur.flip ? "troom-flip" : undefined} /><span>الشاشات</span>
      </button>
      {open && createPortal(
        <div ref={pop} className="troom-laymenu" role="menu" dir="rtl" data-role="troom-layout-menu"
          style={at ? { left: at.left, top: at.top, maxHeight: at.maxH } : { left: 0, top: 0, visibility: "hidden" }}>
          {ITEMS.map(it => {
            const on = it.n === n && (it.n !== 3 || it.v3 === v3);
            return (
              <button key={it.name} type="button" role="menuitemradio" aria-checked={on} className={"troom-layitem" + (on ? " on" : "")}
                data-layout={it.n} data-var={it.v3 || ""} onClick={() => { onPick(it.n, it.v3); setOpen(false); }}>
                <it.Ic size={15} className={it.flip ? "troom-flip" : undefined} /><span>{it.name}</span>{on && <Check size={14} className="troom-laycheck" />}
              </button>
            );
          })}
          <div className="troom-laysep" role="separator" />
          <span className="troom-laycap">المفضّلة</span>
          {presets.length === 0 && <span className="troom-layempty">لا تخصيصَ محفوظاً بعد</span>}
          {presets.map(p => (
            <div key={p.id} className="troom-preset" data-role="troom-preset" data-id={p.id}>
              <button type="button" role="menuitem" className="troom-layitem troom-preset-go" onClick={() => { onApply(p); setOpen(false); }}
                data-role="troom-preset-go" title={p.name}>
                <Bookmark size={14} /><span className="troom-preset-name">{p.name}</span>
              </button>
              <button type="button" className="troom-preset-del" onClick={() => onDelete(p.id)} data-role="troom-preset-del"
                title={`امسح «${p.name}»`} aria-label={`امسح «${p.name}»`}><Trash2 size={14} /></button>
            </div>
          ))}
          {naming == null ? (
            <button type="button" className="troom-layitem troom-preset-add" onClick={() => setNaming(suggest())} data-role="troom-preset-add">
              <BookmarkPlus size={15} /><span>تخصيص — احفظ الشاشاتِ الحاليّةَ في المفضّلة</span>
            </button>
          ) : (
            <div className="troom-preset-form" data-role="troom-preset-form">
              <input ref={inp} className="input" value={naming} maxLength={60} onChange={e => setNaming(e.target.value)} aria-label="اسمُ التخصيص"
                onKeyDown={e => { if (e.key === "Enter") save(); }} data-role="troom-preset-name" />
              <button type="button" className="btn-primary troom-preset-save" onClick={save} data-role="troom-preset-save">حفظ</button>
            </div>
          )}
        </div>,
        document.body,
      )}
    </span>
  );
}
