/* ══ لوحتا القوّة فوق الرسم ══ (‏D782 · بأمر المالك 2026-11-21)
   «لوحةُ الملخّص ما عجبتني — أبغاها قويّة… لوحتان مهمّتان: قوّةُ الاتجاه وقوّةُ السيولة… ولوحةُ الأطر نستغني عنها… شيءٌ بسيطٌ وواضح».
   ‏D796 (المالك 2026-11-24): «اللوحتان روعة — حتى اللونُ الهابطُ بالأحمر والمؤثّراتُ البصريةُ جميلة، والكلماتُ (هابطٌ قويّ · السيولةُ داخلةٌ للصعود
   قويّة · جفافُ سيولة) جميلةٌ حافظ عليها… لكنّ الأرقامَ مشتّتة: 57 و65 والـADX 24 — الواحدُ يتلخبط ولا يعرف كيف يتّخذ قراره. بدلَ الأرقام مؤشّرٌ
   كميزان الموية اللي حطّيناه في السعر العادل… وتظهر التفاصيلُ والأرقامُ إذا أردتُها. أريد الاعتمادَ على التأثير البصريّ».
   فوجهُ اللوحة: الكلمةُ بلونها ودرجتُها، وميزانٌ واحدٌ كميزان السعر العادل (‏TrendBar — المحايدُ في الوسط، والفقاعةُ البيضاءُ تميل نحو الأحمر
   هبوطاً ونحو الأخضر صعوداً بقدر القوّة)؛ والأرقامُ والشواهدُ تحت اللوحة إن ضُغطت (وعند المرور). والحسابُ في ‏analysis/pulse لم يتغيّر. */
import { useState } from "react";
import { TrendingUp, TrendingDown, MoveHorizontal, Droplets, ChevronDown } from "lucide-react";
import type { Force, Side } from "../analysis/pulse";
import { TrendBar } from "../common/ValueBars";

const tone = (s: Side) => (s === "up" ? "pos" : s === "down" ? "neg" : s === "flat" ? "warn" : "muted");
const Arrow = ({ s, size }: { s: Side; size: number }) =>
  s === "up" ? <TrendingUp size={size} strokeWidth={2.4} /> : s === "down" ? <TrendingDown size={size} strokeWidth={2.4} /> : <MoveHorizontal size={size} strokeWidth={2.4} />;
const reasons = (f: Force) => f.why.map(([d, t]) => `${d > 0 ? "▲" : "▼"} ${t}`).join("\n");
/** موضعُ الفقاعة على الميزان: الوسطُ محايد، والصعودُ يميل إلى الأخضر والهبوطُ إلى الأحمر بقدر القوّة */
export const gaugeScore = (f: Force) => 50 + (f.side === "up" ? 1 : f.side === "down" ? -1 : 0) * Math.max(0, Math.min(100, f.strength)) / 2;

function Card({ k, f, role, icon }: { k: string; f: Force; role: string; icon: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const t = tone(f.side);
  const na = f.side === "na";
  return (
    <div className={`fp-card fp-${t}` + (open ? " fp-open" : "")} data-role={role} data-side={f.side}>
      <button type="button" className="fp-face" onClick={() => !na && setOpen(o => !o)} aria-expanded={na ? undefined : open} disabled={na}
        title={na ? f.stat || "" : `${k}: ${f.word} · ${f.level}\nاضغط للتفاصيل والأرقام`} data-role="fp-face">
        <span className="fp-ic" aria-hidden>{icon}</span>
        <span className="fp-body">
          <span className="fp-k">{k}</span>
          <span className="fp-v"><b data-role="fp-word">{f.word}</b>{!na && <span className="fp-lv">{f.level}</span>}
            {f.tag && <span className="fp-tag" data-role="fp-tag">{f.tag}</span>}</span>
          {na ? <span className="fp-na">{f.stat || "غير متوفّر"}</span>
            : <span className="fp-gauge" data-role="fp-gauge" data-score={gaugeScore(f)}><TrendBar score={gaugeScore(f)} /></span>}
        </span>
        {!na && <ChevronDown size={15} className="fp-more" aria-hidden />}
      </button>
      {open && !na && (
        <div className="fp-detail" data-role="fp-detail">
          <span className="fp-dnum"><span>القوّة</span><b dir="ltr" data-role="fp-strength">{f.strength}</b><span>من 100</span>
            {f.stat && <><span className="fp-dsep" aria-hidden>·</span><b className="fp-stat" dir="ltr">{f.stat}</b></>}</span>
          {f.why.length > 0 && (
            <ul className="fp-why">
              {f.why.map(([d, txt], i) => <li key={i} className={d > 0 ? "pos" : "neg"}><span aria-hidden>{d > 0 ? "▲" : "▼"}</span>{txt}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default function ForcePanels({ trend, liq, compact = false }: { trend: Force | null; liq: Force | null; compact?: boolean }) {
  if (!trend && !liq) return null;
  if (compact) return (
    <div className="fp fp-mini" role="group" aria-label="قوّة الاتجاه والسيولة" data-role="force-panels">
      {trend && <span className={`fp-chip fp-${tone(trend.side)}`} data-role="fp-trend" data-side={trend.side}
        title={`الاتجاه: ${trend.word} · ${trend.level} (${trend.strength}/100)\n${reasons(trend)}`}>
        <Arrow s={trend.side} size={13} /><b>{trend.word}</b>{trend.side !== "flat" && <span>{trend.level}</span>}
        <span className="fp-mg" data-role="fp-gauge"><TrendBar score={gaugeScore(trend)} width={38} /></span></span>}
      {liq && <span className={`fp-chip fp-${tone(liq.side)}`} data-role="fp-liq" data-side={liq.side}
        title={liq.side === "na" ? liq.stat || "" : `السيولة: ${liq.word} · ${liq.level} (${liq.strength}/100)\n${reasons(liq)}`}>
        <Droplets size={13} strokeWidth={2.4} /><b>{liq.side === "na" ? "السيولة غير متوفّرة" : liq.word}</b>
        {liq.side !== "na" && <span className="fp-mg" data-role="fp-gauge"><TrendBar score={gaugeScore(liq)} width={38} /></span>}</span>}
    </div>
  );
  return (
    <div className="fp" role="group" aria-label="قوّة الاتجاه والسيولة" data-role="force-panels">
      {trend && <Card k="قوّة الاتجاه" f={trend} role="fp-trend" icon={<Arrow s={trend.side} size={18} />} />}
      {liq && <Card k="قوّة السيولة" f={liq} role="fp-liq" icon={<Droplets size={18} strokeWidth={2.4} />} />}
    </div>
  );
}
