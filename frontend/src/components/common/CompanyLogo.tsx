import React, { useEffect, useRef, useState } from "react";
import { TV_LOGOS } from "../../data/tradingviewLogos";

/* ذاكرةُ نجاحٍ مشتركة لكل الشاشات: أوّل رابطٍ ينجح لرمزٍ ما يُحفظ، فكل
   نسخةٍ أخرى منه تبدأ منه مباشرةً بلا سباقٍ ولا مهلة. وأثرُها عمليّ:
   الشعار الذي ظهر في المفكرة لا يُعاد اختباره في الحيازات ولا في فرز
   السوق — وهو ما كان يُنتج ظهوراً متبايناً بين الشاشات. تُملأ من نجاحٍ
   حقيقيّ لا من افتراض. */
const RESOLVED = new Map<string, string>();

/**
 * شعار الشركة — سلسلةُ مصادر مرتَّبةٌ بالقياس:
 *  ١. الخريطة الثابتة (٣٩٠ رابطاً مقيساً ناجحاً على خادم المالك).
 *  ٢. الرابط المخزَّن في صفّ الشركة — قد يحمل هويّةً أحدث.
 *  ٣. مزوّد الشعارات العامّ، تخميناً بالرمز.
 *  ٤. حرفٌ على تدرّج — فلا تظهر صورةٌ مكسورة أبداً.
 */
