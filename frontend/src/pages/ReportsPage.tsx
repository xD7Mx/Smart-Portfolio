import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { reportsApi, portfoliosApi } from "../services/api";
import PortfolioScopeBadge from "../components/common/PortfolioScopeBadge";
import { FileText, FilePlus, Eye, Trash2, Download } from "lucide-react";
import { useT } from "../i18n";
import { useAuthStore } from "../store/authStore";
import ReportDocument from "../components/reports/ReportDocument";
import ReportViewer from "../components/reports/ReportViewer";

// الكمبيوتر: صفّ متسلسل (أسبوعي ← شهري ← ربع سنوي ← سنوي).
const TYPES = [
  { key: "WEEKLY",    label: "أسبوعي" },
  { key: "MONTHLY",   label: "شهري" },
  { key: "QUARTERLY", label: "ربع سنوي" },
  { key: "ANNUAL",    label: "سنوي" },
];
// الجوال: شبكة 2×2 (RTL) — يمينًا أسبوعي فوق شهري، يسارًا ربع سنوي فوق سنوي.
const TYPES_MOBILE = [
  { key: "WEEKLY",    label: "أسبوعي" },
  { key: "QUARTERLY", label: "ربع سنوي" },
  { key: "MONTHLY",   label: "شهري" },
  { key: "ANNUAL",    label: "سنوي" },
];

/* ══ نوعُ التقرير بالعربية، وتاريخٌ بصيغةٍ واحدةٍ في التطبيق ══ (D333)
   كان الأرشيفُ يعرض `WEEKLY` و`MONTHLY` نصّاً إنجليزياً في شاشةٍ عربيةٍ
   كاملة — والخادمُ يملك الترجمةَ ويستعملها في سطر الفترة وحدَه. وكان
   التاريخُ `en-GB` (‏16/09/2026) في القائمة و`ar-EG…nu-latn` في الورقة:
   قيمةٌ واحدةٌ بصيغتين في الميزة نفسِها. فصارت الترجمةُ والصيغةُ واحدة. */
const TYPE_AR: Record<string, string> = {
  DAILY: "يومي", WEEKLY: "أسبوعي", MONTHLY: "شهري",
  QUARTERLY: "ربع سنوي", ANNUAL: "سنوي",
};
const typeAr = (t?: string | null) => TYPE_AR[String(t || "").toUpperCase()] || t || "—";
const dateAr = (v?: string | null) => {
  if (!v) return "—";
  const d = new Date(v);
  return isNaN(d.getTime()) ? "—"
    : d.toLocaleDateString("ar-EG-u-ca-gregory-nu-latn");
};

function ReportModal({ id, autoDownload = false, onClose }: { id: number; autoDownload?: boolean; onClose: () => void }) {
  const { data } = useQuery({ queryKey: ["report", id], queryFn: () => reportsApi.get(id).then(r => r.data.data) });
  return (
    <ReportViewer data={data} title={`تقرير ${data?.period || ""}`} filename={`تقرير-${data?.period || id}.png`}
      autoDownload={autoDownload} onClose={onClose} render={ref => <ReportDocument ref={ref} data={data} />} />
  );
}

