import React from "react";

/* ══ أيقونةُ حال السوق — شكلٌ لكلّ طور ══ (بأمر المالك)

   كانت الأيقونةُ واحدةً تتلوّن: موجاتُ بثٍّ في كلّ طورٍ مفتوح، واللونُ
   وحده يفرّق بين «قبل الافتتاح» و«السوق مفتوح» و«قبل الإغلاق». واللونُ
   وحدَه أضعفُ حاملٍ للمعنى: من لا يميّز البرتقاليَّ من الأزرق يرى
   الأطوارَ الثلاثة طوراً واحداً. فصار **الشكلُ** يحمل الطور واللونُ
   يؤكّده:

     · قبل الافتتاح — نقطةٌ برتقالية **تومض**: شيءٌ على وشك أن يبدأ.
     · السوق مفتوح  — مصدرٌ ثابت وموجتان تخرجان منه فتتلاشيان: بثٌّ حيّ.
     · قبل الإغلاق  — **هلالٌ** أزرق: قوسٌ ناقص، والنقصانُ هو المعنى.
     · مغلق         — قرصٌ أحمر بشرطةٍ بيضاء: علامةُ منعٍ تُفهم بلا شرح.

   والحركةُ تحترم `prefers-reduced-motion`: من طلب سكونَ الواجهة يرى
   الموجاتِ والنقطةَ ثابتةً ظاهرة، لا وميضاً.
*/

export type BroadcastPhase = "pre" | "open" | "preclose" | "closed";

export default function BroadcastIcon({ size = 13, color, live = true,
  phase, title }: {
    size?: number; color?: string; live?: boolean;
    phase?: BroadcastPhase; title?: string;
  }) {
  // `live` يبقى للتوافق مع مواضع لا تعرف الطور (خام برنت مثلاً).
  const ph: BroadcastPhase = phase || (live ? "open" : "closed");
  // المعرّفُ يُطلب في كل رسمةٍ لا في فرعٍ منها: قواعدُ الخطّافات تمنع
  // النداءَ المشروط، وقناعُ الهلال يحتاج معرّفاً فريداً لكل نسخةٍ من
  // الأيقونة وإلا تشاركت النسخُ قناعاً واحداً.
  const uid = React.useId().replace(/:/g, "");
  const stroke = color || "currentColor";

  if (ph === "closed") {
    /* ══ أصغرُ ما يُقرأ ══ (بأمر المالك: «صغّرها لآخر حجمٍ تقدر عليه»)
       الحدُّ ليس ذوقاً بل قابليةَ قراءة: الشرطةُ داخل القرص يجب أن تبقى
       بيّنة. فرُسمت في مربّعٍ ‎16 بدل ‎24 — نسبةُ الشرطة إلى القرص أكبر —
       ويُرسم بتسعة بكسلات بدل ثلاثةَ عشر. */
    const s = Math.max(8, Math.round(size * 0.7));
    return (
      <svg width={s} height={s} viewBox="0 0 16 16" aria-hidden="true"
        className="shrink-0" role={title ? "img" : undefined}>
        {title && <title>{title}</title>}
        {/* الأحمرُ من رمز التطبيق لا قيمةً ثابتة، والشرطةُ من ورقه
            (‏--bg) لا بياضاً مطلقاً — فتبقى مقروءةً في المظهرين. */}
        <circle cx="8" cy="8" r="7" fill="var(--neg-ink)" />
        <rect x="3.6" y="6.9" width="8.8" height="2.2" rx="1.1" fill="var(--bg)" />
      </svg>
    );
  }

  if (ph === "pre") {
    // وميضٌ برتقاليّ: نقطةٌ واحدة تظهر وتخفت — لا موجاتٍ، فلا بثَّ بعد.
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true"
        className="shrink-0 bcast" role={title ? "img" : undefined}>
        {title && <title>{title}</title>}
        <circle className="bcast-blink" cx="12" cy="12" r="5.2" fill={stroke} />
      </svg>
    );
  }

  if (ph === "preclose") {
    /* هلالٌ: قرصٌ يُقتطع منه قرصٌ آخر مزاح — والقوسُ الناقص هو المعنى.
       والاقتطاعُ بقناعٍ لا بقرصٍ بلون الخلفية، فتبقى الأيقونة سليمةً
       فوق أيّ سطحٍ لا فوق `--bg` وحده. */
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true"
        className="shrink-0" role={title ? "img" : undefined}>
        {title && <title>{title}</title>}
        <mask id={`crv-${uid}`}>
          <rect width="24" height="24" fill="#000" />
          <circle cx="12" cy="12" r="9.4" fill="#fff" />
          <circle cx="17.2" cy="9.4" r="8.4" fill="#000" />
        </mask>
        <rect width="24" height="24" fill={stroke} mask={`url(#crv-${uid})`} />
      </svg>
    );
  }

  // مفتوح: المصدرُ ثابت والموجاتُ تتدرّج ظهوراً واختفاءً.
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={stroke} strokeWidth={2.2} strokeLinecap="round"
      className="shrink-0 bcast" role={title ? "img" : undefined}>
      {title && <title>{title}</title>}
      {/* المركزُ ثابتٌ لا يومض */}
      <circle cx="12" cy="12" r="2.4" fill={stroke} stroke="none" />
      {/* موجتان داخليتان ثم خارجيتان — يمنةً ويسرةً */}
      <g className="bcast-w1">
        <path d="M7.8 8.6a6 6 0 0 0 0 6.8" />
        <path d="M16.2 8.6a6 6 0 0 1 0 6.8" />
      </g>
      <g className="bcast-w2">
        <path d="M4.6 5.9a10 10 0 0 0 0 12.2" />
        <path d="M19.4 5.9a10 10 0 0 1 0 12.2" />
      </g>
    </svg>
  );
}
