/* ══ مختبرُ الأبحاث — قسمُ الأبحاث ══ (‏D745 · D746 · بأمر المالك 2026-11-15)
   «أبغى شيئاً طبقَ الأصل من الجزيرة كابيتال… التقاريرُ مؤرّخة… لا تذكر المصادر، اعتمدها ولا تذكرها… والمكتبةُ لا تظهر، الشغلُ كلُّه في
   الخفاء». فالصفحةُ ورقةُ التقرير نفسُها — الوثيقةُ التي تصل ملفّاً إلى تلغرام بعد إغلاق السوق — في صفحتين: «التقرير اليومي» (السوقُ
   والأسواقُ والنظرةُ الفنية) و«التوصيات» (نظرتُنا لمراكز المحفظة وأفضلُ اختياراتنا)، وأيامُ الأرشيف بتواريخها، وتنزيلُ الملفّ.
   والورقةُ تُكتب في الخادم (‏services/research_paper) فلا تختلف الشاشةُ عن الملفّ. */
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText, Lightbulb, RefreshCw, Download } from "lucide-react";
import { marketApi } from "../services/api";
import { useAuthStore } from "../store/authStore";

type Part = "market" | "portfolio";

export default function ResearchLab() {
  const owner = useAuthStore((s: any) => s.isOwner);
  const [day, setDay] = useState<string | null>(null);
  const [part, setPart] = useState<Part>("market");
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
    queryKey: ["research-paper", rep?.date, part],
    queryFn: () => marketApi.researchPaper(rep.date, part).then(r => r.data.data?.html as string | null),
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
        <div className="seg inline-flex" role="tablist" aria-label="أقسام مختبر الأبحاث">
          {([["market", "التقرير اليومي", FileText], ["portfolio", "التوصيات", Lightbulb]] as const).map(([k, t, Ic]) => (
            <button key={k} type="button" role="tab" aria-selected={part === k} className={"seg-btn chip" + (part === k ? " on" : "")}
              onClick={() => setPart(k)} data-role="rl-tab">
              <Ic size={14} className="inline-block align-[-2px] me-1" />{t}
            </button>
          ))}
        </div>
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
        <div className="rl-days" role="group" aria-label="أيام التقارير">
          {head.data.dates.slice(0, 20).map((d: { date: string; label: string }) => (
            <button key={d.date} type="button" className={"seg-btn chip" + ((day || head.data.dates[0].date) === d.date ? " on" : "")}
              onClick={() => setDay(d.date)} data-role="rl-day">{d.label}</button>
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
