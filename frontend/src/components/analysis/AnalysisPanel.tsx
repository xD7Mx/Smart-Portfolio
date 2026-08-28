import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle, XCircle, TrendingUp, Activity, Sparkles, ShieldCheck
} from "lucide-react";
import { marketApi } from "../../services/api";
import { lookupCompany } from "../../data/saudiCompanies";
import { FairValueBar, TrendBar } from "../common/ValueBars";

const TONE_COLOR: Record<string, string> = { green: "var(--pos-ink)", yellow: "var(--warn-ink)", red: "var(--neg-ink)", na: "var(--ink-muted)" };
const DECISION_COLOR: Record<string, string> = { "شراء قوي": "var(--pos-ink)", "شراء": "var(--pos-ink)", "انتظار": "var(--warn-ink)", "تجنب": "var(--neg-ink)" };

const fmt = (n: number, d = 2) => (n ?? 0).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const compact = (n: number) => {
  if (n == null) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toLocaleString("en-US", { maximumFractionDigits: 2 }) + " مليار";
  if (a >= 1e6) return (n / 1e6).toLocaleString("en-US", { maximumFractionDigits: 2 }) + " مليون";
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
};

const verdictColor = (v: string) =>
  v === "قوي جداً" ? "var(--pos-ink)" : v === "قوي" ? "var(--pos-ink)" : v === "متوسط" ? "var(--warn-ink)" : "var(--neg-ink)";

// Financial verdicts are now full decision sentences (not the old 4 fixed
// labels), so their color follows the score itself, not a string match.
const scoreColor = (score: number) => score >= 70 ? "var(--pos-ink)" : score >= 50 ? "var(--warn-ink)" : "var(--neg-ink)";
// Short tier word above the bar, matching the technical card's style
// ("ضعيف · هابط") — the full reasoning sentence lives on the Financial
// Statements tab, so it isn't repeated here too.
const scoreTier = (score: number) => score >= 70 ? "قوي" : score >= 50 ? "متوسط" : "ضعيف";
// Universal tag coloring rule: positive green, negative red, exactly zero
// neutral gray — applied to every indicator tag, not just one.
const signTagClass = (v: number, zeroTolerance = 0) =>
  v > zeroTolerance ? "tag-g" : v < -zeroTolerance ? "tag-r" : "tag-n";

/**
 * Full automatic company analysis — fundamentals + financial verdict +
 * technical verdict + strengths/weaknesses + AI score + decision.
 * Fetches on mount (no button); the backend caches 24h.
 */
