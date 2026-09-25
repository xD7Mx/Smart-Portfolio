"""كونُ الشركات — السوقُ الرئيسة وحدها، ومصدرٌ واحدٌ لا يُلتفّ عليه.

## لماذا ملفٌّ مستقلّ

كان الاستبعادُ يقع **متأخّراً**: يمرّ الكونُ كلُّه إلى بناء التوزيع،
ثم تُستبعد شركاتُ «نمو» في حلقة التسجيل وحدها. فالنتيجةُ أن الاستبعادَ
يظهر في العدّ ولا يقع في الحساب: `peer_distribution.build` كان يقرأ
‎409 شركة — بالموازية — فتدخل شركاتُ «نمو» **كلَّ عشيرةٍ وكلَّ وسيطٍ
وكلَّ مئين**. ثم تُقاس شركةُ السوق الرئيسة على أقرانٍ نصفُهم من سوقٍ
آخر.

وذلك يفسد المقارنةَ في الاتّجاهين: سوقُ «نمو» رقيقةُ التداول محدودةُ
الإفصاح، مضاعفاتُها وهوامشُها لا تشبه الرئيسة. فمن قِيس عليها قِيس
بمسطرةٍ ليست مسطرتَه.

فصار الكونُ يُحسم **قبل أيّ مرحلة**:

    الكون → التصنيف → السوقُ الرئيسة وحدها → البيانات → المؤشّرات
    → توزيعُ الأقران → الدرجة → الجاهزية

## كيف يُميَّز السوقان

رموزُ تداول أربعةُ أرقام، وما بدأ بـ‎9 فهو السوقُ الموازية «نمو» — وهي
قاعدةُ الترقيم المعتمَدة في السوق. وفُحص الكونُ كلُّه: ‎409 رمزاً،
جميعُها رباعيةٌ رقمية، ‎136 منها تبدأ بـ‎9، و‎273 هي السوقُ الرئيسة.

ولا يُستنتج السوقُ من القطاع ولا من حجم البيانات: الرمزُ وحده هو
الفيصل، وهو معطىً لا اجتهاد فيه.
"""

from __future__ import annotations

MAIN = "MAIN"
NOMU = "NOMU"

# مصدرُ التصنيف: قاعدةُ ترقيم تداول — «نمو» تبدأ بـ‎9، **إلا صناديقَ
# المؤشرات المتداولة (94xx)** فهي في السوق الرئيسة (D486).
CLASSIFICATION_SOURCE = "تداول — بادئةُ الرمز (9xxx = «نمو» · 94xx = صناديق المؤشرات في الرئيسة)"

# ══ صناديقُ المؤشرات ليست «نمو» (بأمر المالك · D486) ══
# قاعدةُ «ما بدأ بـ9 فهو نمو» أسقطت صناديقَ المؤشرات المتداولة (9400–9409
# في دليل تداول: يقين 30، البلاد للذهب…) من السوق الرئيسة، وهي مدرجةٌ فيها
# بقطاعها الرسميّ «صناديق المؤشرات المتداولة». فعومِلت سوقاً موازيةً وأُهملت.
ETF_PREFIX = "94"


def is_etf(symbol: str | None) -> bool:
    s = str(symbol or "").strip().upper().replace(".SR", "")
    return s.isdigit() and len(s) == 4 and s.startswith(ETF_PREFIX)


def market_of(symbol: str | None) -> str | None:
    """سوقُ الرمز، أو `None` إن لم يكن رمزاً صالحاً.

    والرمزُ غيرُ الصالح لا يُلحَق بالرئيسة افتراضاً: يُعاد `None` فيُعلَن
    ولا يدخل حساباً — فإدخالُ مجهولٍ أسوأُ من استبعاده.
    """
    if not symbol:
        return None
    s = str(symbol).strip().upper().replace(".SR", "")
    if not (s.isdigit() and len(s) == 4):
        return None
    if s.startswith(ETF_PREFIX):
        return MAIN
    return NOMU if s.startswith("9") else MAIN


def is_main(symbol: str | None) -> bool:
    return market_of(symbol) == MAIN


def is_nomu(symbol: str | None) -> bool:
    return market_of(symbol) == NOMU


def main_market(universe: dict | None = None) -> dict:
    """شركاتُ السوق الرئيسة وحدها — وهذا هو الكونُ المعتمَد."""
    if universe is None:
        from app.data.market_universe import MARKET_UNIVERSE
        universe = MARKET_UNIVERSE
    return {s: m for s, m in universe.items() if is_main(s)}


def census(universe: dict | None = None) -> dict:
    """تعدادُ الكون — يُطبع في كلّ تقريرٍ فلا يُخمَّن العددُ ولا يُنسى."""
    if universe is None:
        from app.data.market_universe import MARKET_UNIVERSE
        universe = MARKET_UNIVERSE
    main = [s for s in universe if is_main(s)]
    nomu = [s for s in universe if is_nomu(s)]
    unknown = [s for s in universe if market_of(s) is None]
    return {
        "total": len(universe),
        "main": len(main),
        "nomu": len(nomu),
        "unknown": len(unknown),
        "unknown_symbols": sorted(unknown)[:20],
        "source": CLASSIFICATION_SOURCE,
    }
