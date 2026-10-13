#!/usr/bin/env python3
"""حارسُ D701 — محرّكٌ شاملٌ للسوق الرئيسي: من لا تكفيه النماذجُ المثبتة يُقارن بأقرانه في حاله بما ثبت في قطاعه (بأمر المالك 2026-10-13).

قال المالك: «أشكّ أنك قادرٌ على إيجاد محرّك سعرٍ عادلٍ شاملٍ للسوق الرئيسي». قِيس (‏fv_universe_d701): في التأمين الرخصُ بالمضاعفات
يتنبّأ بالعكس والجودةُ تتنبّأ؛ وفي غير الماليّة بلا ثلاثة نماذجَ مثبتة الدخلُ المتبقّي والنموُّ والعائدُ على الحقوق — نسبيّاً إلى الأقران
لا مستوىً. فالحارسُ يمنع العودة:
  · المؤشّراتُ لكلّ نمطٍ كما ثبتت، و‎β من النصف الأوّل، ولا رقمَ من أقلّ من ستة أقران أو من أقلّ من نصف المؤشّرات.
  · الأفضلُ من أقرانه فوق سعره والأضعفُ تحته والوسيطُ عنده — رقمٌ نسبيٌّ لا وعدٌ بمستوى، وهدفُه الرقمُ نفسُه بلا خطأٍ مدّعى.
  · المسحةُ جولتان (الأقرانُ قبل المقارنة)، وبوابةُ المرشَّح والاختبارُ التاريخيّ مثلُها، والإصابةُ تُقاس بالأقران لا بالسوق كلِّه.

    python3 scripts/audit/fv_comprehensive_d701.py
"""
import os, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from types import SimpleNamespace

fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import fair_value_models as F

SEG = getattr(F, "REL_SEGMENTS", {})
check(SEG.get("insurance", {}).get("keys") == ("ri", "margin", "fcf_m", "size")
      and SEG.get("thin", {}).get("keys") == ("ri", "growth", "roe", "ni_g", "mom")
      and SEG.get("core", {}).get("keys") == ("P", "mom", "ni_g", "ebit_ev") and SEG.get("financial", {}).get("keys") == ("cp", "mom")
      and abs(SEG["insurance"]["beta"] - 0.466) < 1e-9 and abs(SEG["thin"]["beta"] - 0.548) < 1e-9
      and abs(SEG["core"]["beta"] - 0.538) < 1e-9,
      "١ مؤشّراتُ كلّ نمطٍ كما ثبتت (‏D702: والمركّبُ القيمةُ والزخمُ والنموّ)، و‎β معايَرٌ بالنصف الأوّل وحده")

# جدولُ أقرانٍ مصطنع: عشرُ شركاتِ تأمينٍ متدرّجةُ الجودة
table = {f"I{k}": {"ri": -1.0 + k * 0.1, "margin": 0.01 * k, "fcf_m": 0.02 * k, "size": 20 + k} for k in range(10)}
best = F.relative_value("I9", {"seg": "insurance", "sig": table["I9"]}, 10.0, table)
worst = F.relative_value("I0", {"seg": "insurance", "sig": table["I0"]}, 10.0, table)
mid = F.relative_value("I5", {"seg": "insurance", "sig": table["I5"]}, 10.0, table)
check(best and worst and mid and best["value"] > 10.0 > worst["value"] and abs(mid["value"] - 10.0) < 0.5,
      "٢ الأفضلُ من أقرانه فوق سعره والأضعفُ تحته والوسيطُ عنده", f"{best and best['value']} · {mid and mid['value']} · {worst and worst['value']}")
check(best and best["value"] <= 10.0 * 1.3 and worst["value"] >= 10.0 / 1.3,
      "٣ والرقمُ نسبيٌّ معتدل (‏β × الموقع) — لا قفزةَ مستوىً لم تثبت")
few = {k: v for k, v in list(table.items())[:5]}
check(F.relative_value("I9", {"seg": "insurance", "sig": table["I9"]}, 10.0, few) is None,
      "٤ ولا رقمَ من أقلّ من ستة أقران")
check(F.relative_value("I9", {"seg": "insurance", "sig": {"ri": 0.1}}, 10.0, table) is None,
      "٥ ولا من أقلّ من نصف المؤشّرات")
check(best and best["weights_kind"] == "peer_relative" and best["models"][0]["assumptions"]
      and any("من شركات التأمين" in str(a[2]) for a in best["models"][0]["assumptions"]),
      "٦ ويُعرض بمؤشّراته وموقعه بين أقرانه — لا رقمٌ بلا شاهد")
b = F.blend(dict(best), None, "insurance", 0.03)
check(b.get("target_12m") == best["value"] and b.get("target_err") == F.TARGET_ERR,
      "٧ وهدفُه الرقمُ نفسُه (توقّعٌ مقيسٌ لاثني عشر شهراً) — وخطؤه خطأُ المحرّك المقيس كلِّه (‏D702)")
