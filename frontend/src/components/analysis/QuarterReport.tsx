import React, { useState } from "react";
import { Eye, FileDown, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { marketApi } from "../../services/api";

/* ══ تقريرُ الربع ══ (D528) — أرقامٌ وعناوين، بلا حواشٍ. */

const num = (v: any, d = 0) =>
  typeof v === "number" ? v.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d }) : "—";
const mn = (v: any, key: string) => (key === "eps" ? num(v, 2) : typeof v === "number" ? num(v / 1e6) : "—");
const pct = (v: any) => (typeof v === "number" ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}%` : "—");
const tone = (v: any) => (typeof v === "number" ? (v >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]") : "text-[var(--ink-muted)]");
const qName = (iso?: string) => {
  if (!iso) return "—";
  const m = Number(iso.slice(5, 7));
  return `الربع ${m <= 3 ? "الأول" : m <= 6 ? "الثاني" : m <= 9 ? "الثالث" : "الرابع"} ${iso.slice(0, 4)}`;
};
const REC_TONE: Record<string, string> = { "شراء": "var(--pos-ink)", "بيع": "var(--neg-ink)", "حياد": "var(--warn-ink)" };

export function QuarterReportView({ symbol, asOf, kind = "quarter" }: { symbol: string; asOf?: string; kind?: "quarter" | "annual" }) {
  const { data: r, isLoading } = useQuery({
    queryKey: ["quarter-report", symbol, asOf, kind],
    queryFn: () => marketApi.quarterReport(symbol, asOf, kind).then(x => x.data?.data || null),
    staleTime: 30 * 60 * 1000,
  });
  if (isLoading) return <div className="h-72 skeleton rounded-xl" />;
  if (!r) return <div className="card py-10 text-center text-sm text-[var(--ink-muted)]">غير متوفّر</div>;
  const h = r.header;
  const t = r.table || {};
  const kv = (label: string, v: React.ReactNode, cls = "text-[var(--ink)]") => (
    <div className="flex items-center justify-between gap-2 min-h-[32px] border-b border-[var(--hairline)] last:border-0">
      <span className="text-[12px] text-[var(--ink-muted)]">{label}</span>
      <span className={"text-[13px] font-bold tabular-nums " + cls} dir="ltr">{v}</span>
    </div>
  );
  return (
    <div className="space-y-3">
      <div className="card p-4 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-base font-bold text-[var(--ink)]">{t.annual ? `النتائج السنوية ${String(t.as_of || "").slice(0, 4)}` : `نتائج ${qName(t.as_of)}`}</h2>
          {!h ? null : h.recommendation
            ? <span className="px-3 py-1 rounded-lg text-[13px] font-bold border"
                style={{ color: REC_TONE[h.recommendation], borderColor: REC_TONE[h.recommendation] }}>{h.recommendation}</span>
            : <span className="text-[12px] text-[var(--ink-muted)]">غير متوفّر</span>}
        </div>
        {h && <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
          {kv("آخر سعر إغلاق", num(h.price, 2))}
          {kv("التغيّر", pct(h.change), tone(h.change))}
          {kv("السعر المستهدف خلال 12 شهراً", num(h.target_12m, 2))}
          {kv("عائد الأرباح الموزّعة", typeof h.dividend_yield === "number" ? `${h.dividend_yield.toFixed(1)}%` : "—")}
          {kv("إجمالي العوائد المتوقّعة", pct(h.total_return), tone(h.total_return))}
        </div>}
      </div>

      <div className="card p-0 overflow-x-auto">
        {!(t.rows || []).length ? (
          <div className="py-10 text-center text-sm text-[var(--ink-muted)]">غير متوفّر</div>
        ) : (
          <table className="w-full text-[12px] min-w-[620px]">
            <thead>
              <tr className="bg-[var(--surface)] text-[var(--ink-muted)]">
                <th className="text-right p-2 font-bold">البند</th>
                <th className="text-right p-2 font-bold">{qName(t.as_of)}</th>
                <th className="text-right p-2 font-bold">{t.annual ? String(t.prior_year || "").slice(0, 4) : qName(t.prior_year)}</th>
                <th className="text-right p-2 font-bold">التغيّر السنوي</th>
                {!t.annual && <th className="text-right p-2 font-bold">{qName(t.prev_quarter)}</th>}
                {!t.annual && <th className="text-right p-2 font-bold">التغيّر الربعي</th>}
                <th className="text-right p-2 font-bold">توقّعاتنا</th>
              </tr>
            </thead>
            <tbody>
              {t.rows.map((x: any) => (
                <tr key={x.key} className="border-t border-[var(--hairline)]">
                  <td className="p-2 text-[var(--ink)] font-semibold">{x.label}</td>
                  <td className="p-2 tabular-nums font-bold text-[var(--ink)]" dir="ltr" style={{ textAlign: "right" }}>{mn(x.cur, x.key)}</td>
                  <td className="p-2 tabular-nums text-[var(--ink)]" dir="ltr" style={{ textAlign: "right" }}>{mn(x.yoy_base, x.key)}</td>
                  <td className={"p-2 tabular-nums font-bold " + tone(x.yoy)} dir="ltr" style={{ textAlign: "right" }}>{pct(x.yoy)}</td>
                  {!t.annual && <td className="p-2 tabular-nums text-[var(--ink)]" dir="ltr" style={{ textAlign: "right" }}>{mn(x.prev, x.key)}</td>}
                  {!t.annual && <td className={"p-2 tabular-nums font-bold " + tone(x.qoq)} dir="ltr" style={{ textAlign: "right" }}>{pct(x.qoq)}</td>}
                  <td className="p-2 tabular-nums text-[var(--ink)]" dir="ltr" style={{ textAlign: "right" }}>{mn(x.expected, x.key)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="card p-4">
          <div className="text-[13px] font-bold text-[var(--ink)] mb-1">بيانات السوق</div>
          {kv("أعلى / أدنى سعر خلال 52 أسبوعاً", `${num(r.market?.high_52w, 2)} / ${num(r.market?.low_52w, 2)}`)}
          {kv("القيمة السوقية (مليون ريال)", typeof r.market?.market_cap === "number" ? num(r.market.market_cap / 1e6) : "—")}
          {kv("الأسهم (مليون سهم)", typeof r.market?.shares === "number" ? num(r.market.shares / 1e6) : "—")}
        </div>
        <div className="card p-4">
          <div className="text-[13px] font-bold text-[var(--ink)] mb-1">الأداء مقابل تاسي</div>
          <div className="grid grid-cols-3 gap-2 text-[11px] text-[var(--ink-muted)] min-h-[32px] items-center">
            <span>المدّة</span><span>السهم</span><span>تاسي</span>
          </div>
          {([["6m", "نصف عام"], ["1y", "عام"], ["2y", "عامان"]] as const).map(([k, lbl]) => (
            <div key={k} className="grid grid-cols-3 gap-2 min-h-[32px] items-center border-t border-[var(--hairline)] text-[13px]">
              <span className="text-[var(--ink)]">{lbl}</span>
              <span className={"tabular-nums font-bold " + tone(r.performance?.[k]?.stock)} dir="ltr" style={{ textAlign: "right" }}>{pct(r.performance?.[k]?.stock)}</span>
              <span className={"tabular-nums font-bold " + tone(r.performance?.[k]?.tasi)} dir="ltr" style={{ textAlign: "right" }}>{pct(r.performance?.[k]?.tasi)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ══ تقاريرُ الشركة (D531) — كلُّ ربعٍ وكلُّ سنة، بزرَّي «عرض» و«PDF» كتقارير المحفظة ══ */
export default function QuarterReport({ symbol }: { symbol: string }) {
  const [open, setOpen] = useState<{ asOf: string; kind: "quarter" | "annual"; print?: boolean } | null>(null);
  const { data: cat, isLoading } = useQuery({
    queryKey: ["quarter-reports", symbol],
    queryFn: () => marketApi.quarterReports(symbol).then(x => x.data?.data || null),
    staleTime: 30 * 60 * 1000,
  });
  React.useEffect(() => {
    if (!open?.print) return;
    const t = setTimeout(() => window.print(), 1200);
    return () => clearTimeout(t);
  }, [open]);
  if (isLoading) return <div className="h-40 skeleton rounded-xl" />;
  const items: { asOf: string; kind: "quarter" | "annual"; label: string }[] = [
    ...(cat?.years || []).map((y: string) => ({ asOf: y, kind: "annual" as const, label: `التقرير السنوي ${y.slice(0, 4)}` })),
    ...(cat?.quarters || []).map((q: string) => ({ asOf: q, kind: "quarter" as const, label: `تقرير ${qName(q)}` })),
  ].sort((a, b) => (a.asOf < b.asOf ? 1 : a.asOf > b.asOf ? -1 : a.kind === "annual" ? -1 : 1));
  return (
    <div className="space-y-3">
      <div className="card p-0">
        {!items.length ? (
          <div className="py-10 text-center text-sm text-[var(--ink-muted)]">غير متوفّر</div>
        ) : items.map(it => (
          <div key={it.kind + it.asOf} className="flex items-center gap-2 px-4 min-h-[48px] border-b border-[var(--hairline)] last:border-0">
            <span className="flex-1 text-[13px] font-semibold text-[var(--ink)]">{it.label}</span>
            <button type="button" onClick={() => setOpen({ asOf: it.asOf, kind: it.kind })}
              className="btn-ghost !py-1.5 text-xs min-h-[32px]"><Eye size={14} /> عرض</button>
            <button type="button" onClick={() => setOpen({ asOf: it.asOf, kind: it.kind, print: true })}
              className="btn-ghost !py-1.5 text-xs min-h-[32px]"><FileDown size={14} /> PDF</button>
          </div>
        ))}
      </div>
      {open && (
        <div className="fixed inset-0 z-50 overflow-y-auto p-3 sm:p-6" style={{ background: "color-mix(in srgb, var(--bg) 92%, transparent)" }}>
          <div className="max-w-3xl mx-auto space-y-3 print-area">
            <div className="flex justify-end no-print">
              <button type="button" onClick={() => setOpen(null)} aria-label="إغلاق"
                className="btn-ghost !p-2 min-h-[32px]"><X size={16} /></button>
            </div>
            <QuarterReportView symbol={symbol} asOf={open.asOf} kind={open.kind} />
          </div>
        </div>
      )}
    </div>
  );
}
