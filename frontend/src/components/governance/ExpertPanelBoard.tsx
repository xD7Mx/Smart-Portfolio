import React from "react";

/* ══ ميزانُ خبراء الحوكمة — مكوّنٌ واحدٌ لا نسختان ══ (D171)
   كان يُرسَم مرّتين بشيفرتين مستقلّتين: نافذةُ قسم الحوكمة (النجمة)
   وتبويبُ التقييم في صفحة السهم. فأُعيد تصميمُ إحداهما وبقيت الأخرى،
   فرأى المالكُ بطاقتين مختلفتين لِميزانٍ واحد.

   ══ ومظهرٌ رسميٌّ لا قائمةَ نقاطٍ مبعثرة ══ (D180 · بأمر المالك)
   الميزانُ **جدولُ قراءاتٍ** لا سطورَ ملاحظات: لكلّ معيارٍ اسمٌ وقراءةٌ
   وحكم. فصار ثلاثةَ أعمدةٍ محاذاةً واحدة، بخطٍّ فاصلٍ رفيعٍ بين الصفوف
   يفصل ولا يزخرف، وأرقامٍ جدوليّةٍ تصطفّ عمودياً — كما تُقرأ نشرةُ
   بيت خبرة.

   والحالةُ تُقرأ من **موضعها** لا من نقطةٍ ملوّنة وحدَها: شريطٌ رأسيٌّ
   رفيعٌ على حافّة الصفّ، والحكمُ بلونه في الطرف. والنقطةُ حُذفت — كانت
   تكرّر ما يقوله اللونُ نفسُه مرّتين في السطر الواحد.

   والعقوباتُ قسمٌ مستقلّ بعنوانه: جملةٌ تشرح سبباً لا تصلح صفّاً في
   جدول، وخلطُها بالقراءات هو الذي جعل البطاقةَ تُقرأ فوضى. */

const TONE: Record<string, string> = {
  green: "var(--pos-ink)", yellow: "var(--warn-ink)",
  red: "var(--neg-ink)", na: "var(--ink-muted)",
};

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-bold tracking-[0.06em] text-[var(--ink-muted)] mb-2">
      {children}
    </p>
  );
}

export default function ExpertPanelBoard({ panel }: { panel: any[] }) {
  const rows = Array.isArray(panel) ? panel : [];
  const drivers = rows.filter(e => e?.role === "driver");
  const readings = rows.filter(e => e?.role !== "driver");
  if (!rows.length) return null;

  return (
    <div className="space-y-4">
      {readings.length > 0 && (
        <div>
          <SectionTitle>قراءات المعايير</SectionTitle>
          {/* ══ شبكةٌ واحدةٌ للجدول كلِّه لا شبكةٌ لكلّ صفّ ══
              كانت كلُّ قراءةٍ شبكةً مستقلّة بعمودَي `auto`، فيقيس كلُّ صفٍّ
              عمودَه بمحتواه وحدَه — فلا تتحاذى الأرقامُ ولا الأحكام، وتُقرأ
              الجدولةُ اهتزازاً. والشبكةُ الواحدة تقيس العمودَ بأعرض ما فيه
              فتصطفّ الأعمدةُ الأربعةُ عبر الصفوف كلِّها. */}
          <div className="grid items-baseline gap-x-3 text-[11.5px]"
               style={{ gridTemplateColumns: "2px minmax(0,1fr) auto auto" }}>
            {readings.map((e: any, i: number) => {
              const c = TONE[e.tone] || "var(--ink-muted)";
              const line = i === 0 ? {} : { borderTop: "1px solid var(--hairline)" };
              return (
                <React.Fragment key={i}>
                  {/* شريطٌ رفيعٌ يحمل الحالة — لا نقطةٌ تكرّر لونَ الحكم */}
                  <span className="self-stretch rounded-full my-1.5"
                        style={{ background: c, opacity: 0.75, ...line, borderTop: undefined }} />
                  <span className="text-[var(--ink)] truncate py-2" style={line}>{e.metric}</span>
                  <span className="tabular-nums whitespace-nowrap text-[var(--ink-muted)] py-2"
                        dir="ltr" style={line}>{e.reading}</span>
                  <span className="whitespace-nowrap font-semibold py-2"
                        style={{ color: c, ...line }}>{e.verdict}</span>
                </React.Fragment>
              );
            })}
          </div>
        </div>
      )}

      {drivers.length > 0 && (
        <div>
          <SectionTitle>ما خفض الدرجة</SectionTitle>
          <div className="space-y-1.5">
            {drivers.map((e: any, i: number) => {
              const c = TONE[e.tone] || "var(--ink-muted)";
              return (
                <div key={i} className="flex items-start gap-2.5 text-[11.5px] leading-relaxed">
                  <span className="w-[2px] self-stretch rounded-full shrink-0 mt-0.5"
                        style={{ background: c, opacity: 0.75 }} />
                  <span className="text-[var(--ink)]">{e.verdict}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