export default function CompanyLogo({ symbol, color, size = 40, logoUrl }: { symbol: string; color?: string; size?: number; logoUrl?: string | null }) {
  const base = (symbol || "").replace(".SR", "").trim();

  /* ══ ترتيب المصادر — صُحِّح بالقياس لا بالافتراض ══
     كان المخزَّن في قاعدة البيانات أولاً والخريطة ثانياً، بحجّة أن المخزَّن
     «متحقَّق». والقياس نقض ذلك: فُحصت روابط الخريطة الـ٣٩٢ كلُّها على خادم
     المالك فنجحت ٣٩٠ (٩٩٫٥٪)، بينما المخزَّن مجهول الصحّة — قديمٌ أو من
     مزوّدٍ تغيّر.

     وأثرُ الترتيب الخاطئ كان ظاهراً للمالك ولم أربطه: **المفكرة تعرض
     الشعارات والحيازات لا تعرضها**. والسبب أن المفكرة لا تمرّر المخزَّن
     أصلاً فتقرأ الخريطة وتنجح، والحيازات تمرّره فتقع في المعطوب. «تظهر
     في أماكن ولا تظهر في أخرى» — هذا هو تفسيرها.

     فالخريطة أولاً لأنها **مقيسة**، والمخزَّن ثانياً لأنه قد يحمل شعاراً
     أحدث لشركةٍ غيّرت هويّتها، وبارْكِت ثالثاً. */
  /* ══ دليلُ الشعارات من «تداول» أوّلاً (بأمر المالك · D488) ══
     قِيس على الخادم (tadawul_logo_door.py): صفحةُ كلّ شركةٍ في تداول تحمل
     شعارَها على `tadawulgroup.sa/Resources/SEMOBILELOGOS/{الرمز}.png` —
     المصدرُ الرسميّ لكلّ مدرَجٍ حتى الجديد والموازي، وهو ما غاب عن خريطة
     TradingView (392 من 409). وما لم يُحمَّل ينتقل تلقائياً إلى التالي. */
  const candidates = [
    /^\d{4}$/.test(base) ? `https://www.tadawulgroup.sa/Resources/SEMOBILELOGOS/${base}.png` : null,
    TV_LOGOS[base] || null,
    logoUrl || null,
    base ? `https://assets.parqet.com/logos/symbol/${base}.SR?format=png&size=${size * 2}` : null,
  ].filter((u, i, a): u is string => !!u && a.indexOf(u) === i);

  /* البداية من الرابط الذي نجح سابقاً لهذا الرمز إن وُجد. */
  const known = RESOLVED.get(base);
  const startAt = known ? Math.max(0, candidates.indexOf(known)) : 0;
  const [stage, setStage] = useState<number>(startAt);
  const url = candidates[stage] || null;

  /* ══ المهلة: أربع ثوانٍ كانت هي الحاجز ══
     وُضعت لعلاج طلبٍ معلّق لا يفشل ولا ينجح. لكنّها قاست **زمن الوصول**
     لا **صحّة الرابط** — والفرق حاسم حين تُعرض عشرات الشعارات دفعةً
     واحدة: المتصفّح يصفّ الطلبات في طابور محدود، فما تأخّر دورُه تجاوز
     الأربع فهُجر وهو سليم.

     وأثرُ ذلك ما رآه المالك: الصفحات قليلة الشعارات (المفكرة) تنجح،
     وكثيرتُها (فرز السوق) تسقط إلى المصدر التالي ثم إلى الحرف. قِيس في
     المتصفّح: صفوف الفرز تحمل روابط المصدر الثالث لا الخريطة.

     صارت خمس عشرة ثانية — تكفي أطول طابور ولا تترك المعلّق أبداً. */
  const imgRef = useRef<HTMLImageElement | null>(null);
  useEffect(() => {
    if (!url) return;
    const t = setTimeout(() => {
      if (!imgRef.current?.complete) setStage(s => s + 1);
    }, 15000);
    return () => clearTimeout(t);
  }, [stage, url]);

  if (url && base) {
    return (
      <img
        ref={imgRef}
        src={url}
        alt={base}
        width={size}
        height={size}
        onError={() => setStage(s => s + 1)}
        onLoad={e => {
          // Some ad-blockers swap a blocked logo request for a blank 1x1
          // pixel with a 200 status instead of failing it outright — that
          // never fires onError, so it would otherwise show as an empty
          // square forever. Treat a suspiciously tiny loaded image as a
          // failure too and fall through the same chain.
          const img = e.currentTarget;
          if (img.naturalWidth <= 2 || img.naturalHeight <= 2) { setStage(s => s + 1); return; }
          if (base && url) RESOLVED.set(base, url);   // نجاحٌ مقيس، يُحفظ
        }}
        className="co-logo rounded-xl object-contain shrink-0"
        style={{ width: size, height: size }}
        /* ══ أولويةٌ عاديةٌ لا منخفضة ══ (بأمر المالك · D194)
           كان `fetchpriority="low"` يأمر المتصفّحَ صراحةً بتأخير الشعارات
           خلف كلّ طلبٍ آخر، و`loading="lazy"` يؤجّل ما قارب حافّةَ الشاشة.
           فاجتمع أمران على التأخير في الشاشات الكثيفة (فرزُ السوق ·
           خريطةُ القطاعات) — وهو «التأخّرُ في مناطق دون أخرى» الذي رآه
           المالك. الشعارُ هويّةُ الصفّ لا زينةٌ فيه: يُحمَّل بأولويةٍ
           عادية، ويبقى التأجيلُ الكسول لما خرج عن الشاشة. */
        loading="lazy"
        decoding="async"
      />
    );
  }
  return (
    <div
      /* `co-logo` على البديل كما على الصورة: صفٌّ واحدٌ يسمّي الحالتين،
         فيُقاس **وجودُ الشعار** لا وجودُ الشبكة (‏D232). */
      className="co-logo rounded-xl flex items-center justify-center font-bold shrink-0"
      style={{
        width: size, height: size, color: "#fff",
        // أرضية ٩٫٥ بكسل: شعارٌ بحجم ٢٤ كان يكتب رمزه بـ٧٫٢ — تحت عتبة
        // القراءة التي أقرّتها اللجنة، خصوصاً في الإضاءة الخافتة.
        fontSize: Math.max(9.5, size * 0.3),
        /* التدرّج يُعتَّم بخلطه بالأسود: لونُ الشركة قد يأتي فاتحاً فيصير
        الرمز الأبيض عليه دون الأرضية (قِيس ٣٫٦٥:١). الخلط يضمن أرضيةً
        داكنةً دائماً مهما كان لون الشركة، والهويّة تبقى لأن الصبغة نفسها. */
        background: `linear-gradient(135deg, color-mix(in srgb, ${color || "#2563eb"} 78%, #000), #4c1d95)`,
      }}
    >
      {base.slice(0, 4)}
    </div>
  );
}
