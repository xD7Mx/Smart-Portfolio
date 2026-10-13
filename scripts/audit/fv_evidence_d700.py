#!/usr/bin/env python3
"""حارسُ D700 — السعرُ العادل من النماذج التي أثبتت نفسها بالنتائج، والثقةُ نسبةُ إصابةٍ مقيسة (بأمر المالك 2026-10-13).

قال المالك: «أريد الأرقامَ بثقةٍ مرتفعة… نماذجُ لها القدرةُ للحكم على شركةٍ ثمّ يتبيّن أنّ توقّعاتها كانت ناجحة».
قِيس (D699 · run 38454399479): الرقمُ كما كان لا يميّز الرابحَ من الخاسر (ارتباط +0.04)، والهدفُ أبعدُ عن السعر المتحقّق
من «لا تغيُّر»، والثقةُ قاعدةٌ داخلية لا تميّز. وفي داخله نماذجُ تتنبّأ فعلاً — فالحارسُ يمنع العودة:
  · غيرُ الماليّة بالنماذج المثبتة وحدها (وسطٌ هندسيّ)، وما سواها معروضٌ خارج الرقم بسببه، ولا رقمَ من أقلّ من ثلاثة.
  · التأمينُ والخدماتُ الماليةُ يُحجب رقمُهما بسببه — والمصارفُ كما ثبتت.
  · الهدفُ = السعر × (تقديرِ النماذج ÷ السعر)^0.15، بخطئه المقيس.
  · الثقةُ من سجلّ فئة القراءة حيث قِيست، بنصّها المقيس؛ وما يُخفّض يبقى يُخفّض.
  · الاختبارُ يقيس أيَّ شيفرة ويطبع مقاييسَ النتيجة، ومهمّةُ المرشَّح تقيس الجانبين بها، وحارسُ التجميد يحكم بها.

    python3 scripts/audit/fv_evidence_d700.py
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
from app.services.analysis import confidence_of

PROVEN = {"epv", "dcf_exit_5", "dcf_exit_10", "peer_ev_sales", "peer_ev_ebit", "peer_ev_ebitda", "peer_pe"}
check(getattr(F, "PROVEN", None) == PROVEN, "١ النماذجُ المثبتةُ بالنتائج سبعة: قوّةُ الأرباح · التدفّقُ بمضاعف الخروج · المنشأة · المكرّر",
      str(sorted(getattr(F, "PROVEN", []) or [])))


def run(arch, vals, price=10.0, sector="s"):
    mods = [{"key": k, "family": "multiples", "name": k, "value": v, "low": v * 0.9, "high": v * 1.1} for k, v in vals.items()]
    saved = (F.base_of, F.cashflow_models, F.equity_models, F.multiple_models, F._tuning)
    F.base_of = lambda i: SimpleNamespace(notes=[], margin_n=0.1, ke=0.1, wacc=0.09, tax=0.02)
    F.cashflow_models = lambda i, bs: mods
    F.equity_models = lambda i, bs: []
    F.multiple_models = lambda i, bs: []
    F._tuning = lambda s: {}
    try:
        return F.value(F.Inputs(symbol="X", price=price, shares=1.0, annual=[], ttm={}, balance={}, ttm_source="t",
                                archetype=arch, sector=sector))
    finally:
        F.base_of, F.cashflow_models, F.equity_models, F.multiple_models, F._tuning = saved


r = run("commodity", {"epv": 12.0, "dcf_exit_5": 15.0, "peer_ev_ebit": 13.0, "peer_pb": 30.0, "ddm_stable": 4.0, "peer_ps": 25.0})
used = sorted(m["key"] for m in r.get("models") or [])
gm = (12.0 * 15.0 * 13.0) ** (1 / 3)
check(used == ["dcf_exit_5", "epv", "peer_ev_ebit"] and abs((r.get("model_value") or 0) - round(gm, 2)) < 0.02,
      "٢ غيرُ الماليّة بالمثبتة وحدها ووسطِها الهندسيّ — الدفتريةُ والتوزيعُ والمبيعاتُ لا تدخل الرقم", f"{used} · {r.get('model_value')}")
ex = {e["key"]: e.get("excluded") for e in r.get("excluded") or []}
check(set(ex) >= {"peer_pb", "ddm_stable", "peer_ps"} and all("لم يُثبت" in str(v) for k, v in ex.items() if k in ("peer_pb", "ddm_stable")),
      "٣ وما لم يثبت معروضٌ خارج الرقم بسببه — لا يختفي رأيٌ بلا أن يُقال لماذا")
r2 = run("consumer_cyclical", {"epv": 12.0, "peer_pe": 13.0, "peer_pb": 20.0, "peer_ps": 18.0, "ddm_stable": 16.0})
check(r2.get("value") is None and "أثبتت نفسها" in str(r2.get("reason")),
      "٤ ولا رقمَ من نموذجين مثبتَين — يُمتنع بسببه ولا يُستكمل بما لم يثبت", str(r2.get("reason"))[:60])
for arch in ("insurance", "financial"):
    ri = run(arch, {"peer_pe": 12.0, "peer_pb": 13.0, "peer_ps": 14.0})
    check(ri.get("value") is None and "لم يثبت" in str(ri.get("reason")),
          f"٥ {arch}: لا يُنشر رقمٌ للقرار — الأرخصُ عنده تخلّف في اختبار ما كان معلوماً", str(ri.get("reason"))[:60])
rb = run("bank", {"peer_pe": 12.0, "peer_pb": 13.0, "peer_ps": 14.0})
check(rb.get("count") == 3 and rb.get("value"), "٦ والمصارفُ بمجموعتها كما ثبتت (+0.18)", str(rb.get("count")))

# الهدفُ معايَرٌ بالنتائج
b = F.blend(dict(r), None, "commodity", 0.03)
exp = round(10.0 * (r["model_value"] / 10.0) ** 0.15, 2)
check(abs((b.get("target_12m") or 0) - exp) < 0.011 and getattr(F, "TARGET_K", None) == 0.15,
      "٧ الهدفُ = السعر × (تقديرِ النماذج ÷ السعر)^0.15 — لا القيمةُ × (1 + كلفةِ الحقوق − التوزيع)", f"{b.get('target_12m')} ≟ {exp}")

# الثقةُ من السجلّ المقيس
saved = dict(F.FV_TRACK)
F.FV_TRACK.clear()
F.FV_TRACK.update({"full_cheap": {"n": 268, "hit": 66, "n1": 120, "hit1": 63, "hit2": 68},
                   "full_dear": {"n": 900, "hit": 55, "n1": 400, "hit1": 52, "hit2": 58},
                   "full_fair": {"n": 240, "hit": 48, "n1": 110, "hit1": 50, "hit2": 46}})
mk = lambda c, n=6, **kw: {"model_value": 10.0 * c, "price": 10.0, "value": 10.0 * c ** 0.6, "count": n,   # noqa: E731
                           "weights_kind": "proven_gmean", "notes": kw.get("notes", []),
                           "models": [{"value": 10.0}] * n}
check(F.track_bucket(mk(1.3)) == "full_cheap" and F.track_bucket(mk(1.7)) == "full_deep" and F.track_bucket(mk(1.3, 4)) == "thin_cheap"
      and F.track_bucket(mk(0.8)) == "full_dear" and F.track_bucket({"model_value": 11, "price": 10, "archetype": "bank"}) == "bank_cheap",
      "٨ فئةُ القراءة: كاملةٌ أو قليلةُ النماذج · مصرف — ثمّ رخيصٌ · عميقُ الخصم · عادل · غالٍ")
check(confidence_of(mk(1.3)) == "مرتفعة", "٩ «مرتفعة» = أصابت فئتُها ≥ 60٪ وفي كلّ نصفٍ ≥ 55٪ — لا اتّفاقُ النماذج")
check(confidence_of(mk(0.8)) == "متوسطة" and confidence_of(mk(1.0)) == "منخفضة",
      "١٠ و«متوسطة» ≥ 55٪ وما دونها «منخفضة» — ولو اتّفقت النماذج", f"{confidence_of(mk(0.8))} · {confidence_of(mk(1.0))}")
check(confidence_of(mk(1.3, notes=["خاسرةٌ في وسيط ثلاث سنوات"])) == "منخفضة"
      and confidence_of(mk(1.3, notes=["أحدثُ قوائم منشورة (x) أقدمُ من تسعة أشهر — الثقةُ أدنى"])) != "مرتفعة",
      "١١ وما يُخفّض يبقى يُخفّض: الخسارةُ «منخفضة» والقوائمُ القديمةُ لا تبلغ «مرتفعة»")
note = F.track_note(mk(1.3)) or ""
check("66٪" in note and "268" in note and "منذ 2023" in note, "١٢ والثقةُ تُعرض بنصّها المقيس", note)
F.FV_TRACK.clear()
F.FV_TRACK.update(saved)

# الاختبارُ ومهمّةُ المرشَّح وحارسُ التجميد
bt = open(os.path.join(ROOT, "scripts/audit/fv_backtest_d699.py"), encoding="utf-8").read()
check("SP_CODE_ROOT" in bt and "@@METRICS@@" in bt and "@@ENGINE_FP@@" in bt and "@@TRACK@@" in bt,
      "١٣ الاختبارُ يقيس أيَّ شيفرة ويطبع بصمتَها ومقاييسَ النتيجة وسجلَّ الفئات")
ops = open(os.path.join(ROOT, ".github/workflows/ops.yml"), encoding="utf-8").read()
_ab = ops[ops.find("candidate_ab)"):ops.find("probe)")]
check(_ab.count("fv_backtest_d699.py") == 2 and "SP_CODE_ROOT=/tmp/control \"$C\" python /app/scripts/audit/fv_backtest_d699.py" in _ab,
      "١٤ ومهمّةُ المرشَّح تقيس النتيجةَ للأساس والمرشَّح على البيانات نفسِها")
fz = open(os.path.join(ROOT, "scripts/audit/engine_freeze_d635.py"), encoding="utf-8").read()
check('"o_ic12": (+1' in fz and '"o_target_err": (-1' in fz and "ANALYST_AGREEMENT" in fz,
      "١٥ وحارسُ التجميد يحكم بالنتيجة — وموافقةُ المحلّلين للاطّلاع حين تُقاس")
ui = open(os.path.join(ROOT, "frontend/src/components/analysis/FairValuePanel.tsx"), encoding="utf-8").read()
check('data-role="fv-track"' in ui and 'data-role="target-err"' in ui,
      "١٦ والتفاصيلُ تعرض إصابةَ الرقم المقيسة وخطأَ الهدف بجانبهما")
# والامتناعُ المقيس لا يملؤه احتياطٌ لم يُختبر — قِيس في A/B (‏run 38457048397) أنّ التأمينَ عاد برقم الاحتياطيّ فارتفعت التغطية
_bi = F.blend({"value": None, "reason": F.UNPROVEN_ARCH["insurance"], "unproven": True, "price": 10.0}, {"value": 12.0}, "insurance", None)
_bt = F.blend({"value": None, "reason": "لا تكفي النماذجُ التي أثبتت نفسها بالنتائج: 2 من 7", "price": 10.0}, {"value": 12.0}, "commodity", None)
check(_bi.get("value") is None and _bt.get("value") is None,
      "١٧ الامتناعُ المقيس لا يملؤه رقمُ الفرز السابق في المزج", f"{_bi.get('value')} · {_bt.get('value')}")
an = open(os.path.join(ROOT, "backend/app/services/analysis.py"), encoding="utf-8").read()
_el = an[an.find('elif _new and _new.get("value") is None'):][:400]
check('_new.get("unproven")' in _el and "أثبتت نفسها" in _el,
      "١٨ ولا رقمُ المحرّك الاحتياطيّ في التحليل — يُعرض السببُ المقيس")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
