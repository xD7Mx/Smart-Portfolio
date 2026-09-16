"""إكمالُ القوائم بالحقل — البديلُ المكمِّل يُدمَج مع الأصل (D336).

## المبدأُ الذي أمر به المالك

«النقصُ ليس اعتذاراً يُعلَن، وإنما اكتشافُ البديلِ المكمِّل لندمجَه مع
المصدر الأساسيّ». فالإعلانُ عن الغياب آخرُ الدواء لا أوّلَه: بندٌ غائبٌ
عن الملفّ الرسميّ يُبحَث عنه في طبقةٍ تملكه، وما لا تملكه طبقةٌ واحدةٌ
تملكه أخرى، وما لا يُنشَر أصلاً **يُشتقّ من منشورٍ بتعريفٍ محاسبيٍّ لا
بالظنّ** — ولا يبقى «غير متوفّر» إلا ما استُنفدت له الطبقاتُ كلُّها.

## وثلاثةُ قيودٍ تمنع الدمجَ أن يصير خلطاً

  · **لا يُستبدَل منشورٌ بمكمِّل**: ما ورد في الملفّ الرسميّ يبقى كما
    ورد، والإكمالُ للفراغ وحدَه.
  · **كلُّ حقلٍ يحمل مصدرَه** في `field_sources` — فرقمٌ لا يُعرف مصدرُه
    لا يُبنى عليه قرار (بند الميثاق)، والدرجةُ تُقرأ ضمن بياناتها.
  · **الفترةُ تُطابَق بسنتها** لا بترتيبها: بندُ ‎2024 يُكمَّل من ‎2024
    وحدَها، وإلا خُلطت سنةٌ بأخرى فصار الاتّجاهُ كذباً.

## وقبل الطبقات: تسويةُ الوحدة (D339)

الملفُّ يُعلن «وحدةَ التقريب» فتُضرَب بها بنودُ المال ولا تُضرَب بها
الأعدادُ — وهو الصواب. لكنّ الملفّات لا تتّفق: منها ما ينشر عددَ الأسهم
بالوحدات ومنها ما ينشره بالآلاف كبقيّة العمود، فيختلف مقياسُ العدد عن
مقياس المال وتنهار كلُّ قيمةٍ للسهم بمقياسٍ ألفيّ (قِيس: مدىً صار
**0.04–0.14** ريالاً).

وهويّةُ `EPS = الربح ÷ الأسهم` تكشف أن أحدَ الطرفين أخطأ — **ولا تقول
أيَّهما**. فالحكمُ بها وحدَها يقسم مالاً مسوّىً على ألف. والفاصلُ
مِرساةٌ مستقلّةٌ عن تقريب الملفّ: **قيمةُ لقطةِ «تداول» السوقيةُ ÷
السعر**. فتُسوّى بها وحدةُ العدد أوّلاً، ثمّ تُسوّى بالهويّة وحدةُ
المال. وبلا مِرساةٍ يُعلَن الفرقُ ولا يُصلَح، ويُمنَع ما يُبنى عليه.

## ترتيبُ الطبقات

  ١· **اشتقاقٌ من المنشور في الفترة نفسِها** — هويّاتٌ محاسبيةٌ لا ظنون:
     حقوقٌ = أصولٌ − التزامات · أسهمٌ = صافي الربح ÷ ربحية السهم ·
     تدفّقٌ حرٌّ = تشغيليٌّ − رأسماليّ · ربحٌ تشغيليٌّ = قبلَ الزكاة +
     تكلفةُ التمويل · دَينٌ = مجموعُ القروض والإيجار.
  ٢· **ياهو** لِما بقي — بمطابقة السنة.
  ٣· **لقطةُ «تداول»** للقيمة السوقية والمضاعفات: منها حقوقٌ = قيمةٌ
     سوقية ÷ مضاعفِ الدفترية، وأسهمٌ = قيمةٌ سوقية ÷ السعر.
  ٤· **«أرقام»** لصافي ربح آخرِ فترةٍ حين يغيب.
"""
from __future__ import annotations

from loguru import logger

# البنودُ التي يطلبها محرّكا السعر العادل والحوكمة
NEEDED = ("revenue", "net_income", "eps", "equity", "total_assets",
          "total_liabilities", "operating_cash_flow", "capex",
          "free_cash_flow", "shares_outstanding", "total_debt",
          "pretax_income", "interest_expense", "ebit", "ending_cash")

_OFFICIAL = "تداول — XBRL"


