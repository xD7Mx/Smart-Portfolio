/**
 * Widget registry — every widget is an independent, self-contained unit
 * (own data fetching via react-query, own empty state). Adding/removing/
 * moving/resizing any widget never affects the rest of the system.
 * Doctrine: NO fake data — if a widget has no real data it says so.
 */
import React, { useState, useEffect } from "react";
import { useAppStore } from "../store/appStore";
import { useAuthStore } from "../store/authStore";
import { createPortal } from "react-dom";
import { NumInput } from "../components/common/UI";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import {
  TrendingUp, TrendingDown, Wallet, Target, Activity, Landmark,
  Coins, Building2, Newspaper, CalendarDays, Sparkles, Bell, ArrowUp, ArrowDown, X, Plus, Trash2, Pencil
} from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { portfolioApi, goalsApi, cashApi, marketApi, aiApi, notificationsApi, notesApi } from "../services/api";
import SectorInfographic, { buildSectorData } from "../components/common/SectorInfographic";
import { lookupCompany } from "../data/saudiCompanies";

/* اللوحة الأساسية الأولى (ما قبل 3d96cf1) بترتيبها الأصلي، لكنْ بالرموز
   لا بقيمٍ ثابتة: القيمة الثابتة لا تعرف المظهر ولا يطالها تغييرٌ لاحق.
   وأُخرجت منها أحبار الدلالة التي كانت مدسوسةً في مواضع ٣ و٦: الأخضر
   والأحمر هنا يقولان «القطاع رقم ٣» وهو معنًى لا يملكانه — والقاعدة
   نفسها هي ما جعل الأشرطة تُقرأ صارخةً. */
const COLORS = ["var(--chart-1)","var(--chart-2)","var(--chart-3)","var(--chart-4)","var(--chart-5)","var(--chart-6)","var(--chart-7)"];
const fmt = (n: number) => (n ?? 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
const fmt2 = (n: number) => (n ?? 0).toLocaleString("en-US", { maximumFractionDigits: 2 });
const fmtPct = (n: number) => (n >= 0 ? "+" : "") + (n ?? 0).toFixed(2) + "%";

/* ── Shared data hooks (react-query dedupes across widgets) ── */
function useSummary() {
  return useQuery({ queryKey: ["portfolio-summary"], queryFn: () => portfolioApi.summary().then(r => r.data.data) });
}
function useHoldings() {
  return useQuery({
    queryKey: ["portfolio"],
    queryFn: () => portfolioApi.get().then(r => Array.isArray(r.data?.data) ? r.data.data : []),
  });
}
function useCash() {
  return useQuery({ queryKey: ["cash"], queryFn: () => cashApi.balance().then(r => r.data?.data) });
}

function Empty({ label = "لا توجد بيانات حالياً" }: { label?: string }) {
  return <div className="flex-1 flex items-center justify-center text-[var(--ink-muted)] text-xs py-4">{label}</div>;
}

/* ── Stat widgets ── */
function StatWidget({ label, value, sub, icon: Icon, ic, color, cls = "" }: any) {
  return (
    <div className="h-full flex flex-col justify-center gap-1 px-1">
      <div className={"mc-icon " + ic}><Icon size={14} style={{color}} /></div>
      <div className="mc-lbl">{label}</div>
      <div className={"mc-val " + cls}>{value}</div>
      {sub && <div className="mc-sub">{sub}</div>}
    </div>
  );
}

/* Small shared modal shell for the widget detail popups below */
function DetailModal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  // Portal to <body>: widgets live inside react-grid-layout items, which are
  // CSS-transformed — a transform creates a new containing block for
  // position:fixed, so without a portal this overlay would be trapped
  // inside the small widget tile instead of covering the screen.
  return createPortal(
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal-box fade-in" style={{ maxWidth: 460 }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="modal-title">{title}</h3>
          <button onClick={onClose} title="إغلاق" aria-label="إغلاق" className="text-[var(--ink-muted)] hover:text-[var(--ink)] p-1"><X size={16} /></button>
        </div>
        {children}
      </div>
    </div>,
    document.body
  );
}


