import React, { useEffect, useRef, useState } from "react";
import { getMarketStatus, getBrentStatus, tasiPhase } from "../../utils/marketHours";
import BroadcastIcon, { BroadcastPhase } from "./BroadcastIcon";

/** Real market-hours indicator (Tadawul by default, Brent when market="brent"):
 * a solid green pulsing dot while open; a neutral gray ring with a small dash
 * inside once closed (not red — "closed" is the normal state, not an alarm).
 * Hover shows the honest detail (time remaining / holiday / break). */
export default function MarketStatusDot({ withLabel = false, className = "", market = "tasi", tappable = false }:
  { withLabel?: boolean; className?: string; market?: "tasi" | "brent"; tappable?: boolean }) {
  /* ══ أيقونة البثّ بدل النقطة ══ (بأمر المالك)
     الأيقونة نفسها التي في شريط الأخبار (`Radio` — موجاتُ بثّ)، ولونها
     يقول الطور: أخضرُ مفتوح · برتقاليّ قبل الافتتاح · أزرقُ قبل الإغلاق.
     والأطوارُ من `tasiPhase` لا من `getMarketStatus`: الثانية بطورين
     فقط، فكانت النقطة **عاجزةً** عن التلوّن بالطورين الانتقاليّين لا
     ممتنعة — مصدرها لا يحملهما أصلاً. */
  const s = market === "brent" ? getBrentStatus() : getMarketStatus();
  const phase = market === "brent" ? null : tasiPhase();
  const isOpen = s.status === "open";
  const tone = phase && phase.key !== "closed" ? phase.color
             : isOpen ? s.color : "var(--ink-muted)";
  const label = phase ? phase.label : s.label;
  const live = phase ? phase.key !== "closed" : isOpen;
  // على الجوال لا يوجد «مرور بالمؤشّر» فلا تظهر التفاصيل — الضغط يُظهر
  // ملاحظة صغيرة تشرح الحالة ثم تختفي تلقائياً.
  const [note, setNote] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  const showNote = (e: React.MouseEvent) => {
    if (!tappable) return;
    e.stopPropagation();
    setNote(true);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setNote(false), 3000);
  };
  return (
    <span className={`relative inline-flex items-center gap-1.5 ${className}`} title={`${label} — ${s.detail}`}
      onClick={showNote} role={tappable ? "button" : undefined}>
      {note && (
        <span className="absolute top-full mt-1.5 start-1/2 -translate-x-1/2 z-40 whitespace-nowrap rounded-lg px-2.5 py-1.5 text-[11px] shadow-xl fade-in"
          style={{ background: "var(--bg)", border: "1px solid var(--field-line)", color: "var(--ink)" }}>
          <span className="font-bold" style={{ color: tone }}>{label}</span>
          <span className="opacity-80"> — {s.detail}</span>
        </span>
      )}
      {/* المركزُ ثابتٌ والموجاتُ تتدرّج (بأمر المالك)، وعند الإغلاق قرصٌ
          أحمر بشرطةٍ بيضاء — الحالةُ نفسها في كل موضعٍ تظهر فيه. */}
      <BroadcastIcon size={13} color={tone} live={live} title={label}
        phase={phase ? (phase.key as BroadcastPhase) : undefined} />
      {withLabel && <span className="text-xs font-bold" style={{ color: tone }}>{label}</span>}
    </span>
  );
}
