import React from "react";

const money = (n: number) => (n ?? 0).toLocaleString("en-US", { maximumFractionDigits: 0 });

const NAVY = "#3b1e78";
const NAVY_2 = "#6d28d9";
const GOLD = "#d4af37";
const GOLD_L = "#f3d98b";
const GREEN = "#0f9d63";
const RED = "#c0273c";
/* ══ ورقُ التقرير لوحُه هو ══ (D333)
   كانت في الورقة ثلاثةُ مواضعَ بلون `var(--ink)` و`var(--ink-muted)` —
   رموزُ **مظهر التطبيق**. والورقةُ أرضيتُها ثابتةٌ (‏#faf6ee) وترويستُها
   بنفسجيةٌ ثابتة، فحبرٌ يتبع المظهرَ يعني: في المظهر الفاتح حبرٌ أسودُ
   على البنفسجيّ (‏1.4:1 — لا يُقرأ)، وفي المصدَّر صورةٌ تختلف باختلاف
   مظهرِ قارئها. فالورقةُ ألوانُها من لوحها نفسِه لا من التطبيق. */
const PAPER_INK = "#241f1a";
const PAPER_MUTED = "#6b6255";
const ON_NAVY = "#efe7ff";

export interface ReportDocData {
  period?: string;
  generated_at?: string;
  overall_score?: number | null;
  content?: string | null;
  metrics?: {
    market_value?: number; total_invested?: number; unrealized_pnl?: number;
    roi_pct?: number; dividends?: number; positions_count?: number;
    wealth?: number | null; net_profit?: number | null;
    capital_growth_pct?: number | null; cagr_pct?: number | null;
    cash_pct?: number | null;
  };
  growth?: {
    boxes?: { key: string; label: string; suffix: string; prev: number | null; now: number | null; neutral?: boolean }[];
  };
  positions?: { name: string; symbol: string; shares: number; market_value: number; pnl: number; pnl_pct: number }[];
}

