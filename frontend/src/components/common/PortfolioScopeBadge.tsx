/* وسم نطاق المحفظة — يقول أي محفظةٍ تصف أرقامُ هذه الصفحة.

   كان معرَّفاً داخل صفحة التقارير وحدها. ونسخه إلى الحوكمة وتحليل الذكاء كان
   سيُنتج ثلاث نسخٍ متطابقة اليوم تتباعد غداً مع أوّل تعديل — وهي العلّة التي
   تكرّرت في هذا التطبيق سبع مرّات. فنُقل هنا كما هو بلا تغيير في مظهره.

   وفي وضع التوحيد يقول «مجمّع» صراحةً: صفحةٌ تجمع محافظ عدّة وتبدو كأنها
   تصف واحدة هي أسوأ من صفحةٍ بلا وسم. */
import { useQuery } from "@tanstack/react-query";
import { portfoliosApi } from "../../services/api";
import { usePortfolioStore } from "../../store/portfolioStore";

export default function PortfolioScopeBadge() {
  const activeId = usePortfolioStore(s => s.activeId);
  const unified = usePortfolioStore(s => s.unified);
  const { data: portfolios = [] } = useQuery({
    queryKey: ["portfolios"],
    queryFn: () => portfoliosApi.list().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
  });

  if (unified) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold pill-o"
        style={{ background: "transparent", border: "1px solid var(--hairline)", color: "var(--brand-ink)" }}>
        مجمّع — كل المحافظ
      </span>
    );
  }

  const list = portfolios as any[];
  const active = list.find(p => String(p.id) === String(activeId)) || list.find(p => p.is_default) || list[0];
  if (!active) return null;

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold text-[var(--ink)]"
      style={{ background: "var(--panel)", border: "1px solid var(--line)" }}>
      <span className="w-2 h-2 rounded-full" style={{ background: active.color || "var(--chart-1)" }} />
      {active.name}
    </span>
  );
}
