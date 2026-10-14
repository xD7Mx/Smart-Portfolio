import React from "react";
import { PAPER } from "./ReportDocument";

const AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];

export interface CandleSet {
  points?: { d: string; o: number; h: number; l: number; c: number }[];
  from?: string | null;
  to?: string | null;
}

/* ══ شموعُ الفترة ══ (بأمر المالك · D698 · D711) — «كما تفعل تقاريرُ البنوك»: اثنا عشر شهراً أسبوعيّة تنتهي بآخر الفترة،
   ونطاقُ الفترة مظلَّلٌ بلون الهويّة، وآخرُ قيمةٍ خطٌّ ووسم. الزمنُ من اليسار إلى اليمين كما في رسم التطبيق، والقيمُ على الحافّة
   اليمنى. ورقةٌ واحدةٌ لتقريرَي الشركة (السعر) والمحفظة (صافي الربح) — والصفرُ خطٌّ حين تعبره السلسلة. */
export default function ReportCandles({ c, label, title, fmt = (v: number) => v.toFixed(2), zeroLine = false }: {
  c: CandleSet; label?: string; title: string; fmt?: (v: number) => string; zeroLine?: boolean;
}) {
  const { NAVY, GOLD, GREEN, RED, MUTED, CARD_LINE, ROW_LINE } = PAPER;      /* داخل الرسم: الاستيرادُ دائريٌّ مع الورقة */
  const pts = c?.points || [];
  if (pts.length < 10) return null;
  const lo = Math.min(...pts.map(p => p.l)), hi = Math.max(...pts.map(p => p.h));
  const pad = (hi - lo) * 0.06 || Math.abs(hi) * 0.02 || 1;
  const y0 = lo - pad, y1 = hi + pad;
  const grid = [0, 1, 2, 3].map(k => y0 + (y1 - y0) * (k + 0.5) / 4);
  const last = pts[pts.length - 1].c;
  const W = 706, H = 214, L = 6, T = 14, B = 24;
  const R = Math.max(52, 6 * Math.max(...[...grid, last].map(v => fmt(v).length)) + 12);
  const y = (v: number) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  const step = (W - L - R) / pts.length;
  const x = (i: number) => L + step * (i + 0.5);
  const t0 = new Date(pts[0].d).getTime(), t1 = new Date(pts[pts.length - 1].d).getTime();
  const xt = (iso: string) => L + ((new Date(iso).getTime() - t0) / Math.max(1, t1 - t0)) * (W - L - R - step) + step / 2;
  const bx0 = c.from ? Math.max(L, Math.min(W - R, xt(c.from))) : 0;
  const bx1 = c.to ? Math.max(L, Math.min(W - R, xt(c.to))) : 0;
  const months: { i: number; m: string }[] = [];
  pts.forEach((p, i) => { const m = p.d.slice(0, 7); if (i > 0 && m !== pts[i - 1].d.slice(0, 7) && i < pts.length - 2) months.push({ i, m }); });
  const bw = Math.max(2, step * 0.62);
  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 500, color: NAVY, marginBottom: 8, borderInlineStart: `3px solid ${GOLD}`, paddingInlineStart: 8 }}>
        {title}
      </div>
      <svg data-role="report-candles" width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: "block", direction: "ltr", background: "#fff",
           border: `1px solid ${CARD_LINE}`, borderRadius: 8 }}>
        {bx1 > bx0 && <g>
          <rect x={bx0} y={T} width={bx1 - bx0} height={H - T - B} fill={GOLD} opacity={0.12} />
          {label && bx1 - bx0 >= 44 && (
            <text x={(bx0 + bx1) / 2} y={T + 11} textAnchor="middle" fontSize={9.5} fill={NAVY} style={{ fontFamily: "inherit" }}>{label}</text>
          )}
        </g>}
        {grid.map((v, k) => (
          <g key={k}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={ROW_LINE} strokeWidth={1} />
            {/* وسمُ الشبكة يُخفى حيث يلامس وسمَ آخر قيمة — لا رقمان فوق بعضهما */}
            {Math.abs(y(v) - y(last)) >= 14 && <text x={W - R + 6} y={y(v) + 3.5} fontSize={9.5} fill={MUTED}>{fmt(v)}</text>}
          </g>
        ))}
        {zeroLine && y0 < 0 && y1 > 0 && (
          <line data-role="candles-zero" x1={L} x2={W - R} y1={y(0)} y2={y(0)} stroke={MUTED} strokeWidth={1} />
        )}
        {pts.map((p, i) => {
          const up = p.c >= p.o, colr = up ? GREEN : RED;
          const top = y(Math.max(p.o, p.c)), bot = y(Math.min(p.o, p.c));
          return (
            <g key={p.d}>
              <line x1={x(i)} x2={x(i)} y1={y(p.h)} y2={y(p.l)} stroke={colr} strokeWidth={1} />
              <rect x={x(i) - bw / 2} y={top} width={bw} height={Math.max(1, bot - top)} fill={colr} />
            </g>
          );
        })}
        <line x1={L} x2={W - R} y1={y(last)} y2={y(last)} stroke={NAVY} strokeWidth={1} strokeDasharray="3 3" />
        <rect x={W - R + 2} y={y(last) - 8} width={R - 4} height={16} rx={3} fill={NAVY} />
        <text x={W - R / 2} y={y(last) + 3.5} textAnchor="middle" fontSize={9.5} fill="#fff">{fmt(last)}</text>
        {months.map(({ i, m }) => (
          <text key={m} x={x(i)} y={H - 8} textAnchor="middle" fontSize={9.5} fill={MUTED} style={{ fontFamily: "inherit" }}>
            {AR_MONTHS[Number(m.slice(5, 7)) - 1]}
          </text>
        ))}
      </svg>
    </div>
  );
}
