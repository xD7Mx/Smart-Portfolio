/* شريطُ D7M الذكيّ (‏D744 · المالك 2026-11-15: «اللوحةُ كبيرةٌ وتفاصيلُها مملّة — نبغى رؤوسَ أقلام: عدّادٌ بحجم الإصبع أفقيّ، شاشاتٌ
   بسيطةٌ فيها دلالاتٌ إرشاديةٌ ذكية… قوّةُ السيولة واتجاهُ السهم… ذكيٌّ يرصد الحيتان»). كان جداولَ فوق الشموع تأخذ ربعَ الرسم،
   وصار صفّاً رفيعاً فوق الرسم لا يغطّي شمعة: الاتجاهُ على أربعة أطرٍ، والحيتانُ بحجمها النسبيّ، وقوّةُ الاتجاه، والقرارُ بعدّاده
   وثقتِه — والمحلّلُ والتنبيهاتُ وأداةُ الصفقة إن فُعّلت. الحسابُ نفسُه في ‏analysis/d7m (المصدرُ الواحد). */
const tone = (t?: string | null) => (t === "pos" ? "pos" : t === "neg" ? "neg" : t === "warn" ? "warn" : "muted");
const word = (v: string) => (v === "شراء" ? "pos" : v === "بيع" ? "neg" : "muted");

function Meter({ v, t }: { v: number; t: string }) {
  const f = Math.min(Math.round(Math.abs(v)), 10);
  return <span className={`d7s-meter d7s-${t}`} role="img" aria-label={`${f} من 10`}>{Array.from({ length: 10 }, (_, k) => <i key={k} className={k < f ? "on" : ""} />)}</span>;
}
function Tile({ k, t = "muted", children, title }: { k: string; t?: string; children: React.ReactNode; title?: string }) {
  return (
    <div className={`d7s-tile d7s-${t}`} title={title}>
      <span className="d7s-k">{k}</span>
      <span className="d7s-v">{children}</span>
    </div>
  );
}

export default function D7MStrip({ dash, msmart, tt, alerts }: {
  dash: any; msmart: any; tt: any; alerts: { mom: string; rev: string; bounce: string } | null;
}) {
  if (!(dash || msmart || tt || alerts)) return null;
  return (
    <div className="d7s" role="group" aria-label="خلاصة D7M" data-role="d7m-strip">
      {dash && (
        <>
          <Tile k="القرار" t={tone(dash.tone)} title={`القوّة ${dash.power}/10 · الثقة ${dash.trust}/10`}>
            <b>{dash.decision}</b><Meter v={dash.power} t={tone(dash.tone)} /><span className="d7s-dim tabular-nums" dir="ltr">{dash.trust}/10</span>
          </Tile>
          <Tile k="الاتجاه" t={dash.summary === "صعود" ? "pos" : dash.summary === "هبوط" ? "neg" : "warn"} title={`مجموعُ الأطر ${dash.score}`}>
            {dash.rows.map((r: any) => (
              <span key={r.tf} className={"d7s-tf " + (r.up == null ? "muted" : r.up ? "pos" : "neg")} dir="ltr">{r.tf}{r.up == null ? "·" : r.up ? "▲" : "▼"}</span>
            ))}
          </Tile>
          <Tile k="الحيتان" t={tone(dash.liq.color)} title="راصدُ الحيتان: الحجمُ النسبيّ للشمعة الأخيرة وموضعُ إغلاقها">
            <b>{dash.liq.state}</b>{dash.liq.rvol != null && <span className="d7s-dim tabular-nums" dir="ltr">{Math.round(dash.liq.rvol)}%</span>}
          </Tile>
          <Tile k="قوّة الاتجاه" t={tone(dash.trend.tone)}>
            <b>{dash.trend.state}</b>{dash.trend.adx != null && <span className="d7s-dim tabular-nums" dir="ltr">ADX {Math.round(dash.trend.adx)}</span>}
          </Tile>
          {(dash.vixWarn || dash.newsWarn) && <Tile k="تحذير" t="neg"><b>{dash.vixWarn || "يومُ خبر"}</b></Tile>}
        </>
      )}
      {msmart && <Tile k="المحلّل" t={msmart.summary === "صعود" ? "pos" : msmart.summary === "هبوط" ? "neg" : "warn"} title={`${msmart.reading} · ${msmart.divergence}`}><b>{msmart.summary}</b></Tile>}
      {alerts && (
        <Tile k="التنبيهات">
          {([["زخم", alerts.mom], ["انعكاس", alerts.rev], ["ارتداد", alerts.bounce]] as const).map(([n, v]) => (
            <span key={n} className={"d7s-tf " + word(v)} title={`${n}: ${v}`}>{n}{v === "شراء" ? "▲" : v === "بيع" ? "▼" : "·"}</span>
          ))}
        </Tile>
      )}
      {tt && (
        <Tile k="الصفقة" t={tt.call ? "pos" : tt.put ? "neg" : "warn"} title={tt.call || tt.put ? `الهدف ${tt.target.toFixed(2)} · الوقف ${tt.stop.toFixed(2)} · R:R 1:${tt.rr.toFixed(1)}` : tt.entry}>
          <b>{tt.dec}</b>{(tt.call || tt.put) && <span className="d7s-dim tabular-nums" dir="ltr">${Math.round(tt.strike)}</span>}
        </Tile>
      )}
    </div>
  );
}
