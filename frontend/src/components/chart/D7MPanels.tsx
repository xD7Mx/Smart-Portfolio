/* لوحاتُ مؤشّر D7M (اللوحةُ · المحلّلُ الذكيّ · التنبيهات · أداةُ الصفقة) — كما في سكربت المالك، للرسم الاحترافيّ (‏D736).
   الحسابُ في ‏analysis/d7m (المصدرُ الواحد)، وهنا العرضُ وحده. */
import React from "react";

/** شريطُ السكربت █░: عشرُ خاناتٍ، الممتلئةُ بلون القرار والباقيةُ منقَّطة. */
function Meter({ v, solid = false }: { v: number; solid?: boolean }) {
  const f = Math.min(Math.round(Math.abs(v)), 10);
  return (
    <div className={"d7m-meter" + (solid ? " d7m-meter-solid" : "")} role="img" aria-label={`${f} من 10`}>
      {Array.from({ length: 10 }, (_, k) => <span key={k} className={k < f ? "on" : ""} />)}
    </div>
  );
}

export default function D7MPanels({ dash, msmart, tt, alerts, pos, axisW }: {
  dash: any; msmart: any; tt: any; alerts: { mom: string; rev: string; bounce: string } | null; pos: string; axisW: number;
}) {
  if (!(dash || msmart || tt || alerts)) return null;
  return (
    <div className={`d7m-panels d7m-at-${pos}`} dir="rtl" data-role="d7m-panels" style={{ ["--d7m-axis" as any]: `${axisW + 6}px` }}>
      {dash && (
        <table className="d7m-table d7m-dash">
          <thead><tr><th>الإطار</th><th>الحالة</th><th>المؤشرات الفنية</th></tr></thead>
          <tbody>
            {dash.rows.map((r: any, k: number) => (
              <tr key={r.tf}>
                <td className="d7m-tf" dir="ltr">{r.tf}</td>
                <td className={r.up == null ? "d7m-muted" : r.up ? "d7m-pos" : "d7m-neg"}>{r.up == null ? "—" : r.up ? "صعود" : "هبوط"}</td>
                <td className={k === 1 ? `d7m-${dash.liq.color}` : k === 3 ? `d7m-${dash.trend.tone}` : "d7m-muted"}>
                  {k === 0 ? "راصد الحيتان" : k === 1 ? dash.liq.state : k === 2 ? "قوة الاتجاه" : dash.trend.state}</td>
              </tr>
            ))}
            <tr><th colSpan={3}>قرار الدخول</th></tr>
            <tr><td colSpan={3} className={`d7m-decision d7m-tone-${dash.tone}`}>
              <div className="d7m-dec-text">{dash.decision}</div>
              <Meter v={dash.power} solid />
              <Meter v={dash.trust} />
              <div className="d7m-dec-cap">الثقة</div>
            </td></tr>
          </tbody>
        </table>
      )}
      {msmart && (
        <table className="d7m-table">
          <thead><tr><th>المحلل الذكي</th></tr></thead>
          <tbody>
            <tr><td className={`d7m-${msmart.readingTone}`}>{msmart.reading}</td></tr>
            <tr><td>{msmart.divergence}</td></tr>
            <tr><td className={msmart.summary === "صعود" ? "d7m-pos" : msmart.summary === "هبوط" ? "d7m-neg" : "d7m-warn"}>{msmart.summary}</td></tr>
          </tbody>
        </table>
      )}
      {alerts && (
        <table className="d7m-table">
          <thead><tr><th colSpan={2}>التنبيهات</th></tr></thead>
          <tbody>
            {([["الزخم", alerts.mom], ["انعكاس", alerts.rev], ["ارتداد", alerts.bounce]] as const).map(([k, v]) => (
              <tr key={k}><td>{k}</td><td className={v === "شراء" ? "d7m-pos" : v === "بيع" ? "d7m-neg" : ""}>{v}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      {tt && (
        <table className="d7m-table">
          <thead><tr><th colSpan={2}>أداة الصفقة 📋</th></tr></thead>
          <tbody>
            <tr><td>القرار</td><td className={tt.call ? "d7m-pos" : tt.put ? "d7m-neg" : "d7m-warn"}>{tt.dec}<Meter v={tt.conf} solid /></td></tr>
            <tr><td>السترايك</td><td>{tt.call || tt.put ? `$${Math.round(tt.strike)}` : "—"}</td></tr>
            <tr><td>الهدف</td><td className="d7m-pos">{tt.call || tt.put ? `$${tt.target.toFixed(2)}` : "—"}</td></tr>
            <tr><td>الوقف</td><td className="d7m-neg">{tt.call || tt.put ? `$${tt.stop.toFixed(2)}` : "—"}</td></tr>
            <tr><td>R : R</td><td>{tt.call || tt.put ? `1 : ${tt.rr.toFixed(1)}` : "—"}</td></tr>
            <tr><td>الدخول</td><td>{tt.entry}</td></tr>
            <tr><td>Gap اليوم</td><td className={tt.gap > 0.2 ? "d7m-pos" : tt.gap < -0.2 ? "d7m-neg" : ""}>{(tt.gap >= 0 ? "+" : "") + tt.gap.toFixed(2)}%</td></tr>
          </tbody>
        </table>
      )}
    </div>
  );
}