/* ── Wealth banner ── */
export function WealthW({ actions }: { actions?: React.ReactNode } = {}) {
  const { data: s } = useSummary();
  const { data: c } = useCash();
  const mv = s?.total_current_value ?? 0, inv = s?.total_cost ?? 0;
  const u = mv - inv, up = u >= 0;
  const cash = c?.available_cash ?? c?.total_cash ?? 0;

  /* نسبة التغيّر للقيمة السوقية — تُقاس من نفس المبلغ المعروض بجانبها:
     (القيمة السوقية − المدفوع) ÷ المدفوع. كانت تأخذ رقم «عائد المحفظة» من
     الخادم، وهو مقياسٌ آخر تماماً (الإنتاج المحقّق لا الارتفاع السعري)، فيظهر
     مبلغُ ربحٍ غير محقّق بجانب نسبةٍ لا تُنتجه أبداً — رقمان لا يتحققان
     أحدهما من الآخر ولا يستطيع القارئ ربطهما، فيبدوان عشوائيين. */
  const mvChangePct = inv ? u / inv * 100 : 0;

  /* **مقياسٌ واحد لا خمسة.** كان الباند يعرض «الربح المحقّق» و«الموزَّع (DPI)»
     جنباً إلى جنب، والثاني أكبر من الأول دائماً لأن بسطه يحوي رأس المال
     العائد — فيُقرأ الأكبر إنجازاً وهو ليس كذلك.
     صافي الربح = الثروة − رأس مال المشروع (صافي الضخّ المسجَّل). مربوطٌ
     بالنقد الفعلي والقيمة السوقية الفعلية، ولا يخدعه نقصٌ في السجل. والضخّ
     لا يحرّكه: كل إيداع يرفع الطرفين بنفس القدر. */
  const netProfit = s?.net_profit ?? null;

  return (
    <div className="wealth h-full" style={{padding: "16px 24px"}}>
      {actions && (
        <div style={{position: "absolute", top: 12, left: 12, display: "flex", gap: 8, zIndex: 2}}>
          {actions}
        </div>
      )}
      <div className="wealth-top">
        <div className="wealth-lbl">إجمالي الثروة</div>
        <div className="wealth-val">{fmt(mv + cash)}</div>
        <div className={"wealth-ch" + (up ? "" : " neg")}>
          {up ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
          {(up ? "+" : "")}{fmt(u)} أرباح غير محققة
          <span style={{margin: "0 4px", opacity: .5}}>·</span>
          <span className="roi-val" style={{color: "inherit"}}>{fmtPct(mvChangePct)}</span>
        </div>
      </div>
      <div className="wealth-stats">
        <div><div className="wealth-stat-lbl">القيمة السوقية</div><div className="wealth-stat-val">{fmt(mv)}</div></div>
        <div><div className="wealth-stat-lbl">إجمالي المدفوع</div><div className="wealth-stat-val">{fmt(inv)}</div></div>
        <div title={`الثروة ${fmt(mv + cash)} − رأس مال المشروع ${fmt(s?.contributed_capital ?? 0)}`}>
          <div className="wealth-stat-lbl">صافي الربح</div>
          {/* رقمٌ بلا نسبة: النسبة نفسها معروضةٌ أسفل الصفحة في عائد
              المحفظة، وتكرارها هنا يزحم الباند بلا معلومةٍ جديدة. */}
          <div className={"wealth-stat-val " + (netProfit != null && netProfit < 0 ? "loss" : "profit")}>
            {netProfit == null ? "—" : (netProfit >= 0 ? "+" : "") + fmt(netProfit)}
          </div>
        </div>
        <div><div className="wealth-stat-lbl">السيولة المتاحة</div><div className="wealth-stat-val">{fmt(cash)}</div></div>
      </div>
    </div>
  );
}

/* ── Portfolio Health — used to be a separate financial/technical-analysis
   score (from /portfolio/health) shown right above "التقييم العام" from
   the SAME evaluate() engine used in the report — two different numbers
   confusingly labelled almost the same thing. Now it's just a visual
   (diverging bar) presentation of that one same overall_score, computed
   once in AIPage's evaluation query and passed in here, so "تقييم المحفظة"
   and "التقييم العام" are always literally the same number. ── */
export function PortfolioHealthW({ score }: { score: number | null | undefined }) {
  if (score == null) {
    return (
      <div className="flex flex-col">
        <Empty label="لا توجد بيانات تحليل كافية بعد" />
      </div>
    );
  }

  const color = score >= 70 ? "var(--pos-ink)" : score >= 45 ? "var(--warn-ink)" : "var(--neg-ink)";

  return <ScoreTrend score={score} color={color} />;
}

/**
 * شريط التقييم — نموذج «الاتجاه»: الدرجة اليوم، وخطُّ درجاتك السابقة.
 *
 * الرقم وحده يقول «أين أنت»، ولا يقول «إلى أين تسير». ومحفظةٌ عند ٦٥ صاعدةً
 * من ٥٢ ليست كمحفظةٍ عند ٦٥ هابطةً من ٧٨ — والشريط القديم يعرضهما سواءً.
 *
 * **مصدر الخطّ:** `evaluation_score` من اللقطات اليومية — وهو **نفس** الرقم
 * المعروض فوقه. ولا يُرسم من `governance_score` وإن كان أوفر تاريخاً: ذاك
 * مقياس الحوكمة والالتزام الشرعي، ورسمُ تاريخه تحت رقم التقييم يُنتج خطّاً
 * لا ينتهي إلى رقمه — بيانٌ كاذب لا يُكتشف لأنه يبدو صحيحاً.
 *
 * ولأن العمود جديد، تبدأ اللقطات القديمة فارغة. فلا يُرسم خطٌّ حتى تجتمع
 * نقطتان، ويُقال ذلك صراحةً: «يُبنى الخطّ مع الأيام» — لا فراغٌ صامت يُقرأ
 * كأنّ التقييم لم يتحرّك.
 */
function ScoreTrend({ score, color }: { score: number; color: string }) {
  const { data: hist = [] } = useQuery({
    queryKey: ["portfolio-history"],
    queryFn: () => portfolioApi.history().then(r => Array.isArray(r.data?.data) ? r.data.data : []),
  });
  const series = (hist as any[])
    .filter(p => p.evaluation_score != null)
    .map(p => ({ d: String(p.date), v: Number(p.evaluation_score) }))
    .slice(-60);

  const W = 300, H = 56, PAD = 5;
  let path = "", endX = 0, endY = 0;
  if (series.length >= 2) {
    const vals = series.map(p => p.v);
    const lo = Math.min(...vals), hi = Math.max(...vals), sp = (hi - lo) || 1;
    const x = (i: number) => PAD + i * (W - PAD * 2) / (series.length - 1);
    const y = (v: number) => PAD + (hi - v) / sp * (H - PAD * 2);
    path = series.map((p, i) => (i ? "L" : "M") + x(i).toFixed(1) + " " + y(p.v).toFixed(1)).join(" ");
    endX = x(series.length - 1); endY = y(series[series.length - 1].v);
  }
  const delta = series.length >= 2 ? series[series.length - 1].v - series[0].v : null;
  const word = score >= 70 ? "جيّدة" : score >= 45 ? "متوسّطة" : "تحتاج مراجعة";

  return (
    <div className="flex flex-col">
      <div className="flex items-baseline justify-between mb-1">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-extrabold tabular-nums" dir="ltr" style={{ color }}>
            {score.toFixed(0)}
          </span>
          <span className="text-xs" style={{ color: "var(--ink-muted)" }}>{word}</span>
        </div>
        {delta != null && (
          /* الفارق رقماً أولاً ثم نصّاً — بلا هذا الفصل ينقلب في العربية
             فيُقرأ «18+» بدل «+18». */
          <span className="text-[11.5px] font-semibold"
            style={{ color: delta >= 0 ? "var(--pos-ink)" : "var(--neg-ink)" }}>
            <span className="tabular-nums" dir="ltr">{delta >= 0 ? "+" : "−"}{Math.abs(delta).toFixed(0)}</span>
            {" "}منذ أول قياس
          </span>
        )}
      </div>

      {series.length >= 2 ? (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 56 }} dir="ltr"
          role="img" aria-label={`اتجاه التقييم: ${score.toFixed(0)} من 100`}>
          <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
          <circle cx={endX} cy={endY} r={7} fill={color} opacity={0.16} />
          <circle cx={endX} cy={endY} r={3.2} fill={color} />
        </svg>
      ) : (
        <div className="text-[11px] py-4" style={{ color: "var(--ink-muted)" }}>
          {series.length === 1
            ? "سُجّل أول قياس — يظهر الخطّ مع القياس التالي"
            : "يُبنى خطّ الاتجاه مع الأيام — تُسجَّل درجة واحدة يومياً"}
        </div>
      )}

      {/* العتبتان مكتوبتان: الخطّ يقول الاتجاه، وهذه تقول أين تقف منه. */}
      <div className="flex items-center justify-between text-[10px] mt-1" style={{ color: "var(--ink-muted)" }}>
        <span>متوسّطة عند ٤٥</span>
        <span>جيّدة عند ٧٠</span>
      </div>
    </div>
  );
}


