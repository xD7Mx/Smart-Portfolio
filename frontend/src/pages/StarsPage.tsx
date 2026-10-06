import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FlaskConical, X, Plus } from "lucide-react";
import { marketApi, goalsApi, portfolioApi, portfoliosApi, holdingsApi } from "../services/api";
import CompanyLogo from "../components/common/CompanyLogo";
import StockSheet from "../components/market/StockSheet";
import { Curve } from "../components/market/TasiStarsPanel";
import { yearsToGoal, yearsLabel } from "../utils/goal";

/* ══ مختبرُ الأبحاث ══ (بأمر المالك · D612 · D613)
   شاشاتٌ: الأولى لشركات محفظته تلقائياً، والثانيةُ لمحفظةٍ أخرى — ولكلّ شاشةٍ مفتاحُ «شركاتُ المحفظة تلقائياً»
   مع الإضافة والاستبعاد. تُضاف الشركاتُ فتظهر إحصاءاتُها بالرسوم نفسِها. قراءةٌ فقط — لا يكتب في المحفظة. */

const pct = (v: any) => (typeof v === "number" ? `${v > 0.05 ? "+" : ""}${Math.abs(v) < 0.05 ? "0.0" : v.toFixed(1)}%` : "—");
const tone = (v: any) => (typeof v === "number" && Math.abs(v) >= 0.05 ? (v > 0 ? "var(--pos-ink)" : "var(--neg-ink)") : "var(--ink)");
const STARTS = ["2015-01", "2018-01", "2020-01", "2022-01", "2024-01"];
const KEY = "lab:screens:v1";

type Screen = { id: string; name: string; pid: number | null; auto: boolean; add: string[]; drop: string[] };
const clean = (s: any) => String(s ?? "").replace(".SR", "").trim();

function loadScreens(): Screen[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || "null");
    if (Array.isArray(v) && v.length) return v;
  } catch { /* محلّيّ */ }
  // النسخةُ السابقة (سلّةٌ واحدة) تنتقل إلى الشاشة الثانية — لا يضيع ما أضافه
  let old: string[] = [];
  try { old = JSON.parse(localStorage.getItem("stars:lab") || "[]"); } catch { /* */ }
  return [
    { id: "s1", name: "محفظتي", pid: null, auto: true, add: [], drop: [] },
    { id: "s2", name: "شاشة 2", pid: null, auto: false, add: Array.isArray(old) ? old : [], drop: [] },
  ];
}

