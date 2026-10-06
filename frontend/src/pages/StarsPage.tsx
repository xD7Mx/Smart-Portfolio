import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FlaskConical, X } from "lucide-react";
import { marketApi, goalsApi, portfolioApi } from "../services/api";
import CompanyLogo from "../components/common/CompanyLogo";
import StockSheet from "../components/market/StockSheet";
import { Curve } from "../components/market/TasiStarsPanel";
import { yearsToGoal, yearsLabel } from "../utils/goal";

/* ══ مختبرُ الأبحاث ══ (بأمر المالك · D612) — أُلغيت «نجوم تاسي» التي يختارها المحرّك؛ الصفحةُ لشركاتك أنت وحدها:
   تضيفها فتظهر إحصاءاتُها بالرسوم نفسِها — أداؤها مقابل تاسي، والوصولُ إلى هدفك، وما تقوله المحرّكاتُ عن كلٍّ منها.
   المهمُّ وحده: لا معاييرَ ولا قوائمَ مراقبةٍ ولا جداولَ سنوية. قراءةٌ فقط — لا يكتب في المحفظة. */

const pct = (v: any) => (typeof v === "number" ? `${v > 0.05 ? "+" : ""}${Math.abs(v) < 0.05 ? "0.0" : v.toFixed(1)}%` : "—");
const tone = (v: any) => (typeof v === "number" && Math.abs(v) >= 0.05 ? (v > 0 ? "var(--pos-ink)" : "var(--neg-ink)") : "var(--ink)");
const KEY = "stars:lab";
const STARTS = ["2015-01", "2018-01", "2020-01", "2022-01", "2024-01"];