/* ── Charts ── */
function PerfW() {
  // Real daily snapshots recorded automatically by the backend — never fabricated.
  const { data: hist = [] } = useQuery({
    queryKey: ["portfolio-history"],
    queryFn: () => portfolioApi.history().then(r => Array.isArray(r.data?.data) ? r.data.data : []),
  });
  const points = hist.filter((p: any) => (p.market_value || 0) > 0 || (p.invested_amount || 0) > 0);

  /* ══ الأعمدة الشهرية ══
     شهرٌ شهراً: عمودٌ لِما دفعتَ وعمودٌ لِما تساويه — وآخرُ لقطةٍ في الشهر
     هي حالتُه، لا متوسّطه: المتوسّط يخترع رقماً لم يقع في يومٍ قطّ.

     وفوق كل شهرٍ يُكتب **الفرق** صراحةً. وهذا ليس زينة: نسبة الربح أمام
     أصل المبلغ صغيرة، فالعمودان يبدوان متساويين للعين ولو اختلفا بعشرات
     الآلاف. فلو تُرك المالك يقارن ارتفاعين، لَما رأى ما جاء يراه. */
  const months = React.useMemo(() => {
    const by = new Map<string, any>();
    for (const p of points) by.set(String(p.date).slice(0, 7), p);  // آخر يومٍ يغلب
    return [...by.entries()].slice(-8).map(([k, p]) => ({
      key: k,
      label: new Date(k + "-01").toLocaleDateString("ar-SA-u-ca-gregory-nu-latn", { month: "short" }),
      inv: p.invested_amount || 0,
      mv: p.market_value || 0,
      gap: (p.market_value || 0) - (p.invested_amount || 0),
    }));
  }, [points]);
  // «peak» لا «top»: الأخير اسمٌ عامّ في المتصفّح، وتسميتُه هنا تلتبس.
  const peak = Math.max(1, ...months.map(m => Math.max(m.inv, m.mv)));

  return (
    <div className="h-full flex flex-col">
      <p className="card-title mb-1">أداء المحفظة</p>
      {months.length >= 1 ? (
        <div className="flex-1 min-h-0 flex flex-col">
          {/* اتّجاه الزمن من اليسار إلى اليمين — كبقية رسوم التطبيق وكخطّ
              اتجاه التقييم. وحدةُ الاتجاه بين الرسوم أهمّ من مجاراة اتجاه
              القراءة في رسمٍ واحد: اختلافُهما يجعل المالك يعيد ضبط عينه
              بين بطاقةٍ وأخرى. */}
          <div className="flex-1 min-h-0 flex items-end justify-between gap-1.5 px-0.5" dir="ltr">
            {months.map(m => {
              const pos = m.gap >= 0;
              const ink = pos ? "var(--pos-ink)" : "var(--neg-ink)";
              return (
                <div key={m.key} className="flex-1 min-w-0 flex flex-col items-center justify-end h-full">
                  <span className="text-[9.5px] font-bold mb-1 shrink-0" dir="ltr" style={{ color: ink }}>
                    {pos ? "+" : "−"}{fmt(Math.abs(m.gap))}
                  </span>
                  <div className="w-full flex items-end justify-center gap-[3px] flex-1 min-h-0">
                    {/* المدفوع أوّلاً (يمين) ثمّ السوقية — ترتيبُ القراءة نفسه:
                        ما دفعتَه ثمّ ما صار إليه. */}
                    {/* ══ عمود المدفوع: تدرّج الهويّة ══ (بأمر المالك)
                        مرّ بدرجتين قبله: `--ink-muted` بشفافية ٣٨٪ فكان
                        يكاد يختفي، ثمّ حبرُ الصفحة بشفافية ٤٥٪ فصار
                        رمادياً محايداً لا ينتمي إلى شيء.
                        ثمّ التدرّج البنفسجيّ، فردَّه المالك إلى البيج.
                        وهو الآن من درجة بيج التطبيق أعمقَ منها قليلاً كي
                        يُرى (انظر --paid-a في globals.css)، ويبقى النصف
                        الآخر (السوقية) دلالياً بلون الربح أو الخسارة. */}
                    <div className="rounded-t-[3px]" title={`المدفوع ${fmt(m.inv)}`}
                      style={{ width: "42%", height: `${(m.inv / peak) * 100}%`,
                               background: "linear-gradient(180deg, var(--paid-a), var(--paid-b))" }} />
                    <div className="rounded-t-[3px]" title={`القيمة السوقية ${fmt(m.mv)}`}
                      style={{ width: "42%", height: `${(m.mv / peak) * 100}%`, background: ink }} />
                  </div>
                  <span className="text-[9.5px] mt-1 shrink-0" style={{ color: "var(--ink-muted)" }}>{m.label}</span>
                </div>
              );
            })}
          </div>
          <div className="flex items-center gap-3 mt-2 shrink-0" style={{ fontSize: 10, color: "var(--ink-muted)" }}>
            <span className="flex items-center gap-1.5">
              <i style={{ width: 11, height: 3, borderRadius: 2, background: "var(--pos-ink)" }} />القيمة السوقية</span>
            <span className="flex items-center gap-1.5">
              <i style={{ width: 11, height: 3, borderRadius: 2,
                          background: "linear-gradient(90deg, var(--paid-b), var(--paid-a))" }} />المدفوع</span>
          </div>
        </div>
      ) : points.length >= 2 ? (
        <div className="flex-1 min-h-0" dir="ltr">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="perfMv" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.12)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--ink-muted)" }} tickFormatter={(d: string) => d.slice(5)} />
              <YAxis tick={{ fontSize: 10, fill: "var(--ink-muted)" }} width={44} tickFormatter={(v: number) => fmt(v)} />
              <Tooltip
                contentStyle={{ background: "var(--pop)", border: "1px solid var(--line)", color: "var(--tip-text)", borderRadius: 10, fontSize: 12 }}
                labelStyle={{ color: "var(--tip-text)", fontWeight: 300, marginBottom: 4 }}
                itemStyle={{ color: "var(--tip-text)" }}
                formatter={(v: any, name: any) => [fmt2(v) + "", name === "market_value" ? "القيمة السوقية" : "المدفوع"]}
                cursor={{ stroke: "rgba(255,255,255,.18)", strokeWidth: 1 }}
              />
              <Area
                type="monotone" dataKey="market_value" stroke="var(--chart-1)" strokeWidth={2} fill="url(#perfMv)" name="market_value"
                dot={(props: any) => props.index === points.length - 1
                  ? <circle key="perf-end-dot" cx={props.cx} cy={props.cy} r={4} fill="var(--chart-1)" stroke="var(--hairline)" strokeWidth={2} />
                  : (null as any)}
                activeDot={{ r: 4, fill: "var(--chart-1)", stroke: "var(--hairline)", strokeWidth: 2 }}
              />
              <Area type="monotone" dataKey="invested_amount" stroke="var(--chart-4)" strokeWidth={1.5} strokeDasharray="4 3" fill="none" name="invested_amount" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : points.length === 1 ? (
        <Empty label={`سُجلت أول لقطة (${points[0].date}) — يكتمل الرسم تلقائياً مع الأيام القادمة`} />
      ) : (
        <Empty label="لا توجد بيانات تاريخية بعد — تُبنى تلقائياً مع مرور الأيام" />
      )}
    </div>
  );
}