export default function ReportsPage() {
  const t = useT();
  const qc = useQueryClient();
  const { isOwner } = useAuthStore();
  const [viewId, setViewId] = useState<number | null>(null);
  const [downloadId, setDownloadId] = useState<number | null>(null);
  const { data: reports = [] } = useQuery({
    queryKey: ["reports"],
    queryFn: () => reportsApi.list().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
  });
  /* ══ وتعذُّرٌ يُعلَن لا يُبتلع ══ (D333)
     كان الزرُّ يُضغَط فيرجع بلا تقرير وبلا كلمة: لا `onError` في الإنشاء
     ولا في الحذف. فعطبُ الخادم يبدو للمالك «زرّاً لا يعمل» — وهو صنفُ
     الصمت الذي أُسجّله في كل مرّة. */
  const [failure, setFailure] = useState<string | null>(null);
  const why = (e: any) =>
    String(e?.response?.data?.detail || e?.response?.data?.message
           || e?.message || e).slice(0, 160);
  const genMutation = useMutation({
    mutationFn: (type: string) => reportsApi.generate(type).then(r => r.data),
    onSuccess: (r: any) => {
      setFailure(null);
      qc.invalidateQueries({ queryKey: ["reports"] });
      if (r?.data?.id) setViewId(r.data.id);
      else setFailure("أُنشئ التقريرُ ولم يُعَد معرِّفُه — افتحه من الأرشيف.");
    },
    onError: (e: any) => setFailure(`تعذّر إنشاءُ التقرير: ${why(e)}`),
  });
  const delMutation = useMutation({
    mutationFn: (id: number) => reportsApi.remove(id).then(r => r.data),
    onSuccess: () => { setFailure(null); qc.invalidateQueries({ queryKey: ["reports"] }); },
    onError: (e: any) => setFailure(`تعذّر حذفُ التقرير: ${why(e)}`),
  });

  return (
    <div className="space-y-5 fade-in">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-medium text-[var(--ink)]">{t("reports.title")}</h1>
        </div>
        <div className="shrink-0"><PortfolioScopeBadge /></div>
      </div>

      {/* Generate card — the button the report is created from */}
      {isOwner && (
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <FilePlus size={16} className="text-[var(--pos-ink)]" />
          <h2 className="card-title">إنشاء تقرير جديد</h2>
        </div>
        {/* Mobile: 2×2 grid (two right, two left) to fill the space nicely;
            desktop: wrap row. */}
        {/* الجوال: شبكة 2×2 · الكمبيوتر: صفّ متسلسل */}
        <div className="grid grid-cols-2 gap-2 sm:hidden">
          {TYPES_MOBILE.map(item => (
            <button key={item.key} className="btn-primary w-full justify-center" disabled={genMutation.isPending}
              onClick={() => genMutation.mutate(item.key)}>
              <FilePlus size={15} /> تقرير {item.label}
            </button>
          ))}
        </div>
        <div className="hidden sm:flex sm:flex-wrap gap-2">
          {TYPES.map(item => (
            <button key={item.key} className="btn-primary justify-center" disabled={genMutation.isPending}
              onClick={() => genMutation.mutate(item.key)}>
              <FilePlus size={15} /> تقرير {item.label}
            </button>
          ))}
        </div>
        {genMutation.isPending && <p className="text-xs text-[var(--ink-muted)] mt-2">جارٍ إنشاء التقرير...</p>}
        {failure && (
          <p className="text-xs mt-2" style={{ color: "var(--neg-ink)" }}>{failure}</p>
        )}
      </div>
      )}

      <div className="card p-0">
        <div className="flex items-center gap-2 p-4 border-b border-[var(--hairline)]">
          <FileText size={16} className="text-[var(--brand-ink)]" />
          <h2 className="card-title">أرشيف التقارير</h2>
        </div>
        {reports.length === 0 ? (
          <div className="text-center py-12 text-[var(--ink-muted)]">
            <FileText size={32} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">لا توجد تقارير بعد — أنشئ أول تقرير من الأعلى.</p>
          </div>
        ) : (
          <>
            {/* Mobile: one clear card per report — no horizontal scroll. */}
            <div className="md:hidden p-3 space-y-2.5">
              {reports.map((r: any) => (
                <div key={r.id} className="rounded-xl border border-[var(--hairline)] panel p-3.5">
                  <div className="flex items-center justify-between gap-2 mb-2.5">
                    <span className="tag-b">{typeAr(r.type)}</span>
                    <span className="text-[11px] text-[var(--ink-muted)]">{dateAr(r.generated_at)}</span>
                  </div>
                  <p className="text-[var(--ink)] text-sm font-semibold mb-3">{r.period ?? "—"}</p>
                  <div className="flex items-center gap-2">
                    <button onClick={() => setViewId(r.id)} className="btn-ghost flex-1 justify-center !py-2 text-xs">
                      <Eye size={14} /> عرض
                    </button>
                    <button onClick={() => setDownloadId(r.id)} className="btn-ghost flex-1 justify-center !py-2 text-xs">
                      <Download size={14} /> تحميل
                    </button>
                    {isOwner && (
                      <button onClick={() => {
                        /* التقرير لقطةُ لحظةٍ بأسعارها وأرقامها؛ إعادة إنشائه
                           تُنتج تقريراً آخر لا نفسه. فحذفه فقدانٌ دائم. */
                        if (confirm(`حذف تقرير «${r.period ?? r.type}» نهائياً؟ لا يمكن استعادته — وإعادة الإنشاء تُنتج تقريراً بأرقام اليوم لا بأرقامه.`)) delMutation.mutate(r.id);
                      }} disabled={delMutation.isPending}
                        className="btn-ghost !px-3 !py-2 text-[var(--neg-ink)] hover:!text-[var(--neg-ink)]">
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Desktop: compact table. */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--hairline)]">
                    <th className="th text-start">النوع</th>
                    <th className="th text-start">الفترة</th>
                    <th className="th text-start">تاريخ الإنشاء</th>
                    <th className="th text-start">الإجراءات</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((r: any) => (
                    <tr key={r.id} className="hover:bg-[var(--field)] transition-colors">
                      <td className="td"><span className="tag-b">{typeAr(r.type)}</span></td>
                      <td className="td text-[var(--ink-muted)]">{r.period ?? "—"}</td>
                      <td className="td text-[var(--ink-muted)]">{dateAr(r.generated_at)}</td>
                      <td className="td">
                        <div className="flex items-center gap-1">
                          <button onClick={() => setViewId(r.id)} title="عرض" className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--brand-ink)] transition-all">
                            <Eye size={15} />
                          </button>
                          <button onClick={() => setDownloadId(r.id)} title="تحميل صورة" className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--pos-ink)] transition-all">
                            <Download size={15} />
                          </button>
                          {isOwner && (
                            <button onClick={() => {
                              /* نفس تأكيد بطاقة الجوّال — وهذا جدولُ الكمبيوتر. */
                              if (confirm(`حذف تقرير «${r.period ?? r.type}» نهائياً؟ لا يمكن استعادته — وإعادة الإنشاء تُنتج تقريراً بأرقام اليوم لا بأرقامه.`)) delMutation.mutate(r.id);
                            }} title="حذف" disabled={delMutation.isPending} className="p-1.5 rounded-lg text-[var(--ink-muted)] hover:text-[var(--neg-ink)] transition-all">
                              <Trash2 size={15} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {viewId != null && <ReportModal id={viewId} onClose={() => setViewId(null)} />}
      {downloadId != null && <ReportModal id={downloadId} autoDownload onClose={() => setDownloadId(null)} />}
    </div>
  );
}
