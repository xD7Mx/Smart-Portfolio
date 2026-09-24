import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { marketApi } from "../../services/api";

/* ══ السلامةُ الماليةُ بخمسة محاور (D469) ══
   كلُّ مقياسٍ مرتَّبٌ بين شركات قطاع «تداول» الرسميّ، ودرجتُه من خمسة بنقطته
   المئوية؛ والمحورُ متوسّطُ مقاييسه، ويُشرح بأقوى مقياسٍ وأضعفه. */

const TONE = (s: number) => (s < 1 ? "var(--neg-ink)" : s < 2.5 ? "var(--warn-ink)" : s < 3.25 ? "var(--gauge-warn)" : "var(--pos-ink)");
const SEG = ["var(--neg-ink)", "var(--warn-ink)", "var(--gauge-warn)", "var(--gauge-pos)", "var(--pos-ink)"];

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="relative pt-2" dir="ltr">
      <div className="grid grid-cols-5 gap-1">
        {SEG.map((c, k) => <div key={k} className="h-1.5 rounded" style={{ background: c, opacity: 0.85 }} />)}
      </div>
      <div className="absolute top-0 -translate-x-1/2 w-0 h-0 border-x-[6px] border-x-transparent border-t-[8px] border-t-[var(--ink)]"
           style={{ left: `${Math.min(Math.max(score / 5, 0), 1) * 100}%` }} />
      <div className="flex justify-between text-[11px] mt-1.5 text-[var(--ink-muted)]">
        <span>ضعيف</span><span>ممتاز</span>
      </div>
    </div>
  );
}

function Pillar({ p }: { p: any }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card p-4 space-y-2">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open}
              className="w-full min-h-[44px] flex items-center gap-2 text-right">
        <span className="flex-1">
          <span className="block text-[14px] font-bold text-[var(--ink)]">{p.name}</span>
          <span className="block text-[12px] font-bold" style={{ color: TONE(p.score) }}>{p.label}</span>
        </span>
        <span className="text-xl font-bold tabular-nums" style={{ color: TONE(p.score) }}>{p.score.toFixed(2)}</span>
        <ChevronDown size={16} className={"text-[var(--ink-muted)] transition-transform " + (open ? "rotate-180" : "")} />
      </button>
      <ScoreBar score={p.score} />
      <p className="text-[12px] leading-relaxed text-[var(--ink-muted)]">{p.why}</p>
      {open && (
        <table className="w-full text-[12px]">
          <thead>
            <tr className="text-[var(--ink-muted)] bg-[var(--surface)]">
              <th className="text-right font-bold p-2">المقياس</th>
              <th className="text-right font-bold p-2">القيمة</th>
              <th className="text-right font-bold p-2">النقطة المئوية</th>
              <th className="text-right font-bold p-2">الدرجة</th>
            </tr>
          </thead>
          <tbody>
            {p.metrics.map((m: any) => (
              <tr key={m.key} className="border-t border-[var(--hairline)]">
                <td className="p-2 text-[var(--ink)]">{m.name}</td>
                <td className="p-2 tabular-nums text-[var(--ink)]" dir="ltr" style={{ textAlign: "right" }}>{m.display}</td>
                <td className="p-2 tabular-nums text-[var(--ink-muted)]" dir="ltr" style={{ textAlign: "right" }}>{m.percentile.toFixed(1)}%</td>
                <td className="p-2 tabular-nums font-bold" style={{ color: TONE(m.score) }}>{m.score.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function HealthPanel({ symbol }: { symbol: string }) {
  const sym = symbol.replace(".SR", "");
  const { data: r, isLoading } = useQuery({
    queryKey: ["health", sym],
    queryFn: () => marketApi.health(sym).then(x => x.data?.data || null),
    staleTime: 30 * 60 * 1000,
  });
  if (isLoading) return <div className="h-64 skeleton rounded-xl" />;
  if (!r) return <div className="py-10 text-center text-sm text-[var(--ink-muted)]">لا أقرانَ كافين في قطاع «تداول» لترتيب هذه الورقة.</div>;
  return (
    <div className="space-y-3">
      <div className="card p-4 space-y-3">
        <div className="flex items-baseline gap-2">
          <span className="flex-1 text-[15px] font-bold text-[var(--ink)]">السلامة المالية</span>
          <span className="text-[13px] font-bold" style={{ color: TONE(r.score) }}>{r.label}</span>
          <span className="text-2xl font-bold tabular-nums" style={{ color: TONE(r.score) }}>{r.score.toFixed(2)}</span>
        </div>
        <ScoreBar score={r.score} />
        <div className="text-[12px] text-[var(--ink-muted)]">بين {r.peers} شركةً في قطاع {r.sector}</div>
      </div>
      {r.pillars.map((p: any) => <Pillar key={p.pillar} p={p} />)}
    </div>
  );
}
