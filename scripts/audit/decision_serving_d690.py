#!/usr/bin/env python3
"""حارسُ D681 · D690 — القرارُ الذي يعرضه الفرزُ هو قرارُ الصفحة: لا يمحوه امتناعٌ عابر، ولا يشيخ عن السعر.

  D681 امتناعُ المسحة (بيانٌ تعذّر وصولُه لحظتَها) كان يمحو حكماً محسوماً حديثاً ما لم يكن حكمَ صفحةٍ بالمحرّك الحاليّ —
       قِيس: خمسُ ريتاتٍ ثمّ 1030 و4339 «بيانات غير كافية» في الفرز والصفحةُ تحكم (run 38130632842 · run 38372206516).
  D690 الفرزُ يعرض حكماً حُسب بسعر فتح الصفحة أو المسحة، والسعرُ يعبر القيمةَ العادلة في الجلسة — قِيس: 1321 · 2370 ·
       4002 · 6015 · 7203 يخالف فرزُها صفحتَها في جلسةٍ واحدة (run 38372206516). فيُحفظ ما قبل سقف القيمة العادلة
       ومُدخَلاتُه، ويُعاد السقفُ بالسعر الحيّ في الفرز وفي الصفحة سواء.
يُشغَّل على الشيفرة الحقيقية بمخزنٍ في الذاكرة — فيُقاس السلوكُ لا النصّ.

    python3 scripts/audit/decision_serving_d690.py
"""
import copy, os, pathlib, sys, tempfile
from datetime import date, timedelta
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts/audit"))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import lastgood   # noqa: E402
from app.services.market_valuation_sweep import record_verdicts   # noqa: E402
from abstain_sim import abstain_overwrite   # noqa: E402
from app.services import decision_engine as DE   # noqa: E402
from app.services import market_screener as MS   # noqa: E402

# ── D681 ──
erased, old_replaced, new_replaced = abstain_overwrite(record_verdicts, lastgood)
check(erased == [], "١ امتناعُ المسحة لا يمحو حكماً محسوماً حديثاً — مسحةُ الأمس وصفحةٌ ومسحةٌ بمحرّكٍ سابق", str(erased))
check(old_replaced and new_replaced, "٢ والحكمُ الشائخ (45 يوماً) يُستبدل، والحكمُ المحسومُ الجديد يحلّ محلّ القديم — لا تجميد",
      f"{old_replaced} · {new_replaced}")

# ── D690: السقفُ بسعر اللحظة ──
lbl = DE.public_label
buy = DE.Decision(decision="شراء", matched_rule_id="R", reason="س")
strong = DE.Decision(decision="شراء قوي", matched_rule_id="S", reason="س")
cb = DE.ceiling_inputs(buy, 100.0, 80.0, coverage=0.9) if hasattr(DE, "ceiling_inputs") else None
cs = DE.ceiling_inputs(strong, 100.0, 80.0, coverage=0.9) if hasattr(DE, "ceiling_inputs") else None
ra = getattr(DE, "reapply_ceiling", lambda c, p: None)
got = [(ra(cb, 90) or buy).decision, (ra(cb, 105) or buy).decision, (ra(cs, 85) or strong).decision, (ra(cs, 75) or strong).decision]
check(got == ["شراء", "انتظار", "شراء", "شراء قوي"],
      "٣ السقفُ يُعاد بالسعر: «شراء» فوق القيمة ⇒ «انتظار»، و«شراء قوي» فوق سعر الدخول ⇒ «شراء» — وفي الاتجاهين", str(got))
check(DE.ceiling_inputs(DE.Decision("تجنب", "X", ""), 100.0) is None if hasattr(DE, "ceiling_inputs") else False,
      "٤ وما لا يحرّكه السعرُ (تجنّبٌ، امتناع) لا سقفَ له يُحفظ")

