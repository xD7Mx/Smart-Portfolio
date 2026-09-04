import React from "react";

/* ══ ميزانُ خبراء الحوكمة — مكوّنٌ واحدٌ لا نسختان ══ (D171)
   كان يُرسَم مرّتين بشيفرتين مستقلّتين: نافذةُ قسم الحوكمة (النجمة)
   وتبويبُ التقييم في صفحة السهم. فأُعيد تصميمُ إحداهما وبقيت الأخرى،
   فرأى المالكُ بطاقتين مختلفتين لِميزانٍ واحد.

   والصفّان لا صفٌّ واحد: قراءةُ مؤشّرٍ (اسمٌ · رقمٌ · حكمٌ من كلمتين)
   وعقوبةٌ اشتعلت (جملةٌ تشرح سبباً) لا يجتمعان في عمودٍ واحدٍ إلّا
   تمزّقت المحاذاة. */

const TONE: Record<string, string> = {
  green: "var(--pos-ink)", yellow: "var(--warn-ink)",
  red: "var(--neg-ink)", na: "var(--ink-muted)",
};

export default function ExpertPanelBoard({ panel }: { panel: any[] }) {
  const rows = Array.isArray(panel) ? panel : [];
  const drivers = rows.filter(e => e?.role === "driver");
  const readings = rows.filter(e => e?.role !== "driver");
  if (!rows.length) return null;

  return (
    <>
      {readings.length > 0 && (
        <div className="mb-3">
          <p className="text-[10px] text-[var(--ink-muted)] mb-1.5">قراءات المعايير</p>
          <div className="grid gap-x-3 gap-y-1.5 items-center text-[11px]"
               style={{ gridTemplateColumns: "auto minmax(0,1fr) auto auto" }}>
            {readings.map((e: any, i: number) => (
              <React.Fragment key={i}>
                <span className="inline-block w-2 h-2 rounded-full"
                      style={{ background: TONE[e.tone] || "var(--ink-muted)" }} />
                <span className="text-[var(--ink)] truncate">{e.metric}</span>
                <span className="text-[var(--ink-muted)] tabular-nums whitespace-nowrap" dir="ltr">{e.reading}</span>
                <span className="font-medium whitespace-nowrap"
                      style={{ color: TONE[e.tone] || "var(--ink-muted)" }}>{e.verdict}</span>
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {drivers.length > 0 && (
        <div>
          <p className="text-[10px] text-[var(--ink-muted)] mb-1.5">ما خفض الدرجة</p>
          <ul className="space-y-1">
            {drivers.map((e: any, i: number) => (
              <li key={i} className="flex items-start gap-2 text-[11px] leading-relaxed">
                <span className="inline-block w-2 h-2 rounded-full shrink-0 mt-1.5"
                      style={{ background: TONE[e.tone] || "var(--ink-muted)" }} />
                <span style={{ color: TONE[e.tone] || "var(--ink-muted)" }}>{e.verdict}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