const ReportDocument = React.forwardRef<HTMLDivElement, { data: ReportDocData }>(({ data }, ref) => {
  const m = data.metrics || {};
  /* ولا يُختلق تاريخُ إصدار (D333): كان الغيابُ يُملأ بـ`new Date()`،
     فيُطبع في ورقةٍ لا تاريخَ لها **تاريخُ اليوم** — وهو رقمٌ لا مصدرَ
     له في التقرير. فالغائبُ شرطة. */
  const genDate = data.generated_at ? new Date(data.generated_at) : null;
  const genText = genDate && !isNaN(genDate.getTime())
    ? genDate.toLocaleDateString("ar-EG-u-ca-gregory-nu-latn") : "—";

  return (
    <div
      ref={ref}
      className="report-doc"
      dir="rtl"
      style={{
        // ورق التقرير من ورق التطبيق نفسه: هويّةٌ واحدة بين الشاشة والمُصدَّر.
        width: 794, minHeight: 1123, background: "#faf6ee", color: "#241f1a",
        fontFamily: "'Thmanyah Serif Display', 'Segoe UI', sans-serif",
        display: "flex", flexDirection: "column", boxSizing: "border-box",
      }}
    >
      {/* Header */}
      <div style={{ background: `linear-gradient(135deg, ${NAVY}, ${NAVY_2})`, padding: "28px 44px 22px", position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ color: "#fff", fontSize: 22, fontWeight: 500 }}>المحفظة الذكية</div>
            <div style={{ color: GOLD_L, fontSize: 11.5, fontWeight: 300, marginTop: 2 }}>تقرير أداء المحفظة الاستثمارية</div>
          </div>
          <div style={{ textAlign: "left", color: ON_NAVY, fontSize: 11 }}>
            <div>الفترة: <span style={{ color: "#fff", fontWeight: 300 }}>{data.period || ""}</span></div>
            <div style={{ marginTop: 3 }}>تاريخ الإصدار: {genText}</div>
          </div>
        </div>
      </div>
      <div style={{ height: 4, background: `linear-gradient(90deg, ${GOLD}, ${GOLD_L}, ${GOLD})` }} />

      {/* Body — flex:1 fills whatever space is left above the footer, so
          the footer always follows the content directly (in print too)
          instead of relying on an absolutely-positioned bottom anchor that
          Chrome's print pagination doesn't reliably honor. */}
      <div style={{ padding: "26px 44px 32px", flex: 1 }}>
        {/* ══ شبكة المالك: ثلاثة صفوفٍ لكلٍّ معنى ══
            الأول: ما تملك.  الثاني: ما ربحت.  الثالث: كيف أدّت.
            وهي الشبكة نفسها في ورقة صقر (`saqr_report.py`) — بندٌ ببند،
            فما يُقرأ في تلغرام هو ما يُقرأ هنا لا شبيهُه. */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 22 }}>
          {(() => {
            /* شرطةٌ للغائب لا صفر: الفرق بين «صفر» و«غير متوفّر» فرقُ معنى.
               والعائد المركّب يمتنع قبل تسعين يوماً من بداية المشروع (بند
               الميثاق) فيصل هنا فارغاً — وخانتُه تبقى باسمها فلا يتزحزح
               الصفّ ولا يُظنّ الاسم ساقطاً. */
            const sgn = (v?: number | null, d = 2) =>
              v == null ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(d)}%`;
            const col = (v?: number | null) => v == null ? NAVY : (v >= 0 ? GREEN : RED);
            /* ولا يُصفَّر غائبٌ (D333): جارتاهما في الشبكة نفسِها تعرضان
               «—» للغائب، وهاتان كانتا تعرضان «+0» و«+0.00%» — فيُقرأ
               الجهلُ تعادلاً. والقاعدةُ في الميثاق: الغيابُ يُقال. */
            const upnl = m.unrealized_pnl ?? null, roi = m.roi_pct ?? null;
            const amt = (v?: number | null) =>
              v == null ? "—" : `${v >= 0 ? "+" : ""}${money(v)}`;
            return [
              { l: "القيمة السوقية", v: money(m.market_value || 0), c: NAVY },
              { l: "القيمة المدفوعة", v: money(m.total_invested || 0), c: NAVY },
              { l: "إجمالي الثروة", v: m.wealth == null ? "—" : money(m.wealth), c: NAVY },

              { l: "الأرباح غير المحققة", v: amt(upnl), c: col(upnl) },
              { l: "نسبة الأرباح غير المحققة", v: sgn(roi), c: col(roi) },
              { l: "صافي الربح", v: m.net_profit == null ? "—" : `${m.net_profit >= 0 ? "+" : ""}${money(m.net_profit)}`, c: col(m.net_profit) },

              { l: "عائد المحفظة", v: sgn(m.capital_growth_pct), c: col(m.capital_growth_pct) },
              { l: "العائد المركّب", v: sgn(m.cagr_pct), c: col(m.cagr_pct) },
              { l: "نسبة السيولة النقدية", v: m.cash_pct == null ? "—" : `${m.cash_pct.toFixed(2)}%`, c: NAVY },
            ];
          })().map(k => (
            <div key={k.l} style={{ border: "1px solid #e4dcc2", borderRadius: 8, padding: "10px 12px", background: "#fff" }}>
              <div style={{ fontSize: 10, color: PAPER_MUTED, fontWeight: 300 }}>{k.l}</div>
              {/* الرقمُ وإشارتُه معزولان يساراً-يميناً: في سطرٍ عربيّ كانت «+» تُطبع بعد الرقم (D479) */}
              <div style={{ fontSize: 16, fontWeight: 300, color: k.c, marginTop: 2, fontVariantNumeric: "tabular-nums" }}>
                <bdi dir="ltr" style={{ unicodeBidi: "isolate" }}>{k.v}</bdi>
              </div>
            </div>
          ))}
        </div>

        {/* ══ صناديق النموّ أُسقطت ══
            كانت تعرض «عائد المحفظة» و«التفوّق على تاسي» و«نسبة السيولة»،
            وقد صار اثنان منها في الشبكة أعلاه بأمر المالك. وإبقاؤها يعني
            رقماً واحداً في موضعين من الورقة نفسها. */}

        {/* Positions table */}
        {!!data.positions?.length && (
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: NAVY, marginBottom: 8, borderInlineStart: `3px solid ${GOLD}`, paddingInlineStart: 8 }}>
              تفاصيل المراكز
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11.5 }}>
              <thead>
                {/* نصٌّ داكنٌ على خلفيةٍ فاتحة: الخلفياتُ لا تُطبع افتراضاً فكان الأبيضُ على الورق الأبيض لا يُقرأ (D479) */}
                <tr style={{ background: "#efe7cf", color: NAVY, borderBottom: `2px solid ${GOLD}`,
                             WebkitPrintColorAdjust: "exact", printColorAdjust: "exact" } as React.CSSProperties}>
                  {["الشركة", "الرمز", "الأسهم", "القيمة", "الربح/الخسارة"].map(h => (
                    <th key={h} style={{ padding: "7px 10px", textAlign: "start", fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.positions.map((p, i) => (
                  <tr key={p.symbol} style={{ background: i % 2 ? "#f6f2e4" : "#fff", borderBottom: "1px solid #e9e2cc" }}>
                    <td style={{ padding: "6px 10px", fontWeight: 300 }}>{p.name}</td>
                    <td style={{ padding: "6px 10px", color: PAPER_MUTED }}>{p.symbol}</td>
                    <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{money(p.shares)}</td>
                    <td style={{ padding: "6px 10px", fontVariantNumeric: "tabular-nums" }}>{money(p.market_value)}</td>
                    <td style={{ padding: "6px 10px", color: p.pnl >= 0 ? GREEN : RED, fontVariantNumeric: "tabular-nums" }}>
                      <bdi dir="ltr" style={{ unicodeBidi: "isolate" }}>
                        {p.pnl >= 0 ? "+" : ""}{money(p.pnl)}
                        {p.pnl_pct == null ? "" : ` (${p.pnl_pct >= 0 ? "+" : ""}${p.pnl_pct.toFixed(1)}%)`}
                      </bdi>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Analysis */}
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: NAVY, borderInlineStart: `3px solid ${GOLD}`, paddingInlineStart: 8 }}>
              التحليل الشامل
            </div>
            {data.overall_score != null && (
              <div style={{ fontSize: 11, fontWeight: 300, color: NAVY, background: "#f6f2e4", border: `1px solid ${GOLD}`, borderRadius: 999, padding: "3px 12px" }}>
                التقييم العام {data.overall_score}/100
              </div>
            )}
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.9, color: "#28324a", whiteSpace: "pre-wrap", background: "#fff", border: "1px solid #e4dcc2", borderRadius: 8, padding: 16 }}>
            {data.content || "لا تتوفر بيانات تحليلية لهذا التقرير."}
          </div>
        </div>
      </div>

      {/* ══ وذيلُ الورقة: شريطُ هويّةٍ لا صندوقٌ خاوٍ ══ (D333)
          كان `padding: 16px` بتدرّجٍ بنفسجيٍّ **وبلا مضمون** — كتلةُ لونٍ
          بارتفاع ٥٠px لا تقول شيئاً (بقيّةُ محتوًى أُزيل). فصار شريطاً
          رقيقاً يُقفل الورقةَ بلون الهويّة: زينةٌ مقصودةٌ لا فراغٌ منسيّ. */}
      <div style={{ height: 6, background: `linear-gradient(90deg, ${NAVY}, ${NAVY_2}, ${NAVY})` }} />
    </div>
  );
});
ReportDocument.displayName = "ReportDocument";
export default ReportDocument;