function SectorsW() {
  const { data: h = [] } = useHoldings();
  const data = buildSectorData(h.map((x: any) => ({ sector: x.company?.sector, value: x.current_value || 0 })));

  return (
    <div className="h-full flex flex-col">
      <p className="card-title mb-4 shrink-0">توزيع القطاعات</p>
      {data.length ? (
        <div className="flex-1 min-h-0">
          <SectorInfographic data={data} size={140} />
        </div>
      ) : <Empty />}
    </div>
  );
}

/* ── Goals / Summary ── */
function GoalEditModal({ goal, onClose }: { goal: any; onClose: () => void }) {
  const qc = useQueryClient();
  const [current, setCurrent] = useState(String(goal.current_value ?? 0));
  const updateMut = useMutation({
    mutationFn: () => goalsApi.update(goal.id, Number(current) || 0).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["goals-progress"] }); onClose(); },
  });
  const deleteMut = useMutation({
    mutationFn: () => goalsApi.remove(goal.id).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["goals-progress"] }); onClose(); },
  });
  return (
    <DetailModal title={goal.name} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label className="label">القيمة الحالية المحققة نحو الهدف</label>
          <NumInput value={current} onChange={setCurrent} autoFocus />
        </div>
        <p className="text-xs text-[var(--ink-muted)]">الهدف: {goal.target_type === "PERCENT" ? `${fmt(goal.target_value)}%` : fmt(goal.target_value)}{goal.deadline ? ` — بحلول ${new Date(goal.deadline).toLocaleDateString("en-GB")}` : ""}</p>
        <div className="flex gap-2 pt-2">
          <button className="btn-primary flex-1" disabled={updateMut.isPending} onClick={() => updateMut.mutate()}>حفظ التقدّم</button>
          <button className="btn-ghost text-[var(--neg-ink)]" disabled={deleteMut.isPending} onClick={() => { if (confirm("حذف هذا الهدف؟")) deleteMut.mutate(); }}>
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </DetailModal>
  );
}

function GoalAddModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [targetType, setTargetType] = useState<"AMOUNT" | "PERCENT">("AMOUNT");
  const [target, setTarget] = useState("");
  const [deadline, setDeadline] = useState("");
  const addMut = useMutation({
    mutationFn: () => goalsApi.add({
      goal_name: name, target_value: Number(target) || 0, target_type: targetType,
      deadline: deadline ? new Date(deadline).toISOString() : undefined,
    }).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["goals-progress"] }); onClose(); },
  });
  return (
    <DetailModal title="هدف استثماري جديد" onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label className="label">اسم الهدف</label>
          <input className="input" placeholder="مثال: تجميع مليون ريال" value={name} onChange={e => setName(e.target.value)} autoFocus />
        </div>
        <div>
          <label className="label">نوع الهدف</label>
          <div className="flex gap-2">
            <button type="button" onClick={() => setTargetType("AMOUNT")}
              className={"flex-1 py-2 rounded-xl text-xs font-bold border transition-all " +
                (targetType === "AMOUNT" ? " text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)]")}>
              مبلغ (ريال)
            </button>
            <button type="button" onClick={() => setTargetType("PERCENT")}
              className={"flex-1 py-2 rounded-xl text-xs font-bold border transition-all " +
                (targetType === "PERCENT" ? " text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)]")}>
              نسبة عائد (%)
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">{targetType === "AMOUNT" ? "المبلغ المستهدف" : "نسبة العائد المستهدفة %"}</label>
            <NumInput value={target} onChange={setTarget} />
          </div>
          <div>
            <label className="label">تاريخ مستهدف (اختياري)</label>
            <input className="input" type="date" lang="en" value={deadline} onChange={e => setDeadline(e.target.value)} />
          </div>
        </div>
        <button className="btn-primary w-full" disabled={!name || !target || addMut.isPending} onClick={() => addMut.mutate()}>
          {addMut.isPending ? "جارٍ الإضافة…" : "إضافة الهدف"}
        </button>
      </div>
    </DetailModal>
  );
}

/** A gradient that mirrors how far along a goal is — hue sweeps from a
 * rose/amber start toward emerald as progress climbs to 100%, so the bar
 * itself visually communicates "far to go" vs "almost there" instead of
 * a color picked at random per goal. */
function progressGradient(_pct: number): string {
  /* ══ تدرّج الهويّة، لا لونٌ لكل شريط ══
     كان أخضرَ فأزرقَ فأخضر — ثلاثةَ ألوانٍ لا علاقة لها بهويّة التطبيق،
     فبدا الشريط قطعةً من تطبيقٍ آخر. وأمرُ المالك أن يكون التدرّج
     البنفسجيّ **أساسَ البنية** لا زينةً في موضع: ما يمتلئ ويتقدّم في
     التطبيق كلّه يمتلئ بلونٍ واحد. */
  return "linear-gradient(90deg, var(--brand-a), var(--brand-b))";
}

