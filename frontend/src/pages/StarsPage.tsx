import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { marketApi, goalsApi, portfolioApi } from "../services/api";
import { yearsToGoal, yearsLabel } from "../utils/goal";
import CompanyLogo from "../components/common/CompanyLogo";
import StockSheet from "../components/market/StockSheet";
import { Curve } from "../components/market/TasiStarsPanel";

/* ══ نجوم تاسي ══ (بأمر المالك · D536) — صفحةٌ مستقلّةٌ ببطاقات: الأداء · النجوم · المعايير. */

const pct = (v: any) => (typeof v === "number" ? `${v > 0.05 ? "+" : ""}${Math.abs(v) < 0.05 ? "0.0" : v.toFixed(1)}%` : "—");
const tone = (v: any) => (typeof v === "number" && Math.abs(v) >= 0.05 ? (v > 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]") : "text-[var(--ink)]");

const FIXED: [string, string][] = [
  ["السلّة", "أعلى 20 بأوزانٍ متساوية"],
  ["تحت المراقبة", "المراتب 21–30"],
  ["إعادة التوازن", "شهرياً"],
];
const OFF_KEY = "stars:off";
const readOff = (): string[] => { try { return JSON.parse(localStorage.getItem(OFF_KEY) || "[]"); } catch { return []; } };

function MiniList({ title, items, onPick, tone: t }: { title: string; items: any[]; onPick: (s: string) => void; tone: string }) {
  if (!items?.length) return null;
  return (
    <div className="card p-0">
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <p className="card-title" style={{ color: t }}>{title}</p>
        <span className="text-[12px] text-[var(--ink-muted)] tabular-nums">{items.length}</span>
      </div>
      {items.map((m: any) => (
        <button key={m.symbol} type="button" onClick={() => onPick(m.symbol)}
          className="w-full flex items-center gap-2 px-4 py-2 min-h-[44px] text-start border-t border-[var(--hairline)] hover:bg-[var(--field)]">
          <CompanyLogo symbol={m.symbol} size={24} />
          <span className="flex-1 min-w-0">
            <span className="block text-[13px] font-semibold text-[var(--ink)] truncate">{m.name}</span>
            <span className="block text-[11px] text-[var(--ink-muted)] tabular-nums" dir="ltr" style={{ textAlign: "right" }}>{m.symbol}</span>
          </span>
          {typeof m.rank === "number" && <span className="text-[12px] font-bold tabular-nums text-[var(--ink-muted)]" dir="ltr">#{m.rank}</span>}
        </button>
      ))}
    </div>
  );
}

/* عدٌّ تنازليٌّ حيّ إلى التوازن القادم — «الأسهم الجديدة القادمة» كما في InvestingPro. */
function Countdown({ to }: { to?: string }) {
  const [now, setNow] = useState(Date.now());
  React.useEffect(() => { const t = setInterval(() => setNow(Date.now()), 30_000); return () => clearInterval(t); }, []);
  if (!to) return null;
  const end = new Date(to + "T13:00:00Z").getTime();       // بعد إغلاق السوق بتوقيت الرياض
  const ms = Math.max(0, end - now);
  const d = Math.floor(ms / 86400000), h = Math.floor(ms / 3600000) % 24, m = Math.floor(ms / 60000) % 60;
  const cell = (v: number, u: string) => (
    <span className="flex items-baseline gap-0.5"><span className="text-2xl font-bold tabular-nums">{String(v).padStart(2, "0")}</span>
      <span className="text-[11px] font-semibold">{u}</span></span>
  );
  return (
    <div className="text-center" style={{ color: "var(--warn-ink)" }}>
      <div className="text-[11px] font-semibold mb-0.5">الأسهم الجديدة القادمة</div>
      <div className="flex items-center justify-center gap-2" dir="rtl">{cell(d, "ي")}<span>:</span>{cell(h, "س")}<span>:</span>{cell(m, "د")}</div>
    </div>
  );
}

export default function StarsPage() {
  const [sheet, setSheet] = useState<string | null>(null);
  /* ‏D546: كلُّ معيارٍ مفتاح — المطفأُ يُرسل للخادم فتُعاد السلّةُ وسجلُّها منذ 2015 به. */
  const [off, setOff] = useState<string[]>(readOff);
  const offKey = [...off].sort().join(",");
  const toggle = (k: string) => setOff(o => {
    const n = o.includes(k) ? o.filter(x => x !== k) : [...o, k];
    try { localStorage.setItem(OFF_KEY, JSON.stringify(n)); } catch { /* تفضيلٌ محلّيّ */ }
    return n;
  });
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["tasi-stars", offKey], staleTime: 5 * 60_000, placeholderData: (p: any) => p,
    queryFn: () => marketApi.tasiStars(offKey).then(r => r.data?.data || null),
  });
  const s = data?.summary || {};
  const bt = data?.backtest || null;
  const criteria: any[] = data?.criteria || [];
  const stat = (label: string, v: any) => (
    <div className="rounded-xl border border-[var(--hairline)] px-3 py-2 min-w-0">
      <div className="text-[11px] text-[var(--ink-muted)] truncate">{label}</div>
      <div className={"text-lg font-bold tabular-nums " + tone(v)} dir="ltr" style={{ textAlign: "right" }}>{pct(v)}</div>
    </div>
  );
  const info = (label: string, v: string) => (
    <div className="rounded-xl border border-[var(--hairline)] px-3 py-2 min-w-0">
      <div className="text-[11px] text-[var(--ink-muted)] truncate">{label}</div>
      <div className="text-[13px] font-semibold text-[var(--ink)] truncate">{v}</div>
    </div>
  );
  return (
    <div className="space-y-4 fade-in">
      <div className="card space-y-3">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="min-w-0">
            <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
              <Star size={22} className="text-[var(--brand-ink)]" /> نجوم تاسي
              <span className="tag-b text-[12px]" dir="ltr">TASI20</span>
            </h1>
            <p className="text-[13px] text-[var(--ink-muted)] mt-1">أقوى 20 شركةً في السوق السعودية للتفوّق على تاسي — تُحدَّث شهرياً.</p>
          </div>
          <Countdown to={data?.next_rebalance} />
        </div>
      </div>

      {isLoading ? <div className="card h-64 skeleton" /> : !data?.members?.length ? (
        <div className="card py-10 text-center text-sm text-[var(--ink-muted)]">غير متوفّر</div>
      ) : (
        <>
          <div className="card space-y-3">
            <p className="card-title">الأداء</p>
            <div className="grid grid-cols-3 gap-2">
              {stat("العائد الإجماليّ", s.total)}
              {stat("الأداءُ المتفوّق", s.excess)}
              {stat("تاسي", s.tasi_total)}
            </div>
            <div className="flex items-center gap-3 text-[11px] text-[var(--ink-muted)]">
              <span className="flex items-center gap-1"><span className="w-2.5 h-0.5 inline-block" style={{ background: "var(--brand-ink)" }} />نجوم تاسي</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-0.5 inline-block" style={{ background: "var(--ink-muted)" }} />تاسي</span>
            </div>
            <Curve track={data.track || []} />
            {bt && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {stat("العائد السنوي المركّب", bt.cagr)}
                {stat("تاسي السنوي المركّب", bt.tasi_cagr)}
                {info("أشهر التفوّق على تاسي", `${bt.beat_pct}%`)}
                {stat("أقصى تراجع", bt.max_dd)}
              </div>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {info("تاريخُ البداية", (data.track || [])[1]?.d || data.inception || data.since)}
              {info("تردّدُ إعادة التوازن", data.rebalance || "شهرياً")}
              {info("التركيزُ على الحجم", off.includes("large") ? "كلّ السوق الرئيسة" : "شركاتٌ كبيرة")}
              {info("الأوزان", data.weighting || "متساوية")}
            </div>
          </div>

          <StarsMetrics bt={bt} s={s} members={data.members} />

          {!!bt?.years?.length && (
            <div className="card p-0">
              <div className="px-4 pt-4 pb-2"><p className="card-title">العوائد السنوية</p></div>
              <div className="grid grid-cols-3 gap-3 px-4 py-1.5 text-[11px] text-[var(--ink-muted)] border-b border-[var(--hairline)]">
                <span>السنة</span><span>نجوم تاسي</span><span>تاسي</span>
              </div>
              {[...bt.years].reverse().map((y: any) => (
                <div key={y.y} className="grid grid-cols-3 gap-3 px-4 min-h-[36px] items-center border-b border-[var(--hairline)] last:border-0 text-[13px]">
                  <span className="tabular-nums text-[var(--ink)]">{y.y}</span>
                  <span className={"tabular-nums font-bold " + tone(y.s)} dir="ltr" style={{ textAlign: "right" }}>{pct(y.s)}</span>
                  <span className={"tabular-nums font-bold " + tone(y.t)} dir="ltr" style={{ textAlign: "right" }}>{pct(y.t)}</span>
                </div>
              ))}
            </div>
          )}

          <div className="card p-0">
            <div className="flex items-center justify-between px-4 pt-4 pb-2">
              <p className="card-title">النجوم</p>
              <span className="text-[12px] text-[var(--ink-muted)] tabular-nums">{data.members.length}</span>
            </div>
            <div className="grid grid-cols-[1fr_auto_auto] gap-3 px-4 py-1.5 text-[11px] text-[var(--ink-muted)] border-b border-[var(--hairline)]">
              <span>الشركة</span><span className="w-14 text-center">مكرّر الربحية</span><span className="w-14 text-center">إلى العادل</span>
            </div>
            {data.members.map((m: any) => (
              <button key={m.symbol} type="button" onClick={() => setSheet(m.symbol)}
                className="w-full grid grid-cols-[1fr_auto_auto] items-center gap-3 px-4 py-2 min-h-[44px] text-start border-b border-[var(--hairline)] last:border-0 hover:bg-[var(--field)]">
                <span className="flex items-center gap-2 min-w-0">
                  <CompanyLogo symbol={m.symbol} size={26} />
                  <span className="min-w-0">
                    <span className="block text-[13px] font-semibold text-[var(--ink)] truncate">{m.name}</span>
                    <span className="block text-[11px] text-[var(--ink-muted)] tabular-nums" dir="ltr" style={{ textAlign: "right" }}>{m.symbol}</span>
                  </span>
                </span>
                <span className="w-14 text-center text-[13px] font-bold tabular-nums text-[var(--ink)]" dir="ltr">
                  {typeof m.pe === "number" ? `${m.pe.toFixed(1)}x` : "—"}</span>
                <span className={"w-14 text-center text-[13px] font-bold tabular-nums " + tone(m.upside)} dir="ltr">{pct(m.upside)}</span>
              </button>
            ))}
          </div>
        </>
      )}

      {data?.members?.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <MiniList title="قادمة هذا الشهر" items={data.entering} onPick={setSheet} tone="var(--pos-ink)" />
          <MiniList title="خارجة هذا الشهر" items={data.exiting} onPick={setSheet} tone="var(--neg-ink)" />
        </div>
      )}
      {data?.members?.length > 0 && <MiniList title="تحت المراقبة" items={data.watch} onPick={setSheet} tone="var(--warn-ink)" />}

      <div className="card">
        <div className="flex items-center justify-between mb-2">
          <p className="card-title">المعايير</p>
          {isFetching && <span className="w-3 h-3 rounded-full skeleton" aria-hidden />}
        </div>
        {([["filter", "الشروط"], ["family", "عائلات الترتيب"]] as const).map(([g, title]) => (
          <div key={g} className="mb-2">
            <div className="text-[11px] font-semibold text-[var(--ink-muted)] mt-2 mb-1">{title}</div>
            {criteria.filter(c => c.group === g).map(c => {
              const on = !off.includes(c.key);
              return (
                <button key={c.key} type="button" role="switch" aria-checked={on} onClick={() => toggle(c.key)}
                  className="w-full flex items-center justify-between gap-3 min-h-[40px] text-start border-b border-[var(--hairline)] last:border-0">
                  <span className={"text-[13px] " + (on ? "text-[var(--ink)]" : "text-[var(--ink-muted)]")}>{c.label}</span>
                  <span aria-hidden className={"switch inline-block" + (on ? " on" : "")} />
                </button>
              );
            })}
          </div>
        ))}
        {FIXED.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between gap-3 min-h-[36px] border-b border-[var(--hairline)] last:border-0">
            <span className="text-[13px] text-[var(--ink)]">{k}</span>
            <span className="text-[13px] font-semibold text-[var(--ink-muted)] text-end">{v}</span>
          </div>
        ))}
      </div>
      <LabCard onPick={setSheet} />
      {sheet && <StockSheet symbol={sheet} onClose={() => setSheet(null)} />}
    </div>
  );
}

