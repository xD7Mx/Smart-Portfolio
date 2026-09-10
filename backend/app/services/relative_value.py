"""القيمةُ النسبيةُ إلى القطاع — لِما لا يغطّيه بيتُ خبرة.

## لماذا وُجدت

‎124 شركةً من ‎273 في السوق الرئيسي بلا هدفِ محلّلين. وقد قِيس ذلك ولم
يُظَنّ: «سهمك» لا تنشر تقديراتٍ أصلاً، و«أرقام» تنشر توصياتِ البيوت حيث
توجد — وهذه الشركاتُ لا يُصدر لها أحدٌ توصية. فالنقصُ في السوق لا في
أنبوبنا، ولا يُملأ باستيرادِ مصدرٍ ثالثٍ لا وجود له.

فيُشتقّ بدلَه تقديرٌ من السوق نفسِه:

    القيمة ≈ وسيطُ مضاعفِ القطاع × مقياسِ الشركة

## ما ليس هذا

ليس «قيمةً عادلة» ولا بديلاً عن خصم التدفّقات. هو **موضعُ السهم من
نظائره**: إن كان القطاعُ كلُّه مبالغاً فيه فالقيمةُ المشتقّةُ مبالغٌ فيها
معه — وهذا حدٌّ في الطريقة لا عيبٌ في التنفيذ، ويُقال للمستخدم بالتسمية:
**«قيمةٌ نسبيةٌ إلى القطاع»**.

ولا يستبدل هدفَ محلّلٍ حيث وُجد؛ يملأ الفراغَ وحدَه.

## قواعدُ الامتناع

يمتنع ولا يُخمّن حين:
  · نظائرُ القطاع أقلُّ من `MIN_PEERS` بعد استبعاد الشركة نفسِها
  · لا مقياسَ موجباً للشركة (خسارةٌ تُبطل المكرّر، وقيمةٌ دفتريةٌ سالبة
    تُبطل المضاعف)
  · القطاعُ غيرُ مصنّف

والامتناعُ يعود بـ`None` ومعه سببُه بالعربية — لا يُجمَّل الفراغُ برقمٍ
ضعيف.

## استبعادُ الشركة من وسيط قطاعها

الشركةُ لا تُقارَن بنفسها: مضاعفُها يُنزَع من الوسيط قبل قياسها به. وبدون
ذلك تُسحَب النتيجةُ نحو السعر الحاليّ، فيقول النموذجُ عن كلّ سهمٍ إنه
«عادل» — وهو عيبٌ صامتٌ لا يظهر إلا بالفحص.
"""
from __future__ import annotations

import statistics
from typing import Iterable

MIN_PEERS = 5                 # أقلُّ نظائرَ لوسيطٍ له معنى (بعد الاستبعاد)
PE_RANGE = (0.0, 100.0)       # مكرّرٌ خارجَه ضجيجُ ربحٍ يكاد ينعدم
PB_RANGE = (0.0, 20.0)


def _ok(v, lo: float, hi: float) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    v = float(v)
    return v if lo < v < hi else None


