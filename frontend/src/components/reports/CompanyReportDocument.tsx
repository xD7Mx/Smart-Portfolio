import React from "react";
import { PAPER } from "./ReportDocument";

/* ══ ورقةُ تقرير الشركة ══ (D544) — بورق تقرير المحفظة نفسِه: الترويسةُ البنفسجية
   وشريطُ الذهب والشبكةُ والجدولُ وذيلُ الهويّة. فتقريرُ الشركة وتقريرُ المحفظة
   ورقةٌ واحدةٌ بمضمونين. */

const { NAVY, NAVY_2, GOLD, GOLD_L, GREEN, RED, INK, MUTED, ON_NAVY, BG, CARD_LINE, HEAD, STRIPE, ROW_LINE, WARN } = PAPER;

const num = (v: any, d = 0) =>
  typeof v === "number" ? v.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d }) : "—";
const mn = (v: any, key: string) => (key === "eps" ? num(v, 2) : typeof v === "number" ? num(v / 1e6) : "—");
const pct = (v: any) => (typeof v === "number" ? `${v > 0 ? "+" : ""}${v.toFixed(1)}%` : "—");
const col = (v: any) => (typeof v === "number" && v !== 0 ? (v > 0 ? GREEN : RED) : NAVY);
export const qName = (iso?: string) => {
  if (!iso) return "—";
  const m = Number(iso.slice(5, 7));
  return `الربع ${m <= 3 ? "الأول" : m <= 6 ? "الثاني" : m <= 9 ? "الثالث" : "الرابع"} ${iso.slice(0, 4)}`;
};
const REC: Record<string, string> = { "شراء": GREEN, "بيع": RED, "حياد": WARN };

/* ‏D548: التوصيةُ قرارُ التطبيق الواحد بمفرداته — يُلوَّن باتّجاهه لا بقائمةٍ ثابتة. */
const recColor = (x?: string) => !x ? NAVY : /شراء|تجميع|إيجاب/.test(x) ? GREEN : /بيع|تجنب|سلب|تخفيف/.test(x) ? RED : REC["حياد"];

const Title = ({ children }: { children: React.ReactNode }) => (
  <div style={{ fontSize: 13, fontWeight: 500, color: NAVY, marginBottom: 8, borderInlineStart: `3px solid ${GOLD}`, paddingInlineStart: 8 }}>
    {children}
  </div>
);
const N = ({ v, c }: { v: string; c?: string }) => (
  <bdi dir="ltr" style={{ unicodeBidi: "isolate", color: c, fontVariantNumeric: "tabular-nums" }}>{v}</bdi>
);
const th: React.CSSProperties = { padding: "7px 8px", textAlign: "start", fontWeight: 500 };
const td: React.CSSProperties = { padding: "6px 8px", fontWeight: 300 };

