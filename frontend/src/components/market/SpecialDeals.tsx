/* تبويبُ «صفقات خاصة» — مصدرُه «أرقام» بأمر المالك (D288 · D292).
 *
 * الصفقةُ الخاصة متفاوَضٌ عليها خارجَ دفتر الأوامر، بحجمٍ كبيرٍ وسعرٍ قد
 * يخالف سعرَ السوق — ولا تُقرأ من شريط الأسعار.
 *
 * ══ لا وسمَ مصدرٍ في الترويسة ══
 * أُزيل بأمر المالك: «لا فوت نوت ولا هيد نوت». والمصدرُ محفوظٌ في
 * الاستجابة لمن يقرأ السجلَّ، ولا يُكتب على الشاشة.
 *
 * والغيابُ يبقى مُعلَناً بجملةٍ واحدة: يومٌ بلا صفقاتٍ **وارد**، ولا
 * يُطوى التبويبُ فيُظنّ أنه لم يُبنَ، ولا يُعرض صفرٌ مختلَق.
 */
import { useQuery } from "@tanstack/react-query";
import { Handshake } from "lucide-react";
import { useState } from "react";

import { marketApi } from "../../services/api";

type Deal = {
  symbol: string; price: number; quantity: number; value: number;
  name?: string; at?: string;
};

const num = (n: number, d = 0) =>
  n.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

/** الرياالاتُ الكبيرةُ تُقرأ بوحدتها: ‎57 مليوناً أسهلُ من ‎57,000,000. */
function money(v: number): string {
  if (v >= 1e9) return `${num(v / 1e9, 2)} مليار`;
  if (v >= 1e6) return `${num(v / 1e6, 1)} مليون`;
  return num(v);
}

const RANGES = [
  { days: 7, label: "أسبوعي" },
  { days: 30, label: "شهري" },
] as const;

export default function SpecialDeals({ onOpen }: { onOpen?: (s: string) => void }) {
  /* مدًى كالمفكرة بأمر المالك: سجلُّ عملياتٍ بالتاريخ لا لقطةٌ لحظية. */
  const [days, setDays] = useState<number>(30);
  const { data, isLoading } = useQuery({
    queryKey: ["special-deals", days],
    queryFn: () => marketApi.specialDeals(days).then(r => r.data.data),
    refetchInterval: 10 * 60 * 1000,
    staleTime: 2 * 60 * 1000,
  });

  const deals: Deal[] = data?.deals ?? [];
  const biggest = deals.reduce((a, d) => Math.max(a, d.value || 0), 0);

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Handshake size={16} className="text-[var(--brand-ink)]" />
        <h2 className="card-title">صفقات خاصة</h2>
        <div className="ms-auto flex rounded-lg border border-[var(--line)] overflow-hidden">
          {RANGES.map(r => (
            <button key={r.days} onClick={() => setDays(r.days)}
                    aria-pressed={days === r.days}
                    className="px-2.5 py-1 text-[11px] font-bold min-h-[32px]"
                    style={days === r.days
                      ? { background: "var(--brand-ink)", color: "var(--on-brand)" }
                      : { color: "var(--ink-muted)" }}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <p className="py-8 text-center text-[13px] text-[var(--ink-muted)]">…</p>
      ) : !deals.length ? (
        <p className="py-8 text-center text-[13px] text-[var(--ink-muted)]">
          لا صفقات خاصة في هذه المدة.
        </p>
      ) : (
        <>
          {/* الجوّال بطاقات، واللوحيُّ فما فوق جدول — النمطُ نفسُه في
              «القوائم المالية»: جدولٌ بعرض 520px لا يُقرأ في 390px. */}
          <div className="md:hidden space-y-2">
            {deals.map((d, i) => (
              <button key={`${d.symbol}-${i}`} onClick={() => onOpen?.(d.symbol)}
                      className="w-full text-right rounded-xl border border-[var(--line)] p-2.5">
                <div className="flex items-baseline gap-2">
                  <span className="font-bold text-[13px] text-[var(--ink)]">
                    {d.name || d.symbol}
                  </span>
                  <span className="text-[11px] text-[var(--ink-muted)] tabular-nums">
                    {d.symbol}
                  </span>
                  <span className="ms-auto font-bold tabular-nums text-[13px] text-[var(--ink)]">
                    {money(d.value)} ﷼
                  </span>
                </div>
                <div className="mt-1 flex items-baseline gap-3 text-[11px] text-[var(--ink-muted)] tabular-nums">
                  <span>{num(d.price, 2)} ﷼</span>
                  <span>{num(d.quantity)} سهم</span>
                  {d.at && <span className="ms-auto">{d.at}</span>}
                </div>
              </button>
            ))}
          </div>

          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-right text-[12.5px]">
              <thead>
                <tr className="text-[var(--ink-muted)] text-[11px]">
                  <th className="py-1.5 font-normal">الشركة</th>
                  <th className="py-1.5 font-normal">الرمز</th>
                  <th className="py-1.5 font-normal">السعر</th>
                  <th className="py-1.5 font-normal">الكمية</th>
                  <th className="py-1.5 font-normal">القيمة</th>
                  <th className="py-1.5 font-normal">التاريخ</th>
                </tr>
              </thead>
              <tbody>
                {deals.map((d, i) => (
                  <tr key={`${d.symbol}-${i}`}
                      onClick={() => onOpen?.(d.symbol)}
                      className="border-t border-[var(--line)] cursor-pointer">
                    <td className="py-1.5 text-[var(--ink)]">{d.name || "—"}</td>
                    <td className="py-1.5 tabular-nums text-[var(--ink-muted)]">{d.symbol}</td>
                    <td className="py-1.5 tabular-nums text-[var(--ink)]">{num(d.price, 2)}</td>
                    <td className="py-1.5 tabular-nums text-[var(--ink)]">{num(d.quantity)}</td>
                    <td className="py-1.5 tabular-nums font-bold text-[var(--ink)]">
                      {money(d.value)}
                      {/* الأكبرُ يُعلَم: حجمُ الصفقة هو معناها. */}
                      {d.value === biggest && biggest > 0 && (
                        <span className="ms-1.5 text-[10px] font-bold text-[var(--brand-ink)]">
                          الأكبر
                        </span>
                      )}
                    </td>
                    <td className="py-1.5 tabular-nums text-[var(--ink-muted)]">{d.at || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex items-center gap-3 text-[11px] text-[var(--ink-muted)] tabular-nums">
            <span>{deals.length} صفقة</span>
            <span>
              إجمالي {money(deals.reduce((a, d) => a + (d.value || 0), 0))} ﷼
            </span>
            {data?.as_of && <span className="ms-auto">{String(data.as_of).slice(0, 16)}</span>}
          </div>
        </>
      )}
    </div>
  );
}