export default function StarsPage() {
  const [sheet, setSheet] = useState<string | null>(null);
  const [syms, setSyms] = useState<string[]>(() => { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; } });
  const [q, setQ] = useState("");
  const [start, setStart] = useState("2015-01");
  const save = (n: string[]) => { setSyms(n); try { localStorage.setItem(KEY, JSON.stringify(n)); } catch { /* محلّيّ */ } };

  const { data: rows = [] } = useQuery({
    queryKey: ["screener-lite"], staleTime: 30 * 60_000,
    queryFn: () => marketApi.screener().then(r => (r.data?.data || []) as any[]),
  });
  const { data, isFetching } = useQuery({
    queryKey: ["stars-lab", syms.join(","), start], enabled: syms.length > 0, staleTime: 10 * 60_000,
    placeholderData: (p: any) => p,
    queryFn: () => marketApi.starsLab(syms, start).then(r => r.data?.data || null),
  });
  const { data: goals } = useQuery({ queryKey: ["goals-builtin"], queryFn: () => goalsApi.builtin().then((r: any) => r.data.data), retry: 0 });
  const { data: pm } = useQuery({ queryKey: ["portfolio-metrics"], queryFn: () => portfolioApi.metrics().then((r: any) => r.data.data), retry: 0 });

  const nameOf = (s: string) => (rows.find((r: any) => String(r.symbol).replace(".SR", "") === s) || {}).name || s;
  const hits = q.trim().length < 2 ? [] : rows.filter((r: any) => {
    const sym = String(r.symbol).replace(".SR", "");
    return !syms.includes(sym) && (sym.startsWith(q.trim()) || String(r.name || "").includes(q.trim()));
  }).slice(0, 6);

  const ready = syms.length > 0 && data?.track?.length > 1;
  const contrib: Record<string, number> = Object.fromEntries((data?.contrib || []).map((c: any) => [c.symbol, c.pts]));
  const fwd: Record<string, any> = Object.fromEntries((data?.forward?.items || []).map((f: any) => [f.symbol, f]));
  const g = goals?.million;

  const stat = (label: string, v: any) => (
    <div className="kpi">
      <div className="kpi-lbl">{label}</div>
      <div className="kpi-val tabular-nums" dir="ltr" style={{ textAlign: "right", color: tone(v) }}>{pct(v)}</div>
    </div>
  );

  return (
    <div className="space-y-4 fade-in">
      <div className="card space-y-3">
        <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
          <FlaskConical size={22} className="text-[var(--brand-ink)]" /> مختبر الأبحاث
        </h1>
        <div className="relative">
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="أضف شركة — اسمها أو رمزها"
            className="w-full min-h-[44px] rounded-xl px-3 text-[14px] bg-[var(--field)] border border-[var(--hairline)] text-[var(--ink)]" />
          {hits.length > 0 && (
            <div className="absolute z-10 inset-x-0 mt-1 rounded-xl border border-[var(--line)] bg-[var(--pop)] overflow-hidden">
              {hits.map((r: any) => {
                const sym = String(r.symbol).replace(".SR", "");
                return (
                  <button key={sym} type="button" onClick={() => { save([...syms, sym].slice(0, 30)); setQ(""); }}
                    className="w-full flex items-center gap-2 px-3 min-h-[44px] text-start hover:bg-[var(--field)]">
                    <CompanyLogo symbol={sym} size={24} />
                    <span className="text-[13px] text-[var(--ink)] truncate flex-1">{r.name}</span>
                    <span className="text-[11px] text-[var(--ink-muted)] tabular-nums">{sym}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {STARTS.map(v => (
            <button key={v} type="button" onClick={() => setStart(v)}
              className="px-3 min-h-[32px] rounded-lg text-[12px] font-bold border tabular-nums"
              style={start === v ? { color: "var(--brand-ink)", borderColor: "var(--brand)" } : { color: "var(--ink-muted)", borderColor: "var(--hairline)" }}>
              منذ {v.slice(0, 4)}
            </button>
          ))}
          {isFetching && <span className="w-3 h-3 rounded-full skeleton" aria-hidden />}
        </div>
      </div>

      {!syms.length ? (
        <div className="card py-12 text-center text-[14px] text-[var(--ink-muted)]">أضف شركاتك لتظهر إحصاءاتُها</div>
      ) : !ready ? (
        isFetching ? <div className="card h-56 skeleton" />
          : <div className="card py-10 text-center text-[13px] text-[var(--ink-muted)]">غير متوفّر — بياناتُ الأسعار التاريخية تُجمع؛ أعد المحاولة بعد دقائق.</div>
      ) : (
        <>
          <div className="card space-y-3">
            <div className="flex items-center justify-between gap-2">
              <p className="card-title">الأداء</p>
              <div className="flex items-center gap-3 text-[11px] text-[var(--ink-muted)]">
                <span className="flex items-center gap-1"><span className="w-2.5 h-0.5 inline-block" style={{ background: "var(--brand-ink)" }} />سلّتك</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-0.5 inline-block" style={{ background: "var(--ink-muted)" }} />تاسي</span>
              </div>
            </div>
            <Curve track={data.track} />
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {stat("العائد الإجماليّ", data.total)}
              {stat("العائد السنويّ المركّب", data.cagr)}
              {stat("تاسي المركّب", data.tasi_cagr)}
              {stat("أقصى تراجع", data.max_dd)}
            </div>
            {g?.target > 0 && (
              <div className="grid grid-cols-2 gap-2">
                <div className="kpi">
                  <div className="kpi-lbl">الوصول إلى {Number(g.target).toLocaleString("en-US")} بعائد السلّة</div>
                  <div className="kpi-val tabular-nums" style={{ color: "var(--brand-ink)" }}>{yearsLabel(yearsToGoal(g.current, g.target, data.cagr))}</div>
                </div>
                <div className="kpi">
                  <div className="kpi-lbl">وبعائد محفظتك</div>
                  <div className="kpi-val tabular-nums">{yearsLabel(yearsToGoal(g.current, g.target, pm?.cagr_pct))}</div>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {syms.length > 0 && (
        <div className="card p-0">
          <div className="grid grid-cols-[1fr_auto_auto_auto] gap-3 px-4 pt-4 pb-2 text-[11px] text-[var(--ink-muted)] border-b border-[var(--hairline)]">
            <span>شركاتك</span><span className="w-14 text-center">المساهمة</span><span className="w-14 text-center">إلى العادل</span><span className="w-8" />
          </div>
          {syms.map(s => {
            const f = fwd[s] || {};
            const reliable = f.conf === "مرتفعة" || f.conf === "متوسطة";
            const missing = (data?.missing || []).includes(s);
            return (
              <div key={s} className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-3 px-4 min-h-[52px] border-b border-[var(--hairline)] last:border-0">
                <button type="button" onClick={() => setSheet(s)} className="flex items-center gap-2 min-w-0 text-start">
                  <CompanyLogo symbol={s} size={26} />
                  <span className="min-w-0">
                    <span className="block text-[13px] font-semibold text-[var(--ink)] truncate">{nameOf(s)}</span>
                    <span className="block text-[11px] text-[var(--ink-muted)] truncate">{missing ? "بلا سجلّ أسعار" : (f.decision || "—")}</span>
                  </span>
                </button>
                <span className="w-14 text-center text-[13px] font-bold tabular-nums" dir="ltr" style={{ color: tone(contrib[s]) }}>
                  {typeof contrib[s] === "number" ? `${contrib[s] > 0 ? "+" : ""}${contrib[s].toFixed(1)}` : "—"}</span>
                <span className="w-14 text-center text-[13px] font-bold tabular-nums" dir="ltr"
                  style={{ color: reliable ? tone(f.upside) : "var(--ink-muted)" }}>{reliable ? pct(f.upside) : "—"}</span>
                <button type="button" onClick={() => save(syms.filter(x => x !== s))} aria-label={`أزل ${nameOf(s)}`}
                  className="w-8 min-h-[32px] flex items-center justify-center rounded-lg text-[var(--ink-muted)] hover:bg-[var(--field)]">
                  <X size={15} />
                </button>
              </div>
            );
          })}
        </div>
      )}
      {sheet && <StockSheet symbol={sheet} onClose={() => setSheet(null)} />}
    </div>
  );
}
