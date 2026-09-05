#!/usr/bin/env python3
"""تقرير قياس محرّك القيمة العادلة.

يُشغَّل على الكون كلِّه، ويُخرج أربع بوابات لا واحدة:

  G1  الانحراف الوسيط عن هدف المحللين          (≤ 25%) — **يُبلَّغ ولا يحكم**
  G2  التشتّت حول التحيّز الوسيط                (≤ 25%)
  G3  ارتباط الترتيب بين V/P و target/P         (سبيرمان ≥ 0.45)
  G4  الكسبُ في التغطية على مَن لا هدفَ له      (≥ 40%)

G1 يقيس الاتفاقَ في المستوى مع مرجعٍ متفائلٍ بنيوياً، وقد بُرهن بالمحاكاة
أن محرّكاً خطؤه صفرٌ يرسب فيه ومحرّكاً رديئاً مقلّداً للسعر قد يجتازه
(‏gate_simulation.py). فأُنزل إلى الإبلاغ.

وG4 هو سؤالُ التطبيق: «هدفُ المحللين» معروضٌ أصلاً ويصل ‎149 من ‎273،
فمحرّكٌ يُصيب حيث يوجد هدفٌ ويمتنع حيث لا هدفَ **لا يضيف شيئاً**. رمزُ
الخروج مربوطٌ بـG2 وG3 وG4 معاً.

    python scripts/audit/fair_value_acceptance.py --out reports/fv_acceptance.json
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

from app.services.fair_value_engine.engine import value_company, universe          # noqa: E402
from app.services.fair_value_engine.fetch import fetch, misalignment_selftest      # noqa: E402
from app.services.fair_value_engine.params import load_params                      # noqa: E402


def quantile(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs); i = q * (len(s) - 1); lo = int(i)
    return s[lo] if lo == len(s) - 1 else s[lo] + (s[lo + 1] - s[lo]) * (i - lo)


def spearman(a: list[float], b: list[float]) -> float:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos + 1
        return r
    if len(a) < 3:
        return float("nan")
    ra, rb = ranks(a), ranks(b)
    n = len(a); ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/fv_acceptance.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=1.2)
    ap.add_argument("--allow-unverified", action="store_true")
    ap.add_argument("--skip-selftest", action="store_true")
    ap.add_argument("--allow-stale", action="store_true",
                    help="تجاوز حارس قِدَم المعايير — للتجارب فقط")
    a = ap.parse_args()

    if not a.skip_selftest:
        st = misalignment_selftest()
        print(f"[selftest #2584] ok={st['ok']}  {st['detail'][:120]}")
        if not st["ok"]:
            print("توقف: فحص انزياح البنود لم يجتز. لا يُقاس المحرك على بيانات مشكوك في محاذاتها.")
            return 2

    p = load_params(allow_unverified=a.allow_unverified, allow_stale=a.allow_stale)
    uni = list(universe().values())
    if a.limit:
        uni = uni[: a.limit]

    results, failures = [], []
    for i, c in enumerate(uni, 1):
        try:
            f = fetch(c["yahoo"])
            r = value_company(c["code"], f, p, allow_unverified=a.allow_unverified)
        except Exception as e:                                  # noqa: BLE001
            failures.append({"code": c["code"], "error": f"{type(e).__name__}: {e}"})
            time.sleep(a.sleep); continue
        r["name_ar"] = c["name_ar"]
        results.append(r)
        print(f"[{i}/{len(uni)}] {c['code']:>5} {c['name_ar'][:18]:<18} "
              f"{'امتناع' if r['abstained'] else r['value']}")
        time.sleep(a.sleep)

    # ---------- measurement population ----------
    scored = [r for r in results
              if not r["abstained"] and r.get("analyst_target")
              and not r["implausible"] and not r["floored_at_book"]]
    excluded_floored = [r for r in results if r.get("floored_at_book") and r.get("analyst_target")]
    excluded_implaus = [r for r in results if r.get("implausible") and r.get("analyst_target")]

    dev   = [abs(r["value"] - r["analyst_target"]) / r["analyst_target"] for r in scored]
    ratio = [r["value"] / r["analyst_target"] for r in scored]
    vp    = [r["value"] / r["price_at_calc"] for r in scored]
    tp    = [r["analyst_target"] / r["price_at_calc"] for r in scored]

    med_ratio = median(ratio) if ratio else float("nan")
    spread = [abs(x - med_ratio) / med_ratio for x in ratio] if ratio else []

    g1 = median(dev) if dev else float("nan")
    g2 = median(spread) if spread else float("nan")
    g3 = spearman(vp, tp)

    by_sector, by_conf = {}, {}
    for r, dv in zip(scored, dev):
        by_sector.setdefault(r["sector"], []).append(dv)
        by_conf.setdefault(r["confidence"], []).append(dv)

    abst = {}
    for r in results:
        if r["abstained"]:
            abst[r["abstain_reason"]] = abst.get(r["abstain_reason"], 0) + 1

    # ---------- G4: الكسبُ في التغطية — وهو سؤالُ التطبيق الحقيقيّ ----------
    # المحرّكُ لا يُحقن ليُكرّر رقماً معروضاً أصلاً. المعروضُ اليوم «هدف
    # المحللين»، ويصل ‎149 من ‎273 — فالسؤالُ: كم شركةً **بلا هدف** يعطيها
    # المحرّكُ رقماً صالحاً للعرض؟ (غير ممتنَع · غير شاذّ · لم تُطبَّق عليه
    # الأرضية · ثقتُه ليست منخفضة). هذا وحدَه يقرّر جدوى الحقن، ولا يقيسه
    # G1 ولا G2 ولا G3.
    _usable = (lambda r: not r["abstained"] and not r["implausible"]
               and not r["floored_at_book"] and r.get("confidence") in ("مرتفعة", "متوسطة"))
    no_target = [r for r in results if not r.get("analyst_target")]
    gained = [r for r in no_target if _usable(r)]
    g4 = (len(gained) / len(no_target)) if no_target else float("nan")

    report = {
        "n_universe": len(uni),
        "n_valued": sum(1 for r in results if not r["abstained"]),
        "n_abstained": sum(1 for r in results if r["abstained"]),
        "n_with_target": sum(1 for r in results if r.get("analyst_target")),
        "n_scored": len(scored),
        "n_excluded_floored": len(excluded_floored),
        "n_excluded_implausible": len(excluded_implaus),
        "n_fetch_failures": len(failures),
        "G1_median_deviation": g1,
        "G1_p25": quantile(dev, 0.25), "G1_p75": quantile(dev, 0.75),
        "G1_pass": bool(g1 == g1 and g1 <= 0.25),
        "G2_median_bias_ratio": med_ratio,
        "G2_median_spread_around_bias": g2,
        "G2_pass": bool(g2 == g2 and g2 <= 0.25),
        "G3_spearman_vp_vs_tp": g3,
        "G3_pass": bool(g3 == g3 and g3 >= 0.45),
        "median_value_over_price": median(vp) if vp else None,
        "median_target_over_price": median(tp) if tp else None,
        "by_sector": {k: {"n": len(v), "median_dev": median(v)} for k, v in sorted(by_sector.items())},
        "by_confidence": {k: {"n": len(v), "median_dev": median(v)} for k, v in by_conf.items()},
        "G4_no_target_n": len(no_target),
        "G4_gained_n": len(gained),
        "G4_coverage_gain": g4,
        "G4_pass": bool(g4 == g4 and g4 >= 0.40),
        "G4_gained_by_sector": {k: sum(1 for r in gained if r["sector"] == k)
                                for k in sorted({r["sector"] for r in gained})},
        "abstain_reasons": abst,
        "fetch_failures": failures[:40],
        "provenance": p.provenance(),
    }

    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"report": report, "rows": results}, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    print("\n" + "=" * 62)
    print(f"العيّنة: {report['n_scored']} من {report['n_with_target']} لها هدف محللين "
          f"(استُبعد {report['n_excluded_floored']} بأرضية دفترية، "
          f"{report['n_excluded_implausible']} شاذة)")
    print(f"G1 الانحراف الوسيط        {g1:.1%}   {'اجتاز' if report['G1_pass'] else 'لم يجتز'}")
    print(f"G2 التشتّت حول التحيّز     {g2:.1%}   {'اجتاز' if report['G2_pass'] else 'لم يجتز'}"
          f"   (التحيّز الوسيط {med_ratio:.3f})")
    print(f"G3 ارتباط الترتيب         {g3:.3f}   {'اجتاز' if report['G3_pass'] else 'لم يجتز'}")
    print(f"وسيط القيمة/السعر {report['median_value_over_price']:.3f} · "
          f"وسيط الهدف/السعر {report['median_target_over_price']:.3f}")
    print(f"G4 الكسبُ في التغطية      {g4:.1%}   {'اجتاز' if report['G4_pass'] else 'لم يجتز'}"
          f"   ({len(gained)} من {len(no_target)} بلا هدف محللين)")
    print("=" * 62)
    print(f"التقرير: {out}")
    # الحكمُ النهائيّ: اتّساقٌ وترتيبٌ وكسبٌ في التغطية. وG1 يُبلَّغ ولا يحكم —
    # فهو يقيس الاتفاقَ مع مرجعٍ متفائلٍ بنيوياً، وقد بُرهن بالمحاكاة أن
    # محرّكاً خطؤه صفر يرسب فيه. (scripts/audit/gate_simulation.py)
    return 0 if (report["G2_pass"] and report["G3_pass"] and report["G4_pass"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