class SectorTable:
    """مضاعفاتُ القطاعات، محسوبةً من صفوف السوق نفسِها."""

    def __init__(self, rows: Iterable[dict]):
        self.pe: dict[str, list[float]] = {}
        self.pb: dict[str, list[float]] = {}
        for r in rows:
            sec = r.get("sector")
            if not sec:
                continue
            pe = _ok(r.get("pe"), *PE_RANGE)
            pb = _ok(r.get("pb"), *PB_RANGE)
            if pe is not None:
                self.pe.setdefault(sec, []).append(pe)
            if pb is not None:
                self.pb.setdefault(sec, []).append(pb)

    @staticmethod
    def _stats(values: list[float], drop: float | None) -> dict | None:
        """وسيطٌ ورُبعان، بعد نزع قيمة الشركة نفسِها من العيّنة."""
        v = list(values)
        if drop is not None:
            try:
                v.remove(drop)
            except ValueError:
                pass          # ليست في العيّنة أصلاً — لا شيء يُنزَع
        if len(v) < MIN_PEERS:
            return None
        v.sort()
        med = statistics.median(v)
        # الرُّبعان يرسمان النطاق: عرضُه من تشتّت القطاع لا من نسبةٍ مخترعة.
        q1, q3 = (statistics.quantiles(v, n=4)[0],
                  statistics.quantiles(v, n=4)[2]) if len(v) >= 4 else (v[0], v[-1])
        # ══ التشتّتُ يُقاس بالوسط لا بالطرفين ══ (قِيس على السوق الحقيقيّ)
        # كان `(الأعلى − الأدنى) ÷ الوسيط`، فحكَمه شاذٌّ واحد: شركةٌ مكرّرُها
        # تسعون في قطاعٍ متقاربٍ تُسقط ثقةَ القطاع كلِّه. فخرجت الشركاتُ
        # كلُّها «منخفضةَ الثقة» على السوق: ‎196 من ‎247 وصفرٌ مرتفعة —
        # وهو حكمٌ على المقياس لا على السوق. والمدى الرُّبيعيُّ يقيس تجمّعَ
        # الوسط، وهو ما يُبنى عليه الوسيطُ أصلاً.
        return {"n": len(v), "median": med, "q1": q1, "q3": q3,
                "spread": (q3 - q1) / med if med else 0.0}

    def for_sector(self, sector: str, *, own_pe: float | None = None,
                   own_pb: float | None = None) -> dict:
        return {
            "pe": self._stats(self.pe.get(sector, []), own_pe),
            "pb": self._stats(self.pb.get(sector, []), own_pb),
        }


def value_from_metrics(*, sector: str | None, eps: float | None,
                       bvps: float | None, table: SectorTable,
                       own_pe: float | None = None,
                       own_pb: float | None = None) -> dict:
    """المحرّكُ الأصليّ: مقياسا الشركة (ربحيةُ السهم ودفتريّتُه) × وسيطِ قطاعها.

    ‏`own_pe`/`own_pb` مضاعفاتُ الشركة نفسِها إن كانت **داخل** العيّنة —
    تُنزَع منها قبل القياس بها. والشركةُ غيرُ المدرَجة (اكتتابٌ مرتقب) ليست
    في العيّنة أصلاً، فلا يُنزَع لها شيء.

    وهذا هو موضعُ الحساب الواحد: `relative_value` تشتقّ المقياسَين من السعر
    والمضاعفات ثم تنزل إلى هنا، وحاسبةُ الاكتتاب تأخذهما من النشرة وتنزل
    إلى هنا — فلا مسطرتان لقياسٍ واحد (D231).
    """
    out: dict = {"value": None, "low": None, "high": None,
                 "confidence": None, "paths": {}, "why": None,
                 "basis": "السعر العادل"}
    if not sector:
        out["why"] = "القطاع غير مصنّف"
        return out
    eps = _ok(eps, -1e9, 1e9)
    bvps = _ok(bvps, 0.0, 1e9)

    t = table.for_sector(sector, own_pe=own_pe, own_pb=own_pb)
    out["sector_stats"] = t
    paths: dict[str, dict] = {}

    # ── مسارُ المكرّر ── يسقط مع الخسارة: مكرّرُ ربحٍ سالبٍ لا معنى له.
    if t["pe"] and eps is not None and eps > 0:
        paths["مكرر الربحية"] = {
            "value": t["pe"]["median"] * eps,
            "low": t["pe"]["q1"] * eps,
            "high": t["pe"]["q3"] * eps,
            "peers": t["pe"]["n"], "spread": t["pe"]["spread"],
        }

    # ── مسارُ القيمة الدفترية ──
    # لا يحتاج سعراً ولا ربحاً: يصمد حيث تخسر الشركةُ ويسقط المكرّر.
    if t["pb"] and bvps:
        paths["مضاعف القيمة الدفترية"] = {
            "value": t["pb"]["median"] * bvps,
            "low": t["pb"]["q1"] * bvps,
            "high": t["pb"]["q3"] * bvps,
            "peers": t["pb"]["n"], "spread": t["pb"]["spread"],
        }

    if not paths:
        out["why"] = ("لا نظائرَ كافيةً في القطاع" if not (t["pe"] or t["pb"])
                      else "لا مقياسَ موجباً للشركة")
        return out
    return _combine(out, paths)


