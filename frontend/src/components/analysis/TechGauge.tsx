import React from "react";

/**
 * Semi-circle "speedometer" gauge for the technical score (0-100), styled
 * after the buy/sell dials on finance portals — a needle across five
 * colored zones from "بيع قوي" to "شراء قوي". Purely a different visual
 * read of the same real technical score computed in technical.py; no new
 * number is invented here.
 */
function tier(score: number) {
  if (score < 20) return { label: "بيع قوي", color: "var(--neg-ink)" };
  if (score < 40) return { label: "بيع", color: "var(--warn-ink)" };
  if (score < 60) return { label: "محايد", color: "var(--warn-ink)" };
  if (score < 80) return { label: "شراء", color: "var(--pos-ink)" };
  return { label: "شراء قوي", color: "var(--pos-ink)" };
}

export default function TechGauge({ score }: { score: number | null }) {
  if (score == null) return null;
  const clamped = Math.max(0, Math.min(100, score));
  const t = tier(clamped);
  // Needle sweeps from -90deg (score 0) to +90deg (score 100).
  const angle = -90 + (clamped / 100) * 180;
  const cx = 90, cy = 90, r = 74;
  const zones = [
    { from: 0, to: 20, color: "var(--neg-ink)" },
    { from: 20, to: 40, color: "var(--warn-ink)" },
    { from: 40, to: 60, color: "var(--warn-ink)" },
    { from: 60, to: 80, color: "var(--pos-ink)" },
    { from: 80, to: 100, color: "var(--pos-ink)" },
  ];
  const pt = (pct: number) => {
    const a = (-90 + (pct / 100) * 180) * (Math.PI / 180);
    return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  };
  return (
    <div className="flex flex-col items-center w-full" style={{ maxWidth: 180 }}>
      <svg viewBox="0 0 180 100" width="100%" style={{ overflow: "visible" }}>
        {zones.map((z, i) => {
          const [x1, y1] = pt(z.from);
          const [x2, y2] = pt(z.to);
          return (
            <path key={i} d={`M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`}
              stroke={z.color} strokeWidth={14} fill="none" strokeLinecap="butt" />
          );
        })}
        <g transform={`rotate(${angle} ${cx} ${cy})`}>
          <line x1={cx} y1={cy} x2={cx} y2={cy - r + 18} stroke="var(--hairline)" strokeWidth={3} strokeLinecap="round" />
        </g>
        <circle cx={cx} cy={cy} r={5} fill="var(--hairline)" />
      </svg>
      <div className="text-sm font-extrabold -mt-1" style={{ color: t.color }}>{t.label}</div>
      <div className="text-[11px] text-[var(--ink-muted)]">{clamped}/100</div>
    </div>
  );
}
