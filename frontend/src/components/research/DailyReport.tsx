/* ══ التقريرُ اليوميّ — ورقةُ قسم الأبحاث ══ (‏D745 · D746 · D749 · D753 · D756 · ‏D763 بأمر المالك 2026-11-18)
   «أبغى شيئاً طبقَ الأصل من الجزيرة كابيتال… التقاريرُ مؤرّخة… لا تذكر المصادر… والمكتبةُ لا تظهر». فالورقةُ نفسُها — الوثيقةُ التي تصل
   ملفّاً إلى تلغرام بعد إغلاق السوق — بأيام أرشيفها وتنزيلِها. ‏D763: «التقريرُ اليوميّ خلاص خلّه في تبويب مفكرة السوق… بجانب الجزيرة كابيتال
   والراجحي كابيتال في مكانهم الأساسي» — فانتقل من المختبر إلى مفكرة السوق بجانب «التوقعات». والورقةُ تُكتب في الخادم (‏services/research_paper)
   فلا تختلف الشاشةُ عن الملفّ.
   ‏D788 (المالك 2026-11-23): «التطبيقُ يدعم تعدّدَ المحافظ — خلِّ في التقرير خياراً: بدون محفظة، أو للمحافظ كاملةً، أو لمحفظةٍ معيّنة»:
   فمبدّلٌ فوق الأيام — «بلا محفظة» (صفحاتُ السوق وحدها) · «كلّ المحافظ» (تقريرُها المجمَّع) · كلُّ محفظةٍ باسمها — يُحفظ في المتصفّح. */
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText, RefreshCw, Download } from "lucide-react";
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
  const pdf = useMutation({
    mutationFn: () => marketApi.researchPdf(rep?.date ?? null, cur || null),
    onSuccess: r => {
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `daily-report-${rep?.date}.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
    },
  });

  /* الإطارُ بطول ورقته — يُقاس عند التحميل وكلّما تغيّر عرضُ النافذة (الورقةُ تلتفّ عموداً واحداً على الهاتف) */
  /* ‏D756: كلُّ صفحةٍ ورقةُ A4 بقياسها — وما زاد من محتواها يُصغَّر بنسبته (دالّةُ الورقة نفسُها، فالإطارُ لا يشغّل نصوصاً) */
  const fitPages = (d: Document) => {
    if ((d.defaultView?.innerWidth || 0) < 820) return;
    d.querySelectorAll<HTMLElement>(".page").forEach(pg => {
      const pb = pg.querySelector<HTMLElement>(".pb"), pf = pg.querySelector<HTMLElement>(".pf");
      if (!pb || !pf) return;
      (pb.style as any).zoom = "";
      const t = pb.getBoundingClientRect().top, lim = pf.getBoundingClientRect().top - 10, pad = parseFloat(getComputedStyle(pb).paddingTop) || 0;
      let b = t;
      Array.from(pb.children).forEach(c => { const r = c.getBoundingClientRect(); if (r.height) b = Math.max(b, r.bottom); });
      if (b > lim) { (pb.style as any).zoom = String(Math.max(0.72, (lim - t - pad) / (b - t - pad))); pg.setAttribute("data-fit", (pb.style as any).zoom); }
      else pg.removeAttribute("data-fit");
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
            <button type="button" className="btn-ghost rl-btn" onClick={() => pdf.mutate()} disabled={pdf.isPending} data-role="rl-pdf"
              aria-label="تنزيل التقرير ملفَّ PDF" title="تنزيل التقرير ملفَّ PDF">
              <Download size={15} className={pdf.isPending ? "rl-spin" : ""} /> PDF
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
        <div className="rl-paper" data-ready={ready ? "1" : "0"} data-role="rl-doc">
          {paper.data && (
            <iframe ref={frame} title={`التقرير اليومي — ${rep.label}`} srcDoc={paper.data} style={{ height }} sandbox="allow-same-origin"
              onLoad={() => { measure(); setReady(true); }} />
          )}
        </div>
      )}
    </div>
  );
}
