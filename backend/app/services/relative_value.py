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
        return {"n": len(v), "median": med, "q1": q1, "q3": q3,
                "spread": (v[-1] - v[0]) / med if med else 0.0}

    def for_sector(self, sector: str, *, own_pe: float | None = None,
                   own_pb: float | None = None) -> dict:
        return {
            "pe": self._stats(self.pe.get(sector, []), own_pe),
            "pb": self._stats(self.pb.get(sector, []), own_pb),
        }


def relative_value(*, sector: str | None, price: float | None,
                   pe: float | None, pb: float | None,
                   book_value: float | None, table: SectorTable) -> dict:
    """قيمةٌ نسبيةٌ إلى القطاع لشركةٍ واحدة — أو امتناعٌ مُعلَّل.

    تُعاد دائماً بنية واحدة؛ و`value=None` تعني الامتناع، و`why` سببَه.
    """
    out: dict = {"value": None, "low": None, "high": None,
                 "confidence": None, "paths": {}, "why": None,
                 "basis": "قيمة نسبية إلى القطاع"}
    if not sector:
        out["why"] = "القطاع غير مصنّف"
        return out
    own_pe = _ok(pe, *PE_RANGE)
    own_pb = _ok(pb, *PB_RANGE)
    px = _ok(price, 0.0, 1e9)
    bvps = _ok(book_value, 0.0, 1e9)

    t = table.for_sector(sector, own_pe=own_pe, own_pb=own_pb)
    paths: dict[str, dict] = {}

    # ── مسارُ المكرّر ──
    # ربحيةُ السهم تُشتقّ من السعر والمكرّر — كلاهما عندنا، فلا نداءَ زائد.
    if t["pe"] and own_pe and px:
        eps = px / own_pe
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
    if peers >= 8 and spread <= 1.5 and agree <= 0.25 and len(paths) == 2:
        out["confidence"] = "مرتفعة"
    elif peers >= MIN_PEERS and spread <= 3.0 and agree <= 0.60:
        out["confidence"] = "متوسطة"
    else:
        out["confidence"] = "منخفضة"
    # المسارُ الواحد لا يبلغ «مرتفعة» أبداً — لا مُقاطعَ يسنده.
    return out
