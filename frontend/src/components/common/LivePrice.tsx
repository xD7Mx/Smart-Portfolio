/* سعرٌ حيٌّ في أيّ شاشة — مكوّنٌ واحدٌ لا نسخةٌ في كلّ جدول (D330).
 *
 * قال المالك: «يكون التطبيقُ بالكامل يعرض آخرَ سعرٍ لكلّ شركةٍ وما يُبنى
 * عليه، يتغيّر على الشاشة بحركةٍ متّصلة». وكان المجرى يصل **أربعَ شاشاتٍ
 * فقط** (الشريطُ · بطاقةُ النبض · صفحةُ السهم · العمق)، وبقيّتُها تقرأ
 * رقمَ الاستعلام: المحفظةُ والحيازاتُ وفرزُ السوق والمتابعة.
 *
 * فبدل أن يُكتب الاشتراكُ في كلّ جدولٍ (ومعه وميضُه ولونُه وتقريبُه)،
 * مكوّنٌ واحدٌ يجمع الثلاثة: يقرأ المجرى بالرمز، ويعود إلى رقم
 * الاستعلام إن لم يصل دفعٌ، ويومض بـ`FlashPrice` القائم.
 *
 * ولا ينشئ اشتراكاً ثانياً للمجرى: `useLiveQuote` اشتراكُه مرجعيٌّ
 * ومقسَّمٌ بالرمز — فمئةُ صفٍّ لا تفتح مئةَ اتّصال، ولا يُعاد رسمُ الجدول
 * لأنّ سهماً تحرّك.
 */
import FlashPrice from "./FlashPrice";
import { useLiveQuote } from "../../hooks/useLivePrices";

const fmt = (v: number | null | undefined, d = 2) =>
  v == null ? "—"
            : Number(v).toLocaleString("en-US", { minimumFractionDigits: d,
                                                  maximumFractionDigits: d });

/** رقمُ السعر الحيّ (أو رقمُ الاستعلام) بلا زينة — لمن يحتاج القيمةَ نفسَها. */
export function useLivePriceValue(symbol?: string | null,
                                  fallback?: number | null): number | null {
  const live = useLiveQuote(symbol);
  const v = live?.p ?? fallback;
  return v == null ? null : Number(v);
}

export default function LivePrice(
  { symbol, fallback, digits = 2, className, style, now }: {
    symbol?: string | null;
    fallback?: number | null;
    digits?: number;
    className?: string;
    style?: React.CSSProperties;
    now?: boolean;            // للسهم المفتوح: بلا تأخيرِ توزيع
  },
) {
  const live = useLiveQuote(symbol, now ? { now: true } : undefined);
  const value = live?.p ?? fallback ?? null;
  return (
    <FlashPrice value={value} className={className} style={style}>
      {value == null ? "—" : fmt(value, digits)}
    </FlashPrice>
  );
}

/** القيمةُ السوقيةُ حيّةً: أسهمٌ × سعرٌ حيّ — وما يُبنى على السعر يتبعه.
 *
 *  والحسابُ هنا **ليس اختلاقاً**: السعرُ منشورٌ من المصدر، وعددُ الأسهم
 *  رقمُ المالك. وبلا سعرٍ حيٍّ يُعرض ما حسبه الخادمُ كما هو.
 */
export function LiveValue(
  { symbol, shares, fallback, className, style }: {
    symbol?: string | null;
    shares?: number | null;
    fallback?: number | null;
    className?: string;
    style?: React.CSSProperties;
  },
) {
  const live = useLiveQuote(symbol);
  const v = (live?.p != null && shares) ? live.p * Number(shares)
                                        : (fallback ?? null);
  return (
    <FlashPrice value={v} className={className} style={style}>
      {v == null ? "—" : Number(v).toLocaleString("en-US",
        { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
    </FlashPrice>
  );
}
