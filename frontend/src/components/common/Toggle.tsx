import React from "react";

/* ══ مفتاحٌ واحدٌ للتطبيق ══ (بأمر المالك · D678: «سيطر على التصاميم الشاذّة ووحّد هويّتها في كلّ مكان»)
   كان التطبيقُ يرسم المفتاحَ بأربع طرق: صندوقُ اختيار المتصفّح (رماديٌّ بلون النظام)، ومربّعٌ بلون `accent`، ومفتاحُ
   التطبيق `.switch` مرّتين بطريقتين. فصار مكوّناً واحداً: زرٌّ بدور `switch` يحمل مفتاحَ التطبيق وتسميتَه، بهدف لمسٍ ≥ 32px. */
export default function Toggle({ checked, onChange, label, disabled, className = "" }: {
  checked: boolean; onChange: (v: boolean) => void; label?: React.ReactNode; disabled?: boolean; className?: string;
}) {
  return (
    <button type="button" role="switch" aria-checked={checked} disabled={disabled} onClick={() => onChange(!checked)}
      className={"flex items-center gap-2 min-h-[32px] text-[12px] text-[var(--ink)] disabled:opacity-50 select-none " + className}>
      <span aria-hidden className={"switch inline-block" + (checked ? " on" : "")} />
      {label != null && <span className="text-start">{label}</span>}
    </button>
  );
}
