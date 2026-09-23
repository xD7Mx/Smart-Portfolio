"""فحصُ القيمة العادلة — سلوكٌ يُقاس لا شيفرةٌ تُقرأ.

## لماذا

نصفُ الميزة درجةٌ ونصفُها قيمةٌ عادلة. وللدرجة فحصٌ سلوكيّ
(`rank_check.py`)، وللقيمة العادلة لم يكن شيء: حرّاسٌ يقرأون النصّ
ويكشفون غيابَ سطر، ولا يكشفون نموذجاً يستجيب للمدخلات استجابةً مقلوبة.

فهذه أسئلةٌ لا يُجيب عنها إلا تشغيلُ النموذج:

  · **أترتفع القيمةُ مع الربحية؟** شركةٌ أعلى عائداً يجب أن تُقدَّر أعلى.
  · **أتنخفض مع المخاطرة؟** بيتا أعلى ⇒ عائدٌ مطلوب أعلى ⇒ قيمةٌ أقلّ.
  · **أتنخفض مع الدَّين؟** رافعةٌ أثقل ⇒ حقوقُ ملكيةٍ أقلّ قيمة.
  · **أيبقى التقديرُ داخل حدّ العقل؟** ولا يخرج رقمٌ شاذٌّ إلى الشاشة.
  · **أتزيد الثقةُ بازدياد الشواهد؟** مساراتٌ أكثر ⇒ ثقةٌ أعلى وهامشُ
    أمانٍ أضيق.
  · **أيمتنع حين يجب؟** بلا قوائمَ لا قيمة. أمّا مؤمِّنٌ بلا نسبةٍ مجمّعة
    **فيُقيَّم بتحفّظٍ مُسعَّر** لا يُفرَّغ (‏بأمر المالك: «غيرُ متوفّرٍ
    عجزُ بناء»): ثقةٌ منخفضةٌ مسمّاةُ السبب، وهامشُ أمانٍ أوسع.
  · **أيُبقي سعرَ الدخول دون القيمة دائماً؟** سعرُ دخولٍ فوق القيمة
    العادلة تناقضٌ في ذاته.

## التشغيل

    python scripts/audit/value_check.py
"""

from __future__ import annotations

# ══ فحصٌ لا يكتب في بيانات المالك ══ (D160)
# الوحداتُ تقرأ مسارَ المخزن عند **تحميلها**، فيُحوَّل في رأس الوحدة قبل
# أيّ استيرادٍ من `app` — بما فيها الاستيراداتُ المؤجَّلة داخل الدوالّ.
# وسكربتُ فحصٍ يغيّر حالةً ليس فحصاً.
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX


import sys

import os

# ══ السكربتُ يعرف موضعَه ══
# كان يُدرج `/app` في رأس المسار، فيدهس `PYTHONPATH` ويقرأ الشيفرةَ
# المثبَّتة بدل التي يُفحَص بها — فيُفحص شيءٌ غيرُ المقصود. والترتيبُ
# هنا مقصود: يُدرج `/app` أوّلاً ثم جذرُ السكربت، فيستقرّ جذرُه في
# الصدارة ويسبق المثبَّت.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

PRICE = 30.0


def periods(profit: float = 1.0, debt: float = 300.0,
            growth: float = 0.06) -> list[dict]:
    """قوائمُ ثماني سنواتٍ — الربحيةُ والدَّينُ والنموّ متغيّراتُ الفحص."""
    rows = []
    for i in range(8):
        ni = 200 * profit * (1 + growth) ** i
        rows.append({
            "year": 2018 + i,
            "net_income": ni, "total_equity": 1300 + 70 * i,
            "revenue": 1400 * (1 + growth) ** i,
            "total_debt": debt, "shares_outstanding": 100,
            "operating_cash_flow": ni * 1.25, "capex": -60,
            "free_cash_flow": ni * 0.95, "cash": 150,
            "total_assets": 2000 + debt, "ebitda": ni * 1.6,
            "depreciation": 55, "interest_expense": debt * 0.05,
            "operating_income": ni * 1.3, "total_liabilities": 400 + debt,
            "gross_profit": 520, "current_assets": 600,
            "current_liabilities": 400, "inventory": 180,
            "dividends_paid": -ni * 0.4,
        })
    return rows


def info(roe: float = 15.0, beta: float = 1.0, eps: float = 2.0) -> dict:
    return {"eps": eps, "book_value": 20.0, "roe": roe,
            "dividend_per_share": 0.8, "beta": beta}


def _v(**kw):
    from app.services.fair_value import compute
    return compute(price=PRICE, sector_avg_pe=15, symbol="1111.SR", **kw)


