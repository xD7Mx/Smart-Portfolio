import React from "react";
import { Check } from "lucide-react";

/* ══ صندوقُ اختيارٍ بهويّة التطبيق ══ (‏D678) — بديلُ `<input type="checkbox">` الذي يرسمه نظامُ الجهاز بلونه وحجمه.
   مربّعٌ بحوافّ التطبيق، يمتلئ بلون الهويّة وعلامةٍ بيضاء حين يُختار؛ والزرُّ كلُّه هدفُ اللمس (≥ 32px). */
export default function CheckBox({ checked, onChange, label, disabled, className = "", align = "center", "aria-label": aria }: {
  checked: boolean; onChange: (v: boolean) => void; label?: React.ReactNode; disabled?: boolean; className?: string;
  align?: "center" | "start"; "aria-label"?: string;
}) {
  return (
    <button type="button" role="checkbox" aria-checked={checked} aria-label={aria} disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`flex ${align === "start" ? "items-start" : "items-center"} gap-2 min-h-[32px] min-w-[32px] text-start select-none disabled:opacity-50 ${className}`}>
      <span aria-hidden className={`shrink-0 grid place-items-center w-[18px] h-[18px] rounded-[5px] transition-colors${align === "start" ? " mt-0.5" : ""}`}
        style={checked ? { background: "var(--brand)", border: "1px solid var(--brand)" }
                       : { background: "var(--field)", border: "1px solid var(--line)" }}>
        {checked && <Check size={12} strokeWidth={3} color="#fff" />}
      </span>
      {label != null && <span className="min-w-0">{label}</span>}
    </button>
  );
}