export default function StarsPage() {
  const [sheet, setSheet] = useState<string | null>(null);
  const [screens, setScreens] = useState<Screen[]>(loadScreens);
  const [cur, setCur] = useState(0);
  const [q, setQ] = useState("");
  const [start, setStart] = useState("2015-01");
  const persist = (n: Screen[]) => { setScreens(n); try { localStorage.setItem(KEY, JSON.stringify(n)); } catch { /* */ } };
  const sc = screens[Math.min(cur, screens.length - 1)];
  const patch = (p: Partial<Screen>) => persist(screens.map(x => (x.id === sc.id ? { ...x, ...p } : x)));

  /* ‏D613: الفرزُ يعود `{rows, state}` لا قائمة — قراءتُه قائمةً أسقطت الصفحة (شاشةٌ سوداء) عند الكتابة في البحث */
  const { data: rows = [] } = useQuery({
    queryKey: ["screener-lite"], staleTime: 30 * 60_000,
    queryFn: () => marketApi.screener().then(r => {
      const d = r.data?.data;
      return (Array.isArray(d) ? d : Array.isArray(d?.rows) ? d.rows : []) as any[];
    }),
  });
  const { data: portfolios = [] } = useQuery({
    queryKey: ["portfolios"], staleTime: 10 * 60_000,
    queryFn: () => portfoliosApi.list().then(r => (Array.isArray(r.data?.data) ? r.data.data : []) as any[]),
  });
  const defPid: number | null = (portfolios.find((p: any) => p.is_default) || portfolios[0] || {}).id ?? null;
  const pid = sc.pid ?? (sc.id === "s1" ? defPid : null);
  const { data: held = [] } = useQuery({
    queryKey: ["lab-holdings", pid], enabled: sc.auto && pid != null, staleTime: 5 * 60_000,
    queryFn: () => holdingsApi.listFor(pid as number).then(r => {
      const d = r.data?.data;
      const items = Array.isArray(d) ? d : Array.isArray(d?.items) ? d.items : [];
      return items.filter((h: any) => Number(h.total_shares) > 0).map((h: any) => clean(h.company?.symbol ?? h.symbol)).filter(Boolean) as string[];
    }),
  });
  const syms = useMemo(() => {
    const base = sc.auto ? held : [];
    return Array.from(new Set([...base, ...sc.add].map(clean))).filter(s => s && !sc.drop.includes(s)).slice(0, 30);
  }, [sc, held]);

  const { data, isFetching } = useQuery({
    queryKey: ["stars-lab", syms.join(","), start], enabled: syms.length > 0, staleTime: 10 * 60_000,
    placeholderData: (p: any) => p,
    queryFn: () => marketApi.starsLab(syms, start).then(r => r.data?.data || null),
  });
  const { data: goals } = useQuery({ queryKey: ["goals-builtin"], queryFn: () => goalsApi.builtin().then((r: any) => r.data.data), retry: 0 });
  const { data: pm } = useQuery({ queryKey: ["portfolio-metrics"], queryFn: () => portfolioApi.metrics().then((r: any) => r.data.data), retry: 0 });

  const nameOf = (s: string) => (rows.find((r: any) => clean(r.symbol) === s) || {}).name || s;
  const term = q.trim();
  const hits = term.length < 2 ? [] : rows.filter((r: any) => {
    const sym = clean(r.symbol);
    return !syms.includes(sym) && (sym.startsWith(term) || String(r.name || "").includes(term));
  }).slice(0, 6);
  const addSym = (s: string) => { patch({ add: Array.from(new Set([...sc.add, s])), drop: sc.drop.filter(x => x !== s) }); setQ(""); };
  const removeSym = (s: string) => patch({ add: sc.add.filter(x => x !== s), drop: held.includes(s) ? Array.from(new Set([...sc.drop, s])) : sc.drop });
  const addScreen = () => {
    if (screens.length >= 4) return;
    const n = [...screens, { id: `s${Date.now()}`, name: `شاشة ${screens.length + 1}`, pid: null, auto: false, add: [], drop: [] }];
    persist(n); setCur(n.length - 1);
  };

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
  const chip = (on: boolean) => (on ? { color: "var(--brand-ink)", borderColor: "var(--brand)" } : { color: "var(--ink-muted)", borderColor: "var(--hairline)" });

  return (
    <div className="space-y-4 fade-in">
      <div className="card space-y-3">
        <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
          <FlaskConical size={22} className="text-[var(--brand-ink)]" /> مختبر الأبحاث
        </h1>

        <div className="flex items-center gap-1.5 overflow-x-auto">
          {screens.map((s, i) => (
            <button key={s.id} type="button" onClick={() => { setCur(i); setQ(""); }}
              className="px-3 min-h-[36px] rounded-lg text-[13px] font-bold border whitespace-nowrap" style={chip(i === cur)}>
              {s.name}
            </button>
          ))}
          {screens.length < 4 && (
            <button type="button" onClick={addScreen} aria-label="شاشةٌ جديدة"
              className="min-w-[36px] min-h-[36px] rounded-lg border flex items-center justify-center" style={chip(false)}>
              <Plus size={15} />
            </button>
          )}
        </div>

        <div className="grid grid-cols-[1fr_auto] gap-2 items-center">
          <select value={pid ?? ""} onChange={e => patch({ pid: e.target.value ? Number(e.target.value) : null, drop: [] })}
            aria-label="محفظةُ الشاشة"
            className="min-h-[40px] rounded-lg px-2 text-[13px] bg-[var(--field)] border border-[var(--hairline)] text-[var(--ink)]">
            <option value="">بلا محفظة</option>
            {portfolios.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button type="button" role="switch" aria-checked={sc.auto} onClick={() => patch({ auto: !sc.auto })}
            disabled={pid == null}
            className="flex items-center gap-2 min-h-[40px] text-[12px] text-[var(--ink)] disabled:opacity-50">
            <span aria-hidden className={"switch inline-block" + (sc.auto && pid != null ? " on" : "")} />
            شركاتُ المحفظة تلقائياً
          </button>
        </div>

        <div className="relative">
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="أضف شركة — اسمها أو رمزها"
            className="w-full min-h-[44px] rounded-xl px-3 text-[14px] bg-[var(--field)] border border-[var(--hairline)] text-[var(--ink)]" />
          {hits.length > 0 && (
            <div className="absolute z-10 inset-x-0 mt-1 rounded-xl border border-[var(--line)] bg-[var(--pop)] overflow-hidden">
              {hits.map((r: any) => {
                const sym = clean(r.symbol);
                return (
                  <button key={sym} type="button" onClick={() => addSym(sym)}
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
              className="px-3 min-h-[32px] rounded-lg text-[12px] font-bold border tabular-nums" style={chip(start === v)}>
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
        <div className="card space-y-3">
          <div className="flex items-center justify-between gap-2">
            <p className="card-title">الأداء</p>
            <div className="flex items-center gap-3 text-[11px] text-[var(--ink-muted)]">
              <span className="flex items-center gap-1"><span className="w-2.5 h-0.5 inline-block" style={{ background: "var(--brand-ink)" }} />{sc.name}</span>
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
                    <span className="block text-[11px] text-[var(--ink-muted)] truncate">
                      {missing ? "بلا سجلّ أسعار" : String(f.decision ?? "—")}{held.includes(s) && sc.auto ? " · من المحفظة" : ""}</span>
                  </span>
                </button>
                <span className="w-14 text-center text-[13px] font-bold tabular-nums" dir="ltr" style={{ color: tone(contrib[s]) }}>
                  {typeof contrib[s] === "number" ? `${contrib[s] > 0 ? "+" : ""}${contrib[s].toFixed(1)}` : "—"}</span>
                <span className="w-14 text-center text-[13px] font-bold tabular-nums" dir="ltr"
                  style={{ color: reliable ? tone(f.upside) : "var(--ink-muted)" }}>{reliable ? pct(f.upside) : "—"}</span>
                <button type="button" onClick={() => removeSym(s)} aria-label={`أزل ${nameOf(s)}`}
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
