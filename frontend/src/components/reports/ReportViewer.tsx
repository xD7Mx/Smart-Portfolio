import React, { useState, useRef } from "react";
import { FileText, X, Download } from "lucide-react";

/* ══ عارضُ الورقة الواحد ══ (D544) — تقاريرُ المحفظة وتقاريرُ الشركات بورقٍ
   واحدٍ ومعاينةٍ واحدةٍ وتصديرٍ واحد: الهويّةُ البصريةُ لا تهتزّ بين تقريرين. */

export const REPORT_WIDTH = 794;

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

export default function ReportViewer({ data, title, filename, render, autoDownload = false, onClose }: {
  data: any; title: string; filename: string;
  render: (ref: React.Ref<HTMLDivElement>) => React.ReactNode;
  autoDownload?: boolean; onClose: () => void;
}) {
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
      await deliverBlob(blob, filename);
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
            <h2 className="modal-title truncate">{title}</h2>
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
                {render(previewRef)}
              </div>
            </div>
            {isMobilePreview && (
              <p className="text-[11px] text-[var(--ink-muted)] text-center mt-2">
                {zoomed ? "اضغط للتصغير ومطابقة الشاشة" : "اضغط على التقرير لتكبيره وقراءته بوضوح"}
              </p>
            )}
            {/* Off-screen, always true-size, never transformed — export source only. */}
            <div style={{ position: "fixed", top: 0, insetInlineStart: -99999, pointerEvents: "none" }} aria-hidden>
              {render(exportRef)}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

