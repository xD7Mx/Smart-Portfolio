import React, { useState } from "react";
import { Eye, Download, FileText } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { marketApi } from "../../services/api";
import ReportViewer from "../reports/ReportViewer";
import CompanyReportDocument, { qName } from "../reports/CompanyReportDocument";

/* ══ تقاريرُ الشركة ══ (D528 · D531 · D544) — كلُّ ربعٍ وكلُّ سنة، بورق تقرير
   المحفظة وعارضه وتصديره نفسِها: «عرض» و«تحميل» كأرشيف التقارير. */

type Pick = { asOf: string; kind: "quarter" | "annual"; download?: boolean };

function CompanyReportModal({ symbol, pick, onClose }: { symbol: string; pick: Pick; onClose: () => void }) {
  const { data } = useQuery({
    queryKey: ["quarter-report", symbol, pick.asOf, pick.kind],
    queryFn: () => marketApi.quarterReport(symbol, pick.asOf, pick.kind).then(x => x.data?.data || null),
    staleTime: 30 * 60 * 1000,
  });
  const label = pick.kind === "annual" ? `التقرير السنوي ${pick.asOf.slice(0, 4)}` : `تقرير ${qName(pick.asOf)}`;
  return (
    <ReportViewer data={data} title={label} filename={`${symbol}-${label}.png`} autoDownload={!!pick.download}
      onClose={onClose} render={ref => <CompanyReportDocument ref={ref} data={data} />} />
  );
}

export default function QuarterReport({ symbol }: { symbol: string }) {
  const [open, setOpen] = useState<Pick | null>(null);
  const { data: cat, isLoading } = useQuery({
    queryKey: ["quarter-reports", symbol],
    queryFn: () => marketApi.quarterReports(symbol).then(x => x.data?.data || null),
    staleTime: 30 * 60 * 1000,
  });
  if (isLoading) return <div className="h-40 skeleton rounded-xl" />;
  const items: (Pick & { type: string; label: string })[] = [
    ...(cat?.years || []).map((y: string) => ({ asOf: y, kind: "annual" as const, type: "سنوي", label: `النتائج السنوية ${y.slice(0, 4)}` })),
    ...(cat?.quarters || []).map((q: string) => ({ asOf: q, kind: "quarter" as const, type: "ربع سنوي", label: `نتائج ${qName(q)}` })),
  ].sort((a, b) => (a.asOf < b.asOf ? 1 : a.asOf > b.asOf ? -1 : a.kind === "annual" ? -1 : 1));
  return (
    <div className="card p-0">
      <div className="flex items-center gap-2 p-4 border-b border-[var(--hairline)]">
        <FileText size={16} className="text-[var(--brand-ink)]" />
        <h2 className="card-title">تقارير الشركة</h2>
      </div>
      {!items.length ? (
        <div className="text-center py-12 text-[var(--ink-muted)]">
          <FileText size={32} className="mx-auto mb-2 opacity-50" />
        </div>
      ) : (
        <>
          <div className="md:hidden p-3 space-y-2.5">
            {items.map(it => (
              <div key={it.kind + it.asOf} className="rounded-xl border border-[var(--hairline)] panel p-3.5">
                <div className="flex items-center justify-between gap-2 mb-2.5">
                  <span className="tag-b">{it.type}</span>
                  <span className="text-[11px] text-[var(--ink-muted)] tabular-nums">{it.asOf}</span>
                </div>
                <p className="text-[var(--ink)] text-sm font-semibold mb-3">{it.label}</p>
                <div className="flex items-center gap-2">
                  <button onClick={() => setOpen(it)} className="btn-ghost flex-1 justify-center !py-2 text-xs">
                    <Eye size={14} /> عرض
                  </button>
                  <button onClick={() => setOpen({ ...it, download: true })} className="btn-ghost flex-1 justify-center !py-2 text-xs">
                    <Download size={14} /> تحميل
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--hairline)]">
                  <th className="th text-start">النوع</th>
                  <th className="th text-start">الفترة</th>
                  <th className="th text-start">نهاية الفترة</th>
                  <th className="th text-start">الإجراءات</th>
                </tr>
              </thead>
              <tbody>
                {items.map(it => (
                  <tr key={it.kind + it.asOf} className="hover:bg-[var(--field)] transition-colors">
                    <td className="td"><span className="tag-b">{it.type}</span></td>
                    <td className="td text-[var(--ink)]">{it.label}</td>
                    <td className="td text-[var(--ink-muted)] tabular-nums">{it.asOf}</td>
                    <td className="td">
                      <div className="flex items-center gap-1">
                        <button onClick={() => setOpen(it)} title="عرض" className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--brand-ink)] transition-all">
                          <Eye size={15} />
                        </button>
                        <button onClick={() => setOpen({ ...it, download: true })} title="تحميل صورة" className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--pos-ink)] transition-all">
                          <Download size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {open && <CompanyReportModal symbol={symbol} pick={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