def _combine(out: dict, paths: dict[str, dict]) -> dict:
    """الجمعُ والنطاقُ ودرجةُ الثقة — موضعٌ واحدٌ لكلّ من يستدعي المحرّك."""

    vals = [p["value"] for p in paths.values()]
    out["paths"] = paths
    out["value"] = sum(vals) / len(vals)
    out["low"] = min(p["low"] for p in paths.values())
    out["high"] = max(p["high"] for p in paths.values())

    # ── الثقة ── تُبنى على ثلاثةٍ تُقاس، لا على انطباع:
    #   عددُ النظائر · تشتّتُ مضاعفات القطاع · واتّفاقُ المسارين
    peers = min(p["peers"] for p in paths.values())
    spread = max(p["spread"] for p in paths.values())
    agree = (abs(vals[0] - vals[1]) / max(vals) if len(vals) == 2 else 0.0)
    # ══ التشتّتُ وحدَه يكفي للخفض ══ (كشفه `relative_value_check.py`)
    # كانت العتباتُ الأولى تشترط عشرةَ نظائرَ للثقة المرتفعة وتسمح بتشتّتٍ
    # حتى ‎5.0 للمتوسطة، فمرّ قطاعٌ مضاعفاتُه بين ‎4 و‎90 بثقةٍ متوسطة —
    # كأنه قطاعٌ متقارب. والتشتّتُ هو جوهرُ الطريقة: وسيطُ قطاعٍ متباعدٍ
    # لا يقول عن السهم شيئاً. فصار يخفض وحدَه مهما كثُر العدد.
    # العتباتُ معايَرةٌ للمدى الرُّبيعيّ لا للمدى الكامل — وهو أصغرُ عدداً
    # بطبيعته، فنقلُ المقياس بلا نقلِ عتباته يجعل الحارسَ بلا أثر.
    # ‎0.35 يعني: النصفُ الأوسط من مضاعفات القطاع داخل ثُلثِ وسيطه.
    # ══ الدرجةُ تقول لماذا ══
    # عُويرت العتباتُ مرّتين بالحدس، ولم يُعرف أيُّ شرطٍ يخفض فعلاً: أهو
    # قلّةُ النظائر أم التشتّتُ أم اختلافُ المسارين أم غيابُ أحدهما؟ فصار
    # القيدُ المُلزِمُ يُسجَّل مع الدرجة. معايرةُ ما لا يُقاس تخمين.
    blocks: list[str] = []
    if len(paths) < 2:
        blocks.append("مسارٌ واحد")
    if peers < 8:
        blocks.append(f"نظائر {peers}")
    if spread > 0.35:
        blocks.append(f"تشتّت {spread:.2f}")
    if agree > 0.25:
        blocks.append(f"تباعدُ المسارين {agree:.2f}")
    out["confidence_why"] = blocks

    if not blocks:
        out["confidence"] = "مرتفعة"
    elif peers >= MIN_PEERS and spread <= 0.80 and agree <= 0.60:
        out["confidence"] = "متوسطة"
    else:
        out["confidence"] = "منخفضة"
    # المسارُ الواحد لا يبلغ «مرتفعة» أبداً — لا مُقاطعَ يسنده.
    return out


def relative_value(*, sector: str | None, price: float | None,
                   pe: float | None, pb: float | None,
                   book_value: float | None, table: SectorTable) -> dict:
    """قيمةٌ نسبيةٌ إلى القطاع لشركةٍ **مدرَجة** — أو امتناعٌ مُعلَّل.

    تُعاد دائماً بنية واحدة؛ و`value=None` تعني الامتناع، و`why` سببَه.
    وربحيةُ السهم تُشتقّ من السعر والمكرّر — كلاهما عندنا، فلا نداءَ زائد.
    """
    own_pe = _ok(pe, *PE_RANGE)
    own_pb = _ok(pb, *PB_RANGE)
    px = _ok(price, 0.0, 1e9)
    return value_from_metrics(
        sector=sector,
        eps=(px / own_pe if own_pe and px else None),
        bvps=book_value, table=table, own_pe=own_pe, own_pb=own_pb)


