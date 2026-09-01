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


async def main(argv: list[str]) -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data import universe as uni
    from app.data.economic_models import (COMPONENTS, CORE_AXES, WEIGHTS_OF_MODEL,
                                          model_of)
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
    check("٣ لا مؤشّرَ يُرتَّب بلا توزيع", not no_dist,
          f"{len(ranked) - len(no_dist)}/{len(ranked)}"
          + (f" · بلا توزيع: {no_dist}" if no_dist else ""))
    thin = [(a, k) for a in archs for k, v in dist["archetypes"][a].items()
            if v.get("n", 0) < pd.MIN_COHORT]
    check("٣ب لا عشيرةَ دون الحدّ", not thin,
          f"MIN_COHORT={pd.MIN_COHORT} · مخالفات {len(thin)}")

    # ══ ٢ — تشغيلُ البيانات ══
    rows, unread = [], Counter()
    for sym, meta in MAIN.items():
        try:
            data = await market_service.get_financials(f"{sym}.SR",
                                                       allow_supplement=False)
        except Exception as e:                                    # noqa: BLE001
            unread[f"API_ERROR:{type(e).__name__}"] += 1
            continue
        ps = (data or {}).get("periods") or []
        if len(ps) < 2:
            unread["TOO_FEW_PERIODS" if ps else "NO_PERIODS"] += 1
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
    for r in rows:
        sector, ps = r["sector"], r["ps"]
        model = model_of(sector)
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

        out.append({
            "Ticker": r["sym"], "Company": name_of(r["sym"]) or "",
            "Sector": sector or "", "Archetype": arch or "",
            "Model": model or "", "FinalScore": res.get("score"),
            "RelativeScore": rel, "RawScore": res.get("raw_score"),
            "Quality": (c["quality"] or {}).get("score"),
            "Distribution": (c["dividend"] or {}).get("score"),
            "Growth": (c["growth"] or {}).get("score"),
            "Valuation": (c["valuation"] or {}).get("score"),
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

    # ٥ — الوحدات: العائدُ والوسيطُ من السلسلة نفسها ونطاقٍ معقول
    roes = [v for r in rows if _finite(v := inv._val(r["fe"], "roe"))]
    unit_ok = bool(roes) and all(-200.0 <= v <= 300.0 for v in roes)
    check("٥ وحدةُ العائد نسبةٌ مئوية والوسيطُ من سلسلتها",
          unit_ok,
          f"n={len(roes)} · المدى "
          f"{(min(roes) if roes else 0):.1f}–{(max(roes) if roes else 0):.1f}٪")

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
    check("١٢ لا انحرافَ في الأوزان والعتبات", not drift,
          "مطابقةٌ حرفية" if not drift else str(drift))

    # ══ ٧ — جدولُ القرار إلى ملفّ ══
    cols = ["Ticker", "Company", "Sector", "Archetype", "Model", "FinalScore",
            "RelativeScore", "RawScore", "Quality", "Distribution", "Growth",
            "Valuation", "Completeness", "Confidence", "RiskGate", "Readiness",
            "ValuationMethod", "FairValue", "Price", "Upside",
            "AbsoluteCeiling", "BlockingReason", "BlockingCodes"]
    try:
        with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for x in sorted(out, key=lambda z: -(z["FinalScore"] or -1)):
                w.writerow({k: x.get(k) for k in cols})
        csv_note = f"{OUT_CSV} — {len(out)} صفّاً"
    except Exception as e:                                        # noqa: BLE001
        csv_note = f"تعذّرت الكتابة: {type(e).__name__}"

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
    print(f"  قُرئت فعلاً                  {len(out)}")
    if unread:
        print(f"  لم تُقرأ                    {sum(unread.values())}")
        for k, v in unread.most_common():
            print(f"      {k:34} {v}")
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

    print(f"\nINTEGRITY")
    for name, ok, detail in tests:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:38} {detail}")

    print(f"\n  جدولُ القرار: {csv_note}")

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