def main() -> int:
    from app.services.fair_value import SANE_LOW, SANE_HIGH

    fails: list[str] = []
    print("═" * 70)
    print("  فحصُ القيمة العادلة — استجابةُ النموذج للمدخلات")
    print("═" * 70)

    # ── ١) الربحيةُ ترفع القيمة ──
    vals = []
    for p in (0.6, 1.0, 1.6):
        o = _v(info=info(roe=9 + 8 * p), periods=periods(profit=p),
               archetype="asset_light")
        vals.append(o.get("value"))
    print(f"  الربحية ×0.6 · ×1.0 · ×1.6      {vals}")
    if any(v is None for v in vals):
        fails.append("الربحية: امتناعٌ عن شركةٍ كاملة البنود")
    elif not (vals[0] < vals[1] < vals[2]):
        fails.append(f"القيمةُ لا ترتفع مع الربحية: {vals}")

    # ── ٢) المخاطرةُ تخفض القيمة ──
    vals = []
    for b in (0.6, 1.0, 1.8):
        o = _v(info=info(beta=b), periods=periods(), archetype="asset_light")
        vals.append(o.get("value"))
    print(f"  بيتا 0.6 · 1.0 · 1.8            {vals}")
    if any(v is None for v in vals):
        fails.append("بيتا: امتناعٌ غيرُ مبرَّر")
    elif not (vals[0] >= vals[1] >= vals[2]):
        fails.append(f"القيمةُ لا تنخفض مع المخاطرة: {vals}")

    # ── ٣) الدَّينُ يخفض قيمةَ حقوق الملكية ──
    vals = []
    for d in (100.0, 600.0, 1400.0):
        o = _v(info=info(), periods=periods(debt=d), archetype="asset_light")
        vals.append(o.get("value"))
    print(f"  الدَّين 100 · 600 · 1400          {vals}")
    if all(v is not None for v in vals) and not (vals[0] >= vals[-1]):
        fails.append(f"القيمةُ لا تنخفض مع الدَّين: {vals}")

    # ── ٤) حدُّ العقل يحكم كلَّ مخرَج ──
    print("\n" + "─" * 70)
    # ══ الشذوذُ يُوسَم لا يُمحى ══
    # كان الشرطُ يطلب بقاءَ كلّ قيمةٍ داخل الحدّ، وذلك يعني محوَ ما خرج —
    # فيُقال «بيانات غير كافية» عن رقمٍ حسبناه، وذلك عند أعمق خصمٍ أو
    # أفدح غلاء، أي في أوضح الحالات. فصار المطلوبُ أن يبقى الرقمُ
    # موسوماً: `implausible` وثقةٌ منخفضة وملاحظةٌ تقول لماذا.
    out_of_band = unmarked = 0
    for p in (0.2, 0.5, 1.0, 2.0, 4.0):
        for b in (0.4, 1.0, 2.5):
            o = _v(info=info(roe=5 + 10 * p, beta=b),
                   periods=periods(profit=p), archetype="asset_light")
            v = o.get("value")
            if v is None:
                continue
            if not (PRICE * SANE_LOW <= v <= PRICE * SANE_HIGH):
                out_of_band += 1
                if not o.get("implausible"):
                    unmarked += 1
                    fails.append(f"قيمةٌ شاذّة ({v} على سعر {PRICE}) بلا وسم")
                elif o.get("confidence") != "منخفضة" or not o.get("note"):
                    fails.append(f"قيمةٌ شاذّة ({v}) موسومةٌ بلا ثقةٍ منخفضة "
                                 f"أو بلا بيانِ سبب")
            elif o.get("implausible"):
                fails.append(f"قيمةٌ داخل الحدّ ({v}) وُسمت شاذّة")
    print(f"  خمسَ عشرةَ حالة · خارج الحدّ {out_of_band} · بلا وسم {unmarked}")

    # ── ٥) سعرُ الدخول دون القيمة دائماً ──
    bad_entry = 0
    for p in (0.4, 1.0, 2.5):
        o = _v(info=info(roe=8 + 9 * p), periods=periods(profit=p),
               archetype="asset_light")
        v, e = o.get("value"), o.get("entry_price")
        if v and e and e >= v:
            bad_entry += 1
            fails.append(f"سعرُ دخولٍ ({e}) ليس دون القيمة ({v})")
    print(f"  سعرُ الدخول دون القيمة: {'✔' if not bad_entry else '✖'}")

    # ── ٦) الثقةُ تتبع عددَ الشواهد ──
    many = _v(info=info(), periods=periods(), archetype="asset_light")
    few = _v(info={"book_value": 20.0, "roe": 15.0, "beta": 1.0},
             periods=periods(), archetype="bank")
    print(f"  ثقةٌ بثلاثة مسارات: {many.get('confidence')}  ·  "
          f"بمسارٍ واحد: {few.get('confidence')}  "
          f"(مسارٌ واحد={few.get('single_path')})")
    if len(many.get("methods") or []) < 2:
        fails.append("شركةٌ كاملةُ البنود لا تُنتج مسارين")
    if (many.get("margin_of_safety_pct") or 0) > (few.get("margin_of_safety_pct") or 100):
        fails.append("هامشُ الأمان لا يتّسع حين تقلّ الشواهد")

    # ── ٧) يمتنع حين يجب ──
    print("\n" + "─" * 70)
    cases = [
        ("بلا قوائم", _v(info=info(), periods=[], archetype="asset_light")),
        ("بلا أيّ مدخل", _v(info={}, periods=[], archetype="asset_light")),
    ]
    for name, o in cases:
        v = o.get("value")
        why = (o.get("unavailable_reason") or "")[:44]
        print(f"  {name:26} قيمة={str(v):>6}  {why}")
        if v is not None:
            fails.append(f"«{name}»: قيمةٌ خرجت حيث يجب الامتناع")
        elif not o.get("unavailable_reason"):
            fails.append(f"«{name}»: امتناعٌ بلا سبب")

    # ── ٧ب) مؤمِّنٌ بلا نسبةٍ مجمّعة: يُسعَّر ولا يُفرَّغ ══ (D428)
    # كان في قائمة «يمتنع حين يجب» بقاعدةٍ سابقة. والقاعدةُ المعتمدةُ في
    # المحرّك (‏`fair_value.py` عند `_ins_no_cr`) أنّ غيابها **تحفّظٌ يُعلَن
    # ويُسعَّر**. فسقط الفحصُ على شفرةٍ صحيحة — والفحصُ الآن يقيس ما تقوله
    # القاعدة: قيمةٌ، وثقةٌ منخفضةٌ باسم السبب، وهامشُ أمانٍ متّسع.
    _ins = _v(info=info(), periods=periods(), archetype="insurance")
    _why = " · ".join(str(x) for x in (_ins.get("confidence_why") or []))
    print(f"  {'تأمينٌ بلا نسبةٍ مجمّعة':26} قيمة={str(_ins.get('value')):>6}"
          f"  ثقة={_ins.get('confidence')} · هامش={_ins.get('margin_of_safety_pct')}%")
    if _ins.get("value") is None:
        fails.append("«تأمينٌ بلا نسبةٍ مجمّعة»: فُرِّغت الخانةُ والقاعدةُ تسعيرٌ لا امتناع")
    else:
        if _ins.get("confidence") != "منخفضة":
            fails.append(f"«تأمينٌ بلا نسبةٍ مجمّعة»: ثقةٌ {_ins.get('confidence')} لا منخفضة")
        if "المجمّعة" not in _why:
            fails.append("«تأمينٌ بلا نسبةٍ مجمّعة»: خفضُ الثقة بلا اسمِ سببه")
        if (_ins.get("margin_of_safety_pct") or 0) < 35:
            fails.append(f"«تأمينٌ بلا نسبةٍ مجمّعة»: هامشُ أمانٍ {_ins.get('margin_of_safety_pct')}% دون 35")

    # ── ٨) القيمةُ لا تتبع السعر ══ (عطبٌ كشفه `decision_check.py`)
    # كان حدُّ العقل يُطبَّق على كلّ مسارٍ بمقارنته بالسعر، فيقرّر السعرُ
    # أيُّ المسارات ينجو: يغلو السهمُ فيُحذف المسارُ القائل إنه أرخص،
    # ويرخص فينجو فتتضارب المسارات ونمتنع. أي أن الأداة تصمت عند الفرصة
    # وتنطق عند الغلاء. والقيمةُ الجوهرية مسطرةٌ يُقاس بها السعر، فلا
    # يجوز أن يقيسها.
    print("\n" + "─" * 70)
    seen = {}
    for p in (12.0, 20.0, 30.0, 55.0, 90.0):
        o = _v(info=info(), periods=periods(), archetype="asset_light")
        from app.services.fair_value import compute as _c
        o = _c(info=info(), price=p, sector_avg_pe=15, periods=periods(),
               archetype="asset_light", symbol="1111.SR")
        # ‏D449 (بأمر المالك): الشاذُّ لا يُنشر «سعراً عادلاً» ويُحفظ في
        # `implausible_value`. فالمقيسُ **التقديرُ المحسوب** أنشِر أم حُجب:
        # يجب أن يكون واحداً عند كلّ سعر، والحجبُ يُعلَن سببُه.
        seen[p] = o.get("value") if o.get("value") is not None else o.get("implausible_value")
        if o.get("value") is None and o.get("implausible_value") is not None \
                and not o.get("unavailable_reason"):
            fails.append(f"تقديرٌ حُجب عند سعر {p} بلا سببٍ معلَن")
    print(f"  القيمةُ عند أسعارٍ مختلفة: {seen}")
    vs = {v for v in seen.values() if v is not None}
    if len(vs) > 1:
        fails.append(f"القيمةُ تتبع السعرَ بدل أن تُقاس به: {seen}")
    if not vs:
        fails.append("امتناعٌ عن شركةٍ كاملة البنود في كل الأسعار")
    if any(v is None for v in seen.values()):
        fails.append(f"التقديرُ يُمحى عند بعض الأسعار ولا يُحفظ: {seen}")

    # ── ٩) «نمو» تُخصم ──
    from app.services.fair_value import compute
    main_mkt = compute(info=info(), price=PRICE, sector_avg_pe=15,
                       periods=periods(), archetype="asset_light",
                       symbol="1111.SR")
    nomu = compute(info=info(), price=PRICE, sector_avg_pe=15,
                   periods=periods(), archetype="asset_light",
                   symbol="9411.SR")
    print(f"  الرئيسة {main_mkt.get('value')} · نمو {nomu.get('value')} "
          f"(خصم {nomu.get('liquidity_discount_pct')}٪)")
    if main_mkt.get("value") and nomu.get("value"):
        if nomu["value"] >= main_mkt["value"]:
            fails.append("«نمو» لا تُخصم — قيمةٌ لا تُسيَّل تُعامَل كالسائلة")

    # ── ٩) التحكيمُ قبل الامتناع — الأغلبيةُ حولَ الوسيط (D337) ────────
    # بأمر المالك: «المبدأُ ليس الاعتذارَ إن وُجد نقصٌ وإنما اكتشافُ
    # البديل المكمِّل». وقِيس على خادمه أن إكمالَ المدخلات رفع الامتناعَ
    # من ٦ إلى ٩ من ٦١ — لأن مساراتٍ صارت قابلةً للحساب فظهر خلافُها.
    # فالقاعدةُ تُقاس هنا وحدَها: معلَنةٌ متناظرةٌ لا انتقاءٌ بالهوى.
    from app.services.fair_value import arbitrate
    _b, _v9, _why = arbitrate({"متعدّد المراحل": 20.0, "نموّ دائم": 24.0,
                               "مضاعف القطاع": 90.0},
                              [20.0, 24.0, 90.0])
    if not (_why and set(_b) == {"متعدّد المراحل", "نموّ دائم"}
            and "مضاعف القطاع" in _why and "90" in _why):
        fails.append("٩ شاذٌّ واحدٌ أمام أغلبيةٍ متّفقةٍ لا يُستبعَد ويُسمّى")
    else:
        print("  ✔ ٩ الشاذُّ يُستبعَد وتُحكَّم الأغلبيةُ، ويُسمّى المستبعَد")

    if arbitrate({"أ": 11.34, "ب": 39.77}, [11.34, 39.77])[2] is not None:
        fails.append("٩ب مسارانِ متباعدان لا أغلبيةَ فيهما — يجب أن يبقى الامتناع")
    else:
        print("  ✔ ٩ب ومسارانِ متباعدان يبقى امتناعُهما — لا تحكيمَ بلا أغلبية")

    if arbitrate({"أ": 5.0, "ب": 20.0, "ج": 90.0}, [5.0, 20.0, 90.0])[2] is not None:
        fails.append("٩ج ثلاثةٌ متباعدةٌ كلُّها لا تُحكَّم بحذف واحدٍ منها")
    else:
        print("  ✔ ٩ج وثلاثةٌ متباعدةٌ كلُّها: لا يُنتقى منها رقمٌ — الامتناعُ حكم")

    if arbitrate({"أ": 10.0, "ب": 12.0, "ج": 11.0}, [10.0, 12.0, 11.0])[2] is not None:
        fails.append("٩د ومتّفقةٌ أصلاً لا يُستبعَد منها شيء")
    else:
        print("  ✔ ٩د والمتّفقةُ لا يُمَسّ منها مسار")

    print("\n" + "═" * 70)
    if fails:
        print(f"  ✖ أخفق {len(fails)}:")
        for m in fails[:15]:
            print(f"      · {m}")
        return 1
    print("  ✔ النموذجُ يستجيب للربحية والمخاطرة والدَّين، ويمتنع حين يجب.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