export default function AnalysisPanel({ symbol, name }: { symbol: string; name?: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["analysis", symbol],
    queryFn: () => marketApi.company(symbol).then(r => r.data.data),
    enabled: !!symbol,
    retry: 0,
  });

  if (isLoading) return (
    <div className="analysis-card space-y-3 animate-pulse">
      <div className="h-6 skeleton w-40" /><div className="h-24 skeleton" />
      <div className="grid grid-cols-3 gap-2">{[...Array(6)].map((_, i) => <div key={i} className="h-14 skeleton" />)}</div>
    </div>
  );
  if (error || !data) return (
    <div className="analysis-card"><div className="py-10 text-center text-[var(--ink-muted)] text-sm">
      لا توجد بيانات تحليل متاحة لهذا الرمز حالياً — تُجلب وتُحلَّل تلقائياً عند توفر المصدر
    </div></div>
  );

  const f = data.fundamentals || {};
  const fin = data.financial || {};
  const tech = data.technical;
  const dec = data.decision || {};
  const up = (data.change_pct ?? 0) >= 0;

  const fv = data.fair_value_detail || {};
  // بطاقةُ النمط وركنُ الحوكمة — يصلان في جذر التحليل أو داخل المالية.
  const spec = data.spec || data.financial?.spec || null;
  const gov = data.governance || data.financial?.governance || null;

  const kpis: [string, string | null][] = [
    ["القيمة السوقية", f.market_cap ? compact(f.market_cap) : null],
    ["الإيرادات", f.revenue ? compact(f.revenue) : null],
    ["صافي الربح", f.net_income ? compact(f.net_income) : null],
    ["ربحية السهم EPS", f.eps != null ? fmt(f.eps) : null],
    ["مكرر الربحية P/E", f.pe_ratio ? fmt(f.pe_ratio) : null],
    ["العائد على الحقوق ROE", f.roe != null ? fmt(f.roe) + "%" : null],
    ["العائد على الأصول ROA", f.roa != null ? fmt(f.roa) + "%" : null],
    ["هامش الربح", f.profit_margin != null ? fmt(f.profit_margin) + "%" : null],
    ["عائد التوزيعات", f.dividend_yield != null ? fmt(f.dividend_yield) + "%" : null],
    ["التدفق النقدي التشغيلي", f.operating_cash_flow ? compact(f.operating_cash_flow) : null],
    ["التدفق النقدي الحر", f.free_cash_flow ? compact(f.free_cash_flow) : null],
    ["الدين لحقوق الملكية", f.debt_to_equity != null ? fmt(f.debt_to_equity) : null],
    ["أعلى 52 أسبوع", f.week52_high != null ? fmt(f.week52_high) : null],
    ["أدنى 52 أسبوع", f.week52_low != null ? fmt(f.week52_low) : null],
    ["تقدير المحللين", f.target_mean_price != null ? fmt(f.target_mean_price) + "" : null],
    /* القيمة الدفترية للسهم (بأمر المالك) — تلي تقدير المحللين لأنها
       المرجعُ المقابل له: ذاك ما يتوقّعه السوق، وهذه ما تملكه الشركة
       فعلاً لكل سهم. وهي مدخلٌ في مضاعف الدفترية المبرَّر أيضاً، فعرضُها
       يجعل ذلك المسار قابلاً للمراجعة. */
    ["القيمة الدفترية للسهم", f.book_value != null ? fmt(f.book_value) : null],
  ].filter(([, v]) => v != null) as [string, string][];

  return (
    /* ══ إعادةُ هيكلة ══ (بأمر المالك)
       كان الكلُّ في صندوقٍ واحد بأرضيةٍ متدرّجة زرقاء-بنفسجية لا نظير لها
       في التطبيق، وداخله صناديقُ مؤطَّرة متداخلة. فبدا القسم غريباً عن
       لغة التطبيق: بطاقاتٌ مسطّحة بحدٍّ شعريّ وعنوانٍ بأيقونة.
       فصار كلُّ محورٍ **بطاقةً قائمة** (`.card`) كسائر الصفحات، والعناوين
       بـ`.card-title`، والوسوم بوسم التطبيق الصلب (`.ev-tag`). */
    <div className="space-y-4">
      {/* ══ الحكم ══ (بأمر المالك: درجةٌ ورقم)
          كانت الصفحة ثماني بطاقاتٍ متساوية الوزن، فيقع استنتاجُ التطبيق
          كلُّه في وزن شبكةِ أرقامٍ خام. والصفحة تُقرأ من أعلاها: فما
          خُلص إليه يتصدّر، وما بُني عليه يليه.
          رقمان لا أكثر: درجةُ الحوكمة والقيمة العادلة، وتحت الثانية سعرُ
          الدخول لأنه محلّ القرار لا القيمةُ نفسها. */}
      <div className="card">
        <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <Sparkles size={15} className="shrink-0 ai-star" />
            <p className="card-title truncate">{lookupCompany(symbol)?.name_ar || data.name || name || symbol}</p>
          </div>
          {data.price != null && (
            <div className="flex items-baseline gap-2">
              <span className="text-lg tabular-nums" style={{ fontWeight: 800, color: up ? "var(--pos-ink)" : "var(--neg-ink)" }}>{fmt(data.price)}</span>
              <span className={up ? "tag-g" : "tag-r"}>{(up ? "+" : "") + (data.change_pct ?? 0).toFixed(2)}%</span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-xl px-3 py-2.5" style={{ background: "color-mix(in srgb, var(--brand) 7%, transparent)" }}>
            <div className="text-[10px] text-[var(--ink-muted)] mb-1">درجة الجودة المالية</div>
            {fin.score != null ? (
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl tabular-nums leading-none" style={{ fontWeight: 800, color: scoreColor(fin.score) }}>{fin.score}</span>
                <span className="text-[11px] text-[var(--ink-muted)]">/100 · {scoreTier(fin.score)}</span>
              </div>
            ) : (
              <div className="text-base text-[var(--ink-muted)]" style={{ fontWeight: 700 }}>بانتظار القوائم</div>
            )}
          </div>

          <div className="rounded-xl px-3 py-2.5" style={{ background: "color-mix(in srgb, var(--brand) 7%, transparent)" }}>
            <div className="text-[10px] text-[var(--ink-muted)] mb-1">القيمة العادلة</div>
            {data.fair_value != null ? (
              <>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-xl tabular-nums leading-none text-[var(--ink)]" style={{ fontWeight: 800 }}>{fmt(data.fair_value)}</span>
                  {data.fair_value_upside_pct != null && (
                    <span className="text-[11px] tabular-nums" dir="ltr"
                      style={{ color: data.fair_value_upside_pct >= 0 ? "var(--pos-ink)" : "var(--neg-ink)" }}>
                      {data.fair_value_upside_pct > 0 ? "+" : ""}{data.fair_value_upside_pct}%
                    </span>
                  )}
                </div>
                {fv.entry_price != null && (
                  <div className="text-[9.5px] text-[var(--ink-muted)] leading-tight mt-1">
                    سعر الدخول <span className="tabular-nums text-[var(--ink)]">{fmt(fv.entry_price)}</span>
                  </div>
                )}
              </>
            ) : (
              <div className="text-base text-[var(--ink-muted)]" style={{ fontWeight: 700 }}>غير متوفّرة</div>
            )}
          </div>
        </div>

        {/* القرار: سطرٌ واحد يجمع حكم المجلس وحكم السعر — وهما سؤالان
            مختلفان لا يُدمجان: أجيّدةٌ الشركة؟ وأعادلٌ سعرها اليوم؟ */}
        <div className="flex items-center justify-between gap-2 mt-2 px-1">
          <span className="text-[11px] text-[var(--ink-muted)]">
            {data.evaluable === false ? "بانتظار وصول القوائم" : "خلاصة المجلس"}
          </span>
          <span className="flex items-center gap-2">
            {fv.entry_verdict && (
              <span className="text-[10px]" style={{ color: fv.entry_gap_pct >= 0 ? "var(--pos-ink)" : "var(--ink-muted)" }}>{fv.entry_verdict}</span>
            )}
            {dec.label && data.evaluable !== false && (
              <span className="text-sm" style={{ fontWeight: 800, color: DECISION_COLOR[dec.label] || dec.color || "var(--ink-muted)" }}>{dec.label}</span>
            )}
          </span>
        </div>
      </div>

      {/* ══ ما حكم في هذه الشركة ══ (بأمر المالك)
          دورُ المستثمر: يفتح الشركة، يرى درجةً، يقرّر. فالشاشةُ تقول
          ثلاثةَ أشياء بهذا الترتيب: خطٌّ أحمر إن وُجد (فهو يُبطِل كلَّ ما
          بعده)، ثم المؤشّراتُ التي رجّحت الحكمَ برتبتها في القطاع، ثم ما
          لا نراه صريحاً. والمستثمرُ يقرّر على شيئين أو ثلاثة لا على ستّة
          أرقامٍ متساوية الحجم. */}
      {Array.isArray(data.red_lines) && data.red_lines.length > 0 && (
        <div className="card" style={{ borderInlineStart: "3px solid var(--neg-ink)" }}>
          <p className="card-title mb-2" style={{ color: "var(--neg-ink)" }}>خطوطٌ حمراء</p>
          <div className="space-y-1.5">
            {data.red_lines.map((r: any, i: number) => (
              <p key={i} className="text-[12.5px] text-[var(--ink)]">{r.message}</p>
            ))}
          </div>
          <p className="text-[11px] text-[var(--ink-muted)] mt-2">
            وقائعُ مطلقة لا تُوزن مع غيرها — الورقةُ مستبعَدة ولا تُرتَّب.
          </p>
        </div>
      )}

      {Array.isArray(spec?.metrics) && spec.metrics.length > 0 && (
        <div className="card">
          <div className="flex items-baseline justify-between flex-wrap gap-1.5 mb-3">
            <p className="card-title">ما حكم في هذه الشركة</p>
            <span className="text-[10.5px] text-[var(--ink-muted)]">
              {spec.score == null
                ? `قِيس ${spec.metrics.length} أركان — دون الحدّ`
                : `${spec.basis || ""} · قِيس ${spec.metrics.length} أركان`}
            </span>
          </div>
          <div className="space-y-2">
            {[...spec.metrics]
              /* ما رجّح الحكمَ لا كلُّ ما قيس: الأبعدُ عن الوسط أوّلاً،
                 مرجَّحاً بوزنه في البطاقة. */
              .sort((a: any, b: any) =>
                Math.abs(b.score - 50) * b.weight - Math.abs(a.score - 50) * a.weight)
              .slice(0, 3)
              .map((m: any) => (
                <div key={m.key} className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="inline-block w-2 h-2 rounded-full shrink-0"
                      style={{ background: TONE_COLOR[m.tone] || "var(--ink-muted)" }} />
                    <span className="text-[12.5px] text-[var(--ink)] truncate">{m.label}</span>
                  </div>
                  <span className="flex items-baseline gap-2 shrink-0">
                    <span className="text-[13px] tabular-nums text-[var(--ink)]"
                      style={{ fontWeight: 700 }} dir="ltr">
                      {Number(m.value).toLocaleString("en-US", { maximumFractionDigits: 2 })}
                    </span>
                    {/* الرتبةُ هي المعنى: «أعلى من ٧٨٪ من قطاعه» يُقرأ،
                        و«٧٨ من ١٠٠» لا يُقرأ. */}
                    <span className="text-[11px] text-[var(--ink-muted)]">
                      {m.basis === "rank"
                        ? `أعلى من ${Math.round(m.score)}٪ من قطاعه`
                        : "بعتبةٍ معلَنة"}
                    </span>
                  </span>
                </div>
              ))}
          </div>
          {(spec.abstain_reason || (spec.missing || []).length > 0) && (
            <p className="text-[11px] text-[var(--ink-muted)] mt-3 pt-2"
              style={{ borderTop: "1px solid var(--field-line)" }}>
              {spec.abstain_reason || `لم يصل: ${(spec.missing || []).join(" · ")}`}
            </p>
          )}
        </div>
      )}

      {gov && Array.isArray(gov.reads) && gov.reads.length > 0 && (
        <div className="card">
          <p className="card-title mb-3">الحوكمة — ما يمسّ حصّتك</p>
          <div className="space-y-2">
            {gov.reads.map((r: any) => (
              <div key={r.key} className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="inline-block w-2 h-2 rounded-full shrink-0 mt-1"
                    style={{ background: TONE_COLOR[r.tone] || "var(--ink-muted)" }} />
                  <div className="min-w-0">
                    <span className="text-[12.5px] text-[var(--ink)]">{r.label}</span>
                    <p className="text-[11px] text-[var(--ink-muted)] leading-snug">{r.verdict}</p>
                  </div>
                </div>
                <span className="text-[13px] tabular-nums text-[var(--ink)] shrink-0"
                  style={{ fontWeight: 700 }} dir="ltr">
                  {Number(r.value).toLocaleString("en-US", { maximumFractionDigits: 1 })}{r.unit}
                </span>
              </div>
            ))}
          </div>
          {Array.isArray(gov.blind) && gov.blind.length > 0 && (
            <p className="text-[11px] text-[var(--ink-muted)] mt-3 pt-2"
              style={{ borderTop: "1px solid var(--field-line)" }}>
              لا نراه: {gov.blind.join(" · ")}
            </p>
          )}
        </div>
      )}

      {/* الحكم الموحّد — نفس ميزان خبراء الحوكمة بالضبط */}
      <div className="card">
        <div className="flex items-baseline justify-between flex-wrap gap-1.5 mb-3">
          <p className="card-title flex items-center gap-1.5"><ShieldCheck size={14} className="text-[var(--brand-ink)]" /> ميزان خبراء الحوكمة</p>
          {/* الإطار المطبَّق على هذا القطاع — يُعرض مع الدرجة لا بعدها:
              البنك لا يُقاس بما يُقاس به مصنع، ودرجةٌ لا يُعرف إطارُها
              ولا نطاقُها لا يُبنى عليها قرار. */}
        </div>
        {/* أركانُ الإطار نفسه — لا مؤشّراتٍ عامّة تُعرض لكل قطاع.
            كلُّ ركنٍ برقمه ونطاقه المعترف به، فيُقرأ الرقم لا يُشاهَد. */}
        {Array.isArray(data.governance_standard?.metrics) && data.governance_standard.metrics.length > 0 && (
          <div className="grid grid-cols-2 gap-1.5 mb-2">
            {data.governance_standard.metrics.map((m: any) => (
              /* اسمُ الركن لا يُقصّ: كانت تُبتر إلى «(‏IR…»،
                 واسمُ المعيار مبتوراً أسوأ من غيابه. فالاسم يلتفّ
                 في سطرين، والرقم تحته لا بجانبه. */
              <div key={m.key} className="rounded-lg px-2 py-1.5 flex flex-col gap-0.5"
                style={{ background: "color-mix(in srgb, var(--brand) 6%, transparent)" }}>
                <span className="text-[10px] text-[var(--ink-muted)] leading-tight">{m.label}</span>
                <span className="flex items-baseline gap-1">
                  <span className="text-[15px] tabular-nums text-[var(--ink)] leading-none" style={{ fontWeight: 800 }} dir="ltr">
                    {m.value.toLocaleString("en-US", { maximumFractionDigits: 2 })}{m.unit === "%" || m.unit === "×" ? m.unit : ""}
                  </span>
                  {m.unit !== "%" && m.unit !== "×" && m.unit && (
                    <span className="text-[9.5px] text-[var(--ink-muted)]">{m.unit}</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* مجلس الخبراء */}
        {Array.isArray(data.expert_panel) && data.expert_panel.length > 0 && (
          <div className="space-y-1.5 mb-3">
            {data.expert_panel.map((e: any, i: number) => (
              <div key={i} className="flex items-center justify-between gap-2 text-[11px]">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="inline-block w-2 h-2 rounded-full shrink-0" style={{ background: TONE_COLOR[e.tone] || "var(--ink-muted)" }} />
                  <span className="text-[var(--ink)] shrink-0">{e.expert}</span>
                  <span className="text-[var(--ink-muted)] truncate">· {e.metric} {e.reading}</span>
                </div>
                <span className="shrink-0 font-medium" style={{ color: TONE_COLOR[e.tone] || "var(--ink-muted)" }}>{e.verdict}</span>
              </div>
            ))}
          </div>
        )}

      </div>

      {/* ══ القيمة العادلة ══ (خطٌّ أحمر للمالك)
          يتّخذها أداةً لقرارٍ استثماريّ، فلا تُعرض رقماً مجرّداً: معه
          نطاقُه ودرجةُ ثقته و**كلُّ مسارٍ بمدخلاته**، فيراجعه بنفسه.
          ولو غابت البيانات قيل ذلك ولم يُعرض بديلٌ في مكانه. */}
      {data.fair_value_detail && (
        <div className="card">
          <p className="card-title mb-3 flex items-center gap-1.5">
            <TrendingUp size={14} className="text-[var(--brand-ink)]" /> القيمة العادلة
          </p>
          {data.fair_value == null ? (
            <>
              {/* تضاربُ المسارات: المدى يبقى معروضاً والنقطةُ تُمتنع —
                  فيرى المالك ما تعرفه الأداة وما لا تعرفه معاً. */}
              {fv.low != null && fv.high != null && (
                <div className="text-base tabular-nums text-[var(--ink-muted)] mb-1" dir="ltr">
                  {fmt(fv.low)} – {fmt(fv.high)}
                </div>
              )}
              <p className="text-[11px] text-[var(--ink-muted)] leading-relaxed">
                {data.fair_value_detail.unavailable_reason}
              </p>
            </>
          ) : (
            <>
              <div className="flex items-baseline justify-between flex-wrap gap-2 mb-2">
                <span className="flex items-baseline gap-2">
                  <span className="text-2xl font-extrabold tabular-nums text-[var(--ink)]">{fmt(data.fair_value)}</span>
                  <span className="text-[11px] text-[var(--ink-muted)] tabular-nums" dir="ltr">
                    {fmt(data.fair_value_detail.low)} – {fmt(data.fair_value_detail.high)}
                  </span>
                </span>
              </div>
              {/* المقياسُ نفسه المستعمل في الذكاء وفرز السوق — لا نسخةٌ
                  ثانية: القيمة العادلة في المنتصف، والعلامة تميل إلى
                  الطرف الذي يقع فيه السهم. */}
              <div className="mb-3">
                <FairValueBar upside={data.fair_value_upside_pct ?? null} width="100%"
                  ctx={{ price: data.price, entry: fv.entry_price, value: data.fair_value }} />
              </div>
              <div className="space-y-1">
                {(data.fair_value_detail.methods || []).map((m: any, i: number) => {
                  return (
                    <div key={i} className="flex items-start justify-between gap-2 text-[11px]">
                      <span className="min-w-0">
                        <span className="text-[var(--ink)]">{m.name}</span>
                      </span>
                      <span className="tabular-nums font-bold text-[var(--ink)] shrink-0">{fmt(m.value)}</span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}

      {/* التحليل الفني (سياق ثانوي) */}
      <div className="grid grid-cols-1 gap-3">
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <span className="card-title flex items-center gap-1.5"><Activity size={14} className="text-[var(--brand-ink)]" /> التحليل الفني</span>
            {tech?.verdict && <span className="text-xs font-bold" style={{ color: verdictColor(tech.verdict) }}>{tech.verdict} · {tech.trend}</span>}
          </div>
          {tech ? (
            <>
              <TrendBar score={tech.score} />
              <div className="flex flex-nowrap items-center gap-1.5 mt-2 overflow-x-auto">
                {tech.rsi != null && <span className={"shrink-0 " + signTagClass(tech.rsi - 50)}>RSI {tech.rsi}</span>}
                {tech.macd != null && <span className={"shrink-0 " + signTagClass(tech.macd)}>MACD {tech.macd}</span>}
                {/* وسمٌ فنّيّ في صفٍّ من وسومٍ فنّية (‏RSI · MACD): فالمعروض
                    هنا متوسطُ السعر لا القيمة العادلة — تلك اسمٌ محجوزٌ في
                    التطبيق لإجماع أهداف المحللين وحده. */}
                {tech.mean_basis != null && tech.pct_from_avg != null && (
                  <span className={"shrink-0 " + signTagClass(tech.pct_from_avg)}>
                    متوسط السعر {fmt(tech.mean_basis)} ({tech.pct_from_avg >= 0 ? "+" : ""}{tech.pct_from_avg}%)
                  </span>
                )}
              </div>
            </>
          ) : <p className="text-[11px] text-[var(--ink-muted)] mt-1">يتطلب تاريخاً سعرياً كافياً</p>}
        </div>
      </div>

      {/* Valuation — a SEPARATE question from the health score above: is the
          current price cheap or expensive relative to real sector peers? */}
      {data.valuation && (
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <span className="card-title flex items-center gap-1.5">
              <TrendingUp size={14} className="text-[var(--brand-ink)]" /> التقييم مقابل القطاع ({data.valuation.sector})
            </span>
            {data.valuation.verdict && (
              <span className="text-xs font-bold" style={{
                color: data.valuation.verdict === "أرخص من متوسط القطاع" ? "var(--pos-ink)"
                  : data.valuation.verdict === "أغلى من متوسط القطاع" ? "var(--neg-ink)" : "var(--warn-ink)",
              }}>{data.valuation.verdict}</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2">
            {data.valuation.pe != null && (
              <div className="kpi">
                <div className="kpi-lbl">مكرر الربحية P/E</div>
                <div className="kpi-val">
                  {fmt(data.valuation.pe, 1)}
                  {data.valuation.sector_avg_pe != null && (
                    <span className="text-[var(--ink-muted)] text-xs font-normal"> / متوسط القطاع {fmt(data.valuation.sector_avg_pe, 1)}</span>
                  )}
                </div>
              </div>
            )}
            {data.valuation.pb != null && (
              <div className="kpi">
                <div className="kpi-lbl">مضاعف القيمة الدفترية P/B</div>
                <div className="kpi-val">
                  {fmt(data.valuation.pb, 1)}
                  {data.valuation.sector_avg_pb != null && (
                    <span className="text-[var(--ink-muted)] text-xs font-normal"> / متوسط القطاع {fmt(data.valuation.sector_avg_pb, 1)}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Fundamentals grid */}
      {kpis.length > 0 && (
        <div className="card">
          <p className="card-title mb-2">البيانات المالية</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {kpis.map(([lbl, v]) => (
              <div key={lbl} className="kpi"><div className="kpi-lbl">{lbl}</div><div className="kpi-val">{v}</div></div>
            ))}
          </div>
        </div>
      )}

      {/* Strengths / weaknesses */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {data.strengths?.length > 0 && (
          <div className="card">
            <p className="card-title mb-2 flex items-center gap-1.5" style={{ color: "var(--pos-ink)" }}><CheckCircle size={14} /> نقاط القوة</p>
            <ul className="space-y-1">{data.strengths.map((s: string, i: number) => (
              <li key={i} className="text-[var(--ink)] text-xs flex items-start gap-1.5"><span className="text-[var(--pos-ink)] mt-0.5">✓</span>{s}</li>))}</ul>
          </div>
        )}
        {data.weaknesses?.length > 0 && (
          <div className="card">
            <p className="card-title mb-2 flex items-center gap-1.5" style={{ color: "var(--warn-ink)" }}><XCircle size={14} /> نقاط المخاطرة</p>
            <ul className="space-y-1">{data.weaknesses.map((s: string, i: number) => (
              <li key={i} className="text-[var(--ink)] text-xs flex items-start gap-1.5"><span className="text-[var(--warn-ink)] mt-0.5">⚠</span>{s}</li>))}</ul>
          </div>
        )}
      </div>
    </div>
  );
}
