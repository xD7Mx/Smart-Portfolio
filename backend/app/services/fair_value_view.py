"""رقمُ اليوم في كلّ ما يُشتقّ منه (‏D655 · سؤالُ المالك 2026-10-09: «هل الرقمُ العادل في تقارير الشركة يطابق المحرّك؟»).

قِيس الجواب: لا — ترويسةُ تقرير الشركة أخذت «السعرَ المستهدف خلال 12 شهراً» من حساب النماذج الحيّ مباشرة، فتجاوزت رقمَ اليوم
(D649) وحجبَ الرقم المتباين البعيد (D628) ووسمَ القطاع غير المعايَر (D634). فالهدفُ يُبنى هنا من السعر العادل **المعروض** نفسِه،
بنسبة الهدف إلى القيمة من النماذج (عائدُ حقوق الملكية ناقصاً التوزيع) — لصفحة السهم وتقرير الشركة معاً."""
from __future__ import annotations


def _pos(v):
    return v if isinstance(v, (int, float)) and v > 0 else None


def target_from(fair_value, models: dict | None) -> float | None:
    """الهدفُ لاثني عشر شهراً من السعر العادل المعروض. ‎None إن حُجب الرقمُ أو لم تُنتج النماذجُ هدفاً."""
    m = models or {}
    fv, lv, t12 = _pos(fair_value), _pos(m.get("live_value") or m.get("value")), m.get("target_12m")
    if not (fv and lv and isinstance(t12, (int, float))):
        return None
    return round(fv * t12 / lv, 2)
