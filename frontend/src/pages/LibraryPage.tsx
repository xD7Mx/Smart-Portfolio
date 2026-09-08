import React, { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { libraryApi } from "../services/api";
import {
  Book, BookOpen, Plus, Download, X, Trash2, Sparkles, Loader2, Quote,
  BookText, GripVertical, ImagePlus, MoveVertical, MoveHorizontal,
  ChevronLeft, ChevronRight, Lightbulb, Bookmark, FileText,
} from "lucide-react";
import { useAuthStore } from "../store/authStore";
import {
  DndContext, closestCenter, PointerSensor, TouchSensor, useSensor, useSensors,
} from "@dnd-kit/core";
import {
  SortableContext, rectSortingStrategy, useSortable, arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

// ── تسليم ملف قويّ: تنزيل مباشر، ثم مشاركة، ثم فتح بتبويب — يعمل على الجوّال ──
async function deliverBlob(blob: Blob, filename: string) {
  const file = new File([blob], filename, { type: blob.type || "application/pdf" });
  if ("download" in HTMLAnchorElement.prototype) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    return;
  }
  if ((navigator as any).canShare?.({ files: [file] })) {
    await (navigator as any).share({ files: [file], title: filename });
    return;
  }
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

// ── غلاف الكتاب: صورة الواجهة (أول صفحة) في المقدّمة؛ بديل أنيق إن غابت ──
function BookCover({ id, title, hasCover, ready, progress, ver }: { id: number; title: string; hasCover: boolean; ready: boolean; progress?: number; ver?: number }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!hasCover) return;
    let obj: string | null = null, alive = true;
    libraryApi.coverBlob(id, ver || 0)
      .then((r) => { if (alive) { obj = URL.createObjectURL(r.data as Blob); setUrl(obj); } })
      .catch(() => {});
    return () => { alive = false; if (obj) URL.revokeObjectURL(obj); };
  }, [id, hasCover, ver]);

  return (
    <div className="relative w-full rounded-lg overflow-hidden shadow-lg shadow-black/40"
      style={{ aspectRatio: "3 / 4", background: "linear-gradient(135deg,var(--brand-a),var(--brand-b))" }}>
      {/* حافة الكعب (spine) تعطي إحساس كتاب حقيقي */}
      <div className="absolute inset-y-0 start-0 w-[6px] bg-black/25" />
      {url ? (
        <img src={url} alt={title} className="w-full h-full object-cover" />
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center p-3 text-center">
          <BookOpen size={26} className="text-white/80 mb-2" />
          <p className="text-[var(--ink)] text-[13px] font-bold leading-snug line-clamp-4">{title}</p>
        </div>
      )}
      {!ready && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-4"
          style={{ background: "transparent", backdropFilter: "blur(1px)" }}>
          <Loader2 size={20} className="animate-spin text-[var(--ink)]" />
          <span className="text-[var(--ink)] text-[11px] font-bold">جارٍ التحضير</span>
          {progress != null && (
            <div className="w-full max-w-[7rem]">
              <div className="h-1.5 rounded-full bg-white/20 overflow-hidden">
                <div className="h-full rounded-full bg-[var(--pos-ink)] transition-all duration-700"
                  style={{ width: `${progress}%` }} />
              </div>
              <div className="text-center text-white/85 text-[11px] tabular-nums mt-1">{progress}%</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── معاينة الكتاب: الـPDF محميّ بالتوكن، فنجلبه blob ونعرضه عبر Object URL ──
function PreviewModal({ id, title, onClose }: { id: number; title: string; onClose: () => void }) {
  const [url, setUrl] = useState<string | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    let objUrl: string | null = null, alive = true;
    libraryApi.fileBlob(id)
      .then((r) => { if (!alive) return; objUrl = URL.createObjectURL(r.data as Blob); setUrl(objUrl); })
      .catch(() => alive && setErr(true));
    return () => { alive = false; if (objUrl) URL.revokeObjectURL(objUrl); };
  }, [id]);

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}
      style={{ padding: 12, alignItems: "flex-start" }}>
      <div className="modal-box lib-surface fade-in" style={{ maxWidth: 900, width: "100%", height: "92vh", padding: 0, display: "flex", flexDirection: "column" }}>
        <div className="flex items-center justify-between gap-2 p-3 border-b border-[var(--hairline)]">
          <div className="flex items-center gap-2 min-w-0">
            <BookOpen size={18} className="text-[var(--brand-ink)] shrink-0" />
            <h2 className="modal-title truncate">{title}</h2>
          </div>
          <button onClick={onClose} title="إغلاق" aria-label="إغلاق" className="text-[var(--ink-muted)] hover:text-[var(--ink)] p-1"><X size={18} /></button>
        </div>
        <div className="flex-1 min-h-0 panel">
          {err ? (
            <div className="h-full flex items-center justify-center text-[var(--ink-muted)] text-sm">تعذّر فتح الملف.</div>
          ) : !url ? (
            <div className="h-full flex items-center justify-center text-[var(--ink-muted)] text-sm gap-2">
              <Loader2 size={16} className="animate-spin" /> جارٍ تحميل الكتاب...
            </div>
          ) : (
            <iframe src={url} title={title} className="w-full h-full" style={{ border: 0 }} />
          )}
        </div>
      </div>
    </div>
  );
}

