"""حسمُ الجاهزية — المنهجُ الحاليّ كاملاً على السوق الرئيسة.

## ما يفعله وما لا يفعله

يطبّق ما بُني: الكونُ الرئيس · المؤشّراتُ التسعةَ عشر · توزيعاتُ
الأقران · الأبعادُ الأربعة · السقفُ المطلق · الجاهزية. **ولا يغيّر
وزناً ولا عتبةً ولا بوّابة**، ويُثبت ذلك باختبارٍ يقارنها بقيمٍ
مكتوبةٍ هنا حرفاً بحرف (‏الاختبار ١٢).

ثم يُخرج:

  · جدولَ القرار لكلّ شركةٍ إلى ملفٍّ (‏`decision_table.csv`) فلا يُغرق
    الطرفية
  · اثني عشرَ اختبارَ سلامةٍ يمنع كلٌّ منها خطأً بعينه
  · ملخّصاً تنفيذياً قصيراً
  · وحكماً واحداً: `DECISION_READY` أو `NOT_DECISION_READY`

والحكمُ **يحسبه البرنامج** من نتائج الاختبارات، لا يكتبه أحد. وقاعدتُه
كما نصّ المالك: إن اجتازت اختباراتُ السلامة كلُّها وصحّ الكونُ وعُولجت
البياناتُ المتاحة بالقواعد القائمة — فالحكمُ جاهز، مهما كان عددُ
`INVESTMENT_READY`. فقلّةُ الجاهزين حالُ بياناتٍ تُعرض، لا عيبٌ يُداوى
بتخفيف عتبة.

    docker exec sp_backend python /app/scripts/audit/decide.py
"""

from __future__ import annotations

import asyncio
import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT_CSV = os.environ.get("SP_DECISION_CSV", "/tmp/decision_table.csv")
OUT_JSON = os.environ.get("SP_DECISION_JSON", "/tmp/decision_payload.json")
MIN_PEERS = 3
PRICE_BASED = {"p_e", "p_b", "ev_ebitda", "p_ffo", "p_e_normalized",
               "dividend_yield", "fv_discount"}

# ══ الثوابتُ المعتمدة — يقارنها الاختبارُ ١٢ فيفشل إن تغيّرت سهواً ══
EXPECTED_WEIGHTS = {
    "FINANCIAL":   {"quality": .35, "dividend": .20, "growth": .15, "valuation": .30},
    "REIT":        {"quality": .30, "dividend": .30, "growth": .15, "valuation": .25},
    "CYCLICAL":    {"quality": .30, "dividend": .15, "growth": .25, "valuation": .30},
    "OPERATING":   {"quality": .30, "dividend": .20, "growth": .25, "valuation": .25},
    "REAL_ESTATE": {"quality": .30, "dividend": .15, "growth": .20, "valuation": .35},
}
EXPECTED_CEILINGS = {"negative_equity": 25.0, "loss_last_year": 45.0,
                     "interest_below_one": 35.0, "payout_over_earnings": 60.0,
                     "negative_ocf": 50.0}
EXPECTED_MIN_COMPLETENESS = 0.80
EXPECTED_MIN_MEDIAN_ROE = 5.0
EXPECTED_MIN_COMPONENT_COVERAGE = 0.34


def _med(v):
    s = sorted(v)
    return None if not s else (s[len(s) // 2] if len(s) % 2
                               else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2)


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) \
        and math.isfinite(x)



def _decision_object(x: dict) -> dict:
    """كائنُ القرار بالأسماء التي تستهلكها الواجهة.

    ولا يُختلق حقل: ما لم يُقَس يخرج `null` صريحاً، والقوائمُ الفارغة
    تبقى فارغة. فالواجهةُ تعرض «غير متاح» ولا تعرض صفراً.
    """
    ex = x.get("_explain") or {}
    codes = [c for c in (x.get("BlockingCodes") or "").split(",") if c]
    reason = x.get("BlockingReason") or ""
    if x["Readiness"] == "INVESTMENT_READY":
        reason = ("المحاورُ الجوهريةُ مقيسة، وطريقةُ التقييم معلَنة، "
                  "والاكتمالُ والثقةُ فوق الحدّ، ولا بوّابةَ مخاطر مغلقة")
    return {
        "ticker": x["Ticker"],
        "company_name": x["Company"],
        "market": "MAIN_MARKET",
        "sector": x["Sector"] or None,
        "archetype": x["Archetype"] or None,
        "model": x["Model"] or None,
        "final_score": x["FinalScore"],
        "relative_score": x["RelativeScore"],
        "decision_status": x["Readiness"],
        "rank_in_class": x.get("RankInClass"),
        "quality_score": x["Quality"],
        "growth_score": x["Growth"],
        "distribution_score": x["Distribution"],
        "valuation_score": x["Valuation"],
        "completeness": x["Completeness"],
        "confidence": x["Confidence"],
        "valuation_method": x["ValuationMethod"] or None,
        "fair_value": x["FairValue"],
        "price": x["Price"],
        "upside_pct": x["Upside"],
        "risk_gate": x["RiskGate"] or None,
        "absolute_ceiling": x["AbsoluteCeiling"],
        "positive_drivers": [
            {"metric": c["key"], "label": c["label"], "value": c["value"],
             "note": c["note"], "impact": c["impact"]}
            for c in (ex.get("raised_by") or [])[:3]],
        "negative_drivers": [
            {"metric": c["key"], "label": c["label"], "value": c["value"],
             "note": c["note"], "impact": c["impact"]}
            for c in (ex.get("lowered_by") or [])[:3]],
        "blockers": codes,
        "decision_reason": reason,
    }