check(F.track_bucket({**best, "price": 10.0}) == "rel_insurance_better" and F.track_bucket({**worst, "price": 10.0}) == "rel_insurance_weaker",
      "٨ وفئتُه «أفضلُ من أقرانها» أو «أضعف» أو «بينهم» — وسجلُّها مقيسٌ بأقرانها")


def run(arch, vals, price=10.0):
    mods = [{"key": k, "family": "multiples", "name": k, "value": v, "low": v * 0.9, "high": v * 1.1} for k, v in vals.items()]
    saved = (F.base_of, F.cashflow_models, F.equity_models, F.multiple_models, F._tuning)
    F.base_of = lambda i: SimpleNamespace(notes=[], margin_n=0.1, ke=0.1, wacc=0.09, tax=0.02)
    F.cashflow_models = lambda i, bs: mods
    F.equity_models = lambda i, bs: []
    F.multiple_models = lambda i, bs: []
    F._tuning = lambda s: {}
    try:
        A = [{"year": y, "as_of": f"{y}-12-31", "revenue": 1e9 * (1.1 ** k), "net_income": 1e8 * (1.2 ** k), "equity": 1e9,
              "free_cash_flow": 5e7} for k, y in enumerate(range(2021, 2026))]
        return F.value(F.Inputs(symbol="X", price=price, shares=1e8, annual=A, ttm={}, balance={}, ttm_source="t",
                                archetype=arch, sector="s"))
    finally:
        F.base_of, F.cashflow_models, F.equity_models, F.multiple_models, F._tuning = saved


ri = run("insurance", {"residual_income": 8.0, "peer_pb": 12.0})
check(ri.get("value") is None and (ri.get("rel") or {}).get("seg") == "insurance"
      and {"ri", "margin", "fcf_m", "size"} <= set((ri.get("rel") or {}).get("sig") or {}),
      "٩ التأمينُ يحمل مؤشّراتِه إلى المقارنة — لا امتناعٌ نهائيّ", str((ri.get("rel") or {}).get("sig")))
rt = run("commodity", {"epv": 12.0, "residual_income": 9.0, "peer_pb": 11.0})
check(rt.get("value") is None and (rt.get("rel") or {}).get("seg") == "thin"
      and {"ri", "growth", "roe", "ni_g"} <= set((rt.get("rel") or {}).get("sig") or {}),   # والزخمُ من الأسعار المحفوظة إن وُجدت
      "١٠ ومن لا تكفيه النماذجُ المثبتة كذلك", str((rt.get("rel") or {}).get("sig")))
rf = run("financial", {"peer_pe": 12.0, "peer_pb": 13.0, "peer_ps": 14.0})
check(rf.get("value") is None and (rf.get("rel") or {}).get("seg") == "financial",
      "١١ (D702) والخدماتُ الماليةُ تُقارن بأقرانها بالتدفّق التشغيليّ والزخم — ثبتا في النصفين")

src = open(os.path.join(ROOT, "backend/app/services/fair_value_models.py"), encoding="utf-8").read()
fs = src[src.find("async def for_symbol"):]
check("apply_relative(sym, res, i.price, rel_table(" in fs, "١٢ والصفحةُ تقارن بجدول الأقران المحفوظ (‏apply_relative نفسُها)")
sw = open(os.path.join(ROOT, "backend/app/services/market_valuation_sweep.py"), encoding="utf-8").read()
check("async def rel_pass" in sw and sw.find("await rel_pass(done, sem)") < sw.find("rep_verdicts = record_verdicts(done)"),
      "١٣ والمسحةُ جولتان: الأقرانُ قبل المقارنة، والأحكامُ بعدها")
cg = open(os.path.join(ROOT, "scripts/audit/candidate_gate.py"), encoding="utf-8").read()
check("await rel_pass(done, sem)" in cg, "١٤ وبوابةُ المرشَّح تفعل الجولتين كالمسحة")
bt = open(os.path.join(ROOT, "scripts/audit/fv_backtest_d699.py"), encoding="utf-8").read()
check("F.apply_relative(s, res, rows_t[s][\"price\"]" in bt and "segmed[(seg_of(o), o[\"t\"])]" in bt,
      "١٥ والاختبارُ التاريخيّ يقارن بأقران كلّ تاريخ، ويقيس إصابةَ المصارف والمقارنة بأقرانها")
# العيّنةُ الصغيرة تُقال بحجمها لا بنسبةٍ تُوهم، وكلمتُها «منخفضة» توافق نصَّها
from app.services.analysis import confidence_of
_small = {"model_value": 13.0, "price": 10.0, "value": 11.7, "count": 4, "weights_kind": "proven_gmean", "notes": [],
          "models": [{"value": 10.0}] * 4}
_tb = F.track_of(_small)
check(_tb and _tb["n"] < 40 and "عيّنتُها صغيرة" in (F.track_note(_small) or "") and "٪" not in (F.track_note(_small) or "")
      and confidence_of(_small) == "منخفضة",
      "١٦ والعيّنةُ دون أربعين حالة تُقال بحجمها («عيّنتُها صغيرة») لا بنسبة، وثقتُها «منخفضة»", F.track_note(_small) or "")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
