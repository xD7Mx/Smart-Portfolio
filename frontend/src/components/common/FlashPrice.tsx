import React, { useEffect, useRef, useState } from "react";
import { isTasiOpen } from "../../utils/marketHours";

/**
 * Flashes green/red behind a price the instant it changes between two
 * automatic refreshes — the same "ticker" feel as live trading apps.
 * Only while Tadawul is actually open — prices don't move after the close.
 */
export default function FlashPrice({ value, children, className = "", style }:
  { value: number | null | undefined; children: React.ReactNode; className?: string; style?: React.CSSProperties }) {
  const prev = useRef<number | null | undefined>(value);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    if (isTasiOpen() && value != null && prev.current != null && value !== prev.current) {
      setFlash(value > prev.current ? "up" : "down");
      const id = setTimeout(() => setFlash(null), 900);
      prev.current = value;
      return () => clearTimeout(id);
    }
    prev.current = value;
  }, [value]);

  return (
    <span
      className={className}
      style={{
        // نمطُ المستدعي أوّلاً (اللون مثلاً) ثم يبقى الوميض فوقه: العكس كان
        // يلغي وميض التغيّر السعري.
        ...style,
        transition: "background-color .9s ease, color .9s ease",
        /* من الرموز لا من قيمٍ مكتوبة: وميض السعر كان على درجتين
           هجرهما التطبيق، فيومض بلونٍ يخالف الرقم الذي يومض تحته. */
        backgroundColor: flash === "up" ? "color-mix(in srgb, var(--pos-ink) 28%, transparent)"
          : flash === "down" ? "color-mix(in srgb, var(--neg-ink) 28%, transparent)" : "transparent",
        borderRadius: 6,
        padding: flash ? "1px 4px" : "1px 0",
        // الهامش السالب يعوّض حشوة الوميض فلا يقفز الرقم عند التغيّر. لكنّه
        // يُخرج الرقم أربع نقاطٍ خارج حدّ خانته، فيبدو غير محاذٍ لتسميته في
        // شبكة البطاقة — فيستطيع المستدعي تصفيره حين تكون المحاذاة أهمّ.
        margin: style?.margin ?? "-1px -4px",
      }}
    >
      {children}
    </span>
  );
}
