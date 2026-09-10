import React, { useState } from "react";
import StockSheet from "../components/market/StockSheet";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "../services/api";
import { Brain, AlertTriangle, TrendingUp, Sparkles, Zap } from "lucide-react";
import { PortfolioHealthW } from "../widgets/Widgets";
import CompanyLogo from "../components/common/CompanyLogo";
import { FairValueBar, fairValueTier, safeColor } from "../components/common/ValueBars";


// ── Portfolio insight — fair value + safety per holding ──
function PortfolioInsight() {
  const { data } = useQuery({ queryKey: ["ai-portfolio-insight"], queryFn: () => aiApi.portfolioInsight().then(r => r.data.data) });
  const companies = data?.companies ?? [];
  // أخضر موحّد مع حالة القيمة العادلة («جيد» = var(--pos-ink)) لتطابق مظهر الحالتين.
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Brain size={16} className="text-[var(--brand-ink)]" />
        <span className="card-title">رؤية الذكاء لشركات محفظتك</span>
      </div>
      {companies.length === 0 ? (
        <p className="text-[var(--ink-muted)] text-sm py-6 text-center">أضف شركات إلى محفظتك لتظهر رؤية الذكاء عنها تلقائياً.</p>
      ) : (
        <>
          {/* Desktop table */}
          <div className="overflow-x-auto hidden md:block">
            <table className="w-full text-sm min-w-[640px]">
              <thead><tr className="border-b border-[var(--hairline)]">
                {["الشركة", "السعر", "هدف المحللين", "الفرصة", "التقييم", "درجة الجودة المالية"].map(h => <th key={h} className="th text-start">{h}</th>)}
              </tr></thead>
              <tbody>
                {companies.map((c: any) => (
                  <tr key={c.symbol} className="border-b border-[var(--hairline)]/40 hover:bg-[var(--field)]">
                    <td className="td"><span className="text-[var(--ink)] font-semibold text-[13px]">{c.name}</span> <span className="tag-b ms-1" style={{ fontSize: 10 }}>{c.symbol}</span></td>
                    <td className="td tabular-nums">{c.price != null ? c.price.toFixed(2) : "—"}</td>
                    {/* ══ التغطيةُ شاملة ══ (بأمر المالك · D228)
                        حيث لا هدفَ لبيوت الخبرة تُعرض القيمةُ النسبيةُ إلى
                        القطاع — بلونٍ خافتٍ وعلامة «≈» لأنها مشتقّةٌ لا
                        منقولة، وبتلميحٍ يحمل نطاقَها وثقتَها. فلا تُقرأ
                        رأيَ محلّلٍ ولا يبقى الصفُّ فارغاً. */}
                    <td className="td tabular-nums"
                      title={c.fair_value == null && c.rel_value != null
                        ? `قيمة نسبية إلى القطاع ${c.rel_low}–${c.rel_high} · ثقة ${c.rel_conf}`
                        : ""}
                      style={{ color: c.fair_value == null && c.rel_value != null ? "var(--ink-muted)" : undefined }}>
                      {c.fair_value != null ? c.fair_value.toFixed(2)
                        : c.rel_value != null ? c.rel_value.toFixed(2) : "—"}
                    </td>
                    <td className="td">{c.upside_pct != null
                      ? <span style={{ color: c.upside_pct >= 0 ? "var(--pos-ink)" : "var(--neg-ink)" }} className="text-xs font-bold">{c.upside_pct >= 0 ? "+" : ""}{c.upside_pct}%</span>
                      : c.rel_upside_pct != null
                        ? <span className="text-xs font-bold text-[var(--ink-muted)]">≈{c.rel_upside_pct >= 0 ? "+" : ""}{c.rel_upside_pct}%</span>
                        : "—"}</td>
                    <td className="td"><FairValueBar upside={c.upside_pct ?? c.rel_upside_pct ?? null} /></td>
                    <td className="td">
                      {/* ══ الدرجةُ غائبةٌ حقّاً أحياناً ══
                          كانت تُستبدَل بـ50 فلم يقع الغياب. ولمّا صارت
                          تُعاد عدماً، خرج `width: "null%"` — شريطٌ ممتلئٌ
                          بلا معنى فوق كلمة «غير متاحة». فيُفحص الغيابُ
                          صراحةً ولا يُرسَم شريطٌ لِما لم يُقَس.
                          وحُذف معه بريقٌ ضبابيٌّ نابضٌ ونقطةٌ بيضاء: زينةٌ
                          على رقمٍ من مئة، والشريطُ وحده يقوله. */}
                      {c.safety_score == null ? (
                        <span className="text-xs text-[var(--ink-muted)]">غير متاحة</span>
                      ) : (
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 rounded-full bg-[var(--surface)] overflow-hidden" style={{ width: 46 }}>
                            <div className="h-full rounded-full" style={{
                              width: `${Math.max(0, Math.min(100, c.safety_score))}%`,
                              background: safeColor(c.safety_score),
                            }} />
                          </div>
                          <span className="text-xs font-bold tabular-nums" style={{ color: safeColor(c.safety_score) }} dir="ltr">
                            {c.safety_score}
                          </span>
                          <span className="text-[10.5px] text-[var(--ink-muted)]">{c.safety_label}</span>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile: visually-consistent bordered cards (one per company),
              matching the portfolio's mobile card language. */}
          <div className="md:hidden grid grid-cols-1 gap-2.5">
            {companies.map((c: any) => (
              <div key={c.symbol} className="rounded-xl border border-[var(--hairline)] panel p-3 space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[var(--ink)] font-semibold text-[13px] truncate">{c.name}</span>
                  <span className="tag-b shrink-0" style={{ fontSize: 10 }}>{c.symbol}</span>
                </div>
                <div className="grid grid-cols-3 gap-1 text-center">
                  <div><div className="text-[9.5px] text-[var(--ink-muted)] mb-0.5">السعر</div><div className="text-[var(--ink)] font-semibold tabular-nums text-xs">{c.price != null ? c.price.toFixed(2) : "—"}</div></div>
                  <div><div className="text-[9.5px] text-[var(--ink-muted)] mb-0.5">{c.fair_value == null && c.rel_value != null ? "نسبية للقطاع" : "هدف المحللين"}</div><div className="font-semibold tabular-nums text-xs" style={{ color: c.fair_value == null && c.rel_value != null ? "var(--ink-muted)" : "var(--ink)" }} title={c.fair_value == null && c.rel_value != null ? `قيمة نسبية إلى القطاع ${c.rel_low}–${c.rel_high} · ثقة ${c.rel_conf}` : ""}>{c.fair_value != null ? c.fair_value.toFixed(2) : c.rel_value != null ? c.rel_value.toFixed(2) : "—"}</div></div>
                  <div><div className="text-[9.5px] text-[var(--ink-muted)] mb-0.5">الفرصة</div><div className="font-bold text-xs" style={{ color: c.upside_pct == null ? "var(--ink-muted)" : c.upside_pct >= 0 ? "var(--pos-ink)" : "var(--neg-ink)" }}>{c.upside_pct != null ? `${c.upside_pct >= 0 ? "+" : ""}${c.upside_pct}%` : "—"}</div></div>
                </div>
                <div className="grid grid-cols-2 gap-3 pt-1 border-t border-[var(--hairline)]">
                  <div className="space-y-1.5">
                    <div className="text-[10px] text-[var(--ink-muted)]">التقييم مقابل هدف المحللين</div>
                    <div className="flex items-center gap-2">
                      <FairValueBar upside={c.upside_pct} hideLabel width={64} />
                      <span className="text-[11px] font-semibold" style={{ color: fairValueTier(c.upside_pct).color }}>{fairValueTier(c.upside_pct).label}</span>
                    </div>
                  </div>
                  {/* درجة الجودة المالية: سطران منفصلان كعمود القيمة تمامًا — سطر العنوان
                      علويًا (يحاذي عنوان القيمة) وسطر الشريط سفليًا (يحاذي شريط
                      القيمة). العنوان فوق منتصف الشريط عبر مُباعِدٍ خفيّ بعرض
                      الحالة، والحالة يسار الشريط. */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 justify-end">
                      <div className="text-[10px] text-[var(--ink-muted)] text-center whitespace-nowrap" style={{ width: 64 }}>درجة الجودة المالية</div>
                      <span className="text-[11px] font-semibold invisible" aria-hidden="true">{c.safety_label}</span>
                    </div>
                    {/* الغيابُ يُعلَن ولا يُرسَم له شريط — كما في الجدول. */}
                    <div className="flex items-center gap-2 justify-end">
                      {c.safety_score == null ? (
                        <span className="text-[11px] text-[var(--ink-muted)]">غير متاحة</span>
                      ) : (
                        <>
                          <div className="h-1.5 rounded-full bg-[var(--surface)] overflow-hidden" style={{ width: 64 }}>
                            <div className="h-full rounded-full" style={{
                              width: `${Math.max(0, Math.min(100, c.safety_score))}%`,
                              background: safeColor(c.safety_score),
                            }} />
                          </div>
                          <span className="text-[11px] font-bold tabular-nums" style={{ color: safeColor(c.safety_score) }} dir="ltr">
                            {c.safety_score}
                          </span>
                          <span className="text-[10px] text-[var(--ink-muted)]">{c.safety_label}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── AI Portfolio Analysis ─────────────────────────────────────
export default function AIPage() {
  const qc = useQueryClient();
  // بطاقة الشركة تُفتح فوق صفحة الذكاء نفسها — يبقى المستخدم في سياقه.
  const [sheet, setSheet] = useState<string | null>(null);

  const { data: status } = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => aiApi.status().then(r => r.data.data),
    refetchInterval: 30000,
  });
  const { data: report } = useQuery({
    queryKey: ["ai-full-report"],
    queryFn: () => aiApi.fullReport().then(r => r.data.data),
  });
  const { data: evaluation } = useQuery({
    queryKey: ["ai-evaluation"],
    queryFn: () => aiApi.evaluation().then(r => r.data.data),
  });
  const { data: opportunities } = useQuery({
    queryKey: ["ai-opportunities"],
    queryFn: () => aiApi.opportunities().then(r => r.data.data),
  });
  const { data: risk } = useQuery({
    queryKey: ["ai-risk"],
    queryFn: () => aiApi.risk().then(r => r.data.data),
  });

  // فلتر الحوكمة للفرص — «المبخّسة فقط» (أرخص من متوسط القطاع)، والفرز إمّا
  // بأعلى درجة حوكمة (الافتراضي) أو بأعلى عائد توزيع.
  const [oppUnderOnly, setOppUnderOnly] = useState(false);
  const [oppSort, setOppSort] = useState<"governance" | "dividend">("governance");
  const filteredOpps = React.useMemo(() => {
    let list = [...(opportunities || [])];
    if (oppUnderOnly) list = list.filter((o: any) => o.is_undervalued);
    if (oppSort === "dividend") {
      list.sort((a: any, b: any) => (b.dividend_yield ?? -1) - (a.dividend_yield ?? -1));
    } else {
      list.sort((a: any, b: any) => (b.governance_score ?? b.ai_score ?? 0) - (a.governance_score ?? a.ai_score ?? 0));
    }
    return list;
  }, [opportunities, oppUnderOnly, oppSort]);

  const runMutation = useMutation({
    mutationFn: () => aiApi.run().then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-report"] });
      qc.invalidateQueries({ queryKey: ["ai-evaluation"] });
      qc.invalidateQueries({ queryKey: ["ai-status"] });
    },
  });

  return (
    <div className="space-y-5 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-2xl font-medium text-[var(--ink)]">تحليل الذكاء</h1>
            </div>
        </div>
        {status && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full animate-pulse"
              style={{ background: status.is_running ? "var(--gauge-warn)" : "var(--gauge-pos)",
                       boxShadow: "0 0 0 1px var(--gauge-edge)" }} />
            <Brain size={16} className="text-[var(--brand-ink)]" />
          </div>
        )}
      </div>

      {/* Portfolio insight — fair value + safety per holding */}
      <PortfolioInsight />

      {/* Portfolio evaluation — the fair analysis-based bar, plus a textual (no-numbers) decision + analysis */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={16} className="text-[var(--brand-ink)]" />
          <h2 className="card-title">تقييم المحفظة</h2>
          {evaluation?.source === "AI" && <span className="tag-v ms-auto" style={{fontSize:10}}>AI</span>}
        </div>

        <PortfolioHealthW score={evaluation?.overall_score} />

        {evaluation && (
          <div className="mt-5 pt-5" style={{ borderTop: "1px solid var(--hairline)" }}>
            <div className="flex flex-wrap gap-2 mb-3">
              {[
                { label: evaluation.diversification_basis === "plan" ? "الالتزام بالخطة" : "توازن المحفظة", value: evaluation.diversification_score },
                { label: "إدارة المخاطر", value: evaluation.risk_score },
              ].map(m => m.value !== undefined && (
                <span key={m.label} className="px-2.5 py-1 rounded-full text-xs font-bold"
                  style={{
                    background: m.value >= 70 ? "color-mix(in srgb, var(--gauge-pos) 14%, transparent)"
                      : m.value >= 45 ? "color-mix(in srgb, var(--gauge-warn) 14%, transparent)"
                      : "color-mix(in srgb, var(--gauge-neg) 14%, transparent)",
                    /* حبرٌ على صِبغةٍ من لونه ⇒ الدرجة العميقة (انظر
                       --pos-fill في globals.css): الأخضر الصريح على صِبغةٍ
                       خضراء قِيس 1.65:1 — أي شارةٌ لا تكاد تُقرأ. */
                    color:      m.value >= 70 ? "var(--pos-fill)"              : m.value >= 45 ? "var(--warn-ink)"              : "var(--neg-fill)",
                  }}>
                  {m.label}: {m.value >= 70 ? "جيد" : m.value >= 45 ? "متوسط" : "ضعيف"}
                </span>
              ))}
              {evaluation.overall_score !== undefined && (
                <span className="px-2.5 py-1 rounded-full text-xs font-bold"
                  style={{
                    background: evaluation.overall_score >= 70 ? "color-mix(in srgb, var(--gauge-pos) 18%, transparent)" : evaluation.overall_score >= 45 ? "color-mix(in srgb, var(--gauge-warn) 18%, transparent)" : "color-mix(in srgb, var(--gauge-neg) 18%, transparent)",
                    // ألوان دلالية من الرموز لا قيماً ثابتة (المعيار 12):
                    // «var(--warn-ink)» على المظهر الفاتح كان 3.41:1 — تحت الأرضية.
                    color:      evaluation.overall_score >= 70 ? "var(--pos-fill)" : evaluation.overall_score >= 45 ? "var(--warn-ink)" : "var(--neg-fill)",
                  }}>
                  القرار: {evaluation.overall_score >= 70 ? "المحفظة في وضع جيد" : evaluation.overall_score >= 45 ? "المحفظة في وضع متوسط، تحتاج مراجعة" : "المحفظة تحتاج إعادة نظر"}
                </span>
              )}
              {!!evaluation.performance_boost && (
                <span className="px-2.5 py-1 rounded-full text-xs font-bold" title="أثر الأداء الفعلي على التقييم مقابل تقلّب السوق"
                  style={{
                    background: evaluation.performance_boost > 0 ? "color-mix(in srgb, var(--gauge-pos) 18%, transparent)" : "color-mix(in srgb, var(--gauge-warn) 18%, transparent)",
                    color:      evaluation.performance_boost > 0 ? "var(--pos-fill)" : "var(--warn-ink)",
                  }}>
                  الأداء ضد السوق: {evaluation.performance_boost > 0 ? "+" : ""}{evaluation.performance_boost} نقطة
                </span>
              )}
              {evaluation.capital_recovered_pct != null && (
                <span className="px-2.5 py-1 rounded-full text-xs font-bold" title="نسبة استرداد رأس المال المدفوع عبر التوزيعات والمنح وإعادة الاستثمار"
                  style={{ background: "transparent", color: "var(--chart-2)" }}>
                  استرداد رأس المال: {evaluation.capital_recovered_pct}%{!!evaluation.recovery_boost && ` (+${evaluation.recovery_boost})`}
                </span>
              )}
            </div>
            {evaluation.diversification_basis === "plan" && evaluation.unplanned_pct > 0 && (
              <p className="text-xs text-[var(--ink-muted)] mt-2">{evaluation.unplanned_pct}% من المحفظة بلا نسبة مستهدفة</p>
            )}

            {/* ══ سطرُ الذكاء خاتمةُ البطاقة ══ (بأمر المالك · D189)
                كانت تحته «خطوات الوصول للدرجة الكاملة» — قائمةٌ تُملي على
                المالك ما يفعل بمحفظته، وقد أمر بحذفها. فحلّ سطرُ الذكاء
                محلَّها خاتمةً: الوسومُ تقول الحال، والسطرُ يقول خلاصتَه. */}
            {evaluation.summary && (
              <div className="rounded-xl p-4 mt-4"
                style={{ background: "var(--panel)", borderInlineStart: "3px solid var(--chart-1)" }}>
                <p className="text-[var(--ink)] text-[13px] leading-relaxed font-medium">{evaluation.summary}</p>
              </div>
            )}

          </div>
        )}
      </div>

      {/* Opportunities — top-momentum companies not already held, re-ranked
          by the same real ai_score used on every company's own page (never
          AI-generated text): computed hourly alongside the market-wide
          movers scan, so this list only refreshes then. */}
      {opportunities && opportunities.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Zap size={16} className="text-[var(--warn-ink)]" />
            <h2 className="card-title">فرص من زخم السوق</h2>
            <span className="text-[10px] text-[var(--ink-muted)] ms-auto">فرز آلي حسب الحوكمة</span>
          </div>

          {/* فلتر الحوكمة: «المبخّسة فقط» + فرز حسب الحوكمة/عائد التوزيع */}
          <div className="flex items-center gap-2 flex-wrap mb-3">
            <button onClick={() => setOppUnderOnly(v => !v)}
              className={oppUnderOnly
                ? "px-3 py-1.5 rounded-lg text-xs font-bold text-[var(--pos-ink)]"
                : "px-3 py-1.5 rounded-lg text-xs text-[var(--ink-muted)] hover:text-[var(--ink)]"}
              style={oppUnderOnly
                ? {background:"transparent", border: "1px solid var(--hairline)"}
                : {background:"var(--field)", border:"1px solid var(--hairline)"}}>
              مبخّسة فقط
            </button>
            <div className="flex items-center gap-1 ms-auto">
              <span className="text-[10px] text-[var(--ink-muted)]">الفرز:</span>
              {([["governance","الحوكمة"],["dividend","عائد التوزيع"]] as const).map(([k, lbl]) => (
                <button key={k} onClick={() => setOppSort(k)}
                  className={oppSort === k
                    ? "px-2.5 py-1 rounded-lg text-[11px] font-bold text-[var(--brand-ink)]"
                    : "px-2.5 py-1 rounded-lg text-[11px] text-[var(--ink-muted)] hover:text-[var(--ink)]"}
                  style={oppSort === k
                    ? {background:"transparent", border: "1px solid var(--hairline)"}
                    : {background:"var(--field)", border:"1px solid var(--hairline)"}}>
                  {lbl}
                </button>
              ))}
            </div>
          </div>

          {filteredOpps.length === 0 ? (
            <p className="text-[var(--ink-muted)] text-[13px] py-4 text-center">لا توجد فرص مطابقة للفلتر الحالي.</p>
          ) : (
          <div className="space-y-2">
            {filteredOpps.map((op: any) => (
              <button key={op.symbol} onClick={() => setSheet(op.symbol)}
                className="w-full flex items-center justify-between gap-3 p-3 bg-[var(--field)] rounded-xl border border-[var(--hairline)] hover:border-[var(--brand)] transition-colors text-start">
                <span className="flex items-center gap-2.5 min-w-0">
                  <CompanyLogo symbol={op.symbol} size={28} />
                  <span className="min-w-0">
                    <span className="flex items-center gap-1.5">
                      <span className="text-[var(--ink)] font-semibold text-sm truncate">{op.name}</span>
                      {op.is_undervalued && <span className="tag-g shrink-0" style={{fontSize:9}}>مبخّس</span>}
                    </span>
                    <span className="flex items-center gap-1.5 text-[11px] text-[var(--ink-muted)]">
                      <span className="tag-b" style={{fontSize:10}}>{op.symbol}</span>
                      <span className={op.change_pct >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]"}>
                        {(op.change_pct ?? 0) >= 0 ? "+" : ""}{(op.change_pct ?? 0).toFixed(2)}%
                      </span>
                      {op.dividend_yield != null && (
                        <span className="text-[var(--warn-ink)]">توزيع {op.dividend_yield}%</span>
                      )}
                    </span>
                  </span>
                </span>
                <span className="flex flex-col items-end gap-1 shrink-0">
                  <span className="tag-g" title="درجة الجودة المالية">{op.governance_score ?? op.ai_score}/100</span>
                </span>
              </button>
            ))}
          </div>
          )}
        </div>
      )}

      {/* Risk */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle size={16} className="text-[var(--neg-ink)]" />
          <h2 className="card-title">تحليل المخاطر</h2>
          {risk?.source === "AI" && <span className="tag-v ms-auto" style={{fontSize:10}}>AI</span>}
        </div>
        {/* ══ الصدقُ لا يكفي فيه أن يكون الحقلُ «صادقاً» ══ (D216)
            كان الشرطُ `!risk`، و`[]` أو `{}` قيمةٌ صادقةٌ في جافاسكربت —
            فيدخل فرعَ العرض ولا يُرسَم شيءٌ تحت العنوان: بطاقةٌ فارغةٌ
            بعنوانٍ يَعِد. فيُسأل عن **مضمون** لا عن وجود. */}
        {!(risk && (risk.overall_risk_level || risk.summary
                    || (Array.isArray(risk.risks) && risk.risks.length > 0))) ? (
          <p className="text-[var(--ink-muted)] text-sm py-4 text-center">لا توجد بيانات حالياً — يُبنى تحليل المخاطر تلقائياً عند وجود شركات في المحفظة وتفعيل مفتاح الذكاء</p>
        ) : (
        <>
          {risk.overall_risk_level && (
            <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-semibold mb-3
              ${risk.overall_risk_level === "LOW" ? "tag-g" : risk.overall_risk_level === "MEDIUM" ? "tag-a" : "tag-r"}`}>
              مستوى المخاطر: {risk.overall_risk_level === "LOW" ? "منخفض" : risk.overall_risk_level === "MEDIUM" ? "متوسط" : "عالٍ"}
            </div>
          )}
          {risk.summary && (
            <div className="rounded-xl p-4"
              style={{ background: "var(--panel)", borderInlineStart: "3px solid var(--chart-1)" }}>
              <p className="text-[var(--ink)] text-[13px] leading-relaxed font-medium">{risk.summary}</p>
            </div>
          )}
          {risk.risks && risk.risks.length > 0 && (
            <div className="mt-3 space-y-2">
              {risk.risks.map((r: any, i: number) => (
                /* كهرمانيٌّ لا برتقاليٌّ صارخ — سببُ مخاطرةٍ يُقرأ لا يصرخ. */
                <div key={i} className="flex items-start gap-2.5 p-3 panel rounded-xl"
                  style={{ borderInlineStart: "3px solid var(--amber-ink)" }}>
                  <span className="h-5 w-5 rounded-full text-[11px] font-bold flex items-center justify-center shrink-0 tabular-nums"
                    /* الحبر لون **أرضية الصفحة** لا الأبيض: الرموز الدلالية تنقلب مع
                      المظهر (كهرمانٌ ساطع في الداكن، بنّيٌّ غامق في الفاتح)،
                      وأرضية الصفحة تنقلب معها عكسياً — فيبقى التباين قائماً
                      في المظهرين بقاعدةٍ واحدة بلا شرط. قِيس: ١٫٦٧ ← ١١٫٦. */
                    style={{ background: "var(--amber-ink)", color: "var(--bg)" }}>{i + 1}</span>
                  <p className="text-[var(--ink)] text-[13px] leading-relaxed">{r.description || r}</p>
                </div>
              ))}
            </div>
          )}
        </>
        )}
      </div>

      {/* AI Report */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Brain size={16} className="text-[var(--brand-ink)]" />
          <h2 className="card-title">التقرير الشامل</h2>
          {report?.source === "AI" && <span className="tag-v ms-auto" style={{fontSize:10}}>AI</span>}
        </div>
        {/* الرسالة كانت تتّهم مفتاح الذكاء دائماً، حتى حين يكون العطل في
            مصدرٍ آخر — فيبدو التقرير معطّلاً بلا سبب. الآن تقول ما جرى. */}
        {!report?.content ? (
          <p className="text-sm py-4 text-center" style={{ color: "var(--ink-muted)" }}>
            تعذّر تحميل التقرير من الخادم — أعد المحاولة، وإن تكرّر فالسبب مسجَّل في سجلّ الخادم.
          </p>
        ) : (
          <div className="rounded-xl p-4 text-sm whitespace-pre-wrap leading-relaxed max-h-80 overflow-y-auto"
            /* سطحُ التطبيق نفسُه لا خلطةٌ رماديّة: كان `--ink 4%` فوق السطح
               يعطي لوناً باهتاً لا يشبه بطاقةً أخرى في التطبيق. */
            style={{ background: "var(--panel)", border: "1px solid var(--line)", color: "var(--ink)" }}>
            {report.content}
          </div>
        )}
      </div>
      {sheet && <StockSheet symbol={sheet} onClose={() => setSheet(null)} />}
    </div>
  );
}
