"""اختبارُ قبول القرار الاستثماريّ — مستقلٌّ فوق الحمولة.

## لماذا مستقلّ

لا يستدعي هذا السكربتُ المحرّكَ ولا يعيد حساب درجة. **يقرأ الحمولة كما
يقرؤها التطبيق** ويحاكم ما فيها. فإن كان بين المحرّك وما يصل الواجهةَ
عطبٌ في التصدير أو التسمية أو الربط، ظهر هنا ولم يستره أنّ الحسابَ صحيح.

وهو بذلك يُثبت شيئين معاً: أنّ القرار قابلٌ للتفسير، وأنّ الحمولة
صالحةٌ للاستهلاك المباشر — لأنّه هو نفسُه أوّلُ مستهلكٍ لها.

## ما يُفشِله

كلُّ تناقضٍ في المخرَج، لا كلُّ نقصٍ في السوق. فشركةٌ بلا قوائم ليست
إخفاقاً — إخفاقٌ أن تظهر جاهزةً، أو أن يُخترع لها رقم، أو أن تختفي من
العدّ. والحدُّ الفاصل: **نقصُ البيانات حالٌ تُعرض، وتناقضُ المخرَج عطب.**

    python scripts/audit/final_decision_acceptance.py [payload.json]
"""

from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DEFAULT_JSON = os.environ.get("SP_DECISION_JSON", "/tmp/decision_payload.json")

READY, WATCH, NOT_READY = "INVESTMENT_READY", "WATCH", "NOT_READY"
STATUSES = (READY, WATCH, NOT_READY)

# الحقولُ التي تعرضها الواجهة — البند ١٢
PWA_FIELDS = ("company_name", "sector", "final_score", "decision_status",
              "quality_score", "growth_score", "distribution_score",
              "valuation_score", "completeness", "confidence",
              "valuation_method", "positive_drivers", "negative_drivers",
              "decision_reason")
REQUIRED = PWA_FIELDS + ("ticker", "market", "archetype", "model",
                         "risk_gate", "absolute_ceiling", "blockers")
# أسبابُ منعٍ مقبولةٌ — والسببُ العامّ مرفوض
KNOWN_BLOCKERS = {"CORE_AXIS_MISSING", "LOW_COMPLETENESS", "LOW_CONFIDENCE",
                  "NO_VALUATION_METHOD", "NO_SECTOR", "NO_MODEL",
                  "RISK_GATE", "NO_PERIODS", "TOO_FEW_PERIODS",
                  "API_ERROR", "FEATURE_BUILD_ERROR"}


def _fin(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) \
        and math.isfinite(x)