function BuiltinGoalBar({ label, pct, current, target, unit = " ﷼", right }: { label: string; pct: number; current: number; target: number; unit?: string; right?: React.ReactNode }) {
  const grad = progressGradient(pct);
  /* **الخسارة**: نسبةٌ سالبة كانت تُنتج `width: -20%` — قيمةٌ غير صالحة يسقطها
     المتصفّح فيعود العرض إلى الافتراضي، أي **شريطاً ممتلئاً** في يوم خسارة.
     فيُقصّ العرض عند صفر (لا شريط سالب)، ويُكتب الرقم بالأحمر صريحاً. */
  const neg = pct < 0;
  const width = Math.max(0, Math.min(100, pct));
  /* ══ هدفٌ غير موجب: لا نسبة له أصلاً ══
     قِيس في المتصفّح: هدفُ «الوصول للمليون» جاء بـ‎−1 فطُبعت النسبة
     ‎−32,846,290٪. القسمة على عددٍ سالبٍ أو صفر لا تُنتج نسبةً بأي معنى،
     وطباعةُ ناتجها تُخيف المالك برقمٍ لا وجود له. فيُقال «—» ويُترك
     الشريط فارغاً: غيابُ المرجع يُعلَن ولا يُموَّه برقم. */
  const noTarget = !(target > 0) || !Number.isFinite(pct);
  return (
    <div className="mb-3.5">
      {/* النسبة تُعرض دائماً ولو كانت التسمية أعلى الشريط: الشريط بلا رقمٍ
          يُقرأ تقديراً بالعين، والنسبة هي المعلومة نفسها. */}
      <div className="flex items-center justify-between text-xs mb-1.5 gap-2">
        <span className="text-[var(--ink)] font-semibold flex items-center gap-1.5 min-w-0">{label}{right}</span>
        {noTarget ? (
          <span className="font-bold shrink-0 text-[var(--ink-muted)]" title="لا هدف صالح — حدّده من القلم">—</span>
        ) : neg ? (
          <span className="font-bold shrink-0" style={{ color: "var(--neg-ink)" }} dir="ltr">{pct.toFixed(0)}%</span>
        ) : (
          <span className="font-bold shrink-0" style={{ background: grad, WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent" }}>{pct.toFixed(0)}%</span>
        )}
      </div>
      <div className="h-3 bg-[var(--surface)] rounded-full overflow-hidden shadow-inner">
        <div className="h-full rounded-full transition-all" style={{ width: (noTarget ? 0 : width) + "%", background: grad }} />
      </div>
      <div className="flex justify-between text-[11px] text-[var(--ink-muted)] mt-1.5">
        {/* بلا هدفٍ لا خسارة: الأحمر يقول «تراجعت» والمبلغ لم يتراجع، بل
            المرجع غائب. فيبقى بحبر المتن. */}
        <span style={(neg && !noTarget) ? { color: "var(--neg-ink)" } : undefined} dir="ltr">{fmt(current)}{unit}</span>
        <span>{noTarget ? "لم يُحدَّد هدف" : `الهدف: ${fmt(target)}${unit}`}</span>
      </div>
    </div>
  );
}

/* تحرير هدفٍ مدمج: رقمٌ واحد لا نموذج — الهدف هو كل ما يملكه المالك هنا. */
function BuiltinGoalEditModal({ goalKey, label, value, onSave, onClose }:
  { goalKey: string; label: string; value: number; onSave: (v: number) => void; onClose: () => void }) {
  const [v, setV] = useState<string>(String(value ?? ""));
  const isPct = goalKey === "growth";
  return (
    <DetailModal title={`تعديل هدف: ${label}`} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label className="text-[11px] text-[var(--ink-muted)] block mb-1">
            {isPct ? "الهدف (٪ من إجمالي المدفوع)" : "الهدف (﷼)"}
          </label>
          <NumInput value={v} onChange={setV} />
        </div>
        <div className="flex gap-2">
          <button className="btn-primary flex-1 text-xs" onClick={() => onSave(Number(v) || 0)}>حفظ</button>
          <button className="btn-ghost flex-1 text-xs" onClick={onClose}>إلغاء</button>
        </div>
      </div>
    </DetailModal>
  );
}

function GoalsW() {
  const { isOwner } = useAuthStore();
  const [showHistory, setShowHistory] = useState(false);
  const { data: goals = [] } = useQuery({
    queryKey: ["goals-progress"],
    queryFn: () => goalsApi.progress().then(r => Array.isArray(r.data?.data) ? r.data.data : []),
  });
  const { data: builtin } = useQuery({
    queryKey: ["goals-builtin"],
    queryFn: () => goalsApi.builtin().then(r => r.data?.data),
  });
  const { data: sum } = useSummary();
  const growth: number | null = sum?.capital_growth_pct ?? null;
  const netProfit: number | null = sum?.net_profit ?? null;
  const costBasis: number = sum?.total_cost ?? 0;
  const { data: history = [] } = useQuery({
    queryKey: ["goals-income-history"],
    queryFn: () => goalsApi.incomeHistory().then(r => Array.isArray(r.data?.data) ? r.data.data : []),
    enabled: showHistory,
  });
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<any>(null);

  /* ── الأهداف المدمجة: إعداداتها على الخادم (هدف كلٍّ منها وترتيبها) ── */
  const qc = useQueryClient();
  const { data: cfg } = useQuery({
    queryKey: ["goals-builtin-config"],
    queryFn: () => goalsApi.builtinConfig().then(r => r.data?.data),
  });
  const saveCfg = useMutation({
    mutationFn: (d: any) => goalsApi.saveBuiltinConfig(d).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["goals-builtin-config"] });
      qc.invalidateQueries({ queryKey: ["goals-builtin"] });
    },
  });
  const [editKey, setEditKey] = useState<string | null>(null);
  const barsRef = React.useRef<HTMLDivElement>(null);

  const growthTargetPct: number = cfg?.growth_target_pct ?? 100;
  const baseOrder: string[] = (cfg?.order?.length ? cfg.order : ["million", "income", "growth"]);

  const bars: Record<string, { label: string; pct: number; current: number; target: number; unit?: string }> = {
    million: {
      label: "الوصول للمليون",
      pct: builtin?.million?.pct || 0,
      current: builtin?.million?.current || 0,
      target: builtin?.million?.target || 1000000,
    },
    income: {
      /* ══ اسمٌ يصف ما يقيسه ══
         كان اسمه «عائد المحفظة» — وفي التطبيق مقياسٌ بهذا الاسم بالضبط
         يعرض نسبةً (صافي الربح ÷ تكلفة المراكز = ‎+10.27٪). فيقرأ المالك
         في الشاشة الواحدة «عائد المحفظة ٣٧٪» و«عائد المحفظة ‎+10.27٪»
         ولا يستطيع ربطهما — كشفته لجنة كشف الأعطال بمسحٍ يقارن كل تسمية
         بقيمها عبر الشاشات.
         والرقم هنا — كما يقول تعليقه الأصلي — **صافي الربح بالريال**
         منسوباً إلى هدفٍ بالريال، لا عائداً بالنسبة. فالاسم يتبع المقياس. */
      label: "هدف صافي الربح",
      pct: builtin?.income?.pct || 0,
      current: builtin?.income?.current || 0,
      target: builtin?.income?.target || 0,
    },
    // استرداد رأس المال: نسبته من الهدف المحرَّر (١٠٠٪ = مضاعفة رأس المال).
    growth: {
      label: "استرداد رأس المال",
      // النسبة تُمرَّر كما هي ولو كانت سالبة: الشريط يقصّها عند صفر ويكتبها
      // بالأحمر، فلا تُخفى خسارةٌ خلف شريطٍ فارغ بلا تفسير.
      pct: growth != null && growthTargetPct ? growth / growthTargetPct * 100 : 0,
      current: netProfit ?? 0,
      target: costBasis * growthTargetPct / 100,
    },
  };

  /* **الترتيب بالامتلاء**: الأقرب إلى هدفه أوّلاً، ثم ما يليه — فتقرأ العين
     تقدّمك متدرّجاً بلا أن تقفز بين شريطٍ ممتلئ وآخر فارغ. والترتيب المحفوظ
     يبقى فاصلاً عند التساوي فقط. */
  const order: string[] = [...baseOrder].sort((a, b) =>
    (bars[b]?.pct ?? 0) - (bars[a]?.pct ?? 0) || baseOrder.indexOf(a) - baseOrder.indexOf(b));

  // Auto-size the panel to how many goals actually exist — one goal shouldn't
  // sit in a box sized for six. ~64px per goal row + ~48px for the header,
  // converted to grid row-units (rowHeight 120px + 10-12px gaps ≈ 132px/unit).
  const { layouts, activeLayout, saveGrid } = useAppStore();
  useEffect(() => {
    const grid = layouts[activeLayout]?.grid;
    const item = grid?.find(g => g.i === "goals");
    if (!item) return;
    const minH = item.minH ?? 2;
    const idealPx = 48 + 140 + Math.max(goals.length, 1) * 64 + 24;
    const idealH = Math.max(minH, Math.min(10, Math.ceil(idealPx / 132)));
    if (item.h !== idealH) {
      saveGrid(grid.map(g => g.i === "goals" ? { ...g, h: idealH } : g));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goals.length, activeLayout]);

  return (
    <div className="h-full flex flex-col overflow-auto">
      <div className="flex items-center justify-between mb-2">
        <p className="card-title flex items-center gap-1.5"><Target size={13} className="text-[var(--pos-ink)]" /> الأهداف الاستثمارية</p>
        {isOwner && (
          <button title="إضافة هدف" onClick={() => setAdding(true)}
            className="p-1.5 rounded-lg transition-colors"
            style={{ color: "var(--brand)" }}
            onMouseEnter={e => (e.currentTarget.style.background = "color-mix(in srgb, var(--brand) 12%, transparent)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
            <Plus size={16} />
          </button>
        )}
      </div>

      {/* الأهداف الثلاثة المدمجة: بياناتها تُحرَّر من القلم، وترتيبها يُغيَّر
          من المقبض بالسحب — ويُحفظان على الخادم فيبقيان بعد تحديث الحزمة. */}
      {builtin && (
        <div ref={barsRef}>
          {order.map((key, idx) => {
            const bar = bars[key];
            if (!bar) return null;
            return (
              <div key={key} data-goal-idx={idx}>
                <BuiltinGoalBar
                  label={bar.label}
                  pct={bar.pct}
                  current={bar.current}
                  target={bar.target}
                  unit={bar.unit}
                  right={isOwner ? (
                    <>
                      <button onClick={() => setEditKey(key)} title="تعديل الهدف"
                        className="text-[var(--ink-muted)] hover:text-[var(--pos-ink)] transition-colors shrink-0">
                        <Pencil size={11} />
                      </button>
                    </>
                  ) : undefined}
                />
                {key === "income" && showHistory && (
                  <div className="mb-3.5 -mt-2 panel rounded-lg p-2 space-y-1.5">
                    {history.length ? history.slice().reverse().map((h: any) => (
                      <div key={h.year} className="flex justify-between items-baseline text-[11px]">
                        <span className="text-[var(--ink-muted)]">{h.year}</span>
                        <span className="text-[var(--ink)] font-semibold tabular-nums" dir="ltr">
                          {fmt(h.total)}{h.target ? ` (${h.pct.toFixed(0)}%)` : ""}
                        </span>
                      </div>
                    )) : <p className="text-[11px] text-[var(--ink-muted)]">لا توجد بيانات سنوات سابقة</p>}
                  </div>
                )}
              </div>
            );
          })}
          <div className="border-t border-[var(--hairline)] mb-3.5" />
        </div>
      )}

      {/* أهدافك المضافة بنفس القاعدة: الأقرب إلى هدفه أوّلاً. */}
      {goals.length ? [...goals].sort((a: any, b: any) =>
        ((b.current_value || 0) / (b.target_value || 1)) - ((a.current_value || 0) / (a.target_value || 1))
      ).map((g: any) => {
        const pct = Math.min(100, ((g.current_value || 0) / (g.target_value || 1)) * 100);
        const unit = g.target_type === "PERCENT" ? "%" : "";
        const grad = progressGradient(pct);
        const Wrap: any = isOwner ? "button" : "div";
        return (
          <Wrap key={g.id} className="mb-3.5 text-start w-full hover:opacity-90 transition-opacity" onClick={isOwner ? () => setEditing(g) : undefined}>
            <div className="flex justify-between items-baseline text-xs mb-1.5">
              <span className="font-bold" style={{ background: grad, WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent" }}>{pct.toFixed(0)}%</span>
              <span className="text-[var(--ink-muted)]">{fmt(g.current_value)}{unit} / {fmt(g.target_value)}{unit}</span>
            </div>
            <div className="h-3 bg-[var(--surface)] rounded-full overflow-hidden shadow-inner">
              <div className="h-full rounded-full transition-all" style={{width: pct + "%", background: grad}} />
            </div>
            <div className="flex items-center gap-1 mt-1.5">
              <span className="text-[var(--ink)] font-semibold text-xs">{g.name}</span>
              {isOwner && <Pencil size={10} className="text-[var(--ink-muted)]" />}
            </div>
          </Wrap>
        );
      }) : (
        /* زرّ الإضافة السفلي حُذف بطلب المالك — زرّ الزائد أعلى اليسار يكفي،
           وزرّان لفعلٍ واحد في بطاقةٍ واحدة تكرار. */
        <div className="flex-1 flex flex-col items-center justify-center text-center gap-2 py-4">
          <p className="text-[12px]" style={{ color: "var(--ink-muted)" }}>لا أهداف مضافة</p>
        </div>
      )}
      {editKey && (
        <BuiltinGoalEditModal
          goalKey={editKey}
          label={bars[editKey]?.label ?? ""}
          value={editKey === "growth" ? growthTargetPct
            : editKey === "million" ? (builtin?.million?.target ?? 1000000)
            : (builtin?.income?.target ?? 0)}
          onSave={(v: number) => {
            const field = editKey === "growth" ? "growth_target_pct"
              : editKey === "million" ? "million_target" : "income_target";
            saveCfg.mutate({ [field]: v });
            setEditKey(null);
          }}
          onClose={() => setEditKey(null)}
        />
      )}
      {adding && <GoalAddModal onClose={() => setAdding(false)} />}
      {editing && <GoalEditModal goal={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

/* Rank 1/2/3 of the same sorted movers list, each a standalone card —
   the fixed grid id ("gainer1".."loser3") stays static while whichever
   holding currently ranks there changes underneath it. */
function MoverRankW({ dir, rank }: { dir: 1 | -1; rank: number }) {
  const { data: h = [] } = useHoldings();
  const sorted = [...h].filter((x: any) => x.company).sort((a: any, b: any) => dir * ((b.unrealized_profit_pct || 0) - (a.unrealized_profit_pct || 0)));
  const top = sorted[rank];
  const up = dir === 1;
  return (
    <div className="h-full flex flex-col justify-center px-1">
      <p className="mc-lbl flex items-center gap-1">
        {up ? <ArrowUp size={12} className="text-[var(--pos-ink)]" /> : <ArrowDown size={12} className="text-[var(--neg-ink)]" />}
        {up ? "الأعلى ارتفاعاً" : "الأعلى انخفاضاً"} #{rank + 1}
      </p>
      {top ? (
        <>
          <p className="text-[var(--ink)] font-bold text-sm mt-1">{top.company.name_ar || top.company.name} <span className="text-[var(--ink-muted)] text-xs">{top.company.symbol}</span></p>
          <p className="text-sm font-bold mt-0.5" style={{color: (top.unrealized_profit_pct || 0) >= 0 ? "var(--pos-ink)" : "var(--neg-ink)"}}>{fmtPct(top.unrealized_profit_pct || 0)}</p>
        </>
      ) : <Empty />}
    </div>
  );
}

/* ── نمو العائد ──────────────────────────────────────────────
 * التصميم السابق (أزرار الفترة أسبوع/شهر/٣أشهر/منذ التأسيس + مبدّل %/ر.س)، لكن
 * الحساب من «المحصول» نفسه (توزيعات + حصيلة البيع الرابحة + قيمة أسهم المنحة)
 * بتواريخه الفعلية — تراكمي من الصفر، لا يُستنتج من فارق القيمة السوقية. */
const RG_RANGES: { k: string; label: string; days: number | null }[] = [
  { k: "7",   label: "أسبوع",       days: 7 },
  { k: "30",  label: "شهر",         days: 30 },
  { k: "90",  label: "3 أشهر",      days: 90 },
  { k: "all", label: "منذ التأسيس", days: null },
];

export function ReturnGrowthW() {
  const [range, setRange] = useState<string>("all");
  const [unit, setUnit] = useState<"pct" | "sar">("pct");
  const { data } = useQuery({
    queryKey: ["goals-income-timeline"],
    queryFn: () => goalsApi.incomeTimeline().then(r => r.data?.data),
  });
  const events: { date: string; amount: number }[] = data?.events ?? [];
  const invested = Number(data?.invested || 0);

  // منحنى تراكمي يومي من الصفر عبر أحداث العائد المؤرّخة.
  let run = 0;
  const cumAll = events.map(e => { run += Number(e.amount || 0); return { date: e.date, cum: run }; });

  const days = RG_RANGES.find(r => r.k === range)?.days ?? null;
  const cutoff = days == null ? null : (() => { const d = new Date(); d.setDate(d.getDate() - days); return d.toISOString().slice(0, 10); })();
  // خطّ الأساس: التراكم قبل بداية الفترة (فتُقاس الزيادة خلالها)؛ «منذ التأسيس»=صفر.
  const base = cutoff == null ? 0 : (cumAll.filter(p => p.date < cutoff).slice(-1)[0]?.cum ?? 0);
  const windowPts = cutoff == null ? cumAll : cumAll.filter(p => p.date >= cutoff);
  const points = windowPts.map(p => ({
    date: p.date,
    v: unit === "pct" ? (invested > 0 ? +(((p.cum - base) / invested) * 100).toFixed(2) : 0)
                      : Math.round(p.cum - base),
  }));
  // نقطة بداية صفرية عند رأس الفترة.
  if (points.length) {
    const d0 = new Date(points[0].date); d0.setDate(d0.getDate() - 1);
    points.unshift({ date: d0.toISOString().slice(0, 10), v: 0 });
  }
  const cur = points.length ? points[points.length - 1].v : 0;
  const curSar = windowPts.length ? Math.round(windowPts[windowPts.length - 1].cum - base) : 0;
  const curPct = invested > 0 ? +(((curSar) / invested) * 100).toFixed(2) : 0;
  const up = cur >= 0;
  const col = up ? "var(--pos-ink)" : "var(--neg-ink)";

  const Seg = ({ opts, val, on }: { opts: {k:string;label:string}[]; val: string; on: (k:string)=>void }) => (
    <div className="inline-flex panel border border-[var(--hairline)] rounded-lg p-0.5 gap-0.5">
      {opts.map(o => (
        <button key={o.k} onClick={() => on(o.k)}
          className={`text-[11px] font-bold px-2 py-1 rounded-md transition ${val === o.k ? " text-[var(--brand-ink)]" : "text-[var(--ink-muted)] hover:text-[var(--ink)]"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between gap-2 mb-1">
        <p className="card-title">نمو العائد</p>
        <Seg opts={[{k:"sar",label:"ر.س"},{k:"pct",label:"%"}]} val={unit} on={k => setUnit(k as any)} />
      </div>

      {points.length >= 2 ? (
        <>
          <div className="flex items-end gap-2.5 mb-0.5">
            <span className="text-2xl font-extrabold tracking-tight" style={{ color: col }}>
              {unit === "pct" ? fmtPct(curPct) : `${curSar >= 0 ? "+" : ""}${fmt(curSar)}`}
              {unit === "sar" && <span className="text-xs font-semibold text-[var(--ink-muted)] ms-1">ر.س</span>}
            </span>
            <span className="text-[11px] font-bold px-2 py-0.5 rounded-md mb-1"
              style={{ background: up ? "color-mix(in srgb, var(--pos-ink) 16%, transparent)" : "color-mix(in srgb, var(--neg-ink) 16%, transparent)", color: col }}>
              <span className="chg-arrow">{up ? "▲" : "▼"}</span> {unit === "pct" ? `${fmt(curSar)} ر.س` : fmtPct(curPct)}
            </span>
          </div>
          <div className="flex-1 min-h-0" dir="ltr">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={points} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="rgFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={col} stopOpacity={0.38} />
                    <stop offset="100%" stopColor={col} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.12)" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--ink-muted)" }} tickFormatter={(d: string) => d.slice(5)} minTickGap={28} />
                <YAxis tick={{ fontSize: 10, fill: "var(--ink-muted)" }} width={40}
                  tickFormatter={(v: number) => unit === "pct" ? `${v}%` : fmt(v)} />
                <Tooltip
                  contentStyle={{ background: "var(--pop)", border: "1px solid var(--line)", color: "var(--tip-text)", borderRadius: 10, fontSize: 12 }}
                  labelStyle={{ color: "var(--tip-text)", fontWeight: 300, marginBottom: 4 }}
                  itemStyle={{ color: "var(--tip-text)" }}
                  formatter={(v: any) => [unit === "pct" ? `${fmtPct(Number(v))}` : `${fmt(Number(v))} ر.س`, "عائد متراكم"]}
                  cursor={{ stroke: "rgba(255,255,255,.18)", strokeWidth: 1 }}
                />
                <Area type="monotone" dataKey="v" stroke={col} strokeWidth={2.4} fill="url(#rgFill)" baseValue={0}
                  dot={(props: any) => props.index === points.length - 1
                    ? <circle key="rg-end" cx={props.cx} cy={props.cy} r={4.5} fill={col} stroke="var(--hairline)" strokeWidth={2} />
                    : (null as any)}
                  activeDot={{ r: 4, fill: col, stroke: "var(--hairline)", strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : (
        <div className="flex-1 min-h-0 flex items-center justify-center">
          <Empty label="لا يوجد عائد مُسجّل في هذه الفترة" />
        </div>
      )}
      {/* أزرار الفترة تبقى ظاهرة دائمًا حتى في الفترة الفارغة كي لا تعلق */}
      <div className="mt-1.5">
        <Seg opts={RG_RANGES} val={range} on={setRange} />
      </div>
    </div>
  );
}

/* ── Registry ─────────────────────────────────────────────── */
export interface WidgetDef {
  id: string;
  title: string;
  component: React.ComponentType;
  defaultSize: { w: number; h: number; minW?: number; minH?: number };
}

export const WIDGETS: WidgetDef[] = [
  { id: "wealth",      title: "بانر الثروة",          component: WealthW,      defaultSize: { w: 12, h: 2, minW: 6, minH: 2 } },
  { id: "perf",        title: "أداء المحفظة",         component: PerfW,        defaultSize: { w: 6, h: 3, minW: 4, minH: 3 } },
  { id: "returngrowth", title: "نمو العائد",           component: ReturnGrowthW, defaultSize: { w: 6, h: 3, minW: 4, minH: 3 } },
  { id: "sectors",     title: "توزيع القطاعات",       component: SectorsW,     defaultSize: { w: 6, h: 3, minW: 4, minH: 3 } },
  { id: "goals",       title: "الأهداف الاستثمارية",  component: GoalsW,       defaultSize: { w: 6, h: 3, minW: 3, minH: 2 } },
  { id: "gainer1",     title: "الأعلى ارتفاعاً #1",    component: () => <MoverRankW dir={1} rank={0} />,  defaultSize: { w: 4, h: 1 } },
  { id: "gainer2",     title: "الأعلى ارتفاعاً #2",    component: () => <MoverRankW dir={1} rank={1} />,  defaultSize: { w: 4, h: 1 } },
  { id: "gainer3",     title: "الأعلى ارتفاعاً #3",    component: () => <MoverRankW dir={1} rank={2} />,  defaultSize: { w: 4, h: 1 } },
  { id: "loser1",      title: "الأعلى انخفاضاً #1",    component: () => <MoverRankW dir={-1} rank={0} />, defaultSize: { w: 4, h: 1 } },
  { id: "loser2",      title: "الأعلى انخفاضاً #2",    component: () => <MoverRankW dir={-1} rank={1} />, defaultSize: { w: 4, h: 1 } },
  { id: "loser3",      title: "الأعلى انخفاضاً #3",    component: () => <MoverRankW dir={-1} rank={2} />, defaultSize: { w: 4, h: 1 } },
];

export const WIDGET_MAP: Record<string, WidgetDef> = Object.fromEntries(WIDGETS.map(w => [w.id, w]));
