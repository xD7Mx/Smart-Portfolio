import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { marketApi } from "../../services/api";
import { SafetyBar, safeColor } from "../common/ValueBars";

/* ══ الجودةُ الماليةُ وتفصيلُها (D469 · D485) ══
   السلامةُ = الحوكمةُ = الجودةُ المالية: رقمٌ واحد من نموذجنا، نسبةً مئوية
   بالشريط نفسِه الذي في فرز السوق — لا «من خمسة» بجانب «من مئة».
   وتحته المحاورُ الخمسة: ترتيبُ الشركة بين أقران قطاع «تداول» الرسميّ نسبةً
   مئوية، وكلُّ محورٍ يُفتح على مقاييسه بلمسة. */

const pct = (s5: number) => Math.round(Math.min(Math.max(s5 / 5, 0), 1) * 100);

function Pillar({ p }: { p: any }) {
  const [open, setOpen] = useState(false);
  const v = pct(p.score);
  return (
    <div className="card p-4 space-y-2">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open}
              className="w-full min-h-[32px] flex items-center gap-2 text-right">
        <span className="flex-1 text-[14px] font-bold text-[var(--ink)]">{p.name}</span>
        <span className="text-lg font-bold tabular-nums" style={{ color: safeColor(v) }}>{v}%</span>
      </button>
      <SafetyBar score={v} width="100%" />
      <p className="text-[12px] leading-relaxed text-[var(--ink-muted)]">{p.why}</p>
      {open && (
        <table className="w-full text-[12px]">
          <thead>
            <tr className="text-[var(--ink-muted)] bg-[var(--surface)]">
              <th className="text-right font-bold p-2">المقياس</th>
              <th className="text-right font-bold p-2">القيمة</th>
              <th className="text-right font-bold p-2">الترتيب بين الأقران</th>
            </tr>
          </thead>
          <tbody>
            {p.metrics.map((m: any) => (
              <tr key={m.key} className="border-t border-[var(--hairline)]">
                <td className="p-2 text-[var(--ink)]">{m.name}</td>
                <td className="p-2 tabular-nums text-[var(--ink)]" dir="ltr" style={{ textAlign: "right" }}>{m.display}</td>
                <td className="p-2 tabular-nums font-bold" style={{ color: safeColor(pct(m.score)) }}>{pct(m.score)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function HealthPanel({ symbol, quality }: { symbol: string; quality?: number | null }) {
  const sym = symbol.replace(".SR", "");
  const { data: r, isLoading } = useQuery({
    queryKey: ["health", sym],
    queryFn: () => marketApi.health(sym).then(x => x.data?.data || null),
    staleTime: 30 * 60 * 1000,
  });
  if (isLoading) return <div className="h-64 skeleton rounded-xl" />;
  return (
    <div className="space-y-3">
      {quality != null && (
        <div className="card p-4 space-y-3">
          <div className="flex items-baseline gap-2">
            <span className="flex-1 text-[15px] font-bold text-[var(--ink)]">الجودة المالية</span>
            <span className="text-2xl font-bold tabular-nums" style={{ color: safeColor(quality) }}>{Math.round(quality)}%</span>
          </div>
          <SafetyBar score={Math.round(quality)} width="100%" />
          {r && <div className="text-[12px] text-[var(--ink-muted)]">المحاور بين {r.peers} شركةً في قطاع {r.sector}</div>}
        </div>
      )}
      {r ? r.pillars.map((p: any) => <Pillar key={p.pillar} p={p} />)
         : <div className="py-6 text-center text-sm text-[var(--ink-muted)]">لا أقرانَ كافين في قطاع «تداول» لترتيب محاور هذه الورقة.</div>}
    </div>
  );
}