// ── نبذة اليوم: ثلاث فرص (لمبات 💡). كل لمبة نبذةٌ من صفحةٍ مختلفة من الكتاب —
//    تعويضٌ لأي نبذةٍ وقعت على صفحةٍ غير مفيدة. المستخدَمة تنطفئ، وينتقل بينها ──
function InsightModal({ id, title, onClose }: { id: number; title: string; onClose: () => void }) {
  const SLOTS = 3;
  // يوم بتوقيت مكة (UTC+3) — يطابق تدوير محتوى النبذة في الخادم، فتُصفَّر
  // اللمبات «المستخدَمة» منتصف الليل بمكة لا الساعة الثالثة فجرًا.
  const today = new Date(Date.now() + 3 * 3600 * 1000).toISOString().slice(0, 10);
  const usedKey = `lib:lamps:${id}:${today}`;
  const [used, setUsed] = useState<Set<number>>(() => {
    try { return new Set(JSON.parse(localStorage.getItem(usedKey) || "[]")); } catch { return new Set(); }
  });
  const [slot, setSlot] = useState(0);
  // دوران تلقائي بين الفرص الثلاث بفترة محددة — النبذة «حيّة» تتبدّل وحدها،
  // والنقر اليدوي على لمبة يُعيد ضبط المؤقّت (cycleKey) فلا تقفز أثناء القراءة.
  const [cycleKey, setCycleKey] = useState(0);
  const ROTATE_MS = 22000;
  useEffect(() => {
    const t = setInterval(() => setSlot((s) => (s + 1) % SLOTS), ROTATE_MS);
    return () => clearInterval(t);
  }, [cycleKey]);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["library-insight", id, slot],
    queryFn: () => libraryApi.insight(id, slot).then((r) => r.data.data),
    retry: false,
  });
  const detail = (error as any)?.response?.data?.detail;

  // عند عرض نبذةٍ بنجاح: تُعتبَر «مستخدَمة» فتنطفئ لمبتها.
  useEffect(() => {
    if (!data || isError) return;
    setUsed((prev) => {
      if (prev.has(slot)) return prev;
      const next = new Set(prev); next.add(slot);
      localStorage.setItem(usedKey, JSON.stringify([...next]));
      return next;
    });
  }, [data, isError, slot]);

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}
      style={{ padding: 12, alignItems: "flex-start", overflowY: "auto" }}>
      <div className="modal-box lib-surface fade-in" style={{ maxWidth: 560, width: "100%", margin: "24px auto" }}>
        <div className="flex items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2 min-w-0">
            <Sparkles size={18} className="shrink-0 ai-star" />
            <h2 className="modal-title truncate">نبذة اليوم — {title}</h2>
          </div>
          <button onClick={onClose} title="إغلاق" aria-label="إغلاق" className="text-[var(--ink-muted)] hover:text-[var(--ink)] p-1"><X size={18} /></button>
        </div>

        {isLoading ? (
          <div className="py-10 text-center text-[var(--ink-muted)] text-sm flex items-center justify-center gap-2">
            <Loader2 size={16} className="animate-spin" /> الذكاء يستخلص فكرة اليوم...
          </div>
        ) : isError ? (
          <div className="py-8 text-center text-[var(--neg-ink)] text-sm">{detail || "تعذّر توليد النبذة."}</div>
        ) : (
          <div className="space-y-4">
            <div className="rounded-2xl p-4" style={{ background: "var(--panel)", border: "1px solid var(--hairline)" }}>
              <FileText size={16} className="text-[var(--warn-ink)] mb-1.5" />
              <p className="text-[var(--ink)] text-[15px] leading-relaxed font-medium">{data.idea}</p>
            </div>
            {Array.isArray(data.points) && data.points.length > 0 && (
              <ul className="space-y-2">
                {data.points.map((p: string, i: number) => (
                  <li key={i} className="flex gap-2.5 text-[var(--ink)] text-sm leading-relaxed">
                    <span className="mt-2 h-1.5 w-1.5 rounded-full bg-[var(--brand)] shrink-0" />
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            )}
            {data.reflection && (
              <div className="rounded-xl p-3.5 panel border border-[var(--hairline)]">
                <p className="text-[11px] font-bold text-[var(--ink-muted)] mb-1">سؤال تأمّل</p>
                <p className="text-[var(--ink)] text-sm leading-relaxed">{data.reflection}</p>
              </div>
            )}
          </div>
        )}

        {/* بطاقة مستقلّة بخطّ ذهبي من اليمين: يمين «من نصّ الكتاب — صفحة X»،
            ويسار ثلاث لمبات صغيرة (فرص النبذة) */}
        <div className="mt-4 rounded-xl p-3.5 panel border-s-2 border-[var(--warn-ink)] flex items-center justify-between gap-4">
          {data && data.page ? (
            <span className="text-[13px] text-[var(--ink)] flex items-center gap-2 whitespace-nowrap">
              <Quote size={13} className="shrink-0 text-[var(--warn-ink)]" /> من نصّ الكتاب — صفحة {data.page}
            </span>
          ) : <span className="text-[13px] text-[var(--ink-muted)]">ثلاث فرص للنبذة</span>}
          <div className="flex items-center gap-2.5 shrink-0">
            {Array.from({ length: SLOTS }, (_, i) => {
              const isUsed = used.has(i);
              const active = i === slot;
              return (
                <button key={i} onClick={() => { setSlot(i); setCycleKey((k) => k + 1); }}
                  title={isUsed ? `فرصة ${i + 1} (مستخدَمة)` : `فرصة ${i + 1}`}
                  className="transition-transform hover:scale-110" style={{ lineHeight: 1 }}>
                  <Lightbulb size={13}
                    className={active ? "text-[var(--warn-ink)]" : isUsed ? "text-[var(--ink-muted)]" : "text-[var(--warn-ink)]"}
                    style={active ? { filter: "drop-shadow(0 0 5px rgba(251,191,36,.7))" } : undefined}
                    fill={active ? "rgba(251,191,36,.25)" : "none"} />
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── صفحة قارئ: صورة مرسومة خادمياً (MuPDF) تُجلب كسولاً عند اقترابها.
//    fit = وضع الكمبيوتر: الصفحة كاملةً تملأ الشاشة والتنقّل صفحةً كاملة ──
function ReaderPage({ id, num, dir, fit, zoom, register }:
  { id: number; num: number; dir: "vertical" | "horizontal"; fit?: boolean; zoom?: number; register: (n: number, el: HTMLDivElement | null) => void }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [aspect, setAspect] = useState(1.414);

  useEffect(() => { register(num, wrapRef.current); return () => register(num, null); }, [num]);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    let obj: string | null = null, alive = true, started = false;
    const load = async () => {
      if (started || !alive) return;
      started = true;
      try {
        const r = await libraryApi.pageImage(id, num, 2);
        if (!alive) return;
        obj = URL.createObjectURL(r.data as Blob);
        setUrl(obj);
      } catch { started = false; }
    };
    const io = new IntersectionObserver((es) => { if (es[0].isIntersecting) load(); },
      { rootMargin: "1500px" });
    io.observe(el);
    return () => { alive = false; io.disconnect(); if (obj) URL.revokeObjectURL(obj); };
  }, [id, num]);

  const loader = (
    <div className="w-full h-full flex items-center justify-center bg-[var(--ink)]">
      <Loader2 size={18} className="animate-spin text-[var(--ink-muted)]" />
    </div>
  );

  // وضع الملاءمة (الكمبيوتر): كل صفحة تملأ ارتفاع الشاشة، والتمرير يقفز صفحةً كاملة.
  // التكبير يزيد الارتفاع (فعلياً) ويسمح بالتمرير داخل الصفحة عند التجاوز.
  if (fit) {
    const z = zoom || 1;
    return (
      <div ref={wrapRef} data-page={num}
        className={`h-full w-full snap-center shrink-0 overflow-auto py-2 flex ${z > 1 ? "items-start justify-start" : "items-center justify-center"}`}>
        {url ? (
          <img src={url} alt={`صفحة ${num}`}
            className="rounded-md shadow-lg shadow-black/40 max-w-none mx-auto"
            style={{ height: `${100 * z}%`, width: "auto" }} />
        ) : <div className="h-full aspect-[1/1.414]">{loader}</div>}
      </div>
    );
  }

  const wrapCls = dir === "horizontal"
    ? "h-full shrink-0 bg-[var(--ink)] rounded-md shadow-lg shadow-black/40 overflow-hidden snap-center"
    : "w-full bg-[var(--ink)] rounded-md shadow-lg shadow-black/40 mb-3 overflow-hidden snap-start";
  const style: React.CSSProperties = dir === "horizontal"
    ? { aspectRatio: `1 / ${aspect}`, height: "100%" }
    : { aspectRatio: `1 / ${aspect}` };
  return (
    <div ref={wrapRef} data-page={num} className={wrapCls} style={style}>
      {url ? (
        <img src={url} alt={`صفحة ${num}`} loading="lazy"
          onLoad={(e) => { const im = e.currentTarget; if (im.naturalWidth) setAspect(im.naturalHeight / im.naturalWidth); }}
          className={dir === "horizontal" ? "h-full w-auto block mx-auto" : "w-full h-auto block"} />
      ) : loader}
    </div>
  );
}

// ── القراءة: صور صفحات مرسومة خادمياً (عرض عربي صحيح) + عدّاد + اتجاه + استئناف ──
function ReaderModal({ id, title, pageCount, onClose }: { id: number; title: string; pageCount: number; onClose: () => void }) {
  const num = pageCount || 0;
  const zoom = 1; // أُزيل زرّا التكبير/التصغير — الملاءمة التلقائية تكفي.
  const [dir, setDir] = useState<"vertical" | "horizontal">(
    () => (localStorage.getItem("lib:reader:dir") as any) || "vertical");
  const [page, setPage] = useState(1);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pageEls = useRef<Map<number, HTMLDivElement>>(new Map());
  const ratios = useRef<Map<number, number>>(new Map());
  const restored = useRef(false);
  const register = (n: number, el: HTMLDivElement | null) => {
    if (el) pageEls.current.set(n, el); else pageEls.current.delete(n);
  };

  // الكمبيوتر (شاشة كبيرة) + تمرير عمودي → وضع الملاءمة: صفحة كاملة/شاشة، تنقّل صفحة صفحة.
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches);
  useEffect(() => {
    const m = window.matchMedia("(min-width: 1024px)");
    const h = () => setIsDesktop(m.matches);
    m.addEventListener("change", h);
    return () => m.removeEventListener("change", h);
  }, []);
  const fit = isDesktop && dir === "vertical";

  // علامة الرجوع: تحفظ آخر صفحة صريحةً كي تبدأ منها لاحقاً (لا من البداية).
  const bmKey = `lib:bookmark:${id}`;
  const [bookmark, setBookmark] = useState<number | null>(() => {
    const v = localStorage.getItem(bmKey); return v ? Number(v) : null;
  });
  const [bmToast, setBmToast] = useState<string | null>(null);
  const bmActive = bookmark != null && bookmark === page;  // الصفحة الحالية معلَّمة
  const toggleBookmark = () => {
    if (bmActive) {                       // ضغطة ثانية على نفس الصفحة → إطفاء
      setBookmark(null);
      localStorage.removeItem(bmKey);
      setBmToast("أُزيلت العلامة");
    } else {                              // حفظ/نقل العلامة للصفحة الحالية
      setBookmark(page);
      localStorage.setItem(bmKey, String(page));
      setBmToast(`حُفظت صفحة ${page} — ستبدأ منها لاحقاً`);
    }
    setTimeout(() => setBmToast(null), 2000);
  };

  useEffect(() => { localStorage.setItem("lib:reader:dir", dir); }, [dir]);
  useEffect(() => { if (num && page >= 1) localStorage.setItem(`lib:page:${id}`, String(page)); }, [page, num, id]);

  // تتبّع الصفحة الظاهرة + الاستئناف لآخر صفحة عند أول فتح.
  useEffect(() => {
    if (!num) return;
    const root = scrollRef.current;
    if (!root) return;
    ratios.current.clear();
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        const n = Number((e.target as HTMLElement).getAttribute("data-page"));
        ratios.current.set(n, e.isIntersecting ? e.intersectionRatio : 0);
      }
      let bestN = 1, best = -1;
      ratios.current.forEach((r, n) => { if (r > best) { best = r; bestN = n; } });
      if (best > 0) setPage(bestN);
    }, { root, threshold: [0, 0.15, 0.35, 0.55, 0.8, 1] });
    Array.from(pageEls.current.values()).forEach((el) => io.observe(el));

    if (!restored.current) {
      restored.current = true;
      // الأولوية لعلامة الرجوع الصريحة، ثم آخر صفحة تلقائية.
      const saved = Number(localStorage.getItem(bmKey) || localStorage.getItem(`lib:page:${id}`) || 1);
      if (saved > 1) setTimeout(() => pageEls.current.get(saved)?.scrollIntoView({ block: "center", inline: "center" }), 80);
    }
    return () => io.disconnect();
  }, [num, dir, id]);

  const goto = (n: number) => {
    const t = Math.min(num, Math.max(1, n));
    pageEls.current.get(t)?.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
  };

  const download = async () => {
    try {
      const r = await libraryApi.fileBlob(id, true);
      await deliverBlob(r.data as Blob, `${title}.pdf`);
    } catch {}
  };

  // ── شريط تنقّل الصفحات (scrubber) — اضغط/اسحب للقفز بين الصفحات بسرعة ──
  const scrubRef = useRef<HTMLDivElement>(null);
  const scrubbing = useRef(false);
  const [scrubPage, setScrubPage] = useState<number | null>(null);
  const pageFromY = (clientY: number) => {
    const el = scrubRef.current;
    if (!el || num < 1) return 1;
    const r = el.getBoundingClientRect();
    const frac = Math.min(1, Math.max(0, (clientY - r.top) / r.height));
    return Math.min(num, Math.max(1, Math.round(1 + frac * (num - 1))));
  };
  const onScrub = (clientY: number) => {
    const p = pageFromY(clientY);
    setScrubPage(p);
    goto(p);
  };

  const maxW = Math.round(760 * zoom);

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}
      style={{ padding: 12, alignItems: "flex-start" }}>
      <div className="modal-box lib-surface fade-in" style={{ maxWidth: 900, width: "100%", height: "94vh", padding: 0, display: "flex", flexDirection: "column" }}>
        <div className="flex items-center justify-between gap-2 p-3 border-b border-[var(--hairline)]">
          <div className="flex items-center gap-2 min-w-0">
            <BookText size={18} className="text-[var(--pos-ink)] shrink-0" />
            <h2 className="modal-title truncate">{title}</h2>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {num > 0 && (
              <>
                <button className="btn-ghost !px-2 !py-1.5"
                  title={bmActive ? "إزالة العلامة" : bookmark ? `علامتك: صفحة ${bookmark} — احفظ هذه الصفحة` : "احفظ آخر صفحة للرجوع إليها"}
                  onClick={toggleBookmark}>
                  <Bookmark size={14} className={bmActive ? "text-[var(--pos-ink)]" : bookmark ? "text-[var(--pos-ink)]" : ""}
                    fill={bmActive ? "currentColor" : "none"} />
                </button>
                <button className="btn-ghost !px-2 !py-1.5" title={dir === "vertical" ? "تمرير أفقي" : "تمرير عمودي"}
                  onClick={() => setDir((d) => (d === "vertical" ? "horizontal" : "vertical"))}>
                  {dir === "vertical" ? <MoveHorizontal size={14} /> : <MoveVertical size={14} />}
                </button>
              </>
            )}
            <button className="btn-ghost !px-2 !py-1.5" title="تحميل" onClick={download}><Download size={14} /></button>
            <button onClick={onClose} title="إغلاق" aria-label="إغلاق" className="text-[var(--ink-muted)] hover:text-[var(--ink)] p-1 ms-1"><X size={18} /></button>
          </div>
        </div>

        <div className="flex-1 min-h-0 relative">
          <div ref={scrollRef}
            className={dir === "horizontal"
              ? "absolute inset-0 overflow-x-auto overflow-y-hidden flex flex-row gap-3 px-3 py-4 snap-x snap-mandatory"
              : fit
                ? "absolute inset-0 overflow-y-auto ps-8 pe-3 snap-y snap-mandatory"
                : "absolute inset-0 overflow-y-auto ps-8 pe-3 py-4 snap-y"}
            style={{ background: "var(--field)", direction: dir === "horizontal" ? "rtl" : undefined }}>
            {!num ? (
              <div className="h-full w-full flex items-center justify-center text-[var(--ink-muted)] text-sm gap-2">
                <Loader2 size={16} className="animate-spin" /> جارٍ تجهيز الكتاب...
              </div>
            ) : dir === "horizontal" ? (
              Array.from({ length: num }, (_, i) => (
                <ReaderPage key={i + 1} id={id} num={i + 1} dir={dir} register={register} />
              ))
            ) : fit ? (
              Array.from({ length: num }, (_, i) => (
                <ReaderPage key={i + 1} id={id} num={i + 1} dir={dir} fit zoom={zoom} register={register} />
              ))
            ) : (
              <div className="mx-auto" style={{ maxWidth: maxW }}>
                {Array.from({ length: num }, (_, i) => (
                  <ReaderPage key={i + 1} id={id} num={i + 1} dir={dir} register={register} />
                ))}
              </div>
            )}
          </div>

          {/* شريط تنقّل الصفحات على جهة البداية (عمودي) */}
          {num > 1 && dir === "vertical" && (
            <div className="absolute inset-y-0 start-0 w-8 flex items-stretch py-4 ps-1.5 z-10 select-none">
              <div ref={scrubRef}
                className="relative flex-1 rounded-full bg-[var(--surface)] cursor-pointer touch-none"
                onPointerDown={(e) => { scrubbing.current = true; (e.target as HTMLElement).setPointerCapture(e.pointerId); onScrub(e.clientY); }}
                onPointerMove={(e) => { if (scrubbing.current) onScrub(e.clientY); }}
                onPointerUp={() => { scrubbing.current = false; setScrubPage(null); }}
                onPointerCancel={() => { scrubbing.current = false; setScrubPage(null); }}>
                {/* مسار مملوء حتى الصفحة الحالية */}
                <div className="absolute inset-x-0 top-0 rounded-full"
                  style={{ height: `${((page - 1) / Math.max(1, num - 1)) * 100}%` }} />
                {/* المقبض */}
                <div className="absolute inset-x-[-2px] flex items-center justify-center"
                  style={{ top: `${((page - 1) / Math.max(1, num - 1)) * 100}%`, transform: "translateY(-50%)" }}>
                  <div className="h-4 w-4 rounded-full bg-[var(--pos-ink)] shadow-md shadow-black/40 border-2 border-[var(--hairline)]" />
                </div>
                {/* شارة رقم الصفحة أثناء السحب */}
                {scrubPage != null && (
                  <div className="absolute start-full ms-1 -translate-y-1/2 rounded-lg bg-black/80 text-[var(--ink)] text-[11px] font-bold px-2 py-1 tabular-nums whitespace-nowrap"
                    style={{ top: `${((scrubPage - 1) / Math.max(1, num - 1)) * 100}%` }}>
                    {scrubPage}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* تأكيد حفظ العلامة */}
          {bmToast && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 rounded-full bg-[var(--pos-ink)] text-[var(--ink)] text-[12px] font-bold px-4 py-1.5 shadow-lg flex items-center gap-1.5 fade-in">
              <Bookmark size={13} fill="currentColor" /> {bmToast}
            </div>
          )}
        </div>

        {num > 0 && (
          <div className="flex items-center justify-center gap-4 py-2 border-t border-[var(--hairline)] text-[var(--ink)]"
            style={{ direction: "rtl" }}>
            <button className="btn-ghost !px-2 !py-1" title="السابق" onClick={() => goto(page - 1)} disabled={page <= 1}>
              <ChevronRight size={16} />
            </button>
            <span className="text-[13px] tabular-nums font-semibold">صفحة {page} من {num}</span>
            <button className="btn-ghost !px-2 !py-1" title="التالي" onClick={() => goto(page + 1)} disabled={page >= num}>
              <ChevronLeft size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── مودال إضافة كتاب (زر لا يأخذ حيّزاً من الرفّ) + خط تقدّم للرفع ──
function UploadModal({ maxFileMb, onClose }: { maxFileMb: number; onClose: () => void }) {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [pct, setPct] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  const mut = useMutation({
    mutationFn: () => libraryApi.upload(file!, title.trim(), author.trim(), setPct).then((r) => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["library"] }); onClose(); },
    onError: (e: any) => setErr(e?.response?.data?.detail || "تعذّر رفع الكتاب."),
  });

  // مؤقّت ثوانٍ حيّ طوال الرفع/الحفظ — يطمئن المستخدم أن العمل جارٍ.
  useEffect(() => {
    if (!mut.isPending) { setElapsed(0); return; }
    const t0 = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - t0) / 1000)), 250);
    return () => clearInterval(id);
  }, [mut.isPending]);

  const oversize = file && file.size > maxFileMb * 1024 * 1024;
  // بعد اكتمال الرفع (100%) يبدأ الخادم المعالجة/الـOCR — نُظهر ذلك للمستخدم.
  const processing = mut.isPending && pct >= 100;

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && !mut.isPending && onClose()}
      style={{ padding: 12, alignItems: "flex-start", overflowY: "auto" }}>
      <div className="modal-box fade-in" style={{ maxWidth: 460, width: "100%", margin: "32px auto" }}>
        <div className="flex items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2">
            <Plus size={18} className="text-[var(--pos-ink)]" />
            <h2 className="modal-title">إضافة كتاب</h2>
          </div>
          {!mut.isPending && <button onClick={onClose} title="إغلاق" aria-label="إغلاق" className="text-[var(--ink-muted)] hover:text-[var(--ink)] p-1"><X size={18} /></button>}
        </div>

        <div className="space-y-3">
          <input className="input w-full" placeholder="عنوان الكتاب" value={title}
            onChange={(e) => setTitle(e.target.value)} disabled={mut.isPending} />
          <input className="input w-full" placeholder="المؤلّف (اختياري)" value={author}
            onChange={(e) => setAuthor(e.target.value)} disabled={mut.isPending} />
          <label className={`btn-ghost w-full justify-center ${mut.isPending ? "opacity-50 pointer-events-none" : "cursor-pointer"}`}>
            <input type="file" accept="application/pdf" className="hidden"
              onChange={(e) => { setFile(e.target.files?.[0] || null); setErr(null); }} />
            <BookOpen size={15} /> {file ? file.name : "اختر ملف PDF"}
          </label>
          {file && (
            <p className={`text-xs ${oversize ? "text-[var(--neg-ink)]" : "text-[var(--ink-muted)]"}`}>
              {(file.size / 1024 / 1024).toFixed(1)}MB {oversize ? `— يتجاوز الحدّ (${maxFileMb}MB)` : ""}
            </p>
          )}

          {mut.isPending && (
            <div>
              <div className="h-2 rounded-full bg-[var(--surface)] overflow-hidden">
                <div className="h-full rounded-full transition-all duration-200"
                  style={{ width: `${processing ? 100 : pct}%`, background: "linear-gradient(90deg, var(--brand-a), var(--brand-b))" }} />
              </div>
              <p className="text-xs text-[var(--ink-muted)] mt-1.5 flex items-center gap-1.5">
                <Loader2 size={12} className="animate-spin" />
                {processing ? "اكتمل الرفع — يُحفظ الكتاب…" : `جارٍ الرفع ${pct}%`}
                <span className="ms-auto tabular-nums text-[var(--ink-muted)]">{elapsed}s</span>
              </p>
            </div>
          )}

          {err && <p className="text-xs text-[var(--neg-ink)]">{err}</p>}

          <button className="btn-primary w-full justify-center"
            disabled={!file || !title.trim() || !!oversize || mut.isPending}
            onClick={() => { setErr(null); mut.mutate(); }}>
            {mut.isPending ? <>جارٍ الحفظ...</> : <><Plus size={15} /> إضافة إلى المكتبة</>}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── بطاقة كتاب: زرّان أساسيان أسفلها، وتحميل/حذف يظهران بسلاسة عند لمس الغلاف ──
