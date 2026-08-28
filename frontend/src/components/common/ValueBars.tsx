/* شريطا التقييم والسلامة — تعريفٌ واحد يخدم «رؤية الذكاء» و«فرز السوق».

   كانا معرَّفين داخل صفحة الذكاء وحدها. ونسخُهما إلى صفحة الفرز كان سيُنتج
   شريطين متطابقين اليوم يتباعدان غداً مع أوّل تعديل على أحدهما — وهي العلّة
   التي تكرّرت في هذا التطبيق. فنُقلا هنا كما هما بلا أي تغيير في المظهر.

   شريط القيمة العادلة يبدأ من **المنتصف** (السعر = القيمة العادلة) ويميل نحو
   الطرف الذي يقع فيه السهم؛ وشريط السلامة يمتلئ من صفر إلى مئة. والفارق
   بينهما مقصود: الأول مقياس انحرافٍ باتجاهين، والثاني مقياس درجةٍ باتجاه واحد.
*/

/* ══ الوسمُ يقرأ ما يقرؤه الحكم ══ (عطبٌ رآه المالك في «الراجحي ريت»)
   كان الوسم يُشتقّ من **الصعود الخام** بعتباتٍ ثابتة (‏±8٪ · ±25٪)، ولا
   يعرف شيئاً عن جودة التقدير. وسعرُ الدخول يعرفها: هامشُ الأمان يتّسع
   كلّما تباعدت المسارات.
   فوقع التناقض على شاشةٍ واحدة: مساراتُ الريت بين 9.68 و19.93 (‏2.06×)،
   فاتّسع الهامشُ إلى 35٪ وصار الدخول 6.47 والسعرُ 7.88 — أي «بلا هامش
   أمان». وفي الوقت نفسه الصعودُ الخام +26.4٪ فتجاوز عتبة 25٪ فكتب
   الشريطُ «تقييم مبخس».
   **الشريط يقول اشترِ والحكم يقول لا تشترِ، عن الرقم نفسه.**

   فصار الوسمُ يُقرأ من موضع السعر بين سعرِ الدخول والقيمة — وهما
   الرقمان اللذان يقوم عليهما الحكم، فلا يفترقان. ومن لا يملك سعرَ دخولٍ
   (فرزُ السوق · صفحة الذكاء) يبقى على العتبات الخام كما كان. */
export function fairValueTier(
  upside: number | null,
  ctx?: { price?: number | null; entry?: number | null; value?: number | null },
) {
  if (upside == null) return { label: "غير متاح", color: "var(--ink-muted)" };
  const { price, entry, value } = ctx || {};
  if (price != null && entry != null && value != null && value > 0) {
    if (price <= entry) return { label: "تقييم مبخس", color: "var(--pos-ink)" };
    if (price < value)  return { label: "عادل",       color: "var(--warn-ink)" };
    if (price < value * 1.15) return { label: "مرتفع", color: "var(--warn-ink)" };
    return { label: "مبالغ فيه", color: "var(--neg-ink)" };
  }
  if (upside >= 25) return { label: "تقييم مبخس", color: "var(--pos-ink)" };
  if (upside >= 8)  return { label: "جيد",         color: "var(--pos-ink)" };
  if (upside > -8)  return { label: "عادل",         color: "var(--warn-ink)" };
  if (upside > -25) return { label: "مرتفع",        color: "var(--warn-ink)" };
  return              { label: "مبالغ فيه",   color: "var(--neg-ink)" };
}

/* لونا الدرجة يخدمان النصّ والشريط معاً. النصّ يحتاج تبايناً أعلى فوق
   الورق، فيُقرأ اللون من رموز الدليل (تُعمَّق في الفاتح تلقائياً)، ويبقى
   الشريط بلونه المشبع لأنه مساحةٌ لا حرف. */
export const safeColor = (s: number) => s >= 65 ? "var(--pos-ink)" : s >= 45 ? "var(--warn-ink)" : "var(--neg-ink)";
export const safeFill = (s: number) => s >= 65 ? "var(--gauge-pos)" : s >= 45 ? "var(--gauge-warn)" : "var(--gauge-neg)";

/* حشوُ العلامة من رموز المقاييس — لونٌ واحد في المظهرين. أمّا نصُّ
   الدرجة فيبقى من رموز الحبر: الحرفُ يحتاج 4.5:1 ولا تبلغها هذه
   الدرجات على البياض، فتوحيدُه يُخفيه. اللونُ وُحّد حيث هو مساحة. */
const tierFill = (upside: number | null) =>
  upside == null ? "var(--ink-muted)" : upside >= 8 ? "var(--gauge-pos)"
  : upside > -25 ? "var(--gauge-warn)" : "var(--gauge-neg)";