/* ══ مختبرُ السلّة (D608) ══ بأمر المالك: شركاتٌ يختارها هو، فيرى أداءها منذ 2015 مقابل تاسي
   بمحرّك «نجوم تاسي» نفسِه، وما تقوله المحرّكاتُ عنها اليوم — قبل أن يعتمدها. قراءةٌ فقط. */
const LAB_KEY = "stars:lab";
function LabCard({ onPick }: { onPick: (s: string) => void }) {
  const [syms, setSyms] = useState<string[]>(() => { try { return JSON.parse(localStorage.getItem(LAB_KEY) || "[]"); } catch { return []; } });
  const [q, setQ] = useState("");
  const [start, setStart] = useState("2015-01");
  const [run, setRun] = useState<string[] | null>(null);
  const save = (n: string[]) => { setSyms(n); try { localStorage.setItem(LAB_KEY, JSON.stringify(n)); } catch { /* محلّيّ */ } };
  const { data: rows = [] } = useQuery({
    queryKey: ["screener-lite"], staleTime: 30 * 60_000,
    queryFn: () => marketApi.screener().then(r => (r.data?.data || []) as any[]),
  });
  const nameOf = (s: string) => (rows.find((r: any) => String(r.symbol).replace(".SR", "") === s) || {}).name || s;
  const hits = q.trim().length < 2 ? [] : rows.filter((r: any) => {
    const sym = String(r.symbol).replace(".SR", "");
    return !syms.includes(sym) && (sym.startsWith(q.trim()) || String(r.name || "").includes(q.trim()));
  }).slice(0, 6);
  const { data, isFetching } = useQuery({
    queryKey: ["stars-lab", (run || []).join(","), start], enabled: !!run?.length,
    queryFn: () => marketApi.starsLab(run || [], start).then(r => r.data?.data || null),
  });
  const fw = data?.forward;
  const box = (label: string, v: any, isPct = true) => (
    <div className="rounded-xl border border-[var(--hairline)] px-3 py-2 min-w-0">
      <div className="text-[11px] text-[var(--ink-muted)] truncate">{label}</div>
      <div className={"text-[15px] font-bold tabular-nums " + (isPct ? tone(v) : "text-[var(--ink)]")} dir="ltr" style={{ textAlign: "right" }}>
        {isPct ? pct(v) : v}</div>
    </div>
  );
  return (
    <div className="card space-y-3">
      <div>
        <p className="card-title">مختبرُ السلّة</p>
        <p className="text-[12px] text-[var(--ink-muted)] mt-1">اختر شركاتك، فترى أداءها مقابل تاسي بمحرّك النجوم نفسِه، وما تقوله المحرّكاتُ عنها اليوم.</p>
      </div>
      <div className="relative">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="اسم الشركة أو رمزها"
          className="w-full min-h-[40px] rounded-xl px-3 text-[13px] bg-[var(--field)] border border-[var(--hairline)] text-[var(--ink)]" />
        {hits.length > 0 && (
          <div className="absolute z-10 inset-x-0 mt-1 rounded-xl border border-[var(--line)] bg-[var(--pop)] overflow-hidden">
            {hits.map((r: any) => {
              const sym = String(r.symbol).replace(".SR", "");
              return (
                <button key={sym} type="button" onClick={() => { save([...syms, sym].slice(0, 30)); setQ(""); }}
                  className="w-full flex items-center justify-between gap-2 px-3 min-h-[40px] text-start hover:bg-[var(--field)]">
                  <span className="text-[13px] text-[var(--ink)] truncate">{r.name}</span>
                  <span className="text-[11px] text-[var(--ink-muted)] tabular-nums">{sym}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>
      {syms.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {syms.map(s => (
            <button key={s} type="button" onClick={() => save(syms.filter(x => x !== s))}
              className="flex items-center gap-1 px-2.5 min-h-[32px] rounded-full border border-[var(--hairline)] text-[12px] text-[var(--ink)]">
              {nameOf(s)} <span className="text-[var(--ink-muted)]">×</span>
            </button>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 flex-wrap">
        <select value={start} onChange={e => setStart(e.target.value)}
          className="min-h-[36px] rounded-lg px-2 text-[12px] bg-[var(--field)] border border-[var(--hairline)] text-[var(--ink)]">
          {["2015-01", "2018-01", "2020-01", "2022-01", "2024-01"].map(v => <option key={v} value={v}>منذ {v.slice(0, 4)}</option>)}
        </select>
        <button type="button" disabled={!syms.length} onClick={() => setRun([...syms])}
          className="btn-primary min-h-[36px] px-4 rounded-lg text-[13px] font-bold disabled:opacity-50">اختبر السلّة</button>
        {isFetching && <span className="w-3 h-3 rounded-full skeleton" aria-hidden />}
      </div>

      {run && !isFetching && !data && <p className="text-[13px] text-[var(--ink-muted)]">غير متوفّر — بياناتُ الأسعار التاريخية تُجمع الآن؛ أعد المحاولة بعد دقائق.</p>}
      {data?.track?.length > 1 && (
        <div className="space-y-3">
          <div className="flex items-center gap-3 text-[11px] text-[var(--ink-muted)]">
            <span className="flex items-center gap-1"><span className="w-2.5 h-0.5 inline-block" style={{ background: "var(--brand-ink)" }} />سلّتك</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-0.5 inline-block" style={{ background: "var(--ink-muted)" }} />تاسي</span>
          </div>
          <Curve track={data.track} />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {box("العائد الإجماليّ", data.total)}
            {box("تاسي", data.tasi_total)}
            {box("العائد السنويّ المركّب", data.cagr)}
            {box("أقصى تراجع", data.max_dd)}
          </div>
          <div className="grid grid-cols-2 gap-2">
            {box("أشهرُ التفوّق على تاسي", `${data.beat_pct}%`, false)}
            {box("تاسي السنويّ المركّب", data.tasi_cagr)}
          </div>
          {!!data.missing?.length && <p className="text-[12px] text-[var(--warn-ink)]">بلا سجلّ أسعار: {data.missing.map(nameOf).join("، ")}</p>}
        </div>
      )}
      {fw?.items?.length > 0 && (
        <div className="rounded-xl border border-[var(--hairline)] overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--hairline)]">
            <span className="text-[13px] font-semibold text-[var(--ink)]">النظرةُ القادمة — ما تقوله المحرّكاتُ اليوم</span>
            <span className="text-[12px] tabular-nums text-[var(--ink-muted)]">
              {fw.upside_reliable != null ? <>إلى العادل <b className={tone(fw.upside_reliable)} dir="ltr">{pct(fw.upside_reliable)}</b> ({fw.reliable_n}/{fw.n} موثوقة)</> : "لا قيمةَ عادلةَ موثوقة"}
            </span>
          </div>
          {fw.items.map((it: any) => (
            <button key={it.symbol} type="button" onClick={() => onPick(it.symbol)}
              className="w-full grid grid-cols-[1fr_auto_auto] items-center gap-3 px-3 min-h-[40px] text-start border-b border-[var(--hairline)] last:border-0 hover:bg-[var(--field)]">
              <span className="text-[13px] text-[var(--ink)] truncate">{it.name || it.symbol}
                <span className="block text-[11px] text-[var(--ink-muted)]">{it.decision || "—"} · جودة {it.quality ?? "—"}</span></span>
              <span className={"text-[13px] font-bold tabular-nums " + tone(it.upside)} dir="ltr">{pct(it.upside)}</span>
              <span className="text-[11px] text-[var(--ink-muted)] w-12 text-center">{it.conf || "—"}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}


/* ‏D609: مؤشراتٌ ماليةٌ لمحفظة النجوم بأسلوب مؤشرات المحفظة الأساسية — والوصولُ إلى هدفك بعائدها مقابل عائدك. */
function StarsMetrics({ bt, s, members }: { bt: any; s: any; members: any[] }) {
  const { data: goals } = useQuery({ queryKey: ["goals-builtin"], queryFn: () => goalsApi.builtin().then((r: any) => r.data.data), retry: 0 });
  const { data: pm } = useQuery({ queryKey: ["portfolio-metrics"], queryFn: () => portfolioApi.metrics().then((r: any) => r.data.data), retry: 0 });
  if (!bt) return null;
  const med = (xs: number[]) => { const v = xs.filter(x => typeof x === "number").sort((a, b) => a - b); return v.length ? v[Math.floor(v.length / 2)] : null; };
  const avg = (xs: number[]) => { const v = xs.filter(x => typeof x === "number"); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
  const pe = med(members.map(m => m.pe));
  const up = avg(members.map(m => m.upside));
  const cells: { lbl: string; val: string | null; color?: string }[] = [
    { lbl: "العائد المركّب", val: pct(bt.cagr) },
    { lbl: "تاسي المركّب", val: pct(bt.tasi_cagr) },
    { lbl: "التفوّقُ السنويّ", val: typeof bt.cagr === "number" && typeof bt.tasi_cagr === "number" ? pct(bt.cagr - bt.tasi_cagr) : null },
    { lbl: "العائد الإجماليّ", val: pct(s?.total) },
    { lbl: "أقصى تراجع", val: pct(bt.max_dd), color: "var(--neg-ink)" },
    { lbl: "أشهرُ التفوّق", val: bt.beat_pct != null ? `${bt.beat_pct}%` : null },
    { lbl: "مكرر الربحية", val: pe != null ? pe.toFixed(1) : null },
    { lbl: "اتجاهٌ إلى العادل", val: up != null ? pct(up) : null },
    { lbl: "الشركات", val: String(members.length) },
  ];
  const g = goals?.million;
  return (
    <div className="card space-y-2">
      <p className="card-title">المؤشرات المالية</p>
      <div className="grid grid-cols-3 gap-2">
        {cells.map(c => (
          <div key={c.lbl} className="kpi">
            <div className="kpi-lbl">{c.lbl}</div>
            <div className="kpi-val tabular-nums" dir="ltr" style={{ textAlign: "right", color: c.val == null ? "var(--ink-muted)" : c.color }}>{c.val ?? "—"}</div>
          </div>
        ))}
      </div>
      {g?.target > 0 && (
        <div className="grid grid-cols-2 gap-2">
          <div className="kpi">
            <div className="kpi-lbl">الوصول إلى {Number(g.target).toLocaleString("en-US")} بعائد النجوم</div>
            <div className="kpi-val tabular-nums" style={{ color: "var(--brand-ink)" }}>{yearsLabel(yearsToGoal(g.current, g.target, bt.cagr))}</div>
          </div>
          <div className="kpi">
            <div className="kpi-lbl">وبعائد محفظتك</div>
            <div className="kpi-val tabular-nums">{yearsLabel(yearsToGoal(g.current, g.target, pm?.cagr_pct))}</div>
          </div>
        </div>
      )}
    </div>
  );
}
