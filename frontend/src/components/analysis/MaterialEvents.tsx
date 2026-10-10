import { useQuery } from "@tanstack/react-query";
import { marketApi } from "../../services/api";
import EventCard from "../common/EventCard";

/* ══ الأحداثُ الجوهرية ══ (اقتراحُ المالك · D644)
   «حصرناها مالياً وظلمناها إخبارياً». ما وقّعته الشركةُ أو واجهته في سنةٍ من إفصاحات «تداول» بنصّها العربيّ:
   العقدُ بقيمته ومدّته وهل يُعدّ في سجلّ أعمالها ولماذا، والسلبياتُ الجسيمة بلون التحذير. عرضٌ لا يمسّ الرقم —
   قِيس أنّ إدخالَ العقود في القيمة لا يُحسّنها (D633). وإعلاناتُ الحدث الواحد بندٌ واحد (ملاحظةُ المالك 2026-10-09).
   ‏D666 (بأمر المالك): «اجعلها بنفس طريقة البطاقات الأخرى ووسمها» — البطاقةُ الموحّدة نفسُها التي في المفكرة، والوسمُ
   رقعةٌ صلبةٌ من عائلة وسومها؛ وموضعُها «نظرة عامة» فتظهر عند فتح السهم في الجوال والحاسوب. */
const money = (v: number) =>
  v >= 1e9 ? `${(v / 1e9).toLocaleString("en-US", { maximumFractionDigits: 2 })} مليار ريال`
           : `${(v / 1e6).toLocaleString("en-US", { maximumFractionDigits: 1 })} مليون ريال`;

/* الحدثُ الواحد بإفصاحاته (ملاحظةُ المالك): يُقال كم إفصاحاً جُمع، فلا يبدو المكرَّرُ محذوفاً */
const filings = (n: number) => (n === 2 ? "إفصاحان" : n <= 10 ? `${n} إفصاحات` : `${n} إفصاحاً`);

/* وسمُ نوع الحدث من عائلة وسوم المفكرة: العقدُ رقعتُه، والاستحواذُ رقعةُ الاندماج، والجسيمُ رقعةُ التحذير */
const TAG: Record<string, string> = {
  contract: "var(--tag-contract)", acquisition: "var(--tag-merger)", leadership: "var(--tag-hold)",
  losses: "var(--tag-sell)", regulator: "var(--tag-sell)", litigation: "var(--tag-sell)",
};

export default function MaterialEvents({ symbol }: { symbol: string }) {
  const sym = symbol.replace(".SR", "");
  const { data, isSuccess } = useQuery({
    queryKey: ["material-events", sym],
    queryFn: () => marketApi.materialEvents(sym).then(x => x.data?.data || null),
    staleTime: 6 * 60 * 60 * 1000,
    retry: 0,
  });
  const events: any[] = data?.events || [];
  /* ‏D668: كانت البطاقةُ تختفي حين لا حدث (قِيس: أرامكو والراجحي والحبيب بلا حدثٍ في سنة) فظنّ المالكُ الميزةَ غائبة.
     فتبقى بعنوانها وسطرِ حالٍ واحد حين يصل الجوابُ فارغاً؛ وتغيب وحدها ما دام الجوابُ لم يصل أو تعذّر. */
  if (!events.length) {
    if (!isSuccess || !data) return null;
    return (
      <div className="card">
        <p className="card-title mb-2">الأحداث الجوهرية</p>
        <p className="text-[12px] text-[var(--ink-muted)]">لا أحداث جوهرية خلال آخر سنة</p>
      </div>
    );
  }
  return (
    <div className="card">
      <p className="card-title mb-3">الأحداث الجوهرية</p>
      <div className="space-y-1.5">
        {/* وسمٌ واحد (ملاحظةُ المالك): نوعُ الحدث — والبطاقةُ نفسُها رابطُ الإفصاح (‏href={e.url}) */}
        {events.map((e, i) => (
          <EventCard key={i} symbol={sym} href={e.url || null}
            tag={{ label: e.kind_ar, bg: TAG[e.kind] || (e.negative ? "var(--tag-sell)" : "var(--tag-news)") }}
            title={e.title} date={e.date}
            meta={(e.first_date && e.first_date !== e.date) || (e.filings || 1) > 1 || e.kind === "contract" ? <>
              {e.first_date && e.first_date !== e.date && (
                <span>أُعلن أوّلاً <span className="tabular-nums" dir="ltr">{e.first_date}</span></span>
              )}
              {(e.filings || 1) > 1 && <span>· {filings(e.filings)}</span>}
              {e.kind === "contract" && e.value != null && <span>· {money(e.value)}{e.months ? ` · ${e.months} شهراً` : ""}</span>}
              {e.kind === "contract" && (e.counted
                ? <span style={{ color: "var(--pos-ink)" }}>· يُعدّ في سجلّ الأعمال</span>
                : e.why_not && <span>· {e.why_not}</span>)}
            </> : null} />
        ))}
      </div>
    </div>
  );
}
