import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ChevronDown, Check } from "lucide-react";

/* ‏D617: قائمةٌ منسدلةٌ مرسومة بدل <select> الأصليّ — بلاغُ المالك: «عند تغيير المحفظة في مختبر الأبحاث
   تظهر القائمةُ بعنفٍ وبشكلٍ قبيح». نافذةُ <select> يرسمها نظامُ الجهاز لا الصفحة، فلا تُحرَّك ولا تُصمَّم.
   بديلٌ يُركَّب مكانه حرفياً: الأبناءُ <option> كما هي، و`onChange` يستلم `{ target: { value } }` كما كان.
   تنفتح من حافّتها وتتلاشى عند الإغلاق (menu-pop)، وتُموضَع ثابتةً فلا يقصّها صندوقٌ حاويها،
   وتُقاد بلوحة المفاتيح (الأسهم · Enter · Esc). */
type Opt = { value: string; label: React.ReactNode; text: string; disabled?: boolean };
type Props = {
  value: string | number | null | undefined;
  onChange?: (e: { target: { value: string } }) => void;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  disabled?: boolean;
  title?: string;
  "aria-label"?: string;
};

const textOf = (n: React.ReactNode): string =>
  typeof n === "string" || typeof n === "number" ? String(n)
  : Array.isArray(n) ? n.map(textOf).join("")
  : React.isValidElement(n) ? textOf((n.props as any).children) : "";

function collect(children: React.ReactNode, out: Opt[] = []): Opt[] {
  React.Children.forEach(children, ch => {
    if (!React.isValidElement(ch)) return;
    const p: any = ch.props;
    if (ch.type === "option") {
      const text = textOf(p.children);
      out.push({ value: p.value !== undefined ? String(p.value) : text, label: p.children, text, disabled: !!p.disabled });
    } else if (p?.children) collect(p.children, out);
  });
  return out;
}

export default function Select({ value, onChange, children, className = "", style, disabled, title, ...rest }: Props) {
  const opts = collect(children);
  const cur = String(value ?? "");
  const sel = opts.find(o => o.value === cur);
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const [pos, setPos] = useState<{ top: number; left: number; width: number; up: boolean }>({ top: 0, left: 0, width: 0, up: false });
  const btn = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (!open || !btn.current) return;
    const r = btn.current.getBoundingClientRect();
    const up = window.innerHeight - r.bottom < 240 && r.top > 240;
    setPos({ top: up ? r.top - 6 : r.bottom + 6, left: r.left, width: Math.max(r.width, 160), up });
    setHi(Math.max(0, opts.findIndex(o => o.value === cur)));
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!btn.current?.contains(t) && !list.current?.contains(t)) setOpen(false);
    };
    const away = (e: Event) => { if (!list.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", off);
    window.addEventListener("scroll", away, true);
    window.addEventListener("resize", away);
    return () => {
      document.removeEventListener("mousedown", off);
      window.removeEventListener("scroll", away, true);
      window.removeEventListener("resize", away);
    };
  }, [open]);

  useEffect(() => { if (open) list.current?.querySelector<HTMLElement>(`[data-i="${hi}"]`)?.scrollIntoView({ block: "nearest" }); }, [hi, open]);

  const pick = (o: Opt) => {
    if (o.disabled) return;
    setOpen(false);
    if (o.value !== cur) onChange?.({ target: { value: o.value } });
    btn.current?.focus();
  };
  const step = (d: number) => {
    let i = hi;
    for (let k = 0; k < opts.length; k++) { i = (i + d + opts.length) % opts.length; if (!opts[i].disabled) break; }
    setHi(i);
  };
  const onKey = (e: React.KeyboardEvent) => {
    if (disabled) return;
    if (!open && ["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) { e.preventDefault(); setOpen(true); return; }
    if (!open) return;
    if (e.key === "ArrowDown") { e.preventDefault(); step(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); step(-1); }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (opts[hi]) pick(opts[hi]); }
    else if (e.key === "Escape" || e.key === "Tab") setOpen(false);
  };

  return (
    <>
      <button ref={btn} type="button" disabled={disabled} title={title} aria-label={rest["aria-label"]}
              aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen(o => !o)} onKeyDown={onKey}
              className={`sp-select ${className}`} style={style}>
        <span className="truncate">{sel ? sel.label : "—"}</span>
        <ChevronDown size={14} className={`sp-select-chev${open ? " is-open" : ""}`} />
      </button>
      {open && (
        <div ref={list} role="listbox" className="menu-pop sp-select-list"
             style={{ position: "fixed", left: pos.left, width: pos.width, zIndex: 80,
                      ...(pos.up ? { bottom: window.innerHeight - pos.top, transformOrigin: "bottom" } : { top: pos.top }) }}>
          {opts.map((o, i) => (
            <div key={o.value + i} data-i={i} role="option" aria-selected={o.value === cur} aria-disabled={o.disabled}
                 onMouseEnter={() => setHi(i)} onClick={() => pick(o)}
                 className={`sp-select-opt${i === hi ? " is-hi" : ""}${o.value === cur ? " is-sel" : ""}${o.disabled ? " is-off" : ""}`}>
              <span className="truncate">{o.label}</span>
              {o.value === cur && <Check size={14} />}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