# ══════════════════════════════════════════════════════════════════════════
# مُنتِجٌ واحدٌ للسعر العادل — بمائدةٍ واحدةٍ ومدخلاتٍ واحدة (D240)
#
# كان لكلٍّ من صفحة السهم والفرز بناؤه الخاصّ للمائدة ومدخلاتِه:
#   · الصفحةُ تبني المائدةَ من المخزن **مصفَّى على السوق الرئيسي**، وتقرأ
#     مضاعفَ الشركة من المخزن وحدَه.
#   · والفرزُ يبنيها من المخزن **كلِّه**، ويقرأ المضاعفَ من الكاش أوّلاً.
# فاختلف وسيطُ القطاع واختلف ما يُنزَع منه — فخرج رقمان لمعنًى واحد:
# ‎28 خلافاً في أربعين شركة (‏1111: ‎44.42 في الفرز و‎38.92 في الصفحة).
# وهو صنفُ العطب الذي تكرّر في هذا التطبيق أكثرَ من غيره، ولا يُعالج
# بتقريب حسابين بل بإلغاء أحدهما.
# ══════════════════════════════════════════════════════════════════════════

def market_table(store: dict) -> SectorTable:
    """مائدةُ مضاعفات القطاعات — تعريفٌ واحدٌ لكلّ من يسأل.

    الكونُ هو السوقُ الرئيسيّ (‏main_market): هو ما يُعرض ويُقارَن به،
    وإدخالُ غيره يُحرّك الوسيطَ بشركاتٍ لا تظهر في أيّ شاشة.
    """
    from app.data.company_sectors import SYMBOL_TO_SECTOR_AR as _SEC
    from app.data.market_universe import MARKET_UNIVERSE as _MU
    from app.data.universe import main_market as _mm
    allowed = _mm(_MU)
    return SectorTable(
        {"sector": _SEC.get(k), "pe": (v or {}).get("pe_ratio"),
         "pb": (v or {}).get("price_to_book")}
        for k, v in (store or {}).items() if k in allowed)


def value_for(symbol: str, price, *, store: dict, fund: dict | None = None,
              table: SectorTable | None = None) -> dict:
    """السعرُ العادل لشركةٍ واحدة — مدخلاتٌ واحدةٌ لكلّ مستدعٍ.

    ‏`fund` كاشُ المزوّد إن وُجد؛ ويُقدَّم على المخزن لأنه الأحدث — وهو
    ما تقرؤه صفحةُ السهم. والمضاعفُ المقروءُ هنا هو نفسُه المنزوعُ من
    وسيط القطاع، فلا تُقارَن الشركةُ بنفسها.
    """
    from app.data.company_sectors import SYMBOL_TO_SECTOR_AR as _SEC
    base = str(symbol).replace(".SR", "")
    row = (store or {}).get(base) or {}
    f = fund or {}

    def pick(key):
        v = f.get(key)
        return v if v is not None else row.get(key)

    return relative_value(
        sector=_SEC.get(base), price=price,
        pe=pick("pe_ratio"), pb=pick("price_to_book"),
        book_value=pick("book_value"),
        table=table if table is not None else market_table(store))


def fields_for(symbol: str, price, *, store: dict, fund: dict | None = None,
               table: SectorTable | None = None) -> dict:
    """حقولُ العرض جاهزةً — تسميةٌ واحدةٌ للحقول في كلّ شاشة."""
    rv = value_for(symbol, price, store=store, fund=fund, table=table)
    if rv["value"] is None:
        return {"rel_value": None, "rel_low": None, "rel_high": None,
                "rel_conf": None, "rel_basis": None, "rel_upside_pct": None,
                "rel_confidence_why": [], "rel_paths": 0,
                "rel_why": rv["why"]}
    up = (round((rv["value"] - price) / price * 100, 1)
          if isinstance(price, (int, float)) and price > 0 else None)
    return {"rel_value": round(rv["value"], 2),
            "rel_low": round(rv["low"], 2), "rel_high": round(rv["high"], 2),
            "rel_conf": rv["confidence"], "rel_basis": rv["basis"],
            "rel_confidence_why": rv.get("confidence_why") or [],
            "rel_paths": len(rv.get("paths") or {}),
            "rel_upside_pct": up, "rel_why": None}