const CompanyReportDocument = React.forwardRef<HTMLDivElement, { data: any }>(({ data: r }, ref) => {
  const h = r?.header;
  const t = r?.table || {};
  const period = t.annual ? `النتائج السنوية ${String(t.as_of || "").slice(0, 4)}` : `نتائج ${qName(t.as_of)}`;
  /* ‏D655: السعرُ العادل في التقرير هو رقمُ صفحة السهم والفرز نفسُه (رقمُ اليوم) بثقته، والهدفُ مبنيٌّ عليه.
     ‏D660 (بأمر المالك): رقمٌ وثقتُه فقط — لا سطرَ تبريرٍ تحته («لا حواشي تفسيرية»). */
  const tiles: { l: string; v: string; c?: string; text?: boolean }[] = h ? [
    { l: "قرار التطبيق", v: h.recommendation || "—", c: recColor(h.recommendation), text: true },
    { l: "آخر سعر إغلاق", v: num(h.price, 2), c: NAVY },
    { l: "السعر العادل اليوم", v: typeof h.fair_value === "number" ? num(h.fair_value, 2) : "غير متوفّر",
      c: NAVY, text: typeof h.fair_value !== "number" },
    { l: "ثقة التقدير", v: h.fair_value_conf || "—", c: h.fair_value_conf === "منخفضة" ? WARN : NAVY, text: true },
    { l: "السعر المستهدف خلال 12 شهراً", v: num(h.target_12m, 2), c: NAVY },
    { l: "التغيّر المتوقّع", v: pct(h.change), c: col(h.change) },
    { l: "عائد الأرباح الموزّعة", v: typeof h.dividend_yield === "number" ? `${h.dividend_yield.toFixed(1)}%` : "—", c: NAVY },
    { l: "إجمالي العوائد المتوقّعة", v: pct(h.total_return), c: col(h.total_return) },
  ] : [];
  const R = r?.research || {};
  const LABEL: Record<string, string> = Object.fromEntries((t.rows || []).map((x: any) => [x.key, x.label]));
  Object.assign(LABEL, { revenue: LABEL.revenue || "الإيرادات", ebit: LABEL.ebit || "الربح التشغيلي",
    net_income_parent: LABEL.net_income_parent || "صافي الدخل", bank_nfi: LABEL.bank_nfi || "صافي دخل التمويل والاستثمار",
    bank_op_income: LABEL.bank_op_income || "الدخل التشغيلي الإجمالي" });
  const fcRows: any[] = Object.values(R.forecast || {});
  const g = R.growth || {}, ph = R.price || {}, pb = R.pe_band, se = R.seasonality;
  const yr = (x: any) => (g.years?.length ? `${g.years[0]}–${g.years[g.years.length - 1]}` : "");
  const hist: { l: string; v: string; c?: string; text?: boolean }[] = [
    ...(g.rev_cagr != null ? [{ l: `نموّ الإيراد السنوي المركّب ${yr(g)}`, v: pct(g.rev_cagr), c: col(g.rev_cagr) }] : []),
    ...(g.ni_cagr != null ? [{ l: `نموّ صافي الدخل السنوي المركّب ${yr(g)}`, v: pct(g.ni_cagr), c: col(g.ni_cagr) }] : []),
    ...(g.margin_last != null ? [{ l: `هامش صافي الربح من ${g.years[0]} إلى ${g.years[g.years.length - 1]}`, v: `من ${g.margin_first}٪ إلى ${g.margin_last}٪`, text: true }] : []),
    ...(se ? [{ l: `أقوى الأرباع (${se.years} سنوات)`, v: `الربع ${se.strongest}`, text: true }] : []),
    ...(ph.cagr != null ? [{ l: `عائد السهم السنوي منذ ${String(ph.since).slice(0, 4)}`, v: pct(ph.cagr), c: col(ph.cagr) }] : []),
    ...(ph.tasi_cagr != null ? [{ l: `تاسي السنوي في المدّة نفسها`, v: pct(ph.tasi_cagr), c: col(ph.tasi_cagr) }] : []),
    ...(ph.max_dd != null ? [{ l: "أقصى تراجع للسهم", v: pct(ph.max_dd), c: col(ph.max_dd) }] : []),
    ...(ph.best ? [{ l: `أفضل سنة (${ph.best.y}) · أسوأ سنة (${ph.worst.y})`, v: `${pct(ph.best.r)} · ${pct(ph.worst.r)}` }] : []),
    ...(ph.div ? [{ l: `التوزيعات منذ ${ph.div.since}`, v: `${ph.div.years_paid} سنة · انتظام ${ph.div.regularity}٪`, text: true }] : []),
    ...(ph.div?.cagr != null ? [{ l: "نموّ التوزيعات السنوي", v: pct(ph.div.cagr), c: col(ph.div.cagr) }] : []),
    ...(pb?.current != null ? [{ l: `مكرّر الربحية ونطاقه (${pb.points[0][0]}–${pb.points[pb.points.length - 1][0]})`, v: `${pb.current}x · ${pb.low}–${pb.high}x` }] : []),
  ];
  const heads = ["البند", t.annual ? String(t.as_of || "").slice(0, 4) : qName(t.as_of),
    t.annual ? String(t.prior_year || "").slice(0, 4) : qName(t.prior_year), "سنوي",
    ...(t.annual ? [] : [qName(t.prev_quarter), "ربعي"]), "توقّعاتنا"];
  return (
    <div ref={ref} className="report-doc" dir="rtl"
      style={{ width: 794, minHeight: 1123, background: BG, color: INK,
               fontFamily: "'Thmanyah Serif Display', 'Segoe UI', sans-serif",
               display: "flex", flexDirection: "column", boxSizing: "border-box" }}>
      <div style={{ background: `linear-gradient(135deg, ${NAVY}, ${NAVY_2})`, padding: "28px 44px 22px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ color: "#fff", fontSize: 22, fontWeight: 500 }}>المحفظة الذكية</div>
            <div style={{ color: GOLD_L, fontSize: 11.5, fontWeight: 300, marginTop: 2 }}>تقرير نتائج الشركة</div>
          </div>
          <div style={{ textAlign: "left", color: ON_NAVY, fontSize: 11 }}>
            <div style={{ color: "#fff", fontSize: 14, fontWeight: 500 }}>{r?.name || r?.symbol} <N v={String(r?.symbol || "")} /></div>
            <div style={{ marginTop: 3 }}>الفترة: <span style={{ color: "#fff", fontWeight: 300 }}>{period}</span></div>
          </div>
        </div>
      </div>
      <div style={{ height: 4, background: `linear-gradient(90deg, ${GOLD}, ${GOLD_L}, ${GOLD})` }} />

      <div style={{ padding: "26px 44px 32px", flex: 1, display: "flex", flexDirection: "column", gap: 22 }}>
        {!!tiles.length && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
            {tiles.map(k => (
              <div key={k.l} style={{ border: `1px solid ${CARD_LINE}`, borderRadius: 8, padding: "10px 12px", background: "#fff" }}>
                <div style={{ fontSize: 10, color: MUTED, fontWeight: 300 }}>{k.l}</div>
                <div style={{ fontSize: 16, fontWeight: k.text ? 500 : 300, color: k.c, marginTop: 2 }}>
                  {k.text ? k.v : <N v={k.v} />}
                </div>
              </div>
            ))}
          </div>
        )}

        {!!(t.rows || []).length && (
          <div>
            <Title>النتائج المالية (مليون ريال)</Title>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11.5 }}>
              <thead>
                <tr style={{ background: HEAD, color: NAVY, borderBottom: `2px solid ${GOLD}`,
                             WebkitPrintColorAdjust: "exact", printColorAdjust: "exact" } as React.CSSProperties}>
                  {heads.map((x, i) => <th key={i} style={th}>{x}</th>)}
                </tr>
              </thead>
              <tbody>
                {t.rows.map((x: any, i: number) => (
                  <tr key={x.key} style={{ background: i % 2 ? STRIPE : "#fff", borderBottom: `1px solid ${ROW_LINE}` }}>
                    <td style={{ ...td, fontWeight: 500 }}>{x.label}</td>
                    <td style={td}><N v={mn(x.cur, x.key)} /></td>
                    <td style={td}><N v={mn(x.yoy_base, x.key)} /></td>
                    <td style={td}><N v={pct(x.yoy)} c={col(x.yoy)} /></td>
                    {!t.annual && <td style={td}><N v={mn(x.prev, x.key)} /></td>}
                    {!t.annual && <td style={td}><N v={pct(x.qoq)} c={col(x.qoq)} /></td>}
                    <td style={td}><N v={mn(x.expected, x.key)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <div>
            <Title>بيانات السوق</Title>
            {[["أعلى سعر خلال 52 أسبوعاً", num(r?.market?.high_52w, 2)],
              ["أدنى سعر خلال 52 أسبوعاً", num(r?.market?.low_52w, 2)],
              ["القيمة السوقية (مليون ريال)", typeof r?.market?.market_cap === "number" ? num(r.market.market_cap / 1e6) : "—"],
              ["الأسهم (مليون سهم)", typeof r?.market?.shares === "number" ? num(r.market.shares / 1e6) : "—"]].map(([l, v], i) => (
              <div key={l} style={{ display: "flex", justifyContent: "space-between", padding: "6px 10px", fontSize: 11.5,
                                    background: i % 2 ? STRIPE : "#fff", borderBottom: `1px solid ${ROW_LINE}` }}>
                <span style={{ fontWeight: 300, color: MUTED }}>{l}</span><N v={v} c={NAVY} />
              </div>
            ))}
          </div>
          <div>
            <Title>الأداء مقابل تاسي</Title>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11.5 }}>
              <thead>
                <tr style={{ background: HEAD, color: NAVY, borderBottom: `2px solid ${GOLD}`,
                             WebkitPrintColorAdjust: "exact", printColorAdjust: "exact" } as React.CSSProperties}>
                  {["المدّة", "السهم", "تاسي"].map(x => <th key={x} style={th}>{x}</th>)}
                </tr>
              </thead>
              <tbody>
                {([["6m", "نصف عام"], ["1y", "عام"], ["2y", "عامان"]] as const).map(([k, l], i) => (
                  <tr key={k} style={{ background: i % 2 ? STRIPE : "#fff", borderBottom: `1px solid ${ROW_LINE}` }}>
                    <td style={td}>{l}</td>
                    <td style={td}><N v={pct(r?.performance?.[k]?.stock)} c={col(r?.performance?.[k]?.stock)} /></td>
                    <td style={td}><N v={pct(r?.performance?.[k]?.tasi)} c={col(r?.performance?.[k]?.tasi)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {!!fcRows.length && (
          <div>
            <Title>توقّعاتنا لـ{qName(fcRows[0].as_of)} (مليون ريال)</Title>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11.5 }}>
              <thead>
                <tr style={{ background: HEAD, color: NAVY, borderBottom: `2px solid ${GOLD}`,
                             WebkitPrintColorAdjust: "exact", printColorAdjust: "exact" } as React.CSSProperties}>
                  {["البند", "التوقّع", "الطريقة الأدقّ لهذه الشركة", "خطؤها التاريخي", "صدقُ الاتجاه", "أرباعٌ مختبَرة"].map(x => <th key={x} style={th}>{x}</th>)}
                </tr>
              </thead>
              <tbody>
                {fcRows.map((f: any, i: number) => (
                  <tr key={f.key} style={{ background: i % 2 ? STRIPE : "#fff", borderBottom: `1px solid ${ROW_LINE}` }}>
                    <td style={{ ...td, fontWeight: 500 }}>{LABEL[f.key] || f.key}</td>
                    <td style={td}><N v={mn(f.value, f.key)} c={NAVY} /></td>
                    <td style={td}>{f.label}</td>
                    <td style={td}><N v={`${f.mape.toFixed(1)}%`} /></td>
                    <td style={td}><N v={f.hit == null ? "—" : `${f.hit}%`} /></td>
                    <td style={td}><N v={String(f.tested)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!!hist.length && (
          <div>
            <Title>القراءة التاريخية</Title>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
              {hist.map(k => (
                <div key={k.l} style={{ border: `1px solid ${CARD_LINE}`, borderRadius: 8, padding: "10px 12px", background: "#fff" }}>
                  <div style={{ fontSize: 10, color: MUTED, fontWeight: 300 }}>{k.l}</div>
                  <div style={{ fontSize: 15, fontWeight: 300, color: k.c || NAVY, marginTop: 2 }}>{k.text ? k.v : <N v={k.v} c={k.c || NAVY} />}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        {!!(r?.insights || []).length && (
          <div>
            <Title>من ملفّات الشركة ومؤتمراتها</Title>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 6 }}>
              {(r.insights as string[]).map((t, i) => (
                <li key={i} style={{ fontSize: 11.5, lineHeight: 1.7, color: NAVY, fontWeight: 300, display: "flex", gap: 8 }}>
                  <span style={{ color: MUTED }}>•</span><span>{t}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <div style={{ height: 6, background: `linear-gradient(90deg, ${NAVY}, ${NAVY_2}, ${NAVY})` }} />
    </div>
  );
});
CompanyReportDocument.displayName = "CompanyReportDocument";
export default CompanyReportDocument;
