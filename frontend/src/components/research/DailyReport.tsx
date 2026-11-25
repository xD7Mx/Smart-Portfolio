/* ══ التقريرُ اليوميّ — ورقةُ قسم الأبحاث ══ (‏D745 · D746 · D749 · D753 · D756 · ‏D763 بأمر المالك 2026-11-18)
   «أبغى شيئاً طبقَ الأصل من الجزيرة كابيتال… التقاريرُ مؤرّخة… لا تذكر المصادر… والمكتبةُ لا تظهر». فالورقةُ نفسُها — الوثيقةُ التي تصل
   ملفّاً إلى تلغرام بعد إغلاق السوق — بأيام أرشيفها وتنزيلِها. ‏D763: «التقريرُ اليوميّ خلاص خلّه في تبويب مفكرة السوق… بجانب الجزيرة كابيتال
   والراجحي كابيتال في مكانهم الأساسي» — فانتقل من المختبر إلى مفكرة السوق بجانب «التوقعات». والورقةُ تُكتب في الخادم (‏services/research_paper)
   فلا تختلف الشاشةُ عن الملفّ.
   ‏D788 (المالك 2026-11-23): «التطبيقُ يدعم تعدّدَ المحافظ — خلِّ في التقرير خياراً: بدون محفظة، أو للمحافظ كاملةً، أو لمحفظةٍ معيّنة»:
   فمبدّلٌ فوق الأيام — «بلا محفظة» (صفحاتُ السوق وحدها) · «كلّ المحافظ» (تقريرُها المجمَّع) · كلُّ محفظةٍ باسمها — يُحفظ في المتصفّح.
   ‏D815 (المالك 2026-11-24): «التقريرُ اليوميّ على الجوال يجب أن يظهر كما يظهر على الكمبيوتر» — كانت الورقةُ تلتفّ عموداً واحداً تحت 820px
   (وسائطُ الشاشة الضيّقة في ورقة الخادم) فتختلف هيئتُها. فالإطارُ يُرسم دائماً بعرض الحاسوب (‏PAPER_W) فتبقى الصفحاتُ الأربعُ بأعمدتها
   وجداولها ورسومها كما هي، ويُصغَّر كلُّه بنسبةٍ واحدةٍ ليسع الشاشة — والقرصُ بالإصبعين يكبّره للقراءة. */
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText, RefreshCw, Check, Maximize2 } from "lucide-react";
import PaperReader from "./PaperReader";
import { marketApi, portfoliosApi } from "../../services/api";
import { getActivePortfolioId } from "../../store/portfolioStore";
import { useAuthStore } from "../../store/authStore";

type Day = { date: string; label: string };
/** «الأحد 15 نوفمبر 2026» ← الشهرُ «نوفمبر 2026» واليومُ «15» — والأيامُ بترتيبها تحت شهرها */
const months = (ds: Day[]): [string, Day[]][] => {
  const out: [string, Day[]][] = [];
  for (const d of ds) {
    const p = d.label.split(" ");
    const m = `${p[2]} ${p[3]}`;
    if (!out.length || out[out.length - 1][0] !== m) out.push([m, []]);
    out[out.length - 1][1].push(d);
  }
  return out;
};

/** ‏D823: أيقونةُ التنزيل — سهمُها يهبط إلى الصينية ما دام الملفُّ يُعدّ (لا دوران) */
function DownloadIc({ busy }: { busy: boolean }) {
  return (
    <svg className={"rl-dl" + (busy ? " busy" : "")} width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" data-role="rl-dl" data-busy={busy ? "1" : "0"}>
      <path className="rl-dl-tray" d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <g className="rl-dl-arrow"><path d="M12 3v12" /><path d="m7 10 5 5 5-5" /></g>
    </svg>
  );
}

