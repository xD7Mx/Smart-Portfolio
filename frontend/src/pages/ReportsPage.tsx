import React, { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { reportsApi, portfoliosApi } from "../services/api";
import PortfolioScopeBadge from "../components/common/PortfolioScopeBadge";
import { FileText, FilePlus, Eye, X, Trash2, Download } from "lucide-react";
import { useT } from "../i18n";
import { useAuthStore } from "../store/authStore";
import ReportDocument from "../components/reports/ReportDocument";

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

const REPORT_WIDTH = 794;

// html-to-image's AUTOMATIC font embedding walks document.styleSheets to
// inline @font-face rules into the exported SVG — a step that fails
// silently on some devices (notably mobile Safari/Chrome, depending on
// how the stylesheet was cached), and the rasterized image then falls
// back to the platform's default font: the downloaded report suddenly
// isn't in the site's own typeface. Building the @font-face CSS ourselves
// (fetch each woff2 → base64 data URI) and handing it to toPng via
// `fontEmbedCSS` (+ skipFonts to disable the fragile automatic path)
// makes the export deterministic on every device. Vite fingerprints the
// font URLs at build time via new URL(..., import.meta.url).
const REPORT_FONTS: [string, string][] = [
  ["300", new URL("../assets/fonts/thmanyahserifdisplay-Light.woff2", import.meta.url).href],
  ["400", new URL("../assets/fonts/thmanyahserifdisplay-Regular.woff2", import.meta.url).href],
  ["500", new URL("../assets/fonts/thmanyahserifdisplay-Medium.woff2", import.meta.url).href],
  ["700", new URL("../assets/fonts/thmanyahserifdisplay-Bold.woff2", import.meta.url).href],
];

let fontEmbedCssPromise: Promise<string> | null = null;
function getFontEmbedCss(): Promise<string> {
  if (!fontEmbedCssPromise) {
    fontEmbedCssPromise = Promise.all(REPORT_FONTS.map(async ([weight, url]) => {
      const buf = await fetch(url).then(r => {
        if (!r.ok) throw new Error(`font fetch ${r.status}`);
        return r.arrayBuffer();
      });
      const bytes = new Uint8Array(buf);
      let bin = "";
      for (let i = 0; i < bytes.length; i += 0x8000) {
        bin += String.fromCharCode(...Array.from(bytes.subarray(i, i + 0x8000)));
      }
      return `@font-face{font-family:'Thmanyah Serif Display';src:url(data:font/woff2;base64,${btoa(bin)}) format('woff2');font-weight:${weight};font-style:normal;}`;
    })).then(parts => parts.join("\n"))
      .catch(err => { fontEmbedCssPromise = null; throw err; });
  }
  return fontEmbedCssPromise;
}

function ReportModal({ id, autoDownload = false, onClose }: { id: number; autoDownload?: boolean; onClose: () => void }) {
  const { data } = useQuery({ queryKey: ["report", id], queryFn: () => reportsApi.get(id).then(r => r.data.data) });
  // The on-screen preview and the exported image are two SEPARATE DOM nodes
  // on purpose: the preview scales visually (transform:scale) to fit phone/
  // tablet/desktop, while the export captures a second, always off-screen,
  // never-transformed copy at true 794px — guaranteeing a byte-identical
  // image regardless of device or screen size the click happened on.
  const previewRef = useRef<HTMLDivElement>(null);
  const exportRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [exporting, setExporting] = useState(false);
  // null = not measured yet — the preview stays hidden for that first frame,
  // so the phone never flashes the huge unscaled document before fitting.
  const [scale, setScale] = useState<number | null>(null);
  const [docHeight, setDocHeight] = useState(0);
  // Fitting the full 794px document to a phone's ~350px width shrinks text
  // to single digits — technically "fits" but unreadable. Instead of forcing
  // that tiny scale, let a tap zoom the preview to a comfortably readable
  // size and pan/scroll around it, like any document viewer on mobile.
  const [zoomed, setZoomed] = useState(false);
  const fitScale = scale ?? 1;
  const isMobilePreview = fitScale < 0.85;
  const effectiveScale = isMobilePreview && zoomed ? 0.75 : fitScale;

  // Fits the fixed-width canvas to whatever space is actually available
  // (phone/tablet/desktop) instead of forcing horizontal scroll on small
  // screens — the document itself always stays true-size pixels underneath.
  // useLayoutEffect + an immediate synchronous measure: the scale is known
  // BEFORE the first paint, so the first open renders already fitted (the
  // old useEffect-only path painted one huge unscaled frame first on phones).
  React.useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const measure = () => {
      const w = el.getBoundingClientRect().width;
      if (w) setScale(Math.min(1, (w - 16) / REPORT_WIDTH));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
    // data ضمن التبعيات عمداً: في الفتح الأول تصل البيانات بعد التركيب،
    // فتُرسم الحاوية لاحقاً — بدون إعادة التشغيل يبقى القياس فاشلاً
    // (containerRef=null) وتبقى المعاينة مخفية إلى الأبد (فراغ أول فتح).
  }, [data]);

  // transform:scale() doesn't shrink the layout box, so without this the
  // container below the shrunk preview would leave dead scroll space equal
  // to the difference between natural and scaled height.
  React.useEffect(() => {
    const el = previewRef.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => setDocHeight(entries[0]?.contentRect.height || 0));
    ro.observe(el);
    return () => ro.disconnect();
  }, [data]);

  const [exportError, setExportError] = useState<string | null>(null);

  // ── Hardened capture: html-to-image (SVG <foreignObject> rendered by the
  // browser's own engine — correct Arabic shaping everywhere, unlike
  // html2canvas) + every reliability workaround stacked:
  //  • fonts.load + fonts.ready before capture (mobile races).
  //  • deterministic base64 font embedding (see getFontEmbedCss).
  //  • toBlob, not a giant data-URL on an anchor (URL-length limits).
  //  • warm-up passes until two consecutive captures agree in size —
  //    WebKit/Safari is known to rasterize the FIRST pass before fonts
  //    finish decoding inside the SVG image; repeating until stable (max 4)
  //    guarantees the shipped image is the fully-rendered one.
  //  • result sanity check (blob exists and isn't suspiciously tiny).
  const captureBlob = async (node: HTMLElement): Promise<Blob> => {
    await Promise.all([
      "300 16px 'Thmanyah Serif Display'",
      "400 16px 'Thmanyah Serif Display'",
      "500 16px 'Thmanyah Serif Display'",
      "700 16px 'Thmanyah Serif Display'",
    ].map(f => document.fonts.load(f).catch(() => {})));
    await document.fonts.ready;

    let fontEmbedCSS: string | undefined;
    try { fontEmbedCSS = await getFontEmbedCss(); } catch { fontEmbedCSS = undefined; }

    const { toBlob } = await import("html-to-image");
    const opts = {
      pixelRatio: 2, backgroundColor: "#faf6ee", cacheBust: true,
      ...(fontEmbedCSS ? { fontEmbedCSS, skipFonts: true } : {}),
    };
    let prev: Blob | null = null;
    for (let pass = 0; pass < 4; pass++) {
      const b = await toBlob(node, opts);
      if (b && b.size > 10_000) {
        if (prev && Math.abs(b.size - prev.size) < 256) return b; // stable across passes
        prev = b;
      }
    }
    if (prev) return prev;
    throw new Error("capture produced no image");
  };

  // ── Hardened delivery: prefer a real download; where the download
  // attribute is ignored (in-app webviews, old iOS), fall back to the
  // native share sheet with the actual file; as a last resort open the
  // image in a new tab so the user can long-press-save. Object URLs are
  // revoked after use.
  const deliverBlob = async (blob: Blob, filename: string) => {
    const file = new File([blob], filename, { type: "image/png" });
    const canAnchorDownload = "download" in HTMLAnchorElement.prototype;
    if (canAnchorDownload) {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
      return;
    }
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file], title: filename });
      return;
    }
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };

  const downloadImage = async (): Promise<boolean> => {
    if (!exportRef.current) return false;
    setExporting(true);
    setExportError(null);
    try {
      let blob: Blob;
      try {
        blob = await captureBlob(exportRef.current);
      } catch {
        // One automatic retry — transient failures (font fetch hiccup,
        // first-open race) usually succeed on the second attempt.
        await new Promise(r => setTimeout(r, 400));
        blob = await captureBlob(exportRef.current);
      }
      await deliverBlob(blob, `تقرير-${data?.period || id}.png`);
      return true;
    } catch (e) {
      // AbortError = the user simply dismissed the share sheet — not a failure.
      if ((e as any)?.name !== "AbortError") {
        setExportError("تعذر إنشاء صورة التقرير على هذا الجهاز — أعد المحاولة، وإن تكرر الخطأ حدّث الصفحة ثم جرّب مجدداً.");
      }
      return false;
    } finally {
      setExporting(false);
    }
  };

  React.useEffect(() => {
    if (autoDownload && data) {
      // Close only on SUCCESS — closing after a silent failure looked like
      // the download "just didn't happen" with no explanation.
      const t = setTimeout(async () => { if (await downloadImage()) onClose(); }, 300);
      return () => clearTimeout(t);
    }
  }, [autoDownload, data]);

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      style={{ padding: "16px", alignItems: "flex-start", overflowY: "auto" }}>
      <div className="modal-box fade-in" style={{ maxWidth: 830, width: "100%", maxHeight: "95vh", overflowY: "auto", margin: "16px auto", padding: 0, background: "transparent", border: "none" }}>
        <div className="flex items-center justify-between gap-2 mb-3 px-1">
          <div className="flex items-center gap-2 min-w-0">
            <FileText size={18} className="text-[var(--brand-ink)] shrink-0" />
            <h2 className="modal-title truncate">تقرير {data?.period || ""}</h2>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button className="btn-ghost text-xs" onClick={downloadImage} disabled={exporting}>
              <Download size={13} />
              <span className="hidden sm:inline">{exporting ? "جارٍ التصدير…" : "تحميل صورة"}</span>
            </button>
            <button onClick={onClose} title="إغلاق" aria-label="إغلاق" className="text-[var(--ink-muted)] hover:text-[var(--ink)] p-2 -m-1"><X size={18} /></button>
          </div>
        </div>
        {exportError && (
          <div className="mb-3 px-3 py-2.5 rounded-xl text-xs flex items-center gap-2"
            style={{ background: "transparent", color: "var(--neg-ink)", border: "1px solid var(--hairline)" }}>
            <span>⚠</span>
            <span className="flex-1">{exportError}</span>
            <button className="font-bold underline shrink-0" onClick={downloadImage} disabled={exporting}>إعادة المحاولة</button>
          </div>
        )}
        {!data ? <div className="py-10 text-center text-[var(--ink-muted)] text-sm">جارٍ التحميل...</div> : (
          <>
            {/* justify-content:center on the container, not margin:auto on the
                scaled child — auto-margins are computed against the child's
                UNSCALED 794px box, so they overflowed the (smaller) mobile
                container equally on both sides and clipped to whatever
                landed inside, not necessarily the visual center. Centering
                on the flex parent instead handles the scale transform
                correctly on every screen size. */}
            <div
              ref={containerRef}
              onClick={() => isMobilePreview && setZoomed(z => !z)}
              style={{
                width: "100%",
                overflow: zoomed ? "auto" : "hidden",
                maxHeight: zoomed ? "70vh" : undefined,
                height: !zoomed && docHeight ? docHeight * effectiveScale : undefined,
                display: "flex",
                justifyContent: zoomed ? "flex-start" : "center",
                touchAction: zoomed ? "pan-x pan-y" : undefined,
                cursor: isMobilePreview ? (zoomed ? "zoom-out" : "zoom-in") : undefined,
              }}
            >
              <div style={{ transform: `scale(${effectiveScale})`, transformOrigin: "top center", width: REPORT_WIDTH, flexShrink: 0,
                            visibility: scale === null ? "hidden" : "visible" }}>
                <ReportDocument ref={previewRef} data={data} />
              </div>
            </div>
            {isMobilePreview && (
              <p className="text-[11px] text-[var(--ink-muted)] text-center mt-2">
                {zoomed ? "اضغط للتصغير ومطابقة الشاشة" : "اضغط على التقرير لتكبيره وقراءته بوضوح"}
              </p>
            )}
            {/* Off-screen, always true-size, never transformed — export source only. */}
            <div style={{ position: "fixed", top: 0, insetInlineStart: -99999, pointerEvents: "none" }} aria-hidden>
              <ReportDocument ref={exportRef} data={data} />
            </div>
          </>
        )}
      </div>
    </div>
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
  const genMutation = useMutation({
    mutationFn: (type: string) => reportsApi.generate(type).then(r => r.data),
    onSuccess: (r: any) => {
      qc.invalidateQueries({ queryKey: ["reports"] });
      if (r?.data?.id) setViewId(r.data.id);
    },
  });
  const delMutation = useMutation({
    mutationFn: (id: number) => reportsApi.remove(id).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports"] }),
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
                    <span className="tag-b">{r.type}</span>
                    <span className="text-[11px] text-[var(--ink-muted)]">{r.generated_at ? new Date(r.generated_at).toLocaleDateString("en-GB") : "—"}</span>
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
                      <td className="td"><span className="tag-b">{r.type}</span></td>
                      <td className="td text-[var(--ink-muted)]">{r.period ?? "—"}</td>
                      <td className="td text-[var(--ink-muted)]">{r.generated_at ? new Date(r.generated_at).toLocaleDateString("en-GB") : "—"}</td>
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
                              /* نفس تأكيد نسخة الكمبيوتر — هذه بطاقة الجوال. */
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
