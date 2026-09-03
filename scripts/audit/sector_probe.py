"""قياسُ عطبِ القطاع قبل علاجه — أدلّةٌ لا ظنون.

## السؤال

خمسةُ قطاعاتٍ يُشتبه أن المسطرةَ العامّة تظلمها: كثيفةُ الإنفاق
الرأسماليّ (المرافق · الاتصالات · النقل · التطبيقات) والمطوّرون
العقاريّون. والشبهةُ أنّ التدفّقَ الحرَّ سالبٌ عندها **بنيةً** كما في
الصناديق العقارية، أو أنّ الإيرادَ متقطّعٌ بتسليم المشاريع.

وهذا المسبارُ يقيسها ولا يفترضها. لكلّ قطاع:

  · كم شركةً تدفّقُها الحرُّ سالبٌ في **كلّ** سنواتها (لا في سنةٍ)
  · وسيطُ هامش التدفّق الحرّ
  · تذبذبُ الإيراد (معامل الاختلاف)
  · وسيطُ الدرجة الآن، ووسيطُها **لو** أُعفيت من التدفّق الحرّ
    ولو قِيس عائدُها عبر الدورة — الفرقُ هو حجمُ العطب

## لا يستهلك حصّة

يقرأ القوائمَ المخزَّنة وحدها (ذاكرةً أو قرصاً) كما يفعل `_governance_score`،
فمن لا قوائمَ له يُترك ولا يُطلب. شغّله بعد تصفّحٍ عاديّ أو بعد مسحٍ.

    docker exec sp_backend python /app/scripts/audit/sector_probe.py
"""

from __future__ import annotations

import os
import statistics as st
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# القطاعاتُ المشتبهة، ومعها المضبوطةُ سلفاً للمقارنة (خطُّ أساسٍ يُقاس عليه)
SUSPECT = ["المرافق العامة", "الاتصالات", "النقل",
           "التطبيقات وخدمات التقنية", "إدارة وتطوير العقارات"]
BASELINE = ["الصناديق العقارية المتداولة", "الطاقة", "المواد الأساسية",
            "الرعاية الصحية", "إنتاج الأغذية", "السلع الرأسمالية"]

MATERIAL = 5.0   # فرقٌ دون خمسِ نقاطٍ لا يُبرّر تعديلاً


def _med(v):
    return st.median(v) if v else None


def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data import universe as uni
    from app.services import cache, lastgood
    from app.services.scores import _finance_score_from_periods as sc

    MAIN = uni.main_market(MARKET_UNIVERSE)
    by_sec: dict[str, list] = defaultdict(list)
    read = 0
    for sym, meta in MAIN.items():
        sec = meta.get("sector")
        if not sec:
            continue
        ck = f"stmt:{sym}.SR"
        data = cache.get(ck) or lastgood.load(
            ck, max_age_seconds=cache.FUNDAMENTALS_TTL)
        periods = (data or {}).get("periods") if isinstance(data, dict) else data
        if not periods or len(periods) < 2:
            continue
        read += 1
        by_sec[sec].append(periods)

    if not read:
        print("✖ لا قوائمَ مخزَّنة. شغّل مسحَ السوق أوّلاً ثم أعِد:")
        print("    docker exec sp_backend python /app/scripts/audit/market_sweep.py --market")
        return 2

    def stats(rows: list) -> dict:
        alln, fcfm, cv, cur, no_fcf, cyc = 0, [], [], [], [], []
        for periods in rows:
            fcfs = [p.get("free_cash_flow") for p in periods
                    if p.get("free_cash_flow") is not None]
            if fcfs and all(f < 0 for f in fcfs):
                alln += 1
            for p in periods:
                r_, f_ = p.get("revenue"), p.get("free_cash_flow")
                if r_ and r_ > 0 and f_ is not None:
                    fcfm.append(f_ / r_ * 100)
            revs = [p["revenue"] for p in periods
                    if p.get("revenue") and p["revenue"] > 0]
            if len(revs) >= 3:
                m = sum(revs) / len(revs)
                cv.append(st.pstdev(revs) / m * 100 if m else 0.0)
            s0 = sc(periods)
            if s0 is None:
                continue
            cur.append(s0)
            # ماذا لو أُعفيت من التدفّق الحرّ (كالصناديق)؟
            stripped = [{k: v for k, v in p.items() if k != "free_cash_flow"}
                        for p in periods]
            s1 = sc(stripped)
            if s1 is not None:
                no_fcf.append(s1 - s0)
            # وماذا لو قِيس عائدُها عبر الدورة (كالدوريّة)؟
            s2 = sc(periods, "الطاقة")
            if s2 is not None:
                cyc.append(s2 - s0)
        return {"n": len(rows), "allneg": alln, "fcf_med": _med(fcfm),
                "cv": _med(cv), "score": _med(cur),
                "d_fcf": _med(no_fcf), "d_cyc": _med(cyc)}

    print("═" * 78)
    print("  قياسُ القطاعات — هل تظلمها المسطرةُ العامّة؟")
    print("═" * 78)
    print(f"  شركاتٌ لها قوائمُ مخزَّنة: {read}\n")
    print(f"  {'القطاع':26} {'ع':>3} {'حرٌّ سالبٌ دوماً':>14} "
          f"{'هامشُ الحرّ':>10} {'تذبذبُ الإيراد':>13} {'الدرجة':>7} "
          f"{'Δ إعفاء':>8} {'Δ دورة':>7}")

    flagged = []
    for label, group in (("المشتبهة", SUSPECT), ("خطُّ الأساس", BASELINE)):
        print(f"\n  ── {label} ──")
        for sec in group:
            rows = by_sec.get(sec) or []
            if not rows:
                print(f"  {sec[:26]:26} {'—':>3}  (لا قوائمَ مخزَّنة)")
                continue
            s = stats(rows)
            pct = f"{s['allneg']}/{s['n']}"
            def f(x, d=1):
                return "—" if x is None else f"{x:.{d}f}"
            print(f"  {sec[:26]:26} {s['n']:>3} {pct:>14} "
                  f"{f(s['fcf_med']):>10} {f(s['cv']):>13} "
                  f"{f(s['score'],0):>7} {f(s['d_fcf']):>8} {f(s['d_cyc']):>7}")
            if label == "المشتبهة":
                for name, d in (("إعفاءُ التدفّق الحرّ", s["d_fcf"]),
                                ("قياسٌ عبر الدورة", s["d_cyc"])):
                    if d is not None and abs(d) >= MATERIAL:
                        flagged.append((sec, name, d, s["allneg"], s["n"]))

    print("\n" + "═" * 78)
    if not flagged:
        print(f"  ✔ لا عطبَ يبلغ {MATERIAL:.0f} نقاطٍ — المسطرةُ العامّة تكفيها.")
        print("    ولا يُضاف تعديلٌ بلا رقمٍ يبرّره.")
    else:
        print("  عطبٌ مقيسٌ يستحقّ التعديل:")
        for sec, name, d, a, n in flagged:
            print(f"    · {sec} — {name}: {d:+.1f} نقطة "
                  f"(سالبٌ دوماً في {a} من {n})")
        print("\n  والشرطُ الثاني قبل التعديل: أن يكون السببُ **بنيوياً**")
        print("  لا ضعفَ أداء — يدلّ عليه أن يكون الحرُّ سالباً في كلّ")
        print("  سنواتِ أكثرِ شركات القطاع، لا في سنةٍ أو شركة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