export function FairValueBar({ upside, hideLabel = false, width = 96, ctx }:
  { upside: number | null; hideLabel?: boolean; width?: number | string;
    ctx?: { price?: number | null; entry?: number | null; value?: number | null } }) {
  const tier = fairValueTier(upside, ctx);
  if (upside == null) return <span className="text-xs text-[var(--ink-muted)]">{tier.label}</span>;
  // القصّ عند ±٥٠٪: انحرافٌ أكبر يدفع العلامة خارج الشريط فتختفي، والرقم
  // المعروض نصّاً يبقى صادقاً بلا قصّ.
  const dev = Math.max(-50, Math.min(50, upside));
  const pos = 50 + dev;
  return (
    <div style={{ width }} dir="ltr">
      {!hideLabel && <div className="text-[11px] font-bold mb-1.5" style={{ color: tier.color }}>{tier.label}</div>}
      <div className="relative h-1.5 rounded-full" style={{ /* مساحةٌ لا حرف ⇒ حشو (انظر --pos-fill في globals.css) */ background: "linear-gradient(90deg, var(--gauge-neg), var(--gauge-warn) 50%, var(--gauge-pos))",
        boxShadow: "inset 0 0 0 1px var(--gauge-edge)" }}>
        <div className="absolute" style={{ left: "50%", top: -3, width: 1, height: 8, background: "transparent" }} />
        <Marker pos={pos} color={tier.color} />
      </div>
    </div>
  );
}

export function SafetyBar({ score, width = 64 }: { score: number | null; width?: number | string }) {
  if (score == null) return <span className="text-xs text-[var(--ink-muted)]">غير متاح</span>;
  const c = safeFill(score);
  return (
    <div className="relative h-1.5 rounded-full bg-[var(--surface)]" style={{ width, boxShadow: "inset 0 0 0 1px var(--gauge-edge)" }}>
      <div className="h-1.5 rounded-full" style={{ width: `${score}%`, background: c }} />
      <Marker pos={score} color={c} from="right" />
    </div>
  );
}

/* علامةُ الشريط — تعريفٌ واحد يخدم المقياسين. كانت مكرّرةً حرفياً في
   شريط القيمة وشريط السلامة، ثم طُلب ثالثٌ للاتجاه الفنّي — ونسخُها
   ثالثةً يُنتج ثلاثةَ أشكالٍ تتباعد مع أوّل تعديل. */
function Marker({ pos, color, from = "left" }:
  { pos: number; color: string; from?: "left" | "right" }) {
  const place = from === "left" ? { left: `${pos}%` } : { right: `${pos}%` };
  const shift = from === "left" ? "translate(-50%, -50%)" : "translate(50%, -50%)";
  return (
    <>
      <div className="absolute rounded-full animate-pulse" style={{
        top: "50%", width: 16, height: 16, ...place,
        transform: shift, background: color, filter: "blur(2px)", opacity: 0.45,
      }} />
      <div className="absolute rounded-full" style={{
        top: "50%", width: 12, height: 12, ...place,
        transform: shift, background: "#fff", border: `2.5px solid ${color}`,
        boxShadow: "0 0 0 1px var(--gauge-edge)",
      }} />
    </>
  );
}

/* ══ مقياسُ الاتجاه الفنّي ══ (باقتراح المالك)
   قال إن شريط التحليل الفنّي يمثّل صعوداً وهبوطاً، واقترح أن يكون
   كشريط القيمة: المحايدُ في المنتصف والعلامةُ تتحرّك. والملاحظة في
   محلّها — الاتجاه كمّيةٌ **ذاتُ إشارة**، وملؤها من صفرٍ إلى مئة
   إخفاءٌ لإشارتها: شريطٌ ممتلئ نصفَه يعني «لا اتجاه» لا «نصفَ صعود»،
   والعينُ تقرأ الامتلاءَ إنجازاً.
   فصار المحايد (٥٠) في الوسط، والعلامةُ تميل إلى الطرف الذي يقع فيه
   السهم — وهي هندسةُ شريط القيمة نفسها لأن السؤال من جنسه: انحرافٌ
   عن مرجعٍ لا امتلاءُ وعاء. */
export function TrendBar({ score, width = "100%" }:
  { score: number | null; width?: number | string }) {
  if (score == null) return null;
  const dev = Math.max(-50, Math.min(50, score - 50));
  const color = dev >= 10 ? "var(--gauge-pos)" : dev <= -10 ? "var(--gauge-neg)" : "var(--gauge-warn)";
  return (
    <div style={{ width }} dir="ltr">
      <div className="relative h-1.5 rounded-full" style={{
        background: "linear-gradient(90deg, var(--gauge-neg), var(--gauge-warn) 50%, var(--gauge-pos))",
        boxShadow: "inset 0 0 0 1px var(--gauge-edge)" }}>
        <Marker pos={50 + dev} color={color} />
      </div>
    </div>
  );
}