sv = getattr(MS, "served_decision", None)
stored = {"label": lbl("انتظار"), "raw": "انتظار", "rule_id": "R+سقف_القيمة_العادلة"}
deep_row = {"decision": stored, "ceiling": cb}
check(sv is not None and sv(deep_row, 95.0) == lbl("شراء") and sv(deep_row, 104.0) == lbl("انتظار"),
      "٥ الفرزُ يقدّم الحكمَ المحفوظ بسعر اللحظة — «انتظار» الصباح يصير «شراء» حين ينزل السعرُ دون القيمة",
      str(sv and (sv(deep_row, 95.0), sv(deep_row, 104.0))))
foreign = {"decision": {"label": lbl("تجنب"), "raw": "تجنب", "rule_id": "red_line"}, "ceiling": cb}
check(sv is not None and sv(foreign, 50.0) == lbl("تجنب") and sv({"decision": stored}, 95.0) == lbl("انتظار"),
      "٦ وسقفٌ لحكمٍ آخر لا يُعاد على هذا الحكم، وما لا سقفَ له يُعرض كما حُفظ")

# والقراءةُ نفسُها (‏with_live_decisions) بالسعر الذي في الصفّ
mem = {"governance:deep": {"7203": copy.deepcopy(deep_row)}}
l0, s0 = lastgood.load, lastgood.save
lastgood.load = lambda key, *a, **k: copy.deepcopy(mem.get(key))
lastgood.save = lambda key, val, *a, **k: mem.__setitem__(key, copy.deepcopy(val))
try:
    rows = MS.with_live_decisions([{"symbol": "7203.SR", "price": 95.0, "decision": lbl("انتظار")},
                                   ])
    check(rows[0].get("decision") == lbl("شراء"), "٧ وقراءةُ الفرز تقدّمه بسعر صفّها لا بالمخزَّن كما هو", rows[0].get("decision"))
    # ومسحةٌ تحكم «تجنّب» بلا سقف تمحو سقفَ «شراء» الأمس — فلا يُعاد عليها
    t = date.today()
    mem["governance:deep"] = {"1321": {"decision": {"label": lbl("شراء"), "raw": "شراء", "rule_id": "R"}, "ceiling": cb,
                                       "at": (t - timedelta(days=8)).isoformat(), "source": "sweep", "v": "OLD"}}
    record_verdicts({"1321": {"_verdict": {"decision": {"label": lbl("تجنب"), "raw": "تجنب", "rule_id": "red_line"},
                                           "evaluable": True}}}, today=t, engine_v="ENG")
    d = mem["governance:deep"]["1321"]
    check(not d.get("ceiling") and (sv(d, 50.0) if sv else None) == lbl("تجنب"),
          "٨ وحكمٌ جديدٌ بلا سقف يمحو سقفَ الحكم السابق — لا يعود «شراءُ» الأمس على «تجنّب» اليوم", str(d.get("ceiling"))[:60])
finally:
    lastgood.load, lastgood.save = l0, s0

# ── المواضعُ التي تحمل السقفَ وتقدّمه ──
rd = lambda p: (ROOT / p).read_text(encoding="utf-8")   # noqa: E731
an, sw, ms, mk = (rd("backend/app/services/analysis.py"), rd("backend/app/services/market_valuation_sweep.py"),
                  rd("backend/app/services/market_screener.py"), rd("backend/app/api/v1/endpoints/market.py"))
check('"decision_ceiling": _ceil' in an and an.count('"ceiling": result.get("decision_ceiling")') == 2
      and '"ceiling": a.get("decision_ceiling")' in sw and '"ceiling": vd.get("ceiling")' in sw,
      "٩ السقفُ يُحمل مع كلّ حكمٍ يُكتب في المخزن العميق — من الصفحة (حكماً وامتناعاً) ومن المسحة")
check(ms.count("served_decision(") >= 4 and 'r["decision"] = served_decision(_dd, r.get("price"))' in ms
      and "reapply_ceiling(data.get(\"decision_ceiling\"), _lp)" in mk and '"ceiling": ceil' in mk,
      "١٠ ويُقدَّم بسعر اللحظة في كلّ موضع: بناءُ الفرز وقراءتُه وإنعاشُه بالسعر الحيّ، وصفحةُ الشركة")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
