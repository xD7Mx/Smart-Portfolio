/* عمقُ السوق — مستوًى واحدٌ من «تداول»، ولا يُوعَد بعشرين (D272).
 *
 * طلب المالك عمقَ السوق لكلّ شركة «حتى 20x». وقِيس أن التغذيةَ المفتوحة
 * تنشر **مستوًى واحداً**: أفضلَ طلبٍ وأفضلَ عرضٍ بكمّيتيهما. والعشرون
 * تغذيةٌ مرخَّصة. فيُعرض الموجودُ باسمه ويُقال عددُ مستوياته — ولا يُرسَم
 * جدولٌ بعشرين سطراً تسعةَ عشرَ منها فراغ.
 *
 * والغيابُ يُقال: بلا لقطةٍ حاضرةٍ تظهر البطاقةُ بجملةِ تعذُّرٍ واحدة — لا
 * تُطوى البطاقةُ فيظنّ المالكُ أن الميزةَ لم تُبنَ.
 */
import { useQuery } from "@tanstack/react-query";

import { marketApi } from "../../services/api";
import FlashPrice from "../common/FlashPrice";

const fmt = (n: number, d = 2) =>
  n.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const qty = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 0 });

type Level = { price: number; quantity: number };

export default function MarketDepth({ symbol }: { symbol: string }) {
  const { data } = useQuery({
    queryKey: ["depth", symbol],
    queryFn: () => marketApi.depth(symbol).then(r => r.data.data),
    refetchInterval: 20_000,          // زمنُ اللقطة نفسُه — لا أسرعَ بلا داعٍ
    staleTime: 10_000,
  });

  const bids: Level[] = data?.bids ?? [];
  const asks: Level[] = data?.asks ?? [];
  const total = (bids[0]?.quantity ?? 0) + (asks[0]?.quantity ?? 0);
  const bidShare = total > 0 ? ((bids[0]?.quantity ?? 0) / total) * 100 : null;

  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-3 text-right">
      <div className="flex items-center justify-between gap-2 mb-2">
        <h3 className="text-[13px] font-bold text-[var(--ink)]">عمق السوق</h3>
        {data?.available && (
          <span className="text-[10px] text-[var(--ink-muted)] tabular-nums">
            مستوى {data.levels} · تداول
          </span>
        )}
      </div>

      {!data?.available ? (
        <p className="py-4 text-center text-[11px] text-[var(--ink-muted)]">
          غير متوفّر الآن.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2">
            <Side label="عرض (بيع)" level={asks[0]} tone="neg" />
            <Side label="طلب (شراء)" level={bids[0]} tone="pos" />
          </div>

          {bidShare != null && (
            /* شريطُ الكفّتين: الكمّيتان نسبةً إلى مجموعهما — شكلٌ يُقرأ
               قبل الرقم، وهو ما يفعله تطبيق التداول. */
            <div className="mt-2 h-1.5 rounded-full overflow-hidden bg-[var(--line)] flex"
                 dir="rtl" aria-hidden>
              <span className="h-full bg-[var(--pos-ink)]" style={{ width: `${bidShare}%` }} />
              <span className="h-full bg-[var(--neg-ink)]" style={{ width: `${100 - bidShare}%` }} />
            </div>
          )}

          <div className="mt-2 flex items-center justify-between gap-2 text-[10px] text-[var(--ink-muted)]">
            {data.spread != null && (
              <span className="tabular-nums">الفارق {fmt(data.spread)} ﷼</span>
            )}
            {data.trades != null && (
              <span className="tabular-nums">{qty(data.trades)} صفقة</span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function Side({ label, level, tone }: { label: string; level?: Level; tone: "pos" | "neg" }) {
  const ink = tone === "pos" ? "var(--pos-ink)" : "var(--neg-ink)";
  return (
    <div className="rounded-lg border border-[var(--line)] px-2 py-1.5">
      <div className="text-[10px] text-[var(--ink-muted)] mb-0.5">{label}</div>
      {level ? (
        <>
          <FlashPrice value={level.price}
                      className="block text-[15px] font-bold tabular-nums"
                      style={{ color: ink }}>
            {fmt(level.price)}
          </FlashPrice>
          <div className="text-[10px] text-[var(--ink-muted)] tabular-nums">
            {qty(level.quantity)} سهم
          </div>
        </>
      ) : (
        /* الجهلُ ليس صفراً: طرفٌ بلا سعرٍ يُقال «—» ولا يُرسَم رقماً. */
        <span className="text-[15px] font-bold text-[var(--ink-muted)]">—</span>
      )}
    </div>
  );
}