export default function DailyReport() {
  const owner = useAuthStore((s: any) => s.isOwner);
  const [day, setDay] = useState<string | null>(null);
  const [pf, setPfState] = useState<string>(() => { try { return localStorage.getItem("sp_report_pf") || ""; } catch { return ""; } });
  const setPf = (v: string) => { setPfState(v); setDay(null); try { localStorage.setItem("sp_report_pf", v); } catch { /* */ } };
  const { data: pfs = [] } = useQuery<any[]>({
    queryKey: ["portfolios"], queryFn: () => portfoliosApi.list().then(r => (Array.isArray(r.data?.data) ? r.data.data : [])), staleTime: 5 * 60_000,
  });
  const live = pfs.filter((p: any) => !p.is_archived);
  const cur = pf || getActivePortfolioId() || "";
  const [ready, setReady] = useState(false);
  const [height, setHeight] = useState(900);
  const frame = useRef<HTMLIFrameElement | null>(null);
  /* ‏D815: عرضُ الحاسوب للورقة — فوق حدّ التفافها (820) فتُرسم بأعمدتها؛ والأضيقُ منه يُصغَّر إليه */
  const PAPER_W = 860;
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [boxW, setBoxW] = useState(0);
  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const on = () => setBoxW(el.clientWidth);
    on();
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(on) : null;
    ro?.observe(el);
    return () => ro?.disconnect();
  });
  const scale = boxW > 0 && boxW < PAPER_W ? boxW / PAPER_W : 1;

  const head = useQuery({
    queryKey: ["research-desk", day, cur],
    queryFn: () => marketApi.researchDesk(day, cur || null).then(r => r.data.data),
    refetchInterval: q => ((q.state.data as any)?.running?.on ? 5000 : false),
  });
  const rep = head.data?.report;
  const running = head.data?.running?.on;
  const paper = useQuery({
    queryKey: ["research-paper", rep?.date, "all", cur],
    queryFn: () => marketApi.researchPaper(rep.date, "all", cur || null).then(r => r.data.data?.html as string | null),
    enabled: !!rep?.date,
    staleTime: 5 * 60 * 1000,
  });
  const run = useMutation({ mutationFn: () => marketApi.researchRun(), onSuccess: () => setTimeout(() => head.refetch(), 800) });
  const [saved, setSaved] = useState(false);
  /* ‏D830 (المالك 2026-11-25: «عند التحميل يصلني تحذيرٌ من كروم — إن قدرتَ فطريقةٌ بلا تحذير»): كروم يحذّر من تنزيل ملفٍّ عبر اتّصالٍ غير
     مشفّر، والعرضُ في قارئ المتصفّح ليس تنزيلاً. فالملفُّ يُفتح في صفحةٍ جديدةٍ بقارئ المتصفّح (ومنه الطباعةُ والحفظُ والمشاركة) برابطٍ موقَّعٍ
     قصيرِ العمر — والصفحةُ تُفتح في لحظة الضغطة نفسِها (المتصفّحاتُ تمنع فتحها بعد انتظار)؛ وإن مُنعت فالتنزيلُ كما كان */
  const pdf = useMutation({
    mutationFn: async (w: Window | null) => {
      if (w) {
        const r = await marketApi.researchPdfLink(rep?.date ?? null, cur || null);
        const path = r.data?.data?.path as string | undefined;
        if (path) { w.location.href = marketApi.apiUrl(path); return "view"; }
        try { w.close(); } catch { /* */ }
      }
      const r = await marketApi.researchPdf(rep?.date ?? null, cur || null);
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `daily-report-${rep?.date}.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      return "download";
    },
    onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 1600); },
    onError: (_e, w) => { try { w?.close(); } catch { /* */ } },
  });
  const openPdf = () => {
    let w: Window | null = null;
    try { w = window.open("", "_blank"); } catch { w = null; }
    if (w) {
      try {
        w.document.title = `التقرير اليومي — ${rep?.label || ""}`;
        /* النافذةُ الجديدة خارجَ ورقة أنماط التطبيق — فألوانُها من رموزه بقيمها الحاليّة (والمظهرُ الداكنُ معها) */
        const tk = getComputedStyle(document.documentElement), v = (n: string) => tk.getPropertyValue(n).trim();
        w.document.body.style.cssText = `margin:0;display:grid;place-items:center;height:100vh;font:15px system-ui,sans-serif;color:${v("--ink-muted")};background:${v("--bg")}`;
        w.document.body.innerHTML = '<p dir="rtl">يُفتح التقرير…</p>';
      } catch { /* */ }
    }
    pdf.mutate(w);
  };
  const [reading, setReading] = useState(false);

  /* الإطارُ بطول ورقته — يُقاس عند التحميل وكلّما تغيّر عرضُ النافذة (الورقةُ تلتفّ عموداً واحداً على الهاتف) */
  /* ‏D756: كلُّ صفحةٍ ورقةُ A4 بقياسها — وما زاد من محتواها يُصغَّر بنسبته (دالّةُ الورقة نفسُها، فالإطارُ لا يشغّل نصوصاً) */
  /* ‏D827: الخوارزميةُ نفسُها التي في الورقة (‏research_paper.FIT): تحويلٌ لا تكبير، والجسمُ يُعرَّض بنسبته، والقياسُ بمواضع التخطيط — ويُكرَّر
     بأكبر نسبةٍ تسع الصفحة (كان التكبيرُ يعيد لفَّ الأسطر فيبقى فراغ؛ وفي الطابع كانت لا تعمل أصلاً فيُقصّ ما زاد) */
  const fitPages = (d: Document) => {
    const cols = d.querySelector(".cols");
    if (cols && (d.defaultView?.getComputedStyle(cols).gridTemplateColumns.split(" ").length || 2) < 2) return;
    d.querySelectorAll<HTMLElement>(".page").forEach(pg => {
      const pb = pg.querySelector<HTMLElement>(".pb"), pf = pg.querySelector<HTMLElement>(".pf");
      if (!pb || !pf) return;
      pb.style.transform = ""; pb.style.width = ""; (pb.style as any).zoom = ""; pg.removeAttribute("data-fit");
      const top = pb.offsetTop, lim = pf.offsetTop - 10, W = pb.offsetWidth;
      const bot = () => Array.from(pb.children).reduce((b, x) => { const e = x as HTMLElement; return e.offsetHeight ? Math.max(b, e.offsetTop + e.offsetHeight) : b; }, top);
      if (bot() <= lim) return;
      pb.style.transformOrigin = "top right";
      /* أكبرُ نسبةٍ تسع الصفحة بالتنصيف — الأصغرُ يسع دائماً (أوسعُ فأقصرُ)، والتكرارُ البسيطُ يتأرجح حين ينفكّ لفُّ الأسطر ويعود */
      const fits = (k: number) => { pb.style.width = `${W / k}px`; return top + (bot() - top) * k <= lim; };
      let lo = 0.72, hi = 1, s = lo;
      if (fits(lo)) { for (let i = 0; i < 12; i++) { const m = (lo + hi) / 2; if (fits(m)) lo = m; else hi = m; } s = lo; }
      pb.style.width = `${W / s}px`;
      pb.style.transform = `scale(${s})`;
      pg.setAttribute("data-fit", String(Math.round(s * 1000) / 1000));
    });
  };
  const measure = () => {
    const d = frame.current?.contentDocument;
    if (d?.body) { fitPages(d); setHeight(Math.max(400, d.documentElement.scrollHeight)); }
  };
  useEffect(() => {
    setReady(false);
    const on = () => measure();
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, [paper.data]);

  return (
    <div className="space-y-3" data-role="daily-report">
      <div className="rl-bar">
        <h2 className="rl-title" data-role="rl-title"><FileText size={15} className="inline-block align-[-2px] me-1" />
          التقرير اليومي{rep?.label ? <span className="rl-date"> · {rep.label}</span> : null}</h2>
        <span className="rl-acts">
          {rep && (
            <button type="button" className="btn-ghost rl-btn" onClick={openPdf} disabled={pdf.isPending} data-role="rl-pdf"
              aria-busy={pdf.isPending} aria-label="تنزيل التقرير ملفَّ PDF" title="تنزيل التقرير ملفَّ PDF">
              {saved ? <Check size={15} className="rl-done" data-role="rl-pdf-done" /> : <DownloadIc busy={pdf.isPending} />} PDF
            </button>
          )}
          {owner && (
            <button type="button" className="btn-ghost rl-btn" disabled={running || run.isPending} onClick={() => run.mutate()} data-role="rl-run"
              aria-label="اكتب التقرير الآن" title={running ? (head.data?.running?.msg || "يعمل") : "اكتب التقرير الآن"}>
              <RefreshCw size={15} className={running ? "rl-spin" : ""} />
            </button>
          )}
        </span>
      </div>

      {/* ‏D788: لأيّ محفظة — أو بلا محفظة، أو المحافظُ مجتمعةً */}
      <div className="seg inline-flex rl-pf" role="group" aria-label="محفظةُ التقرير" data-role="rl-pf">
        <button type="button" className={"seg-btn chip" + (cur === "none" ? " on" : "")} aria-pressed={cur === "none"} onClick={() => setPf("none")} data-v="none">بلا محفظة</button>
        {live.length > 1 && (
          <button type="button" className={"seg-btn chip" + (cur === "all" ? " on" : "")} aria-pressed={cur === "all"} onClick={() => setPf("all")} data-v="all">كلّ المحافظ</button>
        )}
        {live.map((p: any) => (
          <button key={p.id} type="button" className={"seg-btn chip" + (cur === String(p.id) ? " on" : "")} aria-pressed={cur === String(p.id)}
            onClick={() => setPf(String(p.id))} data-v={String(p.id)}>{p.name}</button>
        ))}
      </div>
      {head.data?.market_only && cur === "all" && (
        <p className="sq-muted" data-role="rl-pf-note">لم يُكتب تقريرُ المحافظ مجتمعةً لهذا اليوم — صفحاتُ السوق وحدها، ويُكتب من جلسة اليوم.</p>
      )}

      {(head.data?.dates?.length || 0) > 1 && (
        /* ‏D749 (بأمر المالك): «بصيغة أيام — 15 · 14 · 13 — وبتسلسلٍ تاريخيّ لجميع الأيام»: الأيامُ أرقاماً تحت شهرها، الأحدثُ أوّلاً */
        <div className="rl-days" role="group" aria-label="أيام التقارير" data-role="rl-days">
          {months(head.data.dates).map(([m, ds]) => (
            <div key={m} className="rl-month">
              <span className="rl-mname">{m}</span>
              {ds.map(d => (
                <button key={d.date} type="button" className={"seg-btn chip rl-day" + ((day || head.data.dates[0].date) === d.date ? " on" : "")}
                  onClick={() => setDay(d.date)} data-role="rl-day" title={d.label} aria-label={d.label}>{d.label.split(" ")[1]}</button>
              ))}
            </div>
          ))}
        </div>
      )}

      {!rep ? (
        <div className="rl-empty card" data-role="rl-empty">{head.isPending ? "…" : "يصدر التقرير اليومي بعد إغلاق السوق."}</div>
      ) : (
        <div ref={wrapRef} className="rl-paper" data-ready={ready ? "1" : "0"} data-role="rl-doc" data-scale={scale.toFixed(3)}>
          {paper.data && (
            <div className="rl-fit" style={{ height: Math.ceil(height * scale) }}>
              <iframe ref={frame} title={`التقرير اليومي — ${rep.label}`} srcDoc={paper.data} sandbox="allow-same-origin"
                style={scale < 1 ? { width: PAPER_W, height, transform: `scale(${scale})` } : { height }}
                onLoad={() => { measure(); setReady(true); }} />
              {/* ‏D828: على الجوال الورقةُ مصغَّرةٌ لتسع الشاشة — ولمسُها يفتح القارئَ بملء الشاشة للقراءة والتكبير */}
              {scale < 1 && (
                <button type="button" className="rl-read" onClick={() => setReading(true)} data-role="rl-read" aria-label="اقرأ التقرير بملء الشاشة">
                  <span className="rl-read-chip"><Maximize2 size={14} /> اقرأ بملء الشاشة</span>
                </button>
              )}
            </div>
          )}
        </div>
      )}
      {reading && paper.data && rep && (
        <PaperReader html={paper.data} width={PAPER_W} title={`التقرير اليومي — ${rep.label}`} onClose={() => setReading(false)} fit={fitPages} />
      )}
    </div>
  );
}
