"""حقولُ العرض المشتقّة — مُنتِجٌ واحدٌ لسلسلةِ مصادرها (D244).

## لماذا

بعد توحيد المائدة (‏D240) بقي في مسبار الأعمدة خلافان على أربعين شركة:
مضاعفُ الدفترية (‏1213: ‎63.31 في الفرز و‎11.78 في الصفحة) وعائدُ
التوزيعات (‏1304: ‎1.36 في الفرز و«غير متوفّر» في الصفحة).

والسببُ ليس حساباً مختلفاً بل **ترتيبَ مصادرَ مختلفاً**: كلُّ مسارٍ كتب
سلسلتَه بيده — أيُّهما يُقدَّم، الكاشُ أم المخزن؟ ومتى يُحسب من السعر
بدلَ أن يُنسَخ؟ وأيُّ مدًى يُعدّ معقولاً؟ فاختلفت الأجوبةُ بلا أن يقصد
أحد. وهذا الصنفُ لا يُعالج بتقريب السلسلتين بل بإلغاء إحداهما.

## القاعدة

  · الكاشُ الحيُّ أوّلاً ثمّ المخزنُ الدائم — لأن الأوّلَ هو ما تقرؤه
    صفحةُ السهم، والثاني يبقى حين ينتهي الأوّل.
  · وما هو **دالّةُ سعر** (المكرّرُ ومضاعفُ الدفترية) يُحسب من السعر
    الحاضر ومقياسِ الشركة، ولا يُنسَخ محفوظاً: مكرّرُ أمسِ بجانب سعرِ
    اليوم رقمان لا يجتمعان.
  · وما خرج عن مدى المعقول لا يُنشَر — الحدُّ نفسُه الذي يستعمله محرّكُ
    السعر العادل، فلا يُعرض مضاعفٌ ‎63 في شاشةٍ ويُخفى في أخرى.
"""
from __future__ import annotations

from app.services.relative_value import PB_RANGE, PE_RANGE, _ok


def resolve_display(symbol: str, price, *, fund: dict | None = None,
                    store_row: dict | None = None) -> dict:
    """الحقولُ المشتقّةُ جاهزةً: مكرّرٌ ومضاعفٌ وعائدٌ وهدفٌ وحدّا عام.

    يُعاد ما أمكن فقط — والمفتاحُ الغائبُ يعني «لا تُبدّل ما عندك»، فلا
    يُفرَّغ عمودٌ كان مملوءاً.
    """
    f = fund or {}
    row = store_row or {}

    def pick(key):
        v = f.get(key)
        return v if v is not None else row.get(key)

    out: dict = {}
    px = price if isinstance(price, (int, float)) and price > 0 else None

    # ── دالّتا السعر: تُحسبان لا تُنسَخان ──
    # ══ الرفضُ حكمٌ يُكتب، لا مفتاحٌ يُحجَب ══ (بعد تشغيلٍ رابع · D245)
    # كان المفتاحُ يُحجَب عند الرفض، وقاعدةُ «لا يُفرَّغ عمودٌ كان مملوءاً»
    # تُبقي رقمَ البناء القديم — فبقي مضاعفُ ‎63.31 في الفرز وصفحةُ السهم
    # تقول «غير متوفّر» (‏1213). والفرقُ بين الحالتين جوهريّ:
    #   · **لا مدخَلَ** ⇒ يُحجَب المفتاح: لا علمَ لنا، فلا نُفرّغ.
    #   · **مدخَلٌ ونتيجةٌ خارج المعقول** ⇒ يُكتب `None`: هذا حكمُنا،
    #     والرقمُ القديم مرفوضٌ في الشاشتين معاً.
    if px:
        eps, bv = pick("eps"), pick("book_value")
        if isinstance(eps, (int, float)) and eps > 0:
            out["pe_ratio"] = _ok(round(px / eps, 6), *PE_RANGE)
        if isinstance(bv, (int, float)) and bv > 0:
            out["price_to_book"] = _ok(round(px / bv, 6), *PB_RANGE)

    # ── المنقولاتُ من المصدر: تُقرأ بالسلسلة نفسِها ──
    for key, src in (("fair_value", "target_mean_price"),
                     ("high_52w", "week52_high"),
                     ("low_52w", "week52_low")):
        v = pick(src)
        if isinstance(v, (int, float)) and v > 0:
            out[key] = v
    if px:
        if "high_52w" in out:
            out["high_52w"] = round(max(out["high_52w"], px), 3)
        if "low_52w" in out:
            out["low_52w"] = round(min(out["low_52w"], px), 3)
        if "fair_value" in out:
            out["upside_pct"] = round((out["fair_value"] - px) / px * 100, 1)

    # ── العائد: المُنتِجُ الواحد (‏D223) بالمدخلات نفسِها ──
    # وجوابُه هو الجواب: إن قال «لا عائد» كُتب `None` ولم يُترك رقمُ
    # بناءٍ قديمٌ في الجدول بينما الصفحةُ تقول «غير متوفّر» (‏1304).
    try:
        from app.services.dividend_yield import resolve as _dy
        dy, src = _dy(str(symbol).replace(".SR", ""), px, f, row)
        out["dividend_yield"] = dy
        out["dividend_yield_source"] = src if dy is not None else None
    except Exception:                                             # noqa: BLE001
        pass
    return out
