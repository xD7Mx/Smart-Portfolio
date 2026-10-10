import { useQuery } from "@tanstack/react-query";
import { marketApi } from "../../services/api";

/* ══ الأحداثُ الجوهرية ══ (اقتراحُ المالك · D644)
   «حصرناها مالياً وظلمناها إخبارياً». ما وقّعته الشركةُ أو واجهته في سنةٍ من إفصاحات «تداول» بنصّها العربيّ:
   العقدُ بقيمته ومدّته وهل يُعدّ في سجلّ أعمالها ولماذا، والسلبياتُ الجسيمة بلون التحذير. عرضٌ لا يمسّ الرقم —
   قِيس أنّ إدخالَ العقود في القيمة لا يُحسّنها (D633). وإعلاناتُ الحدث الواحد بندٌ واحد (ملاحظةُ المالك 2026-10-09). */
const money = (v: number) =>
  v >= 1e9 ? `${(v / 1e9).toLocaleString("en-US", { maximumFractionDigits: 2 })} مليار ريال`
           : `${(v / 1e6).toLocaleString("en-US", { maximumFractionDigits: 1 })} مليون ريال`;

/* الحدثُ الواحد بإفصاحاته (ملاحظةُ المالك): يُقال كم إفصاحاً جُمع، فلا يبدو المكرَّرُ محذوفاً */
const filings = (n: number) => (n === 2 ? "إفصاحان" : n <= 10 ? `${n} إفصاحات` : `${n} إفصاحاً`);

export default function MaterialEvents({ symbol }: { symbol: string }) {
  const sym = symbol.replace(".SR", "");
  const { data } = useQuery({
    queryKey: ["material-events", sym],
    queryFn: () => marketApi.materialEvents(sym).then(x => x.data?.data || null),
    staleTime: 6 * 60 * 60 * 1000,
    retry: 0,
  });
  const events: any[] = data?.events || [];
  if (!events.length) return null;
  return (
    <div className="card">
      <p className="card-title mb-3">الأحداث الجوهرية</p>
      <div className="space-y-2.5">
        {events.map((e, i) => (
          <div key={i} className="flex items-start gap-2.5 text-right">
            <span className="text-[10.5px] px-2 py-0.5 rounded-full shrink-0 mt-0.5" style={{
              color: e.negative ? "var(--warn-ink)" : "var(--brand)",
              background: `color-mix(in srgb, ${e.negative ? "var(--warn-ink)" : "var(--brand)"} 12%, transparent)`,
            }}>{e.kind_ar}</span>
            <div className="min-w-0 flex-1">
              {/* وسمٌ واحد (ملاحظةُ المالك): العنوانُ نفسُه رابطُ الإفصاح — لا وسمَ «الإفصاح» ثانياً بجانب نوع الحدث */}
              {e.url ? (
                <a href={e.url} target="_blank" rel="noopener noreferrer"
                   className="block min-h-[32px] text-[12.5px] text-[var(--ink)] leading-relaxed underline-offset-2 hover:underline">
                  {e.title}
                </a>
              ) : <p className="text-[12.5px] text-[var(--ink)] leading-relaxed">{e.title}</p>}
              <div className="flex items-center gap-2 flex-wrap mt-0.5 text-[11px] text-[var(--ink-muted)]">
                <span className="tabular-nums" dir="ltr">{e.date}</span>
                {e.first_date && e.first_date !== e.date && (
                  <span>· أُعلن أوّلاً <span className="tabular-nums" dir="ltr">{e.first_date}</span></span>
                )}
                {(e.filings || 1) > 1 && <span>· {filings(e.filings)}</span>}
                {e.kind === "contract" && e.value != null && <span>· {money(e.value)}{e.months ? ` · ${e.months} شهراً` : ""}</span>}
                {e.kind === "contract" && (e.counted
                  ? <span style={{ color: "var(--pos-ink)" }}>· يُعدّ في سجلّ الأعمال</span>
                  : e.why_not && <span>· {e.why_not}</span>)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