def _pos(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


_UNITS = (1e3, 1e6, 1e9)


def unit_gap(a, b, *, tol: float = 0.02) -> float | None:
    """العاملُ الذي يُضرَب فيه `a` ليوافقَ `b` إن كان **قوّةً للألف**.

    فرقُ الوحدة ليس فرقَ رقم: ملفٌّ يُعلن «بالآلاف» ولم تُطبَّق وحدتُه
    يُخرج رقماً أصغرَ ألفَ مرّةٍ بالضبط — لا «تقديراً مخالفاً». فيُميَّز
    الفرقانِ: هذا يُصحَّح بالضرب، وذاك يُسمّى خلافاً ويُحكَم بينهما.
    وتُشترَط المطابقةُ داخلَ ٢٪ كي لا يُلبَس خلافٌ حقيقيٌّ ثوبَ الوحدة.
    """
    try:
        x, y = float(a), float(b)
    except (TypeError, ValueError):
        return None
    if x <= 0 or y <= 0:
        return None
    for u in _UNITS:
        for f in (u, 1.0 / u):
            if abs(x * f - y) <= tol * y:
                return f
    return None


def _derive(p: dict, src: dict) -> None:
    """هويّاتٌ محاسبيةٌ من بنودِ الفترة نفسِها — لا ظنَّ فيها."""
    ta, tl = p.get("total_assets"), p.get("total_liabilities")
    if p.get("equity") is None and ta is not None and tl is not None:
        p["equity"] = round(float(ta) - float(tl), 2)
        src["equity"] = "مشتقّ: أصولٌ − التزامات"

    # ══ وتسويةٌ بين المنشور والمشتقّ ══ (D339)
    # قِيس على خادم المالك: بعد مطابقة «عدد الأسهم» بالاسم، حالةٌ صار
    # مداها **0.04–0.14** ريالاً — أي أن العددَ المطابَقَ لا يوافق
    # ربحيةَ السهم. و`EPS = الربح ÷ الأسهم` تعريفٌ لا ظنّ، فالخلافُ
    # بينهما دليلٌ قائم. لكنّ الخلافَ خلافانِ ولا يُساوى بينهما:
    #   · **فرقُ وحدةٍ** (قوّةُ ألفٍ بالضبط): الملفُّ يُعلن «بالآلاف»
    #     ووحدتُه لم تُطبَّق على المال — فالمنشورُ عددٌ صحيح، والعلاجُ
    #     تصحيحُ وحدةِ المال عند القراءة. وأوّلُ صياغةٍ لهذا البند كانت
    #     تستبدل المنشورَ الصحيحَ (‏243,201,389) بمشتقٍّ بمقياس الآلاف
    #     (‏243,201) فتُفسد ما جاءت تُصلِح — قِيس محلّياً قبل التسليم.
    #   · **فرقُ عددٍ** (ليس قوّةَ ألف): متوسّطٌ مرجّحٌ لفئةٍ أخرى أو
    #     لتاريخٍ آخر — فالموافقُ للتعريف هو الصالحُ للحساب، ويُقال
    #     إنه خالف المنشورَ ولا يُخفى.
    ni, eps = p.get("net_income"), p.get("eps")
    if ni is not None and isinstance(eps, (int, float)) and abs(eps) > 1e-9:
        sh = float(ni) / float(eps)
        cur = p.get("shares_outstanding")
        if sh > 0 and cur is None:
            p["shares_outstanding"] = round(sh, 0)
            src["shares_outstanding"] = "مشتقّ: صافي الربح ÷ ربحية السهم"
        elif sh > 0 and isinstance(cur, (int, float)) and cur > 0:
            gap = unit_gap(sh, float(cur))
            ratio = max(sh, float(cur)) / min(sh, float(cur))
            if gap:
                # فرقُ **وحدة**: العددُ المنشورُ عددٌ صحيحٌ والخللُ في
                # وحدةِ المال — ويُصحَّح عند القراءة حيث تُعرَف الوحدةُ
                # وتُعرَف بنودُ المال، لا هنا بضربٍ في العمياء. ويُعلَن
                # الفرقُ كي لا يُبنى عليه رقمٌ للسهم وهو غيرُ مسوّى.
                p["shares_unit_gap"] = gap
            elif ratio > 1.25:
                # فرقُ **عدد** لا وحدة: المنشورُ عددُ الأسهم المُصدَرة
                # والقسمةُ تُخرج المتوسّطَ المرجَّح لأساسِ ربحيةِ السهم —
                # واختلافُهما مشروعٌ لا عطب. **فلا يُستبدَل المنشور**
                # (حرسه العقدُ ٧ب في `tadawul_xbrl.py` وأحمرَ على صياغةٍ
                # لي استبدلته): يُسمّى الفرقُ ويبقى الرقمُ كما وردَ.
                p["shares_mismatch"] = round(ratio, 2)

    ocf, capex = p.get("operating_cash_flow"), p.get("capex")
    if p.get("free_cash_flow") is None and ocf is not None and capex is not None:
        p["free_cash_flow"] = round(float(ocf) - abs(float(capex)), 2)
        src["free_cash_flow"] = "مشتقّ: تشغيليٌّ − رأسماليّ"

    pre, fin = p.get("pretax_income"), p.get("interest_expense")
    if p.get("ebit") is None and pre is not None and fin is not None:
        p["ebit"] = round(float(pre) + abs(float(fin)), 2)
        src["ebit"] = "مشتقّ: قبلَ الزكاة + تكلفةُ التمويل"

    if p.get("total_debt") is None:
        parts = [p.get(k) for k in ("borrowings_current", "borrowings_noncurrent",
                                    "lease_current", "lease_noncurrent")
                 if isinstance(p.get(k), (int, float))]
        if parts:
            p["total_debt"] = round(sum(float(x) for x in parts), 2)
            src["total_debt"] = "مشتقّ: مجموعُ القروض والإيجار"

    # وقيمةُ السهم الدفتريةُ لا تُحسَب على وحدةٍ لم تُسوَّ: الفرقُ ألفُ
    # مرّةٍ يُخرج «0.04 ريالاً» فتَنهار مساراتُ التقييم عليه. والغيابُ
    # أصدقُ من رقمٍ بمقياسٍ خاطئ (الجهلُ ليس صفراً).
    eq, sh2 = p.get("equity"), p.get("shares_outstanding")
    if (p.get("book_value_per_share") is None
            and not p.get("shares_unit_gap")
            and not p.get("shares_mismatch")        # D347: الفرقُ عددٌ كذلك
            and _pos(eq) and _pos(sh2)):
        p["book_value_per_share"] = round(float(eq) / float(sh2), 4)
        src["book_value_per_share"] = "مشتقّ: حقوقٌ ÷ عددُ الأسهم"


MONEY = tuple(k for k in NEEDED
              if k not in ("eps", "shares_outstanding")) + (
    "borrowings_current", "borrowings_noncurrent",
    "lease_current", "lease_noncurrent")


def _scale(p: dict, src: dict, anchor: float | None) -> None:
    """تسويةُ الوحدة قبل كلّ اشتقاق — ولا يُحكَم بها بلا مِرساة (D339).

    الهويّةُ `EPS = الربح ÷ الأسهم` **لا تكشف** وحدةَ المال وحدَها: ملفٌّ
    ينشر المالَ بالآلاف والعددَ بالآلاف تصدُق فيه القسمةُ وهو غيرُ مسوّى،
    وملفٌّ سُوّي مالُه وبقي عددُه بالآلاف تخالف فيه القسمةُ ألفَ مرّة. فلا
    تقول الهويّةُ **أيُّ الطرفين** أخطأ — تقول إن أحدَهما أخطأ.
    وقِيس محلّياً أن الحكمَ بها بلا مِرساةٍ يقسم مالاً مسوّىً على ألف
    (‏`scale_fix = 0.001` على ملفٍّ معلَنِ الوحدة صحيحِها).

    فالفاصلُ مِرساةٌ مستقلّةٌ عن وحدةِ الملفّ: **قيمةُ لقطةِ «تداول»
    السوقيةُ ÷ السعرِ** عددُ أسهمٍ لا يمرّ بتقريب الملفّ. فبها تُسوّى
    وحدةُ العدد أوّلاً، ثمّ تُسوّى بالهويّة وحدةُ المال. وبلا مِرساةٍ
    يُعلَن الفرقُ ولا يُصلَح — ويُمنَع ما يُبنى عليه من قيمةٍ للسهم.
    """
    sh = p.get("shares_outstanding")
    # ١· وحدةُ **العدد** تُقاس بمِرساةٍ لا تحمل تقريبَ الملفّ
    if anchor and _pos(sh):
        gap = unit_gap(float(sh), anchor)
        if gap:
            p["shares_outstanding"] = round(float(sh) * gap, 0)
            was = src.get("shares_outstanding") or _OFFICIAL
            src["shares_outstanding"] = (
                f"{was} (وحدةُ العدد سُوّيت "
                + (f"×{gap:,.0f}" if gap >= 1 else f"÷{1 / gap:,.0f}")
                + " بقيمةِ لقطةِ تداول السوقية ÷ السعر)")
            sh = p["shares_outstanding"]

    # ٢· ثمّ وحدةُ **المال** بالهويّة — والعددُ صار مسوّىً بمِرساته
    ni, eps = p.get("net_income"), p.get("eps")
    if not (anchor and _pos(sh) and ni is not None
            and isinstance(eps, (int, float)) and abs(eps) > 1e-9):
        return
    gap = unit_gap(float(ni) / float(eps), float(sh))
    if not gap:
        return
    for k in MONEY:
        if isinstance(p.get(k), (int, float)):
            p[k] = round(p[k] * gap, 2)
    p["scale_fix"] = gap


def _from_rows(p: dict, src: dict, other: list[dict], label: str) -> None:
    """يُكمَل الفراغُ من صفوفِ مصدرٍ آخرَ — **بمطابقة السنة**."""
    year = p.get("year")
    if year is None:
        return
    match = next((o for o in (other or [])
                  if str(o.get("year") or "")[:4] == str(year)[:4]), None)
    if not match:
        return
    for k in NEEDED:
        if p.get(k) is None and match.get(k) is not None:
            p[k] = match[k]
            src[k] = label


def _from_snapshot(p: dict, src: dict, row: dict, price) -> None:
    """لقطةُ السوق: قيمةٌ سوقيةٌ ومضاعفاتٌ ← حقوقٌ وعددُ أسهم."""
    mcap = _pos((row or {}).get("market_cap"))
    pb = _pos((row or {}).get("price_to_book"))
    px = _pos(price) or _pos((row or {}).get("price"))
    if p.get("shares_outstanding") is None and mcap and px:
        p["shares_outstanding"] = round(mcap / px, 0)
        src["shares_outstanding"] = "لقطةُ تداول: قيمةٌ سوقية ÷ السعر"
    if p.get("equity") is None and mcap and pb:
        p["equity"] = round(mcap / pb, 2)
        src["equity"] = "لقطةُ تداول: قيمةٌ سوقية ÷ مضاعفِ الدفترية"


def complete(symbol, periods: list[dict], *,
             yahoo_periods: list[dict] | None = None,
             snapshot_row: dict | None = None,
             price=None,
             argaam: dict | None = None,
             base_source: str | None = None) -> list[dict]:
    """قوائمُ مُكمَّلةٌ حقلاً حقلاً، ومعها `field_sources` لكلّ فترة.

    ولا تُستبدَل قيمةٌ منشورةٌ أبداً: الإكمالُ للفراغ وحدَه، والاشتقاقُ
    يُعاد بعد كلّ طبقةٍ لأن طبقةً قد تُتيح هويّةً كانت ممتنعة (بندٌ من
    ياهو يُكمل «أصولاً» فتُشتقّ منه «حقوق»).
    """
    # مِرساةُ الوحدة: عددُ أسهمٍ من «تداول» لا يمرّ بتقريب الملفّ
    _mc = _pos((snapshot_row or {}).get("market_cap"))
    _px = _pos(price) or _pos((snapshot_row or {}).get("price"))
    _anchor = (_mc / _px) if (_mc and _px) else None

    out: list[dict] = []
    for p0 in periods or []:
        p = dict(p0)
        src: dict[str, str] = {k: (base_source or _OFFICIAL)
                               for k in NEEDED if p.get(k) is not None}
        # وما وسمته الوحدةُ الأصلية مشتقّاً يبقى مشتقّاً لا منشوراً
        if p.get("shares_source"):
            src["shares_outstanding"] = str(p["shares_source"])

        _scale(p, src, _anchor)
        _derive(p, src)
        if yahoo_periods:
            _from_rows(p, src, yahoo_periods, "ياهو")
            _derive(p, src)
        if snapshot_row:
            _from_snapshot(p, src, snapshot_row, price)
            _derive(p, src)
        p["field_sources"] = src
        out.append(p)

    # ── «أرقام»: صافي ربحِ آخرِ فترةٍ حين يغيب ──────────────────────────
    if out and argaam:
        last = out[-1]
        if last.get("net_income") is None:
            cur = ((argaam.get("annual") or {}).get("current")
                   or (argaam.get("quarter") or {}).get("current"))
            if isinstance(cur, (int, float)):
                # أرقامٌ تنشر بالمليون في جدول النتائج — والوحدةُ تُعلَن.
                last["net_income"] = float(cur) * 1_000_000
                last["field_sources"]["net_income"] = "أرقام: جدولُ النتائج"
                _derive(last, last["field_sources"])

    filled = sum(1 for p in out for k, v in (p.get("field_sources") or {}).items()
                 if v != (base_source or _OFFICIAL))
    if filled:
        logger.debug("إكمالُ القوائم {}: {} حقلاً من طبقاتٍ مكمِّلة",
                     symbol, filled)
    return out


def missing(periods: list[dict]) -> list[str]:
    """ما بقي غائباً في **كلّ** الفترات بعد الإكمال — يُقال ولا يُختلق."""
    if not periods:
        return list(NEEDED)
    return [k for k in NEEDED
            if all(p.get(k) is None for p in periods)]
