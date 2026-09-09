"""عائدُ التوزيعات — مُنتِجٌ واحدٌ لكلّ شاشة.

## العطب الذي وُلدت منه

رأى المالكُ ‎2.44٪ في فرز السوق و‎2.56٪ في صفحة السهم للشركة نفسِها. ولم
يكن الفرقُ تقريباً بل **تعريفين**:

  · صفحةُ السهم تعرض `dividendYield` من المزوّد.
  · والفرزُ يسقط — متى غاب الرقمُ من كاشه — إلى حسابٍ خاصّ: مجموعُ توزيعات
    اثني عشر شهراً ÷ السعر.

وكلاهما «عائدُ توزيعات» في الاسم، ولا يلزم أن يتّفقا: المزوّد قد يحسبه على
آخر توزيعٍ مُعلَنٍ سنوياً، وحسابُنا على ما دُفع فعلاً.

وأوّلُ علاجٍ جرّبتُه كان ناقصاً: ثبّتُّ رقمَ المزوّد في المخزن الدائم كي
لا يزول بانتهاء الكاش. صحيحٌ لكنه **يتأخّر**: المخزنُ لا يمتلئ إلا بجلبٍ
جديد، ولقطةُ الفرز تُبنى مرّةً في اليوم — فيبقى الاختلافُ ظاهراً أياماً.

## القاعدة

سلسلةٌ واحدةٌ يقرأ منها الطرفان بالترتيب نفسِه، فيستحيل اختلافُهما مهما
كانت حالُ الكاش:

    ١· رقمُ المزوّد من الكاش      ٢· رقمُ المزوّد من المخزن الدائم
    ٣· توزيعُ اثني عشر شهراً ÷ السعر (احتياطٌ مُعلَنُ المصدر)

ويعود **المصدرُ مع الرقم** دائماً: رقمان بتعريفين لا يُعرضان تحت اسمٍ
واحدٍ بلا بيان.
"""
from __future__ import annotations


def resolve(symbol: str, price: float | None,
            fund_cache: dict | None = None,
            store_row: dict | None = None) -> tuple[float | None, str | None]:
    """(العائد٪ ، مصدرُه) — أو (None, None) إن لم يُعرف.

    `fund_cache`: صفُّ الكاش (`fund:yahoo:<sym>.SR`) إن كان بيد المُستدعي.
    `store_row`:  صفُّ المخزن الدائم لهذا الرمز.
    ولا يُنادى المزوّدُ من هنا: هذه دالّةُ توحيدٍ لا جلب.
    """
    base = str(symbol or "").replace(".SR", "").strip()

    if fund_cache is None or store_row is None:
        try:
            from app.services import cache as _cache
            from app.services.content_engine import fund_store_load
            if fund_cache is None:
                fund_cache = _cache.get(f"fund:yahoo:{base}.SR") or {}
            if store_row is None:
                store_row = (fund_store_load() or {}).get(base) or {}
        except Exception:                                         # noqa: BLE001
            fund_cache = fund_cache or {}
            store_row = store_row or {}

    for src in (fund_cache or {}, store_row or {}):
        v = src.get("dividend_yield")
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
            return round(float(v), 2), "المزوّد"

    # الاحتياطُ: ما دُفع فعلاً في اثني عشر شهراً ÷ السعر. تعريفٌ آخر، فيُسمّى.
    dps = (store_row or {}).get("dps_ttm")
    if (isinstance(dps, (int, float)) and not isinstance(dps, bool) and dps > 0
            and isinstance(price, (int, float)) and price > 0):
        return round(dps / price * 100, 2), "توزيعات ١٢ شهراً ÷ السعر"

    return None, None