function BookCard({ b, now, isOwner, onInsight, onReader, onDownload, onDelete, onSetCover, deleting }: {
  b: any; now: number; isOwner: boolean;
  onInsight: () => void; onReader: () => void; onDownload: () => void; onDelete: () => void;
  onSetCover: (file: File) => void; deleting: boolean;
}) {
  const [revealed, setRevealed] = useState(false);
  const coverInputRef = useRef<HTMLInputElement>(null);
  const aiDisabled = !b.ready || !b.has_text;   // النبذة تحتاج النصّ المستخرَج
  const readDisabled = !b.ready;                // القراءة تعرض صفحات الـPDF (لا نصّ)
  // نسبة تقدّم تقديرية للحفظ (تقارب 100% مع الوقت حتى تجهز فعلاً) — بديل المؤقّت.
  const secs = !b.ready && b.created_at ? Math.max(0, (now - new Date(b.created_at).getTime()) / 1000) : 0;
  const progress = b.ready ? 100 : Math.min(96, Math.round(100 * (1 - Math.exp(-secs / 12))));

  return (
    <div className="flex flex-col">
      <div className="group relative select-none"
        onClick={() => b.ready && setRevealed((v) => !v)}>
        <BookCover id={b.id} title={b.title} hasCover={b.has_cover} ready={b.ready} progress={progress} ver={b.cover_ver} />

        {/* شريط سفلي ينزلق للأعلى عند لمس الغلاف (جوّال) أو التحويم (كمبيوتر) */}
        {b.ready && (
          <div className={`absolute inset-x-0 bottom-0 flex items-center justify-center gap-2 p-2
              bg-gradient-to-t from-black/80 via-black/55 to-transparent
              transition-all duration-300 ease-out
              ${revealed ? "translate-y-0 opacity-100" : "translate-y-full opacity-0"}
              group-hover:translate-y-0 group-hover:opacity-100`}>
            <button onClick={(e) => { e.stopPropagation(); onDownload(); }}
              className="h-9 w-9 rounded-full flex items-center justify-center bg-white/15 hover:bg-white/30 text-[var(--ink)] backdrop-blur-sm transition-colors"
              title="تحميل"><Download size={16} /></button>
            {isOwner && (
              <>
                <button onClick={(e) => { e.stopPropagation(); coverInputRef.current?.click(); }}
                  className="h-9 w-9 rounded-full flex items-center justify-center bg-white/15 hover:bg-white/30 text-[var(--ink)] backdrop-blur-sm transition-colors"
                  title="تغيير الغلاف"><ImagePlus size={16} /></button>
                <button onClick={(e) => { e.stopPropagation(); onDelete(); }} disabled={deleting}
                  className="h-9 w-9 rounded-full flex items-center justify-center text-[var(--neg-ink)] backdrop-blur-sm transition-colors"
                  title="حذف"><Trash2 size={16} /></button>
              </>
            )}
          </div>
        )}
        <input ref={coverInputRef} type="file" accept="image/*" className="hidden"
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onSetCover(f); e.currentTarget.value = ""; }} />
      </div>

      <div className="mt-2.5 px-0.5">
        <h3 className="text-[var(--ink)] font-semibold text-[13px] leading-snug line-clamp-2">{b.title}</h3>
        {b.author && <p className="text-[var(--ink-muted)] text-[11px] mt-0.5 truncate">{b.author}</p>}
        {b.page_count ? <p className="text-[var(--ink-muted)] text-[11px] mt-0.5">{b.page_count} صفحة</p> : null}
      </div>

      <button onClick={onInsight} disabled={aiDisabled}
        title={!b.ready ? "جارٍ تحضير الكتاب" : b.has_text ? "" : "جارٍ استخراج النصّ…"}
        className="lib-daily-btn mt-2.5 w-full justify-center rounded-xl py-2 text-[13px] font-bold flex items-center gap-1.5 transition-all disabled:opacity-40">
        <Sparkles size={14} className="ai-star" /> نبذة اليوم
      </button>
      <button onClick={onReader} disabled={readDisabled}
        title={!b.ready ? "جارٍ تحضير الكتاب" : ""}
        className="lib-read-btn mt-1.5 w-full justify-center rounded-xl py-2 text-[13px] font-bold flex items-center gap-1.5 transition-all disabled:opacity-40">
        <BookText size={14} /> قراءة
      </button>
    </div>
  );
}