async def main(argv: list[str]) -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data import universe as uni
    from app.data.economic_models import (COMPONENTS, CORE_AXES, WEIGHTS_OF_MODEL,
                                          grade_of, model_of)
    from app.services import peer_distribution as pd
    from app.services import investment_score as inv
    from app.services import spec_score, red_lines, risk_gate
    from app.services import model_valuation as mv
    from app.services import investment_readiness as rdy
    from app.services import canonical as cn
    from app.services import absolute_quality as aq
    from app.data.saudi_directory import name_of
    from app.services.four_scores import build_company_features
    from app.services.market_data import market_service

    tests: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = ""):
        tests.append((name, bool(ok), detail))

    # ══ ١ — تثبيتُ الكون ══
    cen = uni.census(MARKET_UNIVERSE)
    MAIN = uni.main_market(MARKET_UNIVERSE)
    check("١ لا «نمو» داخل الكون التحليليّ",
          not [s for s in MAIN if uni.is_nomu(s)] and cen["unknown"] == 0,
          f"رئيسيّ {cen['main']} · موازية مستبعَدة {cen['nomu']} · "
          f"مجهول {cen['unknown']}")

    dist = await pd.build()
    in_dist = int(dist.get("companies") or 0)
    check("٤ توزيعُ الأقران من الرئيسة وحدها",
          in_dist <= cen["main"],
          f"دخلت التوزيعَ {in_dist} · سقفُها {cen['main']}")

    ranked = {k for m in COMPONENTS.values() for c in m.values()
              for k, _l, _w, d in c if k not in PRICE_BASED and d != "discount"}
    archs = sorted(dist.get("archetypes") or {})
    no_dist = [k for k in ranked
               if not any(k in dist["archetypes"].get(a, {}) for a in archs)]
    # يُؤجَّل الحكمُ حتى تُقرأ الشركات: العشيرةُ تُعدّ فيُعرف أهو عطبُ
    # تركيبٍ (القيمُ موجودةٌ ولم يُبنَ توزيع) أم شحٌّ حقيقيّ (لا تبلغ
    # عشيرةٌ الحدَّ). والأوّلُ إخفاقٌ والثاني حالُ بيانات.
    thin = [(a, k) for a in archs for k, v in dist["archetypes"][a].items()
            if v.get("n", 0) < pd.MIN_COHORT]
    check("٣ب لا عشيرةَ دون الحدّ", not thin,
          f"MIN_COHORT={pd.MIN_COHORT} · مخالفات {len(thin)}")

    # ══ ٢ — تشغيلُ البيانات ══
    rows, unread = [], Counter()
    # ══ من لا قوائمَ له يُدرَج ولا يُستبعد صمتاً ══ (البند الخامس)
    # الاستبعادُ الصامتُ يجعل المجموعَ ‎268 وكأنّ السوقَ ‎268، والكونُ
    # ‎273. فتُدرَج بحالتها وسببها، فيُطابق المجموعُ الكونَ دائماً.
    unreadable: list[dict] = []
    for sym, meta in MAIN.items():
        try:
            data = await market_service.get_financials(f"{sym}.SR",
                                                       allow_supplement=False)
        except Exception as e:                                    # noqa: BLE001
            unread[f"API_ERROR:{type(e).__name__}"] += 1
            unreadable.append({"sym": sym, "sector": meta.get("sector"),
                               "code": "API_ERROR"})
            continue
        ps = (data or {}).get("periods") or []
        if len(ps) < 2:
            _w = "TOO_FEW_PERIODS" if ps else "NO_PERIODS"
            unread[_w] += 1
            unreadable.append({"sym": sym, "sector": meta.get("sector"),
                               "code": _w})
            continue
        info = {}
        try:
            ci = await market_service.get_company_info(f"{sym}.SR")
            if isinstance(ci, dict):
                info = dict(ci)
        except Exception:                                         # noqa: BLE001
            pass
        try:
            fe, inf, _ = build_company_features(ps, info=info,
                                                sector=meta.get("sector"))
            merged = dict(inf or {}); merged.update(info)
            fe.update(inv.price_features(merged, fe, ps))
            crows, _s = cn.normalize(ps)
            dv = cn.dividends(crows, merged, merged.get("current_price"))
            for k in ("dividend_yield", "dividend_years",
                      "dividend_growth", "payout_ratio"):
                if dv.get(k) is not None:
                    fe[k] = dv[k]
                else:
                    fe.pop(k, None)
        except Exception as e:                                    # noqa: BLE001
            unread[f"FEATURE_BUILD_ERROR:{type(e).__name__}"] += 1
            unreadable.append({"sym": sym, "sector": meta.get("sector"),
                               "code": "FEATURE_BUILD_ERROR"})
            continue
        rows.append({"sym": sym, "sector": meta.get("sector"), "ps": ps,
                     "crows": crows, "fe": fe, "inf": merged})

    # وسائطُ القطاع — من الرئيسة وحدها بحكم `rows`
    bys = defaultdict(lambda: defaultdict(list))
    for r in rows:
        for k in list(PRICE_BASED - {"fv_discount"}) + ["roe"]:
            v = inv._val(r["fe"], k)
            if _finite(v):
                bys[r["sector"] or ""][k].append(v)
    medians = {s: {k: _med(v) for k, v in ks.items() if len(v) >= MIN_PEERS}
               for s, ks in bys.items()}

    # ══ ٣ · ٤ · ٥ — المؤشّرات والأبعادُ والجاهزية ══
    out: list[dict] = []
    nan_hits, gate_hits, method_bad, axis_ignored = 0, 0, 0, 0
    pending: list[dict] = []
    for r in rows:
        sector, ps = r["sector"], r["ps"]
        model = model_of(sector)
        # ══ بلا نموذجٍ لا تدخل التسجيل ══ (المادة ٨)
        # قطاعٌ مجهولٌ يعني أنه لا مسطرةَ لهذه الورقة ولا عشيرةَ تُقارن
        # بها. فتُسجَّل **بانتظار التصنيف** ولا تُمنح درجةً مصطنعة، وتبقى
        # داخل كون السوق الرئيسة فيطابق المجموعُ الكونَ.
        if model is None:
            pending.append({"sym": r["sym"], "sector": sector,
                            "code": "PENDING_CLASSIFICATION"})
            continue
        arch = spec_score.resolve_archetype_ex(sector, {})[0]
        fe = dict(r["fe"])
        med = medians.get(sector or "", {})
        vr = mv.valuation_report(model, fe, ps, med,
                                 r["inf"].get("current_price"))
        if vr.get("upside_pct") is not None:
            fe["fv_discount"] = vr["upside_pct"]
        res = inv.compute(fe, sector, dist, arch, medians=med, rows=r["crows"])
        ln = red_lines.check(fe, ps, arch)
        gate = risk_gate.evaluate(fe, ps, ln)
        cf, _w = inv.confidence_of(res, inv._val(fe, "years_available"))
        ready = rdy.evaluate(res, gate["status"], cf, vr.get("valuation_method"))
        c = res["components"]

        # ٦ — لا NaN/Inf يدخل الدرجة
        for v in (res.get("score"), res.get("relative_score"),
                  res.get("raw_score"), res.get("data_completeness")):
            if v is not None and not _finite(v):
                nan_hits += 1
        # ٧ — البوّابةُ سقفٌ لا خصم: النهائيةُ إمّا النسبيّةُ أو السقف
        rel, fin = res.get("relative_score"), res.get("score")
        cap = (res.get("absolute") or {}).get("ceiling", 100.0)
        if _finite(rel) and _finite(fin) and abs(fin - min(rel, cap)) > 0.05:
            gate_hits += 1
        # ٩ — طريقةُ تقييمٍ من غير طرق النموذج
        vm = vr.get("valuation_method")
        if vm and model and vm not in mv.METHODS.get(model, ()):
            method_bad += 1
        # ١٠ — محورٌ جوهريٌّ غائبٌ ومع ذلك جاهزة
        live = {k for k in ("quality", "dividend", "growth", "valuation")
                if (c.get(k) or {}).get("score") is not None}
        if ready["readiness"] == rdy.INVESTMENT_READY:
            if set(CORE_AXES.get(model or "", ())) - live:
                axis_ignored += 1

        ex = inv.explain(res)
        out.append({
            "Ticker": r["sym"], "Company": name_of(r["sym"]) or "",
            "TopPositive": " | ".join(
                f"{c['label']}: {c['value']} ({c['note']})"
                for c in ex["raised_by"][:3]),
            "TopNegative": " | ".join(
                f"{c['label']}: {c['value']} ({c['note']})"
                for c in ex["lowered_by"][:3]),
            "_explain": ex,
            "Sector": sector or "", "Archetype": arch or "",
            "Model": model or "", "FinalScore": res.get("score"),
            "RelativeScore": rel, "RawScore": res.get("raw_score"),
            # ══ المكوّنُ يُقرأ بـ`get` لا بالفهرسة ══ (D141)
            # حين لا نموذجَ للقطاع تعود `components` فارغةً، فكانت
            # الفهرسةُ ترفع KeyError وتُسقط التشغيلَ كلَّه. وقد سترَه
            # أنّ الشركات الثلاث بلا قطاعٍ لم تصلنا قوائمُها بعد؛ فأوّلُ
            # يومٍ تصل فيه يسقط الحسم. والغيابُ يُقرأ عدماً لا انهياراً.
            "Quality": (c.get("quality") or {}).get("score"),
            "Distribution": (c.get("dividend") or {}).get("score"),
            "Growth": (c.get("growth") or {}).get("score"),
            "Valuation": (c.get("valuation") or {}).get("score"),
            "Completeness": res.get("data_completeness"),
            "Confidence": cf, "RiskGate": gate["status"],
            "Readiness": ready["readiness"],
            "ValuationMethod": vm or "",
            "FairValue": vr.get("fair_value"), "Price": vr.get("current_price"),
            "Upside": vr.get("upside_pct"),
            "AbsoluteCeiling": cap,
            "BlockingReason": " | ".join(ready.get("why") or []),
            "BlockingCodes": ",".join(ready.get("codes") or []),
        })

    # ══ الاختبار ٣ — بعد إحصاء العشيرات الفعليّة ══
    avail: dict = defaultdict(Counter)
    for r in rows:
        a = spec_score.resolve_archetype_ex(r["sector"], {})[0] or "?"
        for k in ranked:
            if _finite(inv._val(r["fe"], k)):
                avail[k][a] += 1
    wiring, scarce = [], []
    for k in no_dist:
        best = max(avail[k].values(), default=0)
        (wiring if best >= pd.MIN_COHORT else scarce).append(f"{k}(أكبر عشيرة {best})")
    check("٣ لا مؤشّرَ يُرتَّب بلا توزيعٍ مع وجود عشيرةٍ صالحة",
          not wiring,
          f"{len(ranked) - len(no_dist)}/{len(ranked)} لها توزيع"
          + (f" · عطبُ تركيب: {wiring}" if wiring else "")
          + (f" · شحٌّ حقيقيّ (دون {pd.MIN_COHORT}): {scarce}" if scarce else ""))

    check("٦ لا NaN/Inf يدخل الدرجة", nan_hits == 0, f"مخالفات {nan_hits}")
    check("٧ البوّابةُ سقفٌ لا خصم", gate_hits == 0,
          f"‏Final = min(Relative, Ceiling) · مخالفات {gate_hits}")
    check("٩ طريقةُ التقييم من طرق نموذجها", method_bad == 0,
          f"مخالفات {method_bad}")
    check("١٠ لا محورَ جوهريٍّ يُتجاهَل", axis_ignored == 0,
          f"مخالفات {axis_ignored}")

    # ٢ — شركةٌ بلا نمطٍ صالح دخلت التسجيل
    no_arch = [x["Ticker"] for x in out if not x["Archetype"] or not x["Model"]]
    check("٢ لا شركةَ بلا نموذجٍ تدخل التسجيل", not no_arch,
          f"{len(no_arch)}" + (f" · {no_arch[:6]}" if no_arch else ""))

    # ٤ب — لا رمزَ من غير الرئيسة في المخرَج
    strays = [x["Ticker"] for x in out if not uni.is_main(x["Ticker"])]
    check("٤ب لا رمزَ من غير الرئيسة في التسجيل", not strays,
          f"{len(strays)}" + (f" · {strays[:6]}" if strays else ""))

    # ══ ٥ — صحّةُ الحساب والوحدة، لا نطاقٌ تجميليّ ══
    #
    # ‏«ليس NaN» لا يعني «صالحٌ اقتصادياً». فيُفصل الأمران:
    #   (أ) صحّةُ الحساب — يُعاد اشتقاقُ العائد من البنود الخام ويُقارن
    #       بالمحفوظ. فإن طابق فالصيغةُ والوحدةُ سليمتان مهما تطرّف الرقم.
    #   (ب) صلاحيةُ المقام — لا عائدَ على حقوق ملكيةٍ غيرِ موجبة، لأن
    #       الإشارةَ تنقلب فيُقرأ الخاسرُ رابحاً.
    #   (ج) القابليةُ للمقارنة — تُعدّ الملاحظاتُ المتطرّفة وتُعرض بحقوق
    #       ملكيتها، ولا تُعدّ إخفاقاً: هي وقائعُ سوقٍ لا أخطاءَ حساب.
    mism, inverted, extreme = [], [], []
    for r in rows:
        last = (r["ps"] or [{}])[-1]
        ni = last.get("net_income")
        eq = last.get("equity") if last.get("equity") is not None \
            else last.get("total_equity")
        got = inv._val(r["fe"], "roe")
        if isinstance(ni, (int, float)) and isinstance(eq, (int, float)) and eq > 0:
            want = ni / eq * 100.0
            if got is None or abs(got - want) > 0.05:
                mism.append(f"{r['sym']}({got}≠{want:.1f})")
            elif abs(got) > 100.0:
                extreme.append((r["sym"], got, eq))
        elif isinstance(eq, (int, float)) and eq <= 0 and got is not None:
            inverted.append(f"{r['sym']}(حقوق {eq:.0f} → {got:.0f}٪)")
    check("٥أ صحّةُ حساب العائد ووحدته", not mism,
          f"طوبق على {len(rows)} شركة · اختلاف {len(mism)}"
          + (f" · {mism[:5]}" if mism else ""))
    check("٥ب لا عائدَ على حقوقٍ غير موجبة", not inverted,
          f"مقلوباتُ الإشارة {len(inverted)}"
          + (f" · {inverted[:5]}" if inverted else ""))
    if extreme:
        extreme.sort(key=lambda t: abs(t[1]), reverse=True)
        print("\n  ملاحظاتٌ متطرّفةٌ صحيحةُ الحساب (حقوقٌ ضئيلةٌ موجبة):")
        for sym, v, eq in extreme[:8]:
            print(f"    {sym}  ROE {v:+.1f}٪  ·  حقوق الملكية {eq:,.0f}")
        print(f"    المجموع {len(extreme)} — تُعرض ولا تُقصّ، "
              f"والترتيبُ بالرتب فلا يفسده طرف.")

    # ٨ — لا NOT_READY يظهر جاهزاً
    contradiction = [x["Ticker"] for x in out
                     if x["Readiness"] == rdy.INVESTMENT_READY
                     and (x["BlockingCodes"] or x["RiskGate"] == "EXCLUDED")]
    check("٨ لا شركةَ ممنوعةٍ تظهر جاهزة", not contradiction,
          f"{len(contradiction)}")

    # ١١ — لا بديلَ غيرُ معتمد: كلُّ طريقةٍ من الجدول المعلَن
    known = {m for ms in mv.METHODS.values() for m in ms}
    unknown_m = [x["ValuationMethod"] for x in out
                 if x["ValuationMethod"] and x["ValuationMethod"] not in known]
    check("١١ لا طريقةَ خارج الجدول المعلَن", not unknown_m,
          f"{len(unknown_m)}")

    # ١٢ — لا تغيّرَ غيرَ مقصود في الأوزان والعتبات
    drift = []
    for m, w in EXPECTED_WEIGHTS.items():
        got = WEIGHTS_OF_MODEL.get(m, {})
        if {k: round(v, 4) for k, v in got.items()} != w:
            drift.append(f"أوزان {m}")
    for k, v in EXPECTED_CEILINGS.items():
        got = (aq.CEILINGS.get(k) or (None,))[0]
        if not isinstance(got, (int, float)) or abs(got - v) > 1e-9:
            drift.append(f"سقف {k}")
    if abs(rdy.MIN_COMPLETENESS - EXPECTED_MIN_COMPLETENESS) > 1e-9:
        drift.append("حدُّ الاكتمال")
    if abs(mv.MIN_MEDIAN_ROE - EXPECTED_MIN_MEDIAN_ROE) > 1e-9:
        drift.append("عتبةُ PB_ROE")
    if abs(inv.MIN_COMPONENT_COVERAGE - EXPECTED_MIN_COMPONENT_COVERAGE) > 1e-9:
        drift.append("حدُّ تغطية المكوّن")
    check("١٣ العدُّ يطابق الكون",
          len(out) + 0 == cen["main"]
          and len(out) == (len(out) - len(pending) - len(unreadable))
          + len(pending) + len(unreadable),
          f"صفوف {len(out)} · كون {cen['main']}")
    check("١٢ لا انحرافَ في الأوزان والعتبات", not drift,
          "مطابقةٌ حرفية" if not drift else str(drift))

    for u in pending:
        out.append({
            "Ticker": u["sym"], "Company": name_of(u["sym"]) or "",
            "Sector": u["sector"] or "", "Archetype": "", "Model": "",
            "FinalScore": None, "RelativeScore": None, "RawScore": None,
            "Quality": None, "Distribution": None, "Growth": None,
            "Valuation": None, "Completeness": None, "Confidence": "منخفضة",
            "RiskGate": "", "Readiness": rdy.NOT_READY, "ValuationMethod": "",
            "FairValue": None, "Price": None, "Upside": None,
            "AbsoluteCeiling": None, "TopPositive": "", "TopNegative": "",
            "BlockingReason": "القطاعُ غيرُ مصنَّف — لا نموذجَ ولا عشيرةَ أقران",
            "BlockingCodes": u["code"], "_explain": None})

    for u in unreadable:
        out.append({
            "Ticker": u["sym"], "Company": name_of(u["sym"]) or "",
            "Sector": u["sector"] or "", "Archetype": "", "Model": "",
            "FinalScore": None, "RelativeScore": None, "RawScore": None,
            "Quality": None, "Distribution": None, "Growth": None,
            "Valuation": None, "Completeness": None, "Confidence": "منخفضة",
            "RiskGate": "", "Readiness": rdy.NOT_READY, "ValuationMethod": "",
            "FairValue": None, "Price": None, "Upside": None,
            "AbsoluteCeiling": None, "TopPositive": "", "TopNegative": "",
            "BlockingReason": "لم تصل قوائمُ مالية كافية من المصدر",
            "BlockingCodes": u["code"], "_explain": None})

    # ══ ٧ — جدولُ القرار إلى ملفّ ══
    cols = ["Ticker", "Company", "Sector", "Archetype", "Model", "FinalScore",
            "RelativeScore", "RawScore", "Quality", "Distribution", "Growth",
            "Valuation", "Completeness", "Confidence", "RiskGate", "Readiness",
            "ValuationMethod", "FairValue", "Price", "Upside",
            "AbsoluteCeiling", "TopPositive", "TopNegative",
            "BlockingReason", "BlockingCodes"]
    try:
        with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for x in sorted(out, key=lambda z: -(z["FinalScore"] or -1)):
                w.writerow({k: x.get(k) for k in cols})
        csv_note = f"{OUT_CSV} — {len(out)} صفّاً"
    except Exception as e:                                        # noqa: BLE001
        csv_note = f"تعذّرت الكتابة: {type(e).__name__}"

    # ══ طبقةُ القرار — ترتيبٌ داخل كلّ حالة، لا خلطَ بينها ══
    #
    # الدرجةُ تقيس جودةَ الورقة المالية، والجاهزيةُ تقرّر أتصلح للقرار.
    # فالترتيبُ **داخل** كلّ حالةٍ لا عبرها: شركةٌ درجتُها ‎88 وهي
    # `NOT_READY` لا تسبق شركةً درجتُها ‎74 وهي `INVESTMENT_READY`، لأن
    # الأولى لم تُقَس أركانُها كلُّها. ولا يعني الترتيبُ الأعلى «اشترِ»:
    # يعني «الأعلى جودةً بمقياسنا داخل حالته».
    ORDER = {rdy.INVESTMENT_READY: 0, rdy.WATCH: 1, rdy.NOT_READY: 2}
    for x in out:
        x["_ord"] = ORDER.get(x["Readiness"], 3)
    ranked_rows = sorted(out, key=lambda z: (z["_ord"], -(z["FinalScore"] or -1)))
    _seen: Counter = Counter()
    for x in ranked_rows:
        _seen[x["Readiness"]] += 1
        x["RankInClass"] = _seen[x["Readiness"]]

    payload = {
        "metadata": {
            "universe": "MAIN_MARKET_TASI",
            "universe_source": cen["source"],
            "main_market_count": cen["main"],
            "excluded_nomu_count": cen["nomu"],
            "unknown_symbol_count": cen["unknown"],
            "analyzed_count": len(rows),
            "no_periods_count": unread.get("NO_PERIODS", 0),
            "too_few_periods_count": unread.get("TOO_FEW_PERIODS", 0),
            "rows_emitted": len(out),
            "integrity_tests_total": len(tests),
            "integrity_tests_passed": sum(1 for _n, ok, _d in tests if ok),
            "verdict": ("DECISION_READY" if all(ok for _n, ok, _d in tests)
                        else "NOT_DECISION_READY"),
            "readiness_counts": dict(Counter(x["Readiness"] for x in out)),
            "weights": {m: dict(w) for m, w in WEIGHTS_OF_MODEL.items()},
            "absolute_ceilings": {k: v[0] for k, v in aq.CEILINGS.items()},
            "min_completeness": rdy.MIN_COMPLETENESS,
            "min_cohort": pd.MIN_COHORT,
            "score_meaning": ("جودةُ الورقة المالية بمنهج الحوكمة — "
                              "ليست توصيةَ شراءٍ ولا بيع"),
        },
        "integrity": [{"test": n, "status": "PASS" if ok else "FAIL",
                       "detail": d} for n, ok, d in tests],
        "companies": [_decision_object(x) for x in ranked_rows],
    }
    try:
        with open(OUT_JSON, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        json_note = f"{OUT_JSON} — {len(ranked_rows)} شركة"
    except Exception as e:                                        # noqa: BLE001
        json_note = f"تعذّرت الكتابة: {type(e).__name__}"

    # ══ ١٠ — الملخّصُ التنفيذيّ ══
    R = Counter(x["Readiness"] for x in out)
    full = sum(1 for x in out if (x["Completeness"] or 0) >= 0.80)
    part = sum(1 for x in out if 0.40 <= (x["Completeness"] or 0) < 0.80)
    insuf = len(out) - full - part
    dcs = [x["Completeness"] for x in out if _finite(x["Completeness"])]

    print("═" * 72)
    print("  الملخّصُ التنفيذيّ — جاهزيةُ القرار")
    print("═" * 72)
    print(f"\nUNIVERSE")
    print(f"  Main Market companies      {cen['main']}")
    print(f"  NOMU داخل التحليل           0  (مستبعَدة {cen['nomu']})")
    # ══ العدُّ يطابق الكونَ ولا يزيد ══
    # كان يُطبع `len(out)` تحت عنوان «قُرئت فعلاً»، و`out` يضمّ الصفوفَ
    # كلَّها — المحسوبةَ وغيرَ المقروءة ومن ينتظر التصنيف. فظهر ‎273
    # مقروءةً و‎5 غيرَ مقروءة، ومجموعُهما يتجاوز الكون. والعنوانُ الكاذب
    # أخطرُ من الرقم الناقص.
    _scored = len(out) - len(pending) - len(unreadable)
    print(f"  حُسبت لها درجة             {_scored}")
    if pending:
        print(f"  بانتظار التصنيف             {len(pending)} · "
              + " · ".join(u["sym"] for u in pending))
    if unread:
        print(f"  لم تُقرأ                    {sum(unread.values())}")
        for k, v in unread.most_common():
            print(f"      {k:34} {v}")
    print(f"  المجموع                    "
          f"{_scored} + {len(pending)} + {len(unreadable)} = {len(out)}"
          f"  (الكون {cen['main']})")

    print(f"\nDATA")
    print(f"  Fully analyzed (≥80٪)      {full}")
    print(f"  Partial (40–80٪)           {part}")
    print(f"  Insufficient (<40٪)        {insuf}")
    if dcs:
        print(f"  وسيطُ الاكتمال              {_med(dcs):.0%}")
    print(f"\nREADINESS")
    print(f"  INVESTMENT_READY           {R.get('INVESTMENT_READY', 0)}")
    print(f"  WATCH                      {R.get('WATCH', 0)}")
    print(f"  NOT_READY                  {R.get('NOT_READY', 0)}")
    print(f"\nBLOCKERS")
    for k, v in Counter(c for x in out
                        for c in (x["BlockingCodes"].split(",") if
                                  x["BlockingCodes"] else [])).most_common(8):
        print(f"  {k:28} {v}")

    # ── إثباتُ استقلال الدرجة عن القيمة العادلة (المادة ٥) ──
    # على شركاتٍ حقيقيةٍ من هذا التشغيل لا على عيّنةٍ مصنوعة: تُزحزَح
    # القيمةُ العادلة وحدها وتُثبَّت المدخلاتُ الأخرى، ويُقاس الفرق.
    # ويُسلَك مسارُ التسجيل نفسُه حرفاً بحرف — التوزيعُ والنمطُ ووسائطُ
    # القطاع والصفوف — وإلّا أثبت الاختبارُ ثباتَ مسارٍ لا يُستعمل.
    _fvmax, _fvn = 0.0, 0
    for r in rows[:25]:
        _sec = r["sector"]
        _arch = spec_score.resolve_archetype_ex(_sec, {})[0]
        _med_r = medians.get(_sec or "", {})
        fe0 = dict(r["fe"])
        fe0.pop("fv_discount", None)
        base_sc = inv.compute(fe0, _sec, dist, _arch,
                              medians=_med_r, rows=r["crows"])["score"]
        if not isinstance(base_sc, (int, float)):
            continue
        _fvn += 1
        for disc in (-80.0, -10.0, 140.0, 700.0):
            sc = inv.compute({**fe0, "fv_discount": disc}, _sec, dist, _arch,
                             medians=_med_r, rows=r["crows"])["score"]
            if isinstance(sc, (int, float)):
                _fvmax = max(_fvmax, abs(sc - base_sc))
    tests.append(("٥ الدرجةُ لا تتأثّر بالقيمة العادلة", _fvmax == 0.0,
                  f"أقصى فرقٍ {_fvmax:.6f} على {_fvn} شركةً حقيقية"))

    print(f"\nINTEGRITY")
    for name, ok, detail in tests:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:38} {detail}")

    print(f"\n  جدولُ القرار: {csv_note}")
    print(f"  حمولةُ الواجهة: {json_note}")
    print(f"\nRANKING (ترتيبٌ داخل كلّ حالة — لا يعني «اشترِ»)")
    for st, lbl in ((rdy.INVESTMENT_READY, "أ) مؤهّلةٌ لإصدار قرار"),
                    (rdy.WATCH, "ب) مراقبة"),
                    (rdy.NOT_READY, "ج) غيرُ جاهزة")):
        grp = [x for x in ranked_rows if x["Readiness"] == st]
        print(f"  {lbl}: {len(grp)}")
        for x in grp[:5]:
            sc = x["FinalScore"]
            sc_s = f"{sc:.1f}" if isinstance(sc, (int, float)) else "—"
            print(f"      {x['RankInClass']:>3}. {x['Ticker']:>5} "
                  f"{x['Company'][:24]:24} {sc_s:>6}")

    # ── أعلى عشرٍ بالدرجة (المادة ٦) ──
    # على السوق كلِّها لا داخل حالةٍ واحدة، ومعها حالةُ الجاهزية كي لا
    # تُقرأ الصدارةُ توصيةً: الدرجةُ سلامةُ ورقة، والجاهزيةُ حكمٌ آخر.
    scored = [x for x in ranked_rows
              if isinstance(x.get("FinalScore"), (int, float))]
    print(f"\nTOP 10 GOVERNANCE (سلامةُ الورقة — ليست توصيةَ شراء)")
    for i, x in enumerate(sorted(scored, key=lambda r: -r["FinalScore"])[:10],
                          1):
        print(f"  {i:>2}. {x['Ticker']:>5} {x['Company'][:26]:26} "
              f"{x['FinalScore']:>5.1f}  {grade_of(x['FinalScore'])[0]:>2}  "
              f"{x['Readiness']}")

    # ── التوزيعُ على القطاعات (المادة ٧) ──
    print(f"\nBY SECTOR (العدد · الوسيط · الأدنى · الأعلى · جاهزون)")
    by_sec: dict[str, list] = defaultdict(list)
    for x in scored:
        by_sec[x.get("Sector") or "—"].append(x)
    for sec, grp in sorted(by_sec.items(), key=lambda kv: -len(kv[1])):
        ss = sorted(g["FinalScore"] for g in grp)
        nrdy = sum(1 for g in grp
                   if g["Readiness"] == rdy.INVESTMENT_READY)
        print(f"  {sec[:30]:30} {len(grp):>3}  {_med(ss):>5.1f}  "
              f"{ss[0]:>5.1f}  {ss[-1]:>5.1f}  {nrdy:>3}")
    _unscored = [x["Ticker"] for x in ranked_rows
                 if not isinstance(x.get("FinalScore"), (int, float))]
    if _unscored:
        print(f"  بلا درجة: {len(_unscored)} · {_unscored[:8]}")

    print(f"\nFAIR VALUE INVARIANCE (المدخلاتُ ثابتة · القيمةُ العادلة تتحرّك)")
    print(f"  شركاتٌ مختبَرة {_fvn} · أقصى فرقٍ في الدرجة {_fvmax:.6f}")
    print(f"  {'PASS' if _fvmax == 0.0 else 'FAIL'}  "
          f"Fair Value weight = 0٪ · Governance invariant")

    all_pass = all(ok for _n, ok, _d in tests)
    print("\n" + "═" * 72)
    print(f"  FINAL VERDICT: "
          f"{'DECISION_READY' if all_pass else 'NOT_DECISION_READY'}")
    print("═" * 72)
    if not all_pass:
        print("  ما يمنع الجاهزية:")
        for name, ok, detail in tests:
            if not ok:
                print(f"    ✖ {name} — {detail}")
    else:
        print("  اجتازت اختباراتُ السلامة كلُّها، والكونُ صحيح، وعُولجت")
        print("  البياناتُ المتاحة بالقواعد القائمة بلا تخفيفِ عتبة.")
        print(f"  وعددُ الجاهزين ({R.get('INVESTMENT_READY', 0)}) حالُ بياناتٍ")
        print("  تُعرض كما هي، لا معيارَ نجاحٍ يُطارَد.")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
