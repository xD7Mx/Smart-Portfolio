import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Users, Building2, Landmark } from "lucide-react";
import { marketApi } from "../../services/api";

/**
 * Ownership structure — a visual bar of who holds the stock
 * (institutions / insiders / public float). Auto-fetched, no button.
 * Renders nothing until real data exists (no fabricated splits).
 */
export default function OwnershipBar({ symbol }: { symbol: string }) {
  const { data } = useQuery({
    queryKey: ["ownership", symbol],
    queryFn: () => marketApi.ownership(symbol).then(r => r.data.data),
    enabled: !!symbol,
    retry: 0,
  });
  if (!data) return null;
  /* ══ كبارُ الملاك بأسمائهم — في البطاقة نفسِها ══ (D276)
     بناءُ بطاقةٍ ثانيةٍ لهم كان سيكرّر «هيكل الملكية» مرّتين في شاشةٍ
     واحدة، وهو عطبُ «منتِجَين لمعنًى واحد» في الشاشات. فيظهرون تحت
     الشريط إن قُرئوا، ولا شيءَ يتغيّر إن لم يُقرأوا. */
  const holders: { name: string; percent: number }[] = data.major_holders ?? [];
  const foreign: { name: string; percent: number }[] = data.foreign ?? [];
  const board: { name: string; percent: number; position?: string }[] = data.board ?? [];
  const rows = [
    { key: "institutions", label: "الصناديق والمؤسسات", icon: Landmark, color: "var(--chart-1)", value: data.institutions },
    { key: "insiders", label: "كبار الملاك", icon: Building2, color: "var(--chart-3)", value: data.insiders },
    { key: "public", label: "التداول الحر (أفراد)", icon: Users, color: "var(--pos-ink)", value: data.public },
  ].filter(r => r.value != null && r.value > 0);
  /* النِّسَبُ المجمّعةُ قد تغيب والأسماءُ مقروءة — فلا تُطوى البطاقةُ
     على قراءةٍ موجودة. وتُطوى فقط حين لا شيءَ أصلاً. */
  if (rows.length === 0 && holders.length === 0 && foreign.length === 0
      && board.length === 0) return null;

  return (
    <div className="card">
      <p className="card-title mb-3">هيكل الملكية</p>
      {rows.length > 0 && (
      <div className="flex h-3 rounded-full overflow-hidden mb-3" dir="ltr">
        {rows.map(r => (
          <div key={r.key} style={{ width: `${r.value}%`, background: r.color }} title={`${r.label} ${r.value}%`} />
        ))}
      </div>
      )}
      <div className="space-y-2">
        {rows.map(r => (
          <div key={r.key} className="flex items-center gap-2 text-sm">
            <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: r.color }} />
            <r.icon size={13} className="text-[var(--ink-muted)] shrink-0" />
            <span className="text-[var(--ink)]">{r.label}</span>
            <span className="font-bold text-[var(--ink)] mr-auto">{r.value}%</span>
          </div>
        ))}
      </div>

      {holders.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[var(--line)]">
          <p className="text-[11px] font-bold text-[var(--ink)] mb-1.5">كبار الملاك</p>
          <div className="space-y-1">
            {holders.slice(0, 8).map(h => (
              <div key={h.name} className="flex items-baseline gap-2 text-[11px]">
                <span className="text-[var(--ink)] truncate">{h.name}</span>
                <span className="font-bold tabular-nums text-[var(--ink)] mr-auto shrink-0">
                  {h.percent.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {foreign.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[var(--line)]">
          <p className="text-[11px] font-bold text-[var(--ink)] mb-1.5">ملكية الأجانب</p>
          <div className="space-y-1">
            {foreign.slice(0, 4).map(f => (
              <div key={f.name} className="flex items-baseline gap-2 text-[11px]">
                <span className="text-[var(--ink)] truncate">{f.name}</span>
                <span className="font-bold tabular-nums text-[var(--ink)] mr-auto shrink-0">
                  {f.percent.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {board.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[var(--line)]">
          <p className="text-[11px] font-bold text-[var(--ink)] mb-1.5">أعضاء مجلس الإدارة</p>
          <div className="space-y-1">
            {board.slice(0, 8).map(b => (
              <div key={b.name} className="flex items-baseline gap-2 text-[11px]">
                <span className="text-[var(--ink)] truncate">{b.name}</span>
                {b.position && (
                  <span className="text-[10px] text-[var(--ink-muted)] truncate">{b.position}</span>
                )}
                <span className="font-bold tabular-nums text-[var(--ink)] mr-auto shrink-0">
                  {b.percent.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.detail_source && (holders.length > 0 || foreign.length > 0 || board.length > 0) && (
        <p className="mt-2 text-[10px] text-[var(--ink-muted)]">
          {data.detail_source}
        </p>
      )}
    </div>
  );
}
