import { useEffect, useRef, useState } from "react";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";

/* ‏D615: حقلُ تاريخٍ بأرقامٍ لاتينية دائماً. حقلُ المتصفّح الأصليّ (input[type=date]) يرسم
   أرقامه بلغة المتصفّح لا الصفحة — فيظهر ٠٧/١٠/٢٠٢٦ عند من متصفّحُه عربيّ، ولا يغيّره lang="en".
   فالحقلُ والتقويمُ هنا مرسومان بأيدينا: القيمةُ YYYY-MM-DD كما كانت، والعرضُ لاتينيّ. */
type Props = {
  value: string;
  onChange: (e: { target: { value: string } }) => void;
  min?: string;
  max?: string;
  className?: string;
};

const MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];
const DAYS = ["ح", "ن", "ث", "ر", "خ", "ج", "س"];
const pad = (n: number) => String(n).padStart(2, "0");
const iso = (y: number, m: number, d: number) => `${y}-${pad(m + 1)}-${pad(d)}`;

export default function DateInput({ value, onChange, min, max, className = "input" }: Props) {
  const [open, setOpen] = useState(false);
  const base = /^\d{4}-\d{2}-\d{2}$/.test(value || "") ? value : new Date().toISOString().slice(0, 10);
  const [y0, m0] = base.split("-").map(Number);
  const [view, setView] = useState({ y: y0, m: m0 - 1 });
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => { if (open) setView({ y: y0, m: m0 - 1 }); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!open) return;
    const off = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", off);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", off); document.removeEventListener("keydown", esc); };
  }, [open]);

  const first = new Date(view.y, view.m, 1).getDay();
  const count = new Date(view.y, view.m + 1, 0).getDate();
  const cells: (number | null)[] = [...Array(first).fill(null), ...Array.from({ length: count }, (_, i) => i + 1)];
  const shift = (k: number) => setView(v => { const m = v.m + k; return { y: v.y + Math.floor(m / 12), m: ((m % 12) + 12) % 12 }; });
  const ok = (d: string) => (!min || d >= min) && (!max || d <= max);
  const pick = (d: string) => { if (ok(d)) { onChange({ target: { value: d } }); setOpen(false); } };
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div ref={box} className="relative">
      <button type="button" className={`${className} flex items-center justify-between gap-2 text-right`}
              onClick={() => setOpen(o => !o)} aria-haspopup="dialog" aria-expanded={open}>
        <span className="tabular-nums" dir="ltr">{value ? value.split("-").reverse().join("/") : "—"}</span>
        <Calendar size={16} className="text-[var(--ink-muted)]" />
      </button>
      {open && (
        <div role="dialog" className="date-pop absolute z-50 mt-2 w-[280px] rounded-2xl border p-3 shadow-xl"
             style={{ background: "var(--surface)", borderColor: "var(--hairline)", insetInlineStart: 0 }}>
          <div className="mb-2 flex items-center justify-between">
            <button type="button" className="date-nav" onClick={() => shift(-1)} aria-label="الشهر السابق"><ChevronRight size={16} /></button>
            <span className="text-[14px] font-semibold">{MONTHS[view.m]} <span className="tabular-nums">{view.y}</span></span>
            <button type="button" className="date-nav" onClick={() => shift(1)} aria-label="الشهر التالي"><ChevronLeft size={16} /></button>
          </div>
          <div className="grid grid-cols-7 gap-1 text-center text-[11px] text-[var(--ink-muted)]">
            {DAYS.map(d => <span key={d}>{d}</span>)}
          </div>
          <div className="mt-1 grid grid-cols-7 gap-1">
            {cells.map((d, i) => {
              if (d == null) return <span key={`e${i}`} />;
              const s = iso(view.y, view.m, d);
              return (
                <button key={s} type="button" disabled={!ok(s)} onClick={() => pick(s)}
                        className={`date-day tabular-nums${s === value ? " is-sel" : ""}${s === today ? " is-today" : ""}`}>{d}</button>
              );
            })}
          </div>
          {ok(today) && (
            <button type="button" className="date-nav mt-2 w-full text-[12px]" onClick={() => pick(today)}>اليوم</button>
          )}
        </div>
      )}
    </div>
  );
}
