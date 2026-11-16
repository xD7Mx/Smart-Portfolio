/* ══ مختبرُ الأبحاث — قسمُ الأبحاث ══ (‏D745 · D746 · بأمر المالك 2026-11-15)
   «أبغى شيئاً طبقَ الأصل من الجزيرة كابيتال… التقاريرُ مؤرّخة… لا تذكر المصادر، اعتمدها ولا تذكرها… والمكتبةُ لا تظهر، الشغلُ كلُّه في
   الخفاء». فالصفحةُ ورقةُ التقرير نفسُها — الوثيقةُ التي تصل ملفّاً إلى تلغرام بعد إغلاق السوق — في صفحتين: «التقرير اليومي» (السوقُ
   والأسواقُ والنظرةُ الفنية) و«التوصيات» (نظرتُنا لمراكز المحفظة وأفضلُ اختياراتنا)، وأيامُ الأرشيف بتواريخها، وتنزيلُ الملفّ.
   ‏D753 (المالك 2026-11-16): «التوصياتُ داخل التقرير — لا تقريرٌ يوميٌّ وتقريرُ توصيات؛ كلُّها في التقريرِ الواحد مرتّبة» — فصفحةٌ واحدة.
   والورقةُ تُكتب في الخادم (‏services/research_paper) فلا تختلف الشاشةُ عن الملفّ. */
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText, RefreshCw, Download } from "lucide-react";
import { marketApi } from "../services/api";
import { useAuthStore } from "../store/authStore";

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

export default function ResearchLab() {
  const owner = useAuthStore((s: any) => s.isOwner);
  const [day, setDay] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [height, setHeight] = useState(900);
  const frame = useRef<HTMLIFrameElement | null>(null);

  const head = useQuery({
    queryKey: ["research-desk", day],
    queryFn: () => marketApi.researchDesk(day).then(r => r.data.data),
    refetchInterval: q => ((q.state.data as any)?.running?.on ? 5000 : false),
  });
  const rep = head.data?.report;
  const running = head.data?.running?.on;
  const paper = useQuery({
    queryKey: ["research-paper", rep?.date, "all"],
    queryFn: () => marketApi.researchPaper(rep.date, "all").then(r => r.data.data?.html as string | null),
    enabled: !!rep?.date,
    staleTime: 5 * 60 * 1000,
  });
  const run = useMutation({ mutationFn: () => marketApi.researchRun(), onSuccess: () => setTimeout(() => head.refetch(), 800) });
  const pdf = useMutation({
    mutationFn: () => marketApi.researchPdf(rep?.date ?? null),
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
  const measure = () => {
    const d = frame.current?.contentDocument;
    if (d?.body) setHeight(Math.max(400, d.documentElement.scrollHeight));
  };
  useEffect(() => {
    setReady(false);
    const on = () => measure();
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, [paper.data]);

  return (
    <div className="space-y-3" data-role="research-lab">
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
