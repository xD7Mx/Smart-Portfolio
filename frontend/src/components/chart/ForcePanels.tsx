/* ══ لوحتا القوّة فوق الرسم ══ (‏D782 · بأمر المالك 2026-11-21)
   «لوحةُ الملخّص ما عجبتني — أبغاها قويّة… لوحتان مهمّتان: قوّةُ الاتجاه وقوّةُ السيولة… ولوحةُ الأطر نستغني عنها… شيءٌ بسيطٌ وواضح».
   فبدلَ شريط D7M بشاشاته الثماني (القرار · الأطر الأربعة · الحيتان · ‏ADX · المحلّل · التنبيهات · الصفقة) لوحتان: لكلٍّ وجهتُها بسهمها ولونها،
   ودرجتُها بالكلمة والرقم من مئة ومقياسٍ يمتلئ بانسياب، وشاهدُها الأوّل (‏ADX · الحجم النسبيّ)؛ والشواهدُ كلُّها عند المرور. والحسابُ في
   ‏analysis/pulse من شموع الإطار المعروض. وفي الشاشات المتعدّدة سطرٌ واحدٌ صغير لكلّ شاشة. */
import { TrendingUp, TrendingDown, MoveHorizontal, Droplets } from "lucide-react";
import type { Force, Side } from "../analysis/pulse";

const tone = (s: Side) => (s === "up" ? "pos" : s === "down" ? "neg" : s === "flat" ? "warn" : "muted");
const Arrow = ({ s, size }: { s: Side; size: number }) =>
  s === "up" ? <TrendingUp size={size} strokeWidth={2.4} /> : s === "down" ? <TrendingDown size={size} strokeWidth={2.4} /> : <MoveHorizontal size={size} strokeWidth={2.4} />;
const reasons = (f: Force) => f.why.map(([d, t]) => `${d > 0 ? "▲" : "▼"} ${t}`).join("\n");

function Card({ k, f, role, icon }: { k: string; f: Force; role: string; icon: React.ReactNode }) {
  const t = tone(f.side);
  const na = f.side === "na";
  return (
    <div className={`fp-card fp-${t}`} data-role={role} data-side={f.side} title={na ? f.stat || "" : `${k}: ${f.word} · ${f.level} (${f.strength}/100)\n${reasons(f)}`}>
      <span className="fp-ic" aria-hidden>{icon}</span>
      <span className="fp-body">
        <span className="fp-k">{k}</span>
        <span className="fp-v"><b data-role="fp-word">{f.word}</b>{!na && <span className="fp-lv">{f.level}</span>}
          {f.tag && <span className="fp-tag" data-role="fp-tag">{f.tag}</span>}</span>
        <span className="fp-bar" aria-hidden><i style={{ "--v": `${na ? 0 : f.strength}%` } as React.CSSProperties} /></span>
      </span>
      <span className="fp-num">
        {!na && <b dir="ltr" data-role="fp-strength">{f.strength}</b>}
        {f.stat && <span className="fp-stat" dir={na ? undefined : "ltr"}>{f.stat}</span>}
      </span>
    </div>
  );
}

export default function ForcePanels({ trend, liq, compact = false }: { trend: Force | null; liq: Force | null; compact?: boolean }) {
  if (!trend && !liq) return null;
  if (compact) return (
    <div className="fp fp-mini" role="group" aria-label="قوّة الاتجاه والسيولة" data-role="force-panels">
      {trend && <span className={`fp-chip fp-${tone(trend.side)}`} data-role="fp-trend" data-side={trend.side} title={`الاتجاه: ${trend.word} · ${trend.level}\n${reasons(trend)}`}>
        <Arrow s={trend.side} size={13} /><b>{trend.word}</b>{trend.side !== "flat" && <span>{trend.level}</span>}<i dir="ltr">{trend.strength}</i></span>}
      {liq && <span className={`fp-chip fp-${tone(liq.side)}`} data-role="fp-liq" data-side={liq.side} title={liq.side === "na" ? liq.stat || "" : `السيولة: ${liq.word} · ${liq.level}\n${reasons(liq)}`}>
        <Droplets size={13} strokeWidth={2.4} /><b>{liq.side === "na" ? "السيولة غير متوفّرة" : liq.word}</b>{liq.side !== "na" && <i dir="ltr">{liq.strength}</i>}</span>}
    </div>
  );
  return (
    <div className="fp" role="group" aria-label="قوّة الاتجاه والسيولة" data-role="force-panels">
      {trend && <Card k="قوّة الاتجاه" f={trend} role="fp-trend" icon={<Arrow s={trend.side} size={18} />} />}
      {liq && <Card k="قوّة السيولة" f={liq} role="fp-liq" icon={<Droplets size={18} strokeWidth={2.4} />} />}
    </div>
  );
}
