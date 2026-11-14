/* ══ تقسيمُ الشراء بين إعادة الاستثمار والسيولة — آليّاً ══ (بأمر المالك 2026-11-14 · D730)
   «أنا أضع عدد الأسهم والسعر… والتطبيق يحسب مباشرةً كم نصيبها من إعادة الاستثمار — بدون إدخالٍ مني».
   فلا اختيارَ للتمويل في نافذة المعاملة: الخادمُ يحسب التقسيمَ بالدالّة نفسِها التي يحفظ بها، وهنا يُعرض قبل
   التأكيد، والعددُ المعروضُ يُرسَل مع الحفظ — فإن تغيّر بين المعاينة والحفظ رُفضت العملية ولم يُحفظ شيء.
   وبلا معاينةٍ (خطأ شبكة) لا يُسجَّل الشراء: لا تقسيمَ مُخمَّن. */
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { transactionsApi } from "../../services/api";

export type FundingSplitData = {
  reinvest_qty: number; liquidity_qty: number;
  reinvest_amount: number; liquidity_amount: number;
  company_share: number; headroom: number;
};

/* المعاينةُ بعد توقّف الكتابة قليلاً — «372» تُكتب «3» ثمّ «37»، ولا داعي لثلاثة طلبات */
export function useFundingSplit(companyId: number, active: boolean, shares: string, price: string, date: string) {
  const q = Number(shares), p = Number(price);
  const ready = active && q > 0 && p > 0 && Number.isFinite(q) && Number.isFinite(p);
  const key = ready ? `${q}|${p}|${date}` : "";
  const [settled, setSettled] = useState(key);
  useEffect(() => { const t = setTimeout(() => setSettled(key), 250); return () => clearTimeout(t); }, [key]);
  const query = useQuery({
    queryKey: ["funding-preview", companyId, settled],
    queryFn: () => transactionsApi.fundingPreview({ company_id: companyId, quantity: q, price: p, transaction_date: date })
      .then(r => r.data.data as FundingSplitData),
    enabled: ready && settled === key,
    staleTime: 0, gcTime: 0, retry: 1,
  });
  const split = ready && settled === key ? query.data : undefined;
  return { split, ready, pending: ready && !split && !query.isError, error: ready && query.isError, refetch: query.refetch };
}

const n0 = (v: number) => (Number(v) || 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
const n2 = (v: number) => (Number(v) || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function FundingSplit({ split, pending, error }: { split?: FundingSplitData; pending: boolean; error: boolean }) {
  if (error) {
    return <div data-role="funding-split" className="funding-split funding-split-err">تعذّر حسابُ التمويل — لا يُسجَّل الشراءُ دونه. أعد المحاولة.</div>;
  }
  if (!split) {
    return pending ? <div data-role="funding-split" className="funding-split"><div className="h-9 skeleton rounded-lg" /></div> : null;
  }
  const cell = (label: string, qty: number, amt: number, tone: string, role: string) => (
    <div data-role={role} className="min-w-0">
      <div className="text-[10px] text-[var(--ink-muted)]">{label}</div>
      <div className="text-[13px] font-bold tabular-nums mt-0.5" style={{ color: qty > 0 ? tone : "var(--ink-muted)" }}>
        <span dir="ltr">{n0(qty)}</span> <span className="text-[10px] font-normal">سهم</span>
      </div>
      <div className="text-[10px] tabular-nums text-[var(--ink-muted)]" dir="ltr" style={{ textAlign: "right" }}>{n2(amt)}</div>
    </div>
  );
  return (
    <div data-role="funding-split" className="funding-split grid grid-cols-2 gap-3"
      title={`نصيبُ الشركة من إعادة الاستثمار ${n2(split.company_share)}`}>
      {cell("من إعادة الاستثمار", split.reinvest_qty, split.reinvest_amount, "var(--brand-ink)", "split-reinvest")}
      {cell("من السيولة", split.liquidity_qty, split.liquidity_amount, "var(--pos-ink)", "split-liquidity")}
    </div>
  );
}
