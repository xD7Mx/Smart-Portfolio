/* ══ شعارُ صقر — رأسُ صقرٍ آليٍّ ينظر إلى الأمام ══ (‏D764 بأمر المالك 2026-11-18)
   «اعتمد هذا العمل الاحترافي الآليّ حتى يُبرز ملامحَ صقر… أبغى وجهَه للأمام كأنه يطالع إلى الأمام مثل الروبوت… لا أحبّ أيقونةَ الطائر —
   لازم شيءٌ فيه هيبةٌ ونظراتٌ حادّة ودقّة، يُبرز ما يفعله حين يختار بدقّةٍ وينقضّ بدقّة».
   فالرأسُ من تصميم المالك (معدنٌ فضّيٌّ بريشٍ مدبّب ودوائرُ زرقاءُ مضيئة وعينٌ كهرمانية) مرسوماً من الأمام: نصفٌ يُرسم ونصفٌ يعكسه فيتطابق
   الوجهُ تماماً، وحاجبان على هيئة V يلتقيان فوق المنقار فتحتدّ النظرة، ومنقارٌ معقوفٌ في المحور، وطوقٌ بقلبٍ مضيء. والألوانُ رموزٌ
   (‏--sq-*) معرّفةٌ للمظهرين؛ والعينان تتوهّجان والدوائرُ تتنفّس حين يعمل — وتسكن مع تفضيل تقليل الحركة. */
import { useId } from "react";

