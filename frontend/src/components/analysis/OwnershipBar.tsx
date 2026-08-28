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
  const rows = [
    { key: "institutions", label: "الصناديق والمؤسسات", icon: Landmark, color: "var(--chart-1)", value: data.institutions },
    { key: "insiders", label: "كبار الملاك", icon: Building2, color: "var(--chart-3)", value: data.insiders },
    { key: "public", label: "التداول الحر (أفراد)", icon: Users, color: "var(--pos-ink)", value: data.public },
  ].filter(r => r.value != null && r.value > 0);
  if (rows.length === 0) return null;

  return (
    <div className="card">
      <p className="card-title mb-3">هيكل الملكية</p>
      <div className="flex h-3 rounded-full overflow-hidden mb-3" dir="ltr">
        {rows.map(r => (
          <div key={r.key} style={{ width: `${r.value}%`, background: r.color }} title={`${r.label} ${r.value}%`} />
        ))}
      </div>
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
    </div>
  );
}
