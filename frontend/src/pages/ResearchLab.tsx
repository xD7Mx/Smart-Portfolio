/* ══ مختبرُ الأبحاث — قسمُ الأبحاث ══ (‏D745 · بأمر المالك 2026-11-15)
   «دراسةٌ شاملةٌ لجميع التقارير اليومية والدورية والاقتصادية… تقريرٌ خاصٌّ بمحفظتنا بتصميمنا من المصادر الموثوقة… ويرسل على
   تلغرام… والقسمُ الثاني توصياتٌ إن وُجدت». ثلاثُ صفحات: «التقرير اليومي» بتصميم بيوت الأبحاث (شريطُ الهويّة · العنوان · مؤشّراتُ
   اليوم · الأقسام · المصادرُ المرقّمة)، و«التوصيات» انتقائيةً بأسبابها ومصادرها، و«المكتبة» ما قرأه القسمُ من تقارير الجهات.
   والنصُّ كلُّه من الخادم (‏services/research_desk) — كلُّ سطرٍ بأرقام مصادره، ولا شيءَ يُكتب هنا من غيرها. */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText, Lightbulb, Library, RefreshCw, ExternalLink } from "lucide-react";
import { marketApi } from "../services/api";
import { useAuthStore } from "../store/authStore";
import CompanyLogo from "../components/common/CompanyLogo";

type Row = { text: string; src: number[]; name?: string; view?: string; symbol?: string; stance?: string };
type Src = { n: number; source: string; title: string; date: string; kind: string; url?: string };
const TONE: Record<string, string> = { "إيجابي": "pos", "شراء": "pos", "إضافة": "pos", "سلبي": "neg", "بيع": "neg", "تخفيف": "neg", "انتباه": "warn", "انتظار": "warn" };

function Cite({ src }: { src: number[] }) {
  return <sup className="rl-cite" dir="ltr">{src.map(n => (n === 0 ? "التطبيق" : n)).join("·")}</sup>;
}
function Chip({ v }: { v?: string }) {
  return v ? <span className={`rl-chip rl-${TONE[v] || "muted"}`}>{v}</span> : null;
}
function Section({ title, rows }: { title: string; rows: Row[] }) {
  if (!rows?.length) return null;
  return (
    <section className="rl-sec">
      <h3>{title}</h3>
      <ul>{rows.map((r, i) => <li key={i}>{r.text}<Cite src={r.src} /></li>)}</ul>
    </section>
  );
}

