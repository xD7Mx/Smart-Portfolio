"""فحصُ القرار — السلسلةُ كاملةً من القوائم إلى الكلمة التي تُقرأ.

## لماذا

فُحصت الدرجةُ وحدها (`rank_check`)، والقيمةُ العادلة وحدها
(`value_check`)، والمتانةُ بمدخلاتٍ عشوائية (`random_check`). ولم يُفحص
**القرار** — وهو المخرَجُ الوحيد الذي يقرؤه المستثمر ويتصرّف عليه.

والقرارُ ليس درجةً ولا قيمة، بل حصيلةُ اجتماعهما: شركةٌ ممتازة بسعرٍ
مرتفع ليست فرصة، وشركةٌ رخيصةٌ رديئة ليست فرصة، وشركةٌ لا نعرفها لا
حكمَ لها. وأوّلُ عطبٍ عرضه المالك في هذا المشروع كان من هذا الباب
بعينه: قرارُ «شراء» وسعرُ السهم فوق القيمة التي يعرضها التطبيق في
الصفحة نفسها.

فهذا يشغّل السلسلةَ كما يشغّلها التطبيق حرفياً — السماتُ ثم البطاقةُ ثم
الخطوطُ الحمراء ثم بوّابةُ القرار ثم القيمةُ العادلة ثم سقفُها — لكلّ
نمطٍ من الأحد عشر، ويسأل:

  · **أيتناقض القرارُ مع الأرقام المعروضة معه؟** «شراء» فوق القيمة
    العادلة تناقضٌ يُفقد الثقةَ بالتطبيق كلِّه.
  · **أتُنتِج الجودةُ العالية بسعرٍ منخفض قراراً مختلفاً عن الجودة
    العالية بسعرٍ مرتفع؟** وإلّا فالسعرُ لا يدخل الحكم.
  · **أيُبطِل الخطُّ الأحمر كلَّ ما سواه؟**
  · **أتمتنع الأداةُ حيث يجب؟** بياناتٌ قديمة · بلا قيمةٍ عادلة · تغطيةٌ
    دون الحدّ.
  · **أتُترجَم المفردةُ عند النشر العامّ؟**

## التشغيل

    python scripts/audit/decision_check.py
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

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from rank_check import ARCH_SECTOR, company          # noqa: E402


def decide_full(periods: list[dict], sector: str, price: float,
                symbol: str = "1111.SR") -> dict:
    """السلسلةُ كما في `analysis.py` حرفياً — لا نسخةٌ مبسّطة منها.

    ونسخةٌ مبسّطة تُخفي العطب: لو اختصرنا خطوةً هنا لَفحصنا شيئاً غير
    الذي يعمل عند المالك.
    """
    from app.services.four_scores import (build_company_features,
                                          compute_four_scores, CategoryScore)
    from app.services.decision_engine import (evaluate_decision,
                                              apply_fair_value_ceiling,
                                              public_label)
    from app.services import spec_score, red_lines, governance_pillar
    from app.services.fair_value import compute as fv_compute

    # ══ المعلوماتُ الملخّصة تتبع النمطَ كما تتبعه القوائم ══
    # كانت واحدةً للجميع، فخرج الريتُ متضاربَ المسارات (توزيعٌ في
    # الملخّص لا يطابق توزيعَ قوائمه) وامتنع التأمينُ دائماً (لا نسبةَ
    # مجمّعة). وهو درسُ D101 و D110 نفسُه للمرّة الثالثة: عيّنةٌ لا تشبه
    # من تقيسه تقيس شيئاً آخر.
    _base = {"beta": 1.0, "eps": 2.0, "book_value": 20.0, "roe": 15.0,
             "dividend_per_share": 0.8}
    _arch0 = __import__("app.services.spec_score", fromlist=["x"]) \
        .resolve_archetype_ex(sector, {})[0]
    if _arch0 == "reit":
        # توزيعُ الصندوق في الملخّص = ما توزّعه قوائمُه فعلاً للسهم
        _dv = abs(periods[-1].get("dividends_paid") or 0)
        _sh = periods[-1].get("shares_outstanding") or 1
        _base["dividend_per_share"] = _dv / _sh
    if _arch0 == "insurance":
        # النسبةُ المجمّعة تصل من «أرقام» في التطبيق — تُمرَّر هنا ليُختبر
        # القطاعُ فعلاً بدل أن يمتنع دائماً بسبب غيابها عن العيّنة.
        _base["_regulatory_ratios"] = {"combined_ratio": 94.0}
    feats, info, _q = build_company_features(periods, info=_base,
                                             sector=sector)
    four = compute_four_scores(feats, sector=sector)
    sp = spec_score.compute(feats, sector)
    lines = red_lines.check(feats, periods, sp.archetype)
    gov_p = governance_pillar.build(feats, periods, None)
    if sp.score is not None:
        four.quality = CategoryScore(score=sp.score,
                                     hits=list(four.quality.hits),
                                     coverage=sp.coverage)
    dec = evaluate_decision(four, feats, sector)
    fv = fv_compute(info=info, price=price, sector_avg_pe=15,
                    periods=periods, archetype=sp.archetype, symbol=symbol)
    covs = [c for c in (four.quality.coverage, four.safety.coverage)
            if isinstance(c, (int, float))]
    cov = (sum(covs) / len(covs)) if covs else None
    final = apply_fair_value_ceiling(
        dec, price, fv.get("value"), fv.get("entry_price"),
        single_path=bool(fv.get("single_path")), coverage=cov,
        nomu=bool(fv.get("nomu")), red_lines=lines,
        implausible=bool(fv.get("implausible")))
    return {"decision": final.decision, "rule": final.matched_rule_id,
            "reason": final.reason, "quality": sp.score,
            "coverage": sp.coverage, "value": fv.get("value"),
            "entry": fv.get("entry_price"), "price": price,
            "red_lines": [r["id"] for r in lines],
            "archetype": sp.archetype, "public": public_label(final.decision),
            "governance": gov_p.get("score")}


BUY = ("شراء قوي", "شراء")


def main() -> int:
    fails: list[str] = []
    print("═" * 78)
    print("  فحصُ القرار — السلسلةُ كاملةً، أحدَ عشرَ نمطاً")
    print("═" * 78)
    print(f"  {'النمط':20}{'جودة':>7}{'قيمة':>9}{'سعر':>8}  {'القرار':16} السبب")
    print("─" * 78)

    for arch, sector in ARCH_SECTOR.items():
        strong = company(0.95, arch)
        weak = company(0.05, arch)

        # ══ السعرُ يُنسب إلى القيمة لا يُختار جزافاً ══
        # كانت الأسعارُ ثابتة (‏8 و‎90)، فخرج الخصمُ ‎78٪ — وهو خارج حدّ
        # العقل، فتُلغى القيمةُ ويصير المخرَجُ «بيانات غير كافية» في
        # الحالة التي يُفترض أن تكون **أوضحَ فرصة**. والعطبُ في العيّنة:
        # سعرٌ لا يشبه سوقاً حقيقية يقيس الحارسَ لا القرار.
        # فيُقاس التقديرُ أوّلاً ثم يوضع السعرُ منه: خصمُ ‎40٪ وعلاوةُ ‎60٪
        # وهما مدىً واقعيّ في تداول.
        ref = decide_full(strong, sector, price=30.0)
        base = ref["value"] or 30.0
        cheap = decide_full(strong, sector, price=round(base * 0.60, 2))
        rich = decide_full(strong, sector, price=round(base * 1.60, 2))
        wref = decide_full(weak, sector, price=30.0)
        bad = decide_full(weak, sector, price=round((wref["value"] or 30.0) * 0.60, 2))

        for tag, r in (("رخيصة", cheap), ("غالية", rich), ("رديئة", bad)):
            v = r["value"]
            print(f"  {arch:20}{str(r['quality']):>7}"
                  f"{(f'{v:.1f}' if v else '—'):>9}{r['price']:>8.0f}  "
                  f"{r['decision']:16} {tag} · {r['rule'][:28]}")

        # ══ الثابتُ الأوّل: لا شراءَ فوق القيمة العادلة ══
        # وهو أوّلُ عطبٍ عرضه المالك في هذا المشروع.
        for r in (cheap, rich, bad):
            if (r["decision"] in BUY and r["value"] and r["price"]
                    and r["price"] > r["value"]):
                fails.append(f"{arch}: «{r['decision']}» وسعرُ السهم "
                             f"({r['price']}) فوق القيمة ({r['value']})")

        # ══ السعرُ يدخل الحكم ══
        if cheap["decision"] in BUY and rich["decision"] in BUY:
            fails.append(f"{arch}: السعرُ لا يغيّر الحكم — رخيصةً وغاليةً "
                         f"كلتاهما «{cheap['decision']}»")

        # ══ الجيّدةُ بسعرٍ معقول لا تُقابَل بامتناع ══
        # أفضلُ ما في السوق يجب ألّا يخرج «بيانات غير كافية».
        if cheap["decision"] == "بيانات غير كافية":
            fails.append(f"{arch}: شركةٌ ممتازة بخصمِ ‎40٪ خرجت امتناعاً "
                         f"({cheap['rule']})")

        # ══ الرديئةُ لا تُشترى ══
        if bad["decision"] in BUY:
            fails.append(f"{arch}: شركةٌ في أدنى عشيرتها خرجت «{bad['decision']}»")

    # ── الخطُّ الأحمر يُبطِل كلَّ ما سواه ──
    print("\n" + "─" * 78)
    print("  البوّابات")
    print("─" * 78)
    good = company(0.95, "asset_light")
    red = [{**p, "total_equity": -abs(p["total_equity"]),
            "equity": -abs(p["total_equity"])} for p in good]
    _rr = decide_full(good, "التقنية", price=30.0)
    _pb = round((_rr["value"] or 30.0) * 0.6, 2)
    r = decide_full(red, "التقنية", price=_pb)
    print(f"  خطٌّ أحمر على شركةٍ ممتازة      {r['decision']:20} {r['red_lines']}")
    if r["decision"] != "تجنب":
        fails.append(f"خطٌّ أحمر لم يُبطِل الحكم: {r['decision']}")

    # ── بياناتٌ قديمة ──
    old = [{**p, "as_of": f"{p['year'] - 3}-12-31", "year": p["year"] - 3}
           for p in good]
    r = decide_full(old, "التقنية", price=_pb)
    print(f"  قوائمُ عمرُها ثلاثُ سنوات        {r['decision']:20} {r['rule']}")
    if r["rule"] != "stale_data":
        fails.append(f"قوائمُ قديمة لم تمنع الحكم: {r['rule']}")

    # ── سوقٌ موازية ──
    r = decide_full(good, "التقنية", price=_pb, symbol="9411.SR")
    print(f"  ورقةٌ في «نمو»                  {r['decision']:20} {r['rule'][-20:]}")
    if r["decision"] in BUY:
        fails.append("ورقةُ «نمو» خرجت قابلةً للشراء")

    # ── المفردةُ عند النشر العامّ ──
    os.environ["SP_PUBLIC"] = "1"
    import importlib
    from app.services import decision_engine as de
    importlib.reload(de)
    lbl = de.public_label("شراء قوي")
    print(f"  المفردةُ عند النشر العامّ        {lbl}")
    if lbl == "شراء قوي":
        fails.append("المفردةُ لا تُترجَم عند النشر العامّ")
    os.environ.pop("SP_PUBLIC", None)
    importlib.reload(de)

    print("\n" + "═" * 78)
    if fails:
        print(f"  ✖ أخفق {len(fails)}:")
        for m in fails[:20]:
            print(f"      · {m}")
        return 1
    print("  ✔ لا قرارَ يناقض أرقامَه · السعرُ يدخل الحكم · البوّاباتُ تعمل.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