export default function SaqrEmblem({ size = 64, live = false, className = "" }: { size?: number; live?: boolean; className?: string }) {
  const u = useId().replace(/:/g, "");
  const id = (k: string) => `sqe-${u}-${k}`;
  const url = (k: string) => `url(#${id(k)})`;
  return (
    <svg viewBox="0 0 240 262" width={size} height={size * 262 / 240} role="img" aria-label="صقر"
      className={"sqe" + (live ? " live" : "") + (className ? " " + className : "")} data-role="sq-emblem">
      <defs>
        <linearGradient id={id("shell")} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="var(--sq-steel-lo)" />
          <stop offset=".55" stopColor="var(--sq-steel-mid)" />
          <stop offset="1" stopColor="var(--sq-steel-hi)" />
        </linearGradient>
        <linearGradient id={id("crown")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--sq-steel-hi)" />
          <stop offset="1" stopColor="var(--sq-steel-mid)" stopOpacity="0" />
        </linearGradient>
        <linearGradient id={id("spike")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--sq-steel-mid)" />
          <stop offset="1" stopColor="var(--sq-steel-lo)" />
        </linearGradient>
        <linearGradient id={id("plate")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--sq-steel-lo)" />
          <stop offset="1" stopColor="var(--sq-plate)" />
        </linearGradient>
        <linearGradient id={id("beak")} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="var(--sq-beak-lo)" />
          <stop offset=".5" stopColor="var(--sq-beak-hi)" />
          <stop offset="1" stopColor="var(--sq-beak-lo)" />
        </linearGradient>
        <radialGradient id={id("eye")} cx=".58" cy=".45" r=".7">
          <stop offset="0" stopColor="var(--sq-eye)" />
          <stop offset="1" stopColor="var(--sq-eye-deep)" />
        </radialGradient>
        <filter id={id("glow")} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.2" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        {/* نصفُ الوجه الأيسر — والأيمنُ انعكاسُه */}
        <g id={id("half")}>
          {/* ريشُ العنق المدبّب خلف الرأس */}
          <g fill={url("spike")} stroke="var(--sq-seam)" strokeWidth="1.2" strokeLinejoin="round">
            <path d="M52 118 L8 170 L62 150 Z" />
            <path d="M70 148 L24 214 L82 184 Z" />
            <path d="M80 164 L42 238 L96 198 Z" />
            <path d="M94 178 L70 254 L108 208 Z" />
            <path d="M104 188 L98 260 L118 214 Z" />
          </g>
          {/* الخوذة: تاجٌ مسطّحٌ زاويّ (لا قبّةُ بومة) يضيق نحو المنقار — والحدُّ الخارجيّ وحدَه مرسوم فلا خطَّ في المحور */}
          <path d="M120 30 L92 32 L64 42 C50 52 40 66 36 82 L34 104 C37 122 46 136 62 148 L92 168 L120 182 Z" fill={url("shell")} />
          <path d="M120 30 L92 32 L64 42 C50 52 40 66 36 82 L34 104 C37 122 46 136 62 148 L92 168 L120 182" fill="none" stroke="var(--sq-seam)" strokeWidth="1.6" strokeLinejoin="round" />
          <path d="M120 30 L92 32 L64 42 C54 49 47 58 42 68 L120 62 Z" fill={url("crown")} opacity=".5" />
          {/* ريشُ القمّة المنتصب — حدّةُ الصقر لا استدارةُ البومة */}
          <g fill={url("spike")} stroke="var(--sq-seam)" strokeWidth="1.1" strokeLinejoin="round">
            <path d="M66 44 L46 22 L80 37 Z" />
            <path d="M88 33 L80 12 L102 31 Z" />
            <path d="M44 70 L18 56 L40 82 Z" />
          </g>
          {/* ريشُ التاج صفائحُ مدبّبةٌ متراكبة */}
          <g fill="none" stroke="var(--sq-seam)" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" opacity=".85">
            <path d="M118 42 L96 45 L76 55" />
            <path d="M117 56 L95 60 L70 70" />
            <path d="M88 34 L74 46 L64 60" />
            <path d="M62 46 L52 60 L44 76" />
          </g>
          <g fill="none" stroke="var(--sq-steel-hi)" strokeWidth=".9" strokeLinecap="round" opacity=".5">
            <path d="M116 45 L96 48 L80 56" />
            <path d="M86 37 L74 48 L67 58" />
          </g>
          {/* صفيحةُ الخدّ */}
          <path d="M36 108 L48 130 L68 146 L94 152 L84 134 L62 127 Z" fill="var(--sq-steel-mid)" stroke="var(--sq-seam)" strokeWidth="1.2" strokeLinejoin="round" opacity=".92" />
          {/* محجرُ العين تحت الحاجب، والعينُ الكهرمانيةُ مائلةٌ نحو المنقار */}
          <path d="M44 90 L76 92 L102 101 L110 110 L100 119 L74 117 L52 106 Z" fill="var(--sq-seam)" />
          <path className="sqe-iris" d="M52 96 L76 97 L98 104 L103 109 L95 113 L75 112 L58 105 Z" fill={url("eye")} filter={url("glow")} />
          <circle cx="82" cy="105.5" r="4.2" fill="var(--sq-pupil)" />
          <circle cx="79.8" cy="103.2" r="1.3" fill="var(--sq-steel-hi)" />
          <path d="M51 96 L76 97 L98 104 L104 110" fill="none" stroke="var(--sq-seam)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          {/* الحاجبُ: صفيحةٌ ثقيلةٌ تنحدر نحو المنقار وتظلّل العينَ — حدّةُ النظرة */}
          <path d="M120 92 L100 78 L74 70 L50 72 L37 82 L52 90 L77 92 L100 102 L112 110 Z" fill={url("plate")} stroke="var(--sq-seam)" strokeWidth="1.4" strokeLinejoin="round" />
          {/* خطوطُ الدوائر المضيئة */}
          <g className="sqe-glow" fill="none" stroke="var(--sq-glow)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" filter={url("glow")}>
            <path d="M118 91 L100 79 L74 71 L51 73 L39 82" />
            <path d="M40 118 L52 134 L78 140" />
            <path d="M44 90 L38 102" />
            <circle cx="78" cy="140" r="1.9" fill="var(--sq-glow)" />
          </g>
          {/* حدُّ الفمّ */}
          <path d="M99 134 C95 143 91 149 86 153" fill="none" stroke="var(--sq-seam)" strokeWidth="2" strokeLinecap="round" />
        </g>
      </defs>
      <use href={`#${id("half")}`} />
      <use href={`#${id("half")}`} transform="translate(240 0) scale(-1 1)" />
      {/* المنقارُ المعقوف في المحور، وعلى قاعدته الشمعُ (‏cere) بشقّين — لا انحناءةَ تُقرأ ابتسامة */}
      <path d="M120 94 C109 98 99 109 97 128 C96 148 104 168 114 186 L120 212 L126 186 C136 168 144 148 143 128 C141 109 131 98 120 94 Z"
        fill={url("beak")} stroke="var(--sq-seam)" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M120 116 L120 196" stroke="var(--sq-steel-hi)" strokeWidth="1.3" opacity=".5" />
      <path d="M104 106 Q120 98 136 106 L132 117 Q120 111 108 117 Z" fill={url("plate")} stroke="var(--sq-seam)" strokeWidth="1.2" strokeLinejoin="round" />
      <path d="M110 110 L115 113 M130 110 L125 113" fill="none" stroke="var(--sq-glow)" strokeWidth="1.6" strokeLinecap="round" className="sqe-glow" />
      <path d="M113 186 L120 212 L127 186 Q120 195 113 186 Z" fill="var(--sq-seam)" />
      {/* الطوقُ وقلبُه المضيء */}
      <path d="M90 206 L120 214 L150 206 L141 230 L120 237 L99 230 Z" fill={url("plate")} stroke="var(--sq-seam)" strokeWidth="1.3" strokeLinejoin="round" />
      <circle cx="120" cy="223" r="9.5" fill="var(--sq-seam)" stroke="var(--sq-glow)" strokeWidth="2.4" className="sqe-glow" filter={url("glow")} />
      <circle cx="120" cy="223" r="4.6" fill="var(--sq-glow)" className="sqe-core" filter={url("glow")} />
    </svg>
  );
}
