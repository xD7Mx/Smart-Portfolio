/**
 * Smart Portfolio brand mark — rising bars forming an upward arrow inside a
 * gradient squircle. Unique identity, not an admin-template icon.
 */
import React from "react";

/* ‏D667: `flat` بلا هالة — حين تملأ العلامةُ مكانَ شعارٍ غائبٍ داخل بطاقة (بأمر المالك: «إذا لم يوجد شعار ضع أيقونة التطبيق
   ليملأ فراغ الشعار»)؛ والهالةُ للترويسة وحدها. */
export default function Logo({ size = 36, flat = false }: { size?: number; flat?: boolean }) {
  return (
    <div
      className="shrink-0 flex items-center justify-center"
      style={{
        width: size, height: size, borderRadius: size * 0.3,
        background: "linear-gradient(135deg,#2563eb 0%,#6d28d9 60%,#9333ea 100%)",
        boxShadow: flat ? "inset 0 1px 1px rgba(255,255,255,.25)" : "0 0 22px rgba(79,70,229,.45), inset 0 1px 1px rgba(255,255,255,.25)",
      }}>
      <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 24 24" fill="none">
        {/* rising bars */}
        <rect x="3.2" y="13.5" width="3.6" height="7.5" rx="1.2" fill="rgba(255,255,255,.55)" />
        <rect x="9"   y="9.5"  width="3.6" height="11.5" rx="1.2" fill="rgba(255,255,255,.8)" />
        <rect x="14.8" y="5.5" width="3.6" height="15.5" rx="1.2" fill="#ffffff" />
        {/* spark */}
        <path d="M17.2 2.2l.75 1.55 1.55.75-1.55.75-.75 1.55-.75-1.55-1.55-.75 1.55-.75z" fill="#fde047" />
      </svg>
    </div>
  );
}
