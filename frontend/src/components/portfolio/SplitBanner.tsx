import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { transactionsApi } from "../../services/api";

/* ‏D614: تجزئةٌ معلنةٌ أو مقيسةٌ من السعر ولم تُطبَّق على الحيازة — تُقترح ولا تُفرض.
   بزرٍّ واحد تُسجَّل عمليةُ «تجزئة» بالمعامل وتاريخها، فيتضاعف العددُ وتنقسم التكلفة. */
type Pending = { key: string; company_id: number; symbol: string; name: string; factor: number;
                 date: string; source: string; shares: number; shares_after: number };

const n = (x: number) => (Number.isInteger(x) ? String(x) : x.toLocaleString("en-US", { maximumFractionDigits: 4 }));

export function SplitBanner() {
  const qc = useQueryClient();
  const { data = [] } = useQuery<Pending[]>({
    queryKey: ["pending-splits"],
    queryFn: () => transactionsApi.pendingSplits().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
    staleTime: 5 * 60_000,
  });
  const apply = useMutation({
    mutationFn: (p: Pending) => transactionsApi.add({
      company_id: p.company_id, transaction_type: "SPLIT", transaction_date: p.date,
      factor: p.factor, confirm_prior_pre_split: true, notes: `تجزئة ${n(p.factor)}:1 — من كاشف التجزئة`,
    }),
    onSuccess: () => qc.invalidateQueries(),
  });
  const skip = useMutation({
    mutationFn: (p: Pending) => transactionsApi.dismissSplit(p.key),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pending-splits"] }),
  });
  if (!data.length) return null;
  return (
    <div className="space-y-2" data-testid="split-banner">
      {data.map(p => (
        <div key={p.key} className="card flex flex-wrap items-center justify-between gap-3 text-right"
             style={{ borderColor: "color-mix(in srgb, var(--warn-ink) 45%, transparent)" }}>
          <div className="space-y-1">
            <p className="text-[14px] font-semibold" style={{ color: "var(--warn-ink)" }}>
              تجزئة {p.name} {n(p.factor)}:1 بانتظار التأكيد
            </p>
            <p className="text-[12px] text-[var(--ink-muted)]">
              أسهمك <span className="tabular-nums">{n(p.shares)}</span> تصير{" "}
              <span className="tabular-nums">{n(p.shares_after)}</span>، والتكلفةُ للسهم تنقسم على {n(p.factor)} ·{" "}
              {p.source === "إعلان" ? "من إعلان الشركة" : "من هبوط السعر بالنسبة نفسها"} · {p.date}
            </p>
            {apply.isError && <p className="text-[12px]" style={{ color: "var(--neg-ink)" }}>تعذّر التطبيق — حاول مجدداً</p>}
          </div>
          <div className="flex gap-2">
            <button type="button" className="btn-primary min-h-[32px] px-3 text-[13px]"
                    disabled={apply.isPending} onClick={() => apply.mutate(p)}>طبّق التجزئة</button>
            <button type="button" className="btn-ghost min-h-[32px] px-3 text-[13px]"
                    disabled={skip.isPending} onClick={() => skip.mutate(p)}>ليست تجزئة</button>
          </div>
        </div>
      ))}
    </div>
  );
}
