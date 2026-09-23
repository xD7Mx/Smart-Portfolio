import React, { useState } from "react";
import { LivePct } from "../common/LivePrice";
import StockSheet from "./StockSheet";
import { useQuery } from "@tanstack/react-query";
import { AreaChart, Area, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { LineChart as LineIcon, Fuel, Grid3x3, BarChart3, Gauge, Layers, Activity, ChevronLeft } from "lucide-react";
import clsx from "clsx";
import { marketApi, portfolioApi } from "../../services/api";
import CompanyLogo from "../common/CompanyLogo";

/* لصقُ لاحقةٍ ستّ عشرية على اللون (`${color}33`) يعمل مع قيمةٍ ثابتة فقط،
   ويبطل تماماً إن كان اللون رمزاً (`var(--pos-ink)33` غير صالح) فيسقط
   الخلفية أو الحدّ بلا أثر. هذه تُنتج الشفافية بطريقةٍ تقبل الاثنين. */
const mixA = (c: string, pct: number) => `color-mix(in srgb, ${c} ${pct}%, transparent)`;


const govColor = (s: number | null | undefined) =>
  s == null ? "var(--ink-muted)" : s >= 70 ? "var(--pos-ink)" : s >= 50 ? "var(--warn-ink)" : "var(--neg-ink)";

const fmtNum = (n: number, d = 0) => (n ?? 0).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const compactSar = (n: number) => {
  const a = Math.abs(n || 0);
  if (a >= 1e9) return fmtNum(n / 1e9, 2) + " مليار";
  if (a >= 1e6) return fmtNum(n / 1e6, 2) + " مليون";
  if (a >= 1e3) return fmtNum(n / 1e3, 1) + " ألف";
  return fmtNum(n);
};

/** Honest "last close" badge — shown whenever the served market snapshot is
 * a persisted last-known-good copy (carries _stale_since) rather than a live
 * intraday scan, so a served close is never presented as live. */
export function StaleNote({ movers }: { movers: any }) {
  if (!movers?._stale_since) return null;
  let when = "";
  try {
    when = new Date(movers._stale_since).toLocaleDateString("ar-SA-u-ca-gregory-nu-latn", { day: "2-digit", month: "2-digit" });
  } catch { /* ignore */ }
  return <span className="text-[10px] text-[var(--warn-ink)] font-semibold shrink-0">آخر إغلاق {when}</span>;
}

const TIP = {
  contentStyle: { background: "var(--pop)", border: "1px solid var(--line)", color: "var(--tip-text)", borderRadius: 10, fontSize: 12 },
  labelStyle: { color: "var(--tip-text)", fontWeight: 300 as const, marginBottom: 4 },
  itemStyle: { color: "var(--tip-text)" },
};

/* ── 04 / 07 — Index history line (TASI or Brent) ───────────────── */
export function IndexHistoryCard({ symbol, title, icon, defaultRange = "6mo", valueLabel, suffix = "" }:
  { symbol: string; title: string; icon: "index" | "brent"; defaultRange?: string; valueLabel: string; suffix?: string }) {
  const [range, setRange] = useState(defaultRange);
  const { data: points = [], isLoading } = useQuery({
    queryKey: ["mkt-history", symbol, range],
    queryFn: () => marketApi.history(symbol, range).then(r => Array.isArray(r.data?.data) ? r.data.data : []),
    staleTime: 60 * 60 * 1000,
  });
  const up = points.length >= 2 && points[points.length - 1].close >= points[0].close;
  const color = up ? "var(--pos-ink)" : "var(--neg-ink)";
  const Icon = icon === "brent" ? Fuel : LineIcon;
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <p className="card-title flex items-center gap-1.5">
          <Icon size={15} className={icon === "brent" ? "text-[var(--warn-ink)]" : "text-[var(--brand-ink)]"} /> {title}
        </p>
        <div className="flex gap-1.5" dir="rtl">
          {[["1mo", "شهر"], ["3mo", "3 أشهر"], ["6mo", "6 أشهر"], ["1y", "سنة"]].map(([id, lbl]) => (
            <button key={id} onClick={() => setRange(id)}
              className={clsx("px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all",
                range === id ? " text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)] hover:text-[var(--ink)]")}>
              {lbl}
            </button>
          ))}
        </div>
      </div>
      {isLoading ? <div className="h-[200px] skeleton" /> : points.length >= 2 ? (
        <div style={{ height: 200 }} dir="ltr">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`ih-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.12)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--ink-muted)" }} tickFormatter={(d: string) => d.slice(5)} minTickGap={30} />
              <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fill: "var(--ink-muted)" }} orientation="right" mirror width={1} tickLine={false} axisLine={false}
                tickFormatter={(v: number) => fmtNum(v)} />
              <Tooltip {...TIP} formatter={(v: any) => [fmtNum(Number(v), 2) + suffix, valueLabel]} />
              <Area type="monotone" dataKey="close" stroke={color} strokeWidth={2} fill={`url(#ih-${symbol})`} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="py-14 text-center text-[var(--ink-muted)] text-sm">لا يتوفر تاريخ لهذا المؤشر حالياً — يُجلب مرة يومياً عند توفر المصدر</div>
      )}
    </div>
  );
}

/* ── 05 — Sector heatmap ────────────────────────────────────────── */
/* القطاع الثابت (‏|تغيّر| < 0.3٪) كان يأخذ `--ink-muted` — رماديّاً
   شديد القتامة يُقرأ أسودَ على الورق الرملي، فيبدو مربّعاً شاذّاً بين
   إخوته. وهو ليس حالةً دلالية أصلاً: لا صعودَ ولا هبوط، فلا لون.
   فيأخذ سطح التطبيق نفسه كالقطاع الذي لا بيانات له — تناسقٌ لونيّ،
   واللون يبقى للمتحرّك وحده. */
const isFlat = (pct: number | null | undefined) => pct == null || Math.abs(pct) < 0.3;
/* ══ درجاتُ الصفحة الواحدة ══ (بأمر المالك)
   كانت الخريطة تأخذ `--pos-ink`/`--neg-ink` بينما جاراتُها في الصفحة
   نفسها (توزيع الحركة · شريط الصاعد/الهابط · قوس المزاج) تأخذ
   `--pos-fill`/`--neg-fill`. فيختلف أخضرُ الخريطة عن أخضر الرسم الذي
   يعلوها بدرجةٍ كاملة، والعين تقرأ الاختلاف معنىً لا صدفة.
   والصواب هو الحشو لا الحبر: مربّعات الخريطة **مساحاتٌ يُكتب فوقها
   أبيض**، وهذا بالضبط ما وُضع له `--*-fill` (انظر D014). فالتوحيد هنا
   يُصلح شيئين معاً: اتّساق الصفحة، وأرضيةً صُمّمت لبياضِ حروفها. */
function heatColor(pct: number): string {
  if (pct >= 0.3) return "var(--pos-fill)";
  if (pct <= -0.3) return "var(--neg-fill)";
  return "var(--surface)";
}
export function SectorHeatmapCard({ movers }: { movers: any }) {
  const [open, setOpen] = useState<string | null>(null);
  // نافذة الشركة تُفتح فوق الخريطة نفسها — لا قذف إلى صفحة السوق.
  const [sheet, setSheet] = useState<string | null>(null);

  // ONE comprehensive payload: every sector + all its companies + each
  // company's governance score (same as the governance market tab) + move.
  const { data, isLoading } = useQuery({
    queryKey: ["sector-map"],
    queryFn: () => portfolioApi.sectorMap().then(r => r.data.data),
    staleTime: 5 * 60 * 1000,
  });
  const sectors: any[] = data?.sectors || [];
  const current = open ? sectors.find(s => s.sector === open) : null;

  return (
    <div className="card">
      <p className="card-title mb-3 flex items-center gap-1.5"><Grid3x3 size={15} className="text-[var(--brand-ink)]" /> خريطة أداء القطاعات<span className="ms-auto"><StaleNote movers={movers} /></span></p>
      {isLoading && sectors.length === 0 ? (
        <div className="h-24 flex items-center justify-center text-[var(--ink-muted)] text-sm">جارٍ تحميل القطاعات…</div>
      ) : sectors.length === 0 ? (
        <div className="h-24 flex items-center justify-center text-[var(--ink-muted)] text-sm">لم تُحسب بيانات السوق بعد — تُحدَّث تلقائياً كل ساعة</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2" dir="rtl">
          {sectors.map((s: any) => {
            const chg = s.avg_change_pct;
            return (
              <button key={s.sector} onClick={() => setOpen(open === s.sector ? null : s.sector)}
                className="rounded-xl p-2.5 flex flex-col justify-between text-start transition-transform hover:scale-[1.03] focus:outline-none focus:ring-2 focus:ring-white/60"
                /* القطاع بلا بيانات كان مربّعاً أزرق داكناً — جزيرةٌ باردة فوق
                   الورق الرملي، ونصٌّ أبيض بظلٍّ على خلفيةٍ لا تحتاجه. الآن
                   سطحٌ من الدليل ونصٌّ بلون الحبر، والملوَّن يبقى للمتحرّك. */
                style={{ background: isFlat(chg) ? "var(--surface)" : heatColor(chg), minHeight: 64,
                         border: isFlat(chg) ? "1px solid var(--hairline)" : undefined,
                         boxShadow: open === s.sector ? "0 0 0 2px var(--brand) inset" : undefined }}
                title={`اعرض شركات ${s.sector}`}>
                <span className="text-[11px] font-bold leading-tight"
                  style={{ color: isFlat(chg) ? "var(--ink)" : "#fff", textShadow: isFlat(chg) ? "none" : "0 1px 3px rgba(0,0,0,.35)" }}>{s.sector}</span>
                <span className="text-[13px] font-extrabold tabular-nums flex items-center justify-between" dir="ltr"
                  style={{ color: isFlat(chg) ? "var(--ink-muted)" : "#fff", textShadow: isFlat(chg) ? "none" : "0 1px 3px rgba(0,0,0,.4)" }}>
                  <span>{chg == null ? "—" : (chg >= 0 ? "+" : "") + chg.toFixed(2) + "%"}</span>
                  <span className="text-[10px] opacity-80">{s.count} شركة</span>
                </span>
              </button>
            );
          })}
        </div>
      )}

      {current && (
        <div className="mt-3 rounded-xl p-3" style={{ background: "var(--panel)", border: "1px solid var(--line)" }}>
          <div className="flex items-center justify-between mb-2">
            <p className="card-title">{current.sector} — {current.count} شركة{current.avg_score != null ? ` · متوسط الحوكمة ${current.avg_score}` : ""}</p>
            <button onClick={() => setOpen(null)} className="text-[var(--ink-muted)] hover:text-[var(--ink)] text-xs flex items-center gap-1"><ChevronLeft size={14} /> إغلاق</button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-[360px] overflow-y-auto">
            {current.companies.map((c: any) => (
              <button key={c.symbol} onClick={() => setSheet(c.symbol)}
                className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-[var(--field)] transition-colors text-start">
                <CompanyLogo symbol={c.symbol} size={26} logoUrl={c.logo_url} />
                <div className="min-w-0 flex-1">
                  <div className="text-[var(--ink)] text-[13px] font-semibold truncate">{c.name}</div>
                  <div className="text-[10px] text-[var(--ink-muted)] tabular-nums">{c.symbol}</div>
                </div>
                {c.finance_score != null ? (
                  <span className="shrink-0 text-[11px] font-extrabold rounded-md px-1.5 py-0.5 tabular-nums" title="درجة الجودة المالية"
                    style={{ color: govColor(c.finance_score), background: mixA(govColor(c.finance_score), 10) }}>
                    {Math.round(c.finance_score)}
                  </span>
                ) : (
                  <span className="shrink-0 text-[9.5px] text-[var(--ink-muted)] rounded-md px-1.5 py-0.5" title="بيانات غير كافية لحكم موثوق"
                    style={{ background: "transparent" }}>لا ينطبق</span>
                )}
                {c.change_pct != null ? (
                  /* شركاتُ القطاع تقرأ المجرى كما الشريط (D331) */
                  <LivePct symbol={c.symbol} fallback={c.change_pct}
                    className="text-[12px] font-bold tabular-nums shrink-0 w-14 text-end"
                    tone={(v) => v == null ? "var(--ink-muted)"
                      : v > 0 ? "var(--pos-ink)"
                      : v < 0 ? "var(--neg-ink)" : "var(--ink-muted)"} />
                ) : (
                  <span className="text-[10px] text-[var(--ink-muted)] shrink-0 w-14 text-end">—</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
      {sheet && <StockSheet symbol={sheet} onClose={() => setSheet(null)} />}
    </div>
  );
}

/* ── 06 — Return distribution histogram ─────────────────────────── */
export function ReturnDistributionCard({ movers }: { movers: any }) {
  const dist: any[] = movers?.distribution || [];
  const has = dist.some((b: any) => b.count > 0);
  return (
    <div className="card">
      <p className="card-title mb-3 flex items-center gap-1.5"><BarChart3 size={15} className="text-[var(--brand-ink)]" /> توزيع أداء السوق اليوم<span className="ms-auto"><StaleNote movers={movers} /></span></p>
      {!has ? (
        <div className="h-24 flex items-center justify-center text-[var(--ink-muted)] text-sm">لم تُحسب بيانات السوق بعد</div>
      ) : (
        <div style={{ height: 180 }} dir="ltr">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={dist} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.12)" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 9, fill: "var(--ink-muted)" }} interval={0} />
              <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "var(--ink-muted)" }} width={32} />
              <Tooltip {...TIP} cursor={{ fill: "rgba(148,163,184,.08)" }} formatter={(v: any) => [v + " شركة", "العدد"]} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {dist.map((b: any, i: number) => <Cell key={i} fill={b.tone === "up" ? "var(--pos-fill)" : "var(--neg-fill)"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

/* ── 08 — Market breadth proportional bar ───────────────────────── */
export function BreadthBarCard({ movers }: { movers: any }) {
  const adv = movers?.advancers ?? 0, dec = movers?.decliners ?? 0, unch = movers?.unchanged ?? 0;
  const total = adv + dec + unch;
  const pct = (n: number) => total ? (n / total) * 100 : 0;
  return (
    <div className="card flex flex-col h-full">
      <p className="card-title mb-3 flex items-center gap-1.5"><Activity size={15} className="text-[var(--brand-ink)]" /> عرض النطاق — اتساع السوق<span className="ms-auto"><StaleNote movers={movers} /></span></p>
      {total === 0 ? (
        <div className="h-16 flex items-center justify-center text-[var(--ink-muted)] text-sm">لم تُحسب بيانات السوق بعد</div>
      ) : (
        <div className="flex flex-col flex-1">
          <div className="breadth-bar flex h-7 w-full rounded-lg overflow-hidden text-[11px] font-bold" dir="ltr"
>
            {/* الرقم أبيضُ داخل الشريحة، فتعبئتها هي خلفيته: الأخضر الفاتح
                أعطى 2.54:1 والأحمر 3.67:1 — رقمٌ يُقرأ يومياً تحت الأرضية.
                التعبئة تصير الحبر الدلالي العميق، فيصعد التباين فوق 5:1
                ويبقى معنى اللون كما هو. */}
            {adv > 0 && <div style={{ width: `${pct(adv)}%`, background: "var(--pos-fill)" }} className="flex items-center justify-center">{adv}</div>}
            {/* الشريحة الثابتة كانت `--ink-muted` — كتلةٌ سوداء بين الأخضر
                والأحمر. والثبات ليس دلالةً ملوّنة، فتأخذ سطح التطبيق
                وحبره الطبيعيّ بدل البياض الذي كان يحتاج أرضيةً داكنة. */}
            {unch > 0 && <div style={{ width: `${pct(unch)}%`, background: "var(--surface)", color: "var(--ink)" }} className="flex items-center justify-center">{unch > total * 0.05 ? unch : ""}</div>}
            {dec > 0 && <div style={{ width: `${pct(dec)}%`, background: "var(--neg-fill)" }} className="flex items-center justify-center">{dec}</div>}
          </div>
          {/* dir=ltr مطابقٌ لاتجاه الشريط أعلاه: كانت التسميات ترث RTL بينما
              الشريط ltr، فتقع «هابطة» تحت الشريحة الخضراء والعكس (انعكاس). */}
          <div className="flex items-center justify-between mt-2.5 text-[11px]" dir="ltr">
            <span className="text-[var(--pos-ink)] font-semibold">▲ صاعدة {adv}</span>
            <span className="text-[var(--ink-muted)]">ثابتة {unch}</span>
            <span className="text-[var(--neg-ink)] font-semibold">هابطة {dec} ▼</span>
          </div>
          {/* فوت نوت البطاقة: مدفوع لأسفلها (mt-auto) ومفصول بخطّ */}
          <p className="text-[10.5px] text-[var(--ink-muted)] mt-auto pt-2.5 text-center"
            style={{ borderTop: "1px solid var(--line)" }}>
            نسبة الصاعدين {Math.round(pct(adv))}٪ من {total} شركة
          </p>
        </div>
      )}
    </div>
  );
}

/* ── 09 — Market sentiment gauge ────────────────────────────────── */
export function SentimentGaugeCard({ movers }: { movers: any }) {
  const s = movers?.sentiment;
  const score = s?.score ?? 50;
  const has = !!s;
  // Semicircle: 180° arc, needle angle from score. Color by zone.
  // نصّ «مزاج إيجابي» يأخذ هذا اللون؛ الأخضر الفاتح أعطى 2.35:1 على الورق.
  const color = score >= 56 ? "var(--pos-ink)" : score >= 45 ? "var(--warn-ink)" : "var(--neg-ink)";
  // القوس خطٌّ بسُمك 12 يلفّ نصف دائرة — مساحةٌ لا حرف، فيأخذ الحشو.
  // والنصّ تحته يبقى على الحبر لأنه يُقرأ ويحتاج تباينه.
  const arcColor = score >= 56 ? "var(--pos-fill)" : score >= 45 ? "var(--warn-ink)" : "var(--neg-fill)";
  const R = 68, CX = 80, CY = 80;
  const ang = Math.PI * (1 - score / 100); // 0->right(180°..) map: score0=π(left), score100=0(right)
  const ex = CX + R * Math.cos(ang), ey = CY - R * Math.sin(ang);
  // filled arc from left (score 0) to needle
  const large = 0;
  const arcPath = `M ${CX - R} ${CY} A ${R} ${R} 0 ${large} 1 ${ex} ${ey}`;
  return (
    <div className="card">
      <p className="card-title mb-2 flex items-center gap-1.5"><Gauge size={15} className="text-[var(--brand-ink)]" /> مزاج السوق<span className="ms-auto"><StaleNote movers={movers} /></span></p>
      {!has ? (
        <div className="h-32 flex items-center justify-center text-[var(--ink-muted)] text-sm">لم تُحسب بيانات السوق بعد</div>
      ) : (
        <div className="flex flex-col items-center" dir="ltr">
          <svg viewBox="0 0 160 96" width="170" height="102">
            <path d={`M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`} fill="none" stroke="var(--line)" strokeWidth="12" strokeLinecap="round" />
            <path d={arcPath} fill="none" stroke={arcColor} strokeWidth="12" strokeLinecap="round" />
            <circle cx={ex} cy={ey} r="6" fill="var(--panel)" stroke={arcColor} strokeWidth="3" />
            <text x={CX} y="66" textAnchor="middle" fontSize="20" fontWeight="800" className="text-[var(--ink)]" fill="currentColor">{score}</text>
            <text x={CX} y="82" textAnchor="middle" fontSize="10" className="text-[var(--ink-muted)]" fill="currentColor">/ 100</text>
          </svg>
          <p className="text-sm font-bold mt-1" style={{ color }}>{s.label}</p>
        </div>
      )}
    </div>
  );
}

/* ── 10 — Sector leaders / laggards ─────────────────────────────── */
export function SectorLeadersCard({ movers }: { movers: any }) {
  const sectors: any[] = movers?.sectors || [];
  const top = sectors.slice(0, 3);
  const bottom = sectors.slice(-3).reverse().filter((b: any) => !top.includes(b));
  const Row = ({ s }: { s: any }) => (
    <div className="flex items-center justify-between py-1.5 text-[13px]">
      <span className="text-[var(--ink)] truncate">{s.sector} <span className="text-[var(--ink-muted)] text-[11px]">({s.count})</span></span>
      <span className={"font-bold tabular-nums " + (s.avg_change_pct >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")} dir="ltr">
        {s.avg_change_pct >= 0 ? "+" : ""}{s.avg_change_pct.toFixed(2)}%
      </span>
    </div>
  );
  return (
    <div className="card">
      <p className="card-title mb-2 flex items-center gap-1.5"><Layers size={15} className="text-[var(--brand-ink)]" /> أقوى القطاعات وأضعفها<span className="ms-auto"><StaleNote movers={movers} /></span></p>
      {sectors.length === 0 ? (
        <div className="h-24 flex items-center justify-center text-[var(--ink-muted)] text-sm">لم تُحسب بيانات السوق بعد</div>
      ) : (
        <>
          <p className="text-[11px] font-bold text-[var(--pos-ink)] mt-1">الأقوى</p>
          {top.map((s: any) => <Row key={s.sector} s={s} />)}
          {bottom.length > 0 && <>
            <div className="h-px bg-[var(--surface)] my-1.5" />
            <p className="text-[11px] font-bold text-[var(--neg-ink)]">الأضعف</p>
            {bottom.map((s: any) => <Row key={s.sector} s={s} />)}
          </>}
        </>
      )}
    </div>
  );
}

/* ── 14 — Daily market liquidity — REAL aggregate traded value ─ */
export function LiquidityCard({ movers }: { movers?: any }) {
  // REAL headline: Σ(price × today's volume) across every scanned company —
  // the actual market turnover, not an index estimate.
  const realToday: number | null = movers?.market_liquidity ?? null;
  /* ══ الأعمدةُ لم تكن تظهر ══ (عطبٌ رآه المالك)
     الاحتياطُ كان (إغلاق تاسي × حجمه)، وياهو لا يُعيد حجماً للمؤشّر —
     فيُصفّى كلُّ عمود ويبقى الشرطُ `bars.length >= 2` غيرَ مستوفٍ أبداً،
     فتظهر البطاقةُ برأسٍ بلا جسم. والسلسلةُ الحقيقية صارت تُملأ رجعياً في
     الخادم من تاريخ الشركات التي تحمل سيولةَ السوق، فسقط الاحتياطُ الميّت
     ولم يُترك ليموّه الغياب. */
  const ownSeries: any[] = Array.isArray(movers?.liquidity_series) ? movers.liquidity_series : [];
  const bars = ownSeries
    .filter((p: any) => Number(p?.value) > 0)
    .slice(-12)
    .map((p: any) => ({ date: p.date, value: Number(p.value) }));
  // كم عمودٍ منها من العيّنة لا من المسح الكامل — يُقال ولا يُخفى.
  const sampled = ownSeries.slice(-12).filter((p: any) => p?.src === "sample" && Number(p?.value) > 0).length;
  const avg = bars.length ? bars.reduce((a: number, b: any) => a + b.value, 0) / bars.length : 0;
  const trendToday = bars.length ? bars[bars.length - 1].value : 0;
  const vsAvg = avg ? ((trendToday - avg) / avg) * 100 : 0;
  return (
    <div className="card">
      <p className="card-title mb-3 flex items-center gap-1.5"><Activity size={15} className="text-[var(--brand-ink)]" /> السيولة اليومية للسوق</p>
      {realToday == null && bars.length < 1 ? (
        <div className="py-12 text-center text-[var(--ink-muted)] text-sm">لم تُحسب السيولة بعد — تُحدَّث مع فحص السوق</div>
      ) : (
        <>
          {/* **الرقم يقول ما هو.** كان يُعرض `realToday ?? trendToday` بلا
              تفريق: فإن غاب مجموعُ التداول الحقيقي حلّ محلّه تقديرٌ مشتقٌّ من
              (إغلاق المؤشر × حجم المؤشر) وظهر بالمظهر نفسه — رقمٌ ليس قيمة
              التداول ويُقرأ على أنه هي. الآن يُسمّى التقدير تقديراً.
              والتغطية تُذكر: المجموع هو مجموع ما وصلت أسعاره وأحجامه، فإن
              سقط جزءٌ من السوق سقط من الرقم — ويجب أن يُقال لا أن يُخفى. */}
          <div className="flex items-baseline gap-2 mb-1" dir="ltr">
            <span className="text-xl font-extrabold text-[var(--ink)] tabular-nums">{compactSar(realToday ?? trendToday)}</span>
            <span className="text-[13px] text-[var(--ink-muted)]">﷼</span>
            {realToday == null && (
              <span className="text-[10px] font-bold ms-2 px-1.5 py-0.5 rounded-md"
                style={{ background: "color-mix(in srgb, var(--warn-ink) 14%, transparent)", color: "var(--warn-ink)" }}>
                تقدير من المؤشر — ليس مجموع التداول
              </span>
            )}
          </div>
          <p className="text-[10px] text-[var(--ink-muted)] mb-2" dir="rtl">
            {realToday != null && movers?.scanned != null
              ? `مجموع (السعر × حجم اليوم) لـ${movers.liquidity_symbols ?? movers.scanned} شركة من ${movers.universe ?? movers.scanned}`
              : realToday != null ? "مجموع (السعر × حجم اليوم) للشركات المرصودة"
              : "لم يصل مجموع التداول الفعلي — الرقم أعلاه تقديرٌ من حجم المؤشر"}
          </p>
          {bars.length >= 2 && (
            <div style={{ height: 120 }} dir="ltr">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={bars} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: "var(--ink-muted)" }} tickFormatter={(d: string) => d.slice(5)} minTickGap={18} />
                  {/* مستويات القياس على اليسار: الرقم مجرّداً بالمليار (خانة
                      أفراد/عشرات) بلا كلمة «مليار» — الوحدة مفهومة من العنوان.
                      عرض كافٍ + هامش يسار صفري حتى لا يُقصّ الرقم الصحيح. */}
                  <YAxis tick={{ fontSize: 9, fill: "var(--ink-muted)" }} width={34}
                    tickFormatter={(v: number) => {
                      const b = v / 1e9;
                      return b >= 10 ? b.toFixed(0) : b.toFixed(1);
                    }} />
                  <Tooltip {...TIP} cursor={{ fill: "rgba(148,163,184,.08)" }} formatter={(v: any) => [compactSar(Number(v)) + " ﷼", "سيولة السوق"]} />
                  <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                    {bars.map((_: any, i: number) => <Cell key={i} fill={i === bars.length - 1 ? "var(--chart-1)" : "rgba(59,130,246,.4)"} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          {/* الأعمدة ليست تاريخاً حقيقياً لمجموع التداول — لا وجود لمثل هذا
              التاريخ عندنا. هي شكلُ حجم المؤشر معايَراً كي ينتهي عند رقم
              اليوم الحقيقي، فتُقرأ الحركة لا القيم. يُقال ذلك تحتها بدل أن
              يُترك القارئ يحسبها أرقاماً مقيسة. */}
          {sampled > 0 && (
            <p className="text-[9.5px] text-[var(--ink-muted)] mt-1" dir="rtl">
              {sampled} يوماً سابقاً من عيّنة أكبر الشركات تداولاً، معايَرةً على رقم اليوم
            </p>
          )}
        </>
      )}
    </div>
  );
}
