import React from "react";

/* ══ شعارُ تداول — الرمزُ وحدَه بلا كلمة ══ (بأمر المالك · D184)
   كان لسانُ تاسي يحمل رمزَ **طور الجلسة** (مفتوح · قبل الإغلاق · مغلق)،
   فأمر المالكُ بوضع شعار تداول مكانَه. والطورُ لم يضِع: يبقى في تلميحة
   اللسان ونصّه المسموع.

   الهندسةُ منقولةٌ حرفياً من ملفّ المالك (‏Illustrator SVG): ثلاثةُ مثلّثات
   بين ‎x=498 و‎675.94 و‎y=199.67 و‎377.6 — نُقلت إلى مبدأ الإحداثيات
   ومساحةٍ ‎178×178، ولم يُمسّ شكلٌ ولا لون.

   والتدرّجُ يحتاج معرّفاً **فريداً لكلّ نسخة**: معرّفٌ ثابتٌ يتصادم متى
   رُسم الشعارُ مرّتين في صفحةٍ واحدة، فيرث الثاني تدرّجَ الأول أو يفقده. */

const GREEN = "#73BF44";
const BLUE = "#01A4DE";

let _seq = 0;

export default function TadawulMark({ size = 14, title }: { size?: number; title?: string }) {
  const gid = React.useMemo(() => `tdwl-g-${++_seq}`, []);
  return (
    <svg width={size} height={size} viewBox="0 0 177.91 177.93"
         role="img" aria-label={title || "تداول"} className="shrink-0">
      {title && <title>{title}</title>}
      <defs>
        <linearGradient id={gid} gradientUnits="userSpaceOnUse"
                        x1="133.46" y1="0" x2="133.46" y2="88.98">
          <stop offset="0" stopColor="#00476D" />
          <stop offset="0.22" stopColor="#0B5F89" />
          <stop offset="0.445" stopColor="#1576A5" />
          <stop offset="0.6567" stopColor="#1888BD" />
          <stop offset="0.8477" stopColor="#1795CE" />
          <stop offset="1" stopColor="#149BD7" />
        </linearGradient>
      </defs>
      <polygon fill={GREEN} points="88.95,88.98 0.03,88.98 88.95,0" />
      <polygon fill={BLUE} points="88.95,88.98 88.95,177.93 177.91,88.98 177.91,0" />
      <polygon fill={`url(#${gid})`} points="88.95,0 177.91,0 88.95,88.98" />
    </svg>
  );
}