// ── غلاف قابل للسحب: مقبض ترتيب (للمالك) يبدأ السحب دون تعطيل بقية اللمسات ──
function SortableBookCard(props: any) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: props.b.id });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 50 : undefined,
    opacity: isDragging ? 0.85 : 1,
  };
  return (
    <div ref={setNodeRef} style={style} className="relative">
      <button {...attributes} {...listeners}
        className="absolute top-1.5 start-1.5 z-20 h-7 w-7 rounded-lg bg-black/55 hover:bg-black/75 text-white/90 flex items-center justify-center cursor-grab active:cursor-grabbing touch-none"
        title="اسحب لترتيب الكتاب" onClick={(e) => e.stopPropagation()}>
        <GripVertical size={15} />
      </button>
      <BookCard {...props} />
    </div>
  );
}

export default function LibraryPage() {
  const qc = useQueryClient();
  const { isOwner } = useAuthStore();
  const [insightId, setInsightId] = useState<{ id: number; title: string } | null>(null);
  const [readerId, setReaderId] = useState<{ id: number; title: string; pages: number } | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);

  const { data } = useQuery({
    queryKey: ["library"],
    queryFn: () => libraryApi.list().then((r) => r.data.data),
    // بينما هناك كتاب قيد المعالجة الخلفية، نُعيد الجلب كل 4 ثوانٍ حتى يجهز.
    refetchInterval: (q) =>
      (q.state.data?.books ?? []).some((b: any) => !b.ready || !b.has_text) ? 4000 : false,
  });
  const books: any[] = data?.books ?? [];
  const limits = data?.limits;
  const anyProcessing = books.some((b) => !b.ready);

  // مؤقّت حيّ لبطاقات «جارٍ التحضير» — يعرض الثواني المنقضية منذ الرفع.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!anyProcessing) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [anyProcessing]);

  const del = useMutation({
    mutationFn: (id: number) => libraryApi.remove(id).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library"] }),
  });

  const setCover = useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => libraryApi.setCover(id, file).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["library"] }),
  });

  // ── ترتيب يدويّ بالسحب (للمالك) ──
  const [order, setOrder] = useState<number[]>([]);
  const idsKey = books.map((b) => b.id).join(",");
  useEffect(() => { setOrder(books.map((b) => b.id)); }, [idsKey]);
  const sensors = useSensors(
    // مسافة تفعيل صغيرة كي تبقى اللمسات العادية (فتح/كشف) تعمل بلا سحب عرضيّ.
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 180, tolerance: 6 } }),
  );
  const reorderMut = useMutation({
    mutationFn: (ids: number[]) => libraryApi.reorder(ids).then((r) => r.data),
    onError: () => qc.invalidateQueries({ queryKey: ["library"] }),
  });
  const onDragEnd = (e: any) => {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    setOrder((o) => {
      const next = arrayMove(o, o.indexOf(active.id), o.indexOf(over.id));
      reorderMut.mutate(next);
      return next;
    });
  };
  const byId = new Map(books.map((b) => [b.id, b]));
  const orderedBooks = (order.length ? order : books.map((b) => b.id))
    .map((id) => byId.get(id)).filter(Boolean) as any[];

  const download = async (id: number, title: string) => {
    try {
      const r = await libraryApi.fileBlob(id, true);
      await deliverBlob(r.data as Blob, `${title}.pdf`);
    } catch (e) {
      if ((e as any)?.name !== "AbortError") alert("تعذّر تحميل الكتاب — أعد المحاولة.");
    }
  };

  const booksFull = limits && limits.count >= limits.max_books;
  const spaceFull = limits && limits.used_mb >= limits.max_total_mb;
  const atLimit = booksFull || spaceFull;

  return (
    <div className="space-y-5 fade-in">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <Book size={24} className="text-[var(--brand-ink)]" />
            <h1 className="text-2xl font-medium text-[var(--ink)]">المكتبة</h1>
          </div>
          {limits && (() => {
            const pct = Math.min(100, (limits.used_mb / limits.max_total_mb) * 100);
            const remMb = Math.max(0, +(limits.max_total_mb - limits.used_mb).toFixed(1));
            const remBooks = Math.max(0, limits.max_books - limits.count);
            const color = pct >= 90 ? "var(--neg-ink)" : pct >= 70 ? "var(--warn-ink)" : "var(--pos-ink)";
            return (
              <div className="mt-2 max-w-sm">
                <div className="flex items-center justify-between text-[11px] mb-1">
                  <span className="text-[var(--ink-muted)]">
                    {limits.count}/{limits.max_books} كتاب
                    <span className="text-[var(--ink-muted)]"> · متبقٍّ {remBooks}</span>
                  </span>
                  <span style={{ color }}>{limits.used_mb} / {limits.max_total_mb}MB</span>
                </div>
                <div className="h-1.5 rounded-full bg-[var(--surface)] overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${pct}%`, background: color }} />
                </div>
                <p className="text-[10px] text-[var(--ink-muted)] mt-1">
                  المساحة المتبقّية {remMb}MB · حدّ الكتاب الواحد {limits.max_file_mb}MB
                </p>
              </div>
            );
          })()}
        </div>
        {isOwner && (
          <button className="btn-primary shrink-0" disabled={!!atLimit}
            title={spaceFull ? "امتلأت مساحة المكتبة" : booksFull ? "بلغت المكتبة حدّ الكتب" : ""}
            onClick={() => setUploadOpen(true)}>
            <Plus size={16} /> إضافة كتاب
          </button>
        )}
      </div>

      {books.length === 0 ? (
        <div className="card text-center py-16 text-[var(--ink-muted)]">
          <Book size={36} className="mx-auto mb-3 opacity-50" />
          <p className="text-sm">لا كتب بعد{isOwner ? " — أضف أول كتاب" : "."}</p>
        </div>
      ) : isOwner ? (
        <>
          <p className="text-[11px] text-[var(--ink-muted)] flex items-center gap-1.5">
            <GripVertical size={12} /> اسحب من المقبض لترتيب الكتب كما تريد.
          </p>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
            <SortableContext items={order} strategy={rectSortingStrategy}>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-7">
                {orderedBooks.map((b) => (
                  <SortableBookCard key={b.id} b={b} now={now} isOwner={isOwner}
                    deleting={del.isPending}
                    onInsight={() => setInsightId({ id: b.id, title: b.title })}
                    onReader={() => setReaderId({ id: b.id, title: b.title, pages: b.page_count || 0 })}
                    onDownload={() => download(b.id, b.title)}
                    onSetCover={(file: File) => setCover.mutate({ id: b.id, file })}
                    onDelete={() => {
                      /* تأكيدٌ باسم الكتاب — زرّ الحذف يقع فوق الغلاف حيث
                         يُضغَط لفتح الكتاب، فمِسّةٌ خاطئة كانت تمحو ملفاً
                         رفعتَه بلا رجعة ولا سؤال. */
                      if (confirm(`حذف «${b.title}» من المكتبة نهائياً؟`)) del.mutate(b.id);
                    }} />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-7">
          {books.map((b) => (
            <BookCard key={b.id} b={b} now={now} isOwner={isOwner}
              deleting={del.isPending}
              onInsight={() => setInsightId({ id: b.id, title: b.title })}
              onReader={() => setReaderId({ id: b.id, title: b.title, pages: b.page_count || 0 })}
              onDownload={() => download(b.id, b.title)}
              onSetCover={(file: File) => setCover.mutate({ id: b.id, file })}
              onDelete={() => {
                      /* تأكيدٌ باسم الكتاب — زرّ الحذف يقع فوق الغلاف حيث
                         يُضغَط لفتح الكتاب، فمِسّةٌ خاطئة كانت تمحو ملفاً
                         رفعتَه بلا رجعة ولا سؤال. */
                      if (confirm(`حذف «${b.title}» من المكتبة نهائياً؟`)) del.mutate(b.id);
                    }} />
          ))}
        </div>
      )}

      {uploadOpen && <UploadModal maxFileMb={limits?.max_file_mb ?? 60} onClose={() => setUploadOpen(false)} />}
      {readerId && <ReaderModal id={readerId.id} title={readerId.title} pageCount={readerId.pages} onClose={() => setReaderId(null)} />}
      {insightId && <InsightModal id={insightId.id} title={insightId.title} onClose={() => setInsightId(null)} />}
    </div>
  );
}