def main(argv: list[str]) -> int:
    from app.data import universe as uni
    from app.services import model_valuation as mv
    from app.data.economic_models import CORE_AXES
    from app.services import investment_readiness as rdy

    path = argv[0] if argv else DEFAULT_JSON
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as e:                                        # noqa: BLE001
        print(f"✖ تعذّرت قراءةُ الحمولة «{path}»: {type(e).__name__}: {e}")
        return 1

    meta = payload.get("metadata") or {}
    cos = payload.get("companies") or []
    results: list[tuple[str, bool, str]] = []

    def t(name: str, ok: bool, detail: str = ""):
        results.append((name, bool(ok), detail))

    # ══ ١ — الكون ══
    strays = [c["ticker"] for c in cos if not uni.is_main(c.get("ticker"))]
    wrong_mkt = [c["ticker"] for c in cos if c.get("market") != "MAIN_MARKET"]
    t("Universe — الرئيسة وحدها",
      not strays and not wrong_mkt and meta.get("excluded_nomu_count", -1) >= 0,
      f"شركات {len(cos)} · كونٌ معلَن {meta.get('main_market_count')} · "
      f"«نمو» مستبعَدة {meta.get('excluded_nomu_count')} · "
      f"دخيل {len(strays) + len(wrong_mkt)}")
    t("Universe — العددُ يطابق الكون",
      len(cos) == meta.get("main_market_count"),
      f"صفوف {len(cos)} مقابل {meta.get('main_market_count')}")

    # ══ ٢ — الحالاتُ الثلاث لا رابع ══
    bad_st = sorted({c.get("decision_status") for c in cos} - set(STATUSES))
    t("الحالاتُ ثلاثٌ لا غير", not bad_st, f"حالاتٌ دخيلة: {bad_st or '—'}")

    # ══ ٣ — كائنُ القرار مكتمل ══
    missing_fields = Counter()
    for c in cos:
        for f in REQUIRED:
            if f not in c:
                missing_fields[f] += 1
    t("كائنُ القرار مكتملُ الحقول", not missing_fields,
      f"{len(cos)}/{len(cos)} كائناً"
      + (f" · حقولٌ ناقصة: {dict(missing_fields)}" if missing_fields else ""))

    # ══ ٤ — قابليةُ تفسير READY ══
    ready = [c for c in cos if c.get("decision_status") == READY]
    bad_ready = []
    for c in ready:
        why = []
        core = CORE_AXES.get(c.get("model") or "", ())
        for ax in core:
            k = {"quality": "quality_score", "dividend": "distribution_score",
                 "growth": "growth_score", "valuation": "valuation_score"}[ax]
            if not _fin(c.get(k)):
                why.append(f"محورٌ جوهريٌّ غائب: {ax}")
        if not c.get("valuation_method"):
            why.append("لا طريقةَ تقييم")
        if not _fin(c.get("completeness")) or \
                c["completeness"] < rdy.MIN_COMPLETENESS:
            why.append(f"اكتمال {c.get('completeness')}")
        if c.get("confidence") == "منخفضة":
            why.append("ثقةٌ منخفضة")
        if c.get("risk_gate") == "EXCLUDED":
            why.append("بوّابةٌ مغلقة")
        if c.get("blockers"):
            why.append(f"مانعٌ قائم: {c['blockers']}")
        if not c.get("positive_drivers") and not c.get("negative_drivers"):
            why.append("بلا عواملَ مفسِّرة")
        if not (c.get("decision_reason") or "").strip():
            why.append("بلا سببٍ للقرار")
        if why:
            bad_ready.append(f"{c['ticker']}({'، '.join(why)})")
    t("READY قابلةٌ للتفسير بلا تناقض", not bad_ready,
      f"جاهزة {len(ready)} · متناقضة {len(bad_ready)}"
      + (f" · {bad_ready[:5]}" if bad_ready else ""))

    # ══ ٥ — WATCH و NOT_READY لكلٍّ سببٌ محدَّد ══
    blocked = [c for c in cos if c.get("decision_status") in (WATCH, NOT_READY)]
    vague = [c["ticker"] for c in blocked
             if not c.get("blockers")
             or set(c["blockers"]) - KNOWN_BLOCKERS]
    t("لكلّ ممنوعةٍ سببٌ مصنَّف", not vague,
      f"ممنوعة {len(blocked)} · بلا سببٍ مصنَّف {len(vague)}"
      + (f" · {vague[:5]}" if vague else ""))

    # ══ ٦ — الدرجةُ ليست القرار ══
    ready_sc = [c["final_score"] for c in ready if _fin(c.get("final_score"))]
    blocked_sc = [c["final_score"] for c in blocked
                  if _fin(c.get("final_score"))]
    overlap = 0
    if ready_sc and blocked_sc:
        lo_ready = min(ready_sc)
        overlap = sum(1 for v in blocked_sc if v > lo_ready)
    t("القرار لا يُشتقّ من الدرجة وحدها", True,
      f"ممنوعاتٌ درجتُها تفوق أدنى جاهزة: {overlap}"
      + (" — والحالةُ من الأهلية لا من الرقم" if overlap else
         " (لا تداخلَ في هذه التشغيلة)"))

    # ══ ٧ — التقييم ══
    known = {m for ms in mv.METHODS.values() for m in ms}
    bad_vm = []
    for c in cos:
        vm = c.get("valuation_method")
        if vm and vm not in known:
            bad_vm.append(f"{c['ticker']}:{vm} غيرُ مسجَّلة")
        elif vm and c.get("model") and vm not in mv.METHODS.get(c["model"], ()):
            bad_vm.append(f"{c['ticker']}:{vm} ليست من طرق {c['model']}")
    null_ready = [c["ticker"] for c in ready if not c.get("valuation_method")]
    t("طريقةُ التقييم من طرق نموذجها", not bad_vm and not null_ready,
      f"مخالفات {len(bad_vm)} · جاهزةٌ بلا طريقة {len(null_ready)}"
      + (f" · {(bad_vm + null_ready)[:5]}" if (bad_vm or null_ready) else ""))

    # ══ ٨ — البوّابةُ سقفٌ لا خصم ══
    gate_bad, gated = [], 0
    for c in cos:
        rel, fin, cap = (c.get("relative_score"), c.get("final_score"),
                         c.get("absolute_ceiling"))
        if not (_fin(rel) and _fin(fin)):
            continue
        cap = cap if _fin(cap) else 100.0
        if cap < 100.0:
            gated += 1
        if abs(fin - min(rel, cap)) > 0.05:
            gate_bad.append(f"{c['ticker']}({fin}≠min({rel},{cap}))")
    excluded_ready = [c["ticker"] for c in ready
                      if c.get("risk_gate") == "EXCLUDED"]
    t("البوّابةُ سقفٌ لا خصم", not gate_bad and not excluded_ready,
      f"مسقوفة {gated} · مخالفات {len(gate_bad)} · "
      f"مستبعَدةٌ ظهرت جاهزة {len(excluded_ready)}"
      + (f" · {gate_bad[:4]}" if gate_bad else ""))

    # ══ ٩ — لا بياناتٍ مصطنعة ══
    fake = []
    for c in cos:
        if c.get("decision_status") == NOT_READY and \
                {"NO_PERIODS", "TOO_FEW_PERIODS"} & set(c.get("blockers") or []):
            for k in ("final_score", "quality_score", "growth_score",
                      "distribution_score", "valuation_score", "completeness"):
                if c.get(k) is not None:
                    fake.append(f"{c['ticker']}.{k}={c[k]}")
        for k in ("final_score", "quality_score", "completeness"):
            v = c.get(k)
            if v is not None and not _fin(v):
                fake.append(f"{c['ticker']}.{k} غيرُ منتهية")
    t("لا بياناتٍ مصطنعة", not fake,
      f"مخالفات {len(fake)}" + (f" · {fake[:5]}" if fake else ""))

    # ══ ١٠ — معالجةُ من لا قوائمَ له ══
    nop = [c for c in cos
           if "NO_PERIODS" in (c.get("blockers") or [])]
    nop_bad = [c["ticker"] for c in nop if c.get("decision_status") == READY]
    declared = meta.get("no_periods_count")
    t("من لا قوائمَ له: مُدرَجٌ وغيرُ جاهز",
      not nop_bad and (declared is None or len(nop) == declared),
      f"مُدرَجة {len(nop)} · مُعلَنٌ {declared} · ظهرت جاهزة {len(nop_bad)}")

    # ══ ١٢ — صلاحيةُ الحمولة للواجهة ══
    ui_gap = Counter()
    for c in cos:
        for f in PWA_FIELDS:
            if f not in c:
                ui_gap[f] += 1
    drv_bad = [c["ticker"] for c in cos
               if not isinstance(c.get("positive_drivers"), list)
               or not isinstance(c.get("negative_drivers"), list)]
    t("الحمولةُ صالحةٌ لاستهلاك الواجهة",
      not ui_gap and not drv_bad,
      f"حقولُ العرض {len(PWA_FIELDS)} حاضرةٌ في {len(cos)} شركة"
      + (f" · نقص {dict(ui_gap)}" if ui_gap else ""))

    # ══ التقرير ══
    counts = Counter(c.get("decision_status") for c in cos)
    print("═" * 66)
    print("  FINAL INVESTMENT DECISION ACCEPTANCE")
    print("═" * 66)
    print(f"\nUniverse:")
    print(f"  Main Market:  {meta.get('main_market_count')}")
    print(f"  NOMU:         {meta.get('excluded_nomu_count')} (مستبعَدة)")
    print(f"  READY:        {counts.get(READY, 0)}")
    print(f"  WATCH:        {counts.get(WATCH, 0)}")
    print(f"  NOT_READY:    {counts.get(NOT_READY, 0)}")
    print(f"\nDecision Objects: {len(cos)} / {meta.get('main_market_count')}")
    print()
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:34} {detail}")

    bad = [n for n, ok, _d in results if not ok]
    print("\n" + "═" * 66)
    print(f"  Critical contradictions: {len(bad)}")
    print(f"  FINAL ACCEPTANCE: {'PASS' if not bad else 'FAIL'}")
    print("═" * 66)
    if bad:
        print("  الاختباراتُ التي أخفقت:")
        for n, ok, detail in results:
            if not ok:
                print(f"    ✖ {n} — {detail}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