export default function ResearchLab() {
  const owner = useAuthStore((s: any) => s.isOwner);
  const [day, setDay] = useState<string | null>(null);
  const [tab, setTab] = useState<"report" | "recs" | "lib">("report");
  const { data, refetch, isPending } = useQuery({
    queryKey: ["research-desk", day],
    queryFn: () => marketApi.researchDesk(day).then(r => r.data.data),
    refetchInterval: q => ((q.state.data as any)?.running?.on ? 5000 : false),
  });
  const lib = useQuery({ queryKey: ["research-library"], queryFn: () => marketApi.researchLibrary().then(r => r.data.data || []), enabled: tab === "lib" });
  const run = useMutation({ mutationFn: () => marketApi.researchRun(), onSuccess: () => setTimeout(() => refetch(), 800) });
  const rep = data?.report, st = data?.stats, running = data?.running?.on;
  const srcs: Src[] = rep?.sources || [];

  return (
    <div className="rl space-y-3" data-role="research-lab">
      <div className="rl-bar">
        <div className="seg inline-flex" role="tablist" aria-label="أقسام مختبر الأبحاث">
          {([["report", "التقرير اليومي", FileText], ["recs", "التوصيات", Lightbulb], ["lib", "المكتبة", Library]] as const).map(([k, t, Ic]) => (
            <button key={k} type="button" role="tab" aria-selected={tab === k} className={"seg-btn chip" + (tab === k ? " on" : "")} onClick={() => setTab(k)} data-role="rl-tab">
              <Ic size={14} className="inline-block align-[-2px] me-1" />{t}
            </button>
          ))}
        </div>
        <span className="rl-stat" data-role="rl-stat">
          {st?.notes ? `${st.notes} تقريراً مقروءاً${st.first ? ` منذ ${st.first}` : ""}` : "لم يُقرأ تقريرٌ بعد"}
        </span>
        {owner && (
          <button type="button" className="btn-ghost rl-run" disabled={running || run.isPending} onClick={() => run.mutate()} data-role="rl-run">
            <RefreshCw size={14} className={running ? "rl-spin" : ""} /> {running ? (data?.running?.msg || "يعمل") : "اقرأ واكتب الآن"}
          </button>
        )}
      </div>

      {(data?.dates?.length || 0) > 1 && tab !== "lib" && (
        <div className="rl-days" role="group" aria-label="أرشيف التقارير">
          {data.dates.slice(0, 14).map((d: string) => (
            <button key={d} type="button" className={"seg-btn chip" + ((day || data.dates[0]) === d ? " on" : "")} onClick={() => setDay(d)} dir="ltr">{d.slice(5)}</button>
          ))}
        </div>
      )}

      {tab === "lib" ? (
        <div className="rl-lib" data-role="rl-lib">
          {(lib.data || []).map((n: any, i: number) => (
            <article key={i} className="rl-libitem card-rise" style={{ animationDelay: `${Math.min(i, 12) * 22}ms` }}>
              <div className="rl-libhead">
                <span className="rl-chip rl-muted">{n.source}</span><span className="rl-kind">{n.kind}</span><time dir="ltr">{n.date}</time>
                {n.url && <a href={n.url} target="_blank" rel="noreferrer" className="rl-link" aria-label="الملفّ الأصليّ"><ExternalLink size={14} /></a>}
              </div>
              <h4>{n.title}</h4>
              {n.headline && <p>{n.headline}</p>}
            </article>
          ))}
          {lib.data && !lib.data.length && <div className="rl-empty">لا تقاريرَ مقروءةً بعد.</div>}
        </div>
      ) : !rep ? (
        <div className="rl-empty card" data-role="rl-empty">{isPending ? "…" : "لم يُكتب تقريرٌ بعد."}</div>
      ) : tab === "report" ? (
        <article className="rl-doc card" data-role="rl-doc">
          <header className="rl-band">
            <div><span className="rl-eyebrow">قسم الأبحاث · {rep.portfolio_name}</span><h2>التقرير اليومي</h2></div>
            <time dir="ltr">{rep.date}</time>
          </header>
          {rep.headline && <p className="rl-headline">{rep.headline}</p>}
          <div className="rl-kpis">
            <div><span>تاسي</span><b dir="ltr">{rep.tasi ? `${rep.tasi.price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${rep.tasi.pct != null
              ? ` (${rep.tasi.pct > 0 ? "+" : ""}${rep.tasi.pct.toFixed(2)}%)` : ""}` : "غير متوفّر"}</b></div>
            <div><span>المصادر</span><b>{srcs.length}</b></div>
            <div><span>مراكزُ تعنيها الأخبار</span><b>{rep.portfolio?.length || 0}</b></div>
            <div><span>التوصيات</span><b>{rep.recommendations?.length || 0}</b></div>
          </div>
          {(rep.market?.summary || rep.market?.points?.length) && (
            <section className="rl-sec">
              <h3>السوق</h3>
              {rep.market.summary && <p>{rep.market.summary}</p>}
              {!!rep.market.points?.length && <ul>{rep.market.points.map((r: Row, i: number) => <li key={i}>{r.text}<Cite src={r.src} /></li>)}</ul>}
            </section>
          )}
          <div className="rl-cols">
            <Section title="الأخبار المحلية" rows={rep.local} />
            <Section title="الأخبار العالمية" rows={rep.global} />
          </div>
          {!!rep.sectors?.length && (
            <section className="rl-sec">
              <h3>القطاعات</h3>
              <div className="rl-table">{rep.sectors.map((r: Row, i: number) => (
                <div key={i} className="rl-tr"><b>{r.name}</b><Chip v={r.view} /><span>{r.text}<Cite src={r.src} /></span></div>
              ))}</div>
            </section>
          )}
          {!!rep.portfolio?.length && (
            <section className="rl-sec">
              <h3>محفظتنا</h3>
              <div className="rl-table">{rep.portfolio.map((r: Row, i: number) => (
                <div key={i} className="rl-tr"><b className="rl-co"><CompanyLogo symbol={r.symbol || ""} size={22} />{r.name}</b><Chip v={r.stance} />
                  <span>{r.text}<Cite src={r.src} /></span></div>
              ))}</div>
            </section>
          )}
          <Section title="للمتابعة" rows={rep.watch} />
          <footer className="rl-srcs">
            <h3>المصادر</h3>
            <ol>
              <li value={0}>أرقامُ التطبيق: السعرُ العادل وقرارُ التطبيق وموقفُ المستشار لكلّ مركز</li>
              {srcs.map(s => (
                <li key={s.n} value={s.n}>{s.source} — {s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.title}</a> : s.title} <time dir="ltr">{s.date}</time></li>
              ))}
            </ol>
          </footer>
        </article>
      ) : (
        <div className="rl-recs" data-role="rl-recs">
          {(rep.recommendations || []).map((r: any, i: number) => (
            <article key={i} className="rl-rec card card-rise" style={{ animationDelay: `${i * 40}ms` }}>
              <div className="rl-rechead"><CompanyLogo symbol={r.symbol} size={30} /><b>{r.name}</b><Chip v={r.action} /></div>
              <p>{r.why}<Cite src={r.src} /></p>
              {r.condition && <p className="rl-cond">الشرط: {r.condition}</p>}
            </article>
          ))}
          {!rep.recommendations?.length && <div className="rl-empty card">{rep.no_rec_reason ? `لا توصيةَ اليوم: ${rep.no_rec_reason}` : "لا توصيةَ اليوم."}</div>}
        </div>
      )}
    </div>
  );
}
