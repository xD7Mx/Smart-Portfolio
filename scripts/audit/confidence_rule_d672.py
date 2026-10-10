#!/usr/bin/env python3
"""حارسُ D672 (المرشَّح 2.3): «مرتفعة» وعدٌ بخطأٍ أصغر — ثلاثةُ نماذج متّفقة تكفي، والنموذجُ المنحازُ بالنمط يُحذف.

القياسُ قبل الإصلاح (conf_calib_door.py · run 38071627969 · conf_prune_door.py · run 38072025586):
  · تشتّتٌ ≤ 10٪ بثلاثة نماذج خطؤه 4.0٪ عن أهداف المحلّلين (14 ورقة، المصارفُ كلُّها) — وشرطُ الأربعة يُنزلها «متوسطة».
    بالثلاثة: خطأُ «المرتفعة» 12.0٪ ← 9.2٪ وحصّتُها 13٪ ← 19٪.
  · نماذجُ منحازةٌ تحت الهدف في أنماطٍ بعينها؛ وحذفُها بتحقّقٍ متقاطعٍ بإسقاط ورقة: السلعُ الرأسمالية 16.0٪ ← 10.3٪ ·
    الاستهلاكُ الدفاعيّ 14.9٪ ← 11.7٪ · التطويرُ العقاريّ 27.6٪ ← 20.1٪. والباقيةُ لم تجتز فلا تُمسّ.
والحارسُ يمنع أن تُرفع الكلمةُ بغير ما قِيس: الخاسرةُ والمتأخّرةُ والمتباعدةُ تبقى دون «مرتفعة».

    python3 scripts/audit/confidence_rule_d672.py
"""
import os, pathlib, sys, tempfile
from types import SimpleNamespace
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services.analysis import confidence_of   # noqa: E402
from app.services import fair_value_models as F   # noqa: E402

M = lambda *vs: [{"key": f"m{i}", "value": v} for i, v in enumerate(vs)]   # noqa: E731
check(confidence_of({"models": M(10, 10.5, 9.8), "notes": [], "set_size": 3}) == "مرتفعة",
      "١ ثلاثةُ نماذج متّفقة هي مجموعةُ القطاع كاملةً (المصارف) تكفي لـ«مرتفعة» — كانت تُنزل أدقَّ الأوراق")
check(confidence_of({"models": M(10, 10.5, 9.8), "notes": [], "set_size": 14}) != "مرتفعة",
      "١ب وثلاثةٌ بقيت من أربعة عشر تعذّر أكثرُها لا تبلغها — تتّفق بالبناء لا بالشهادة (لومي وذيب في بوابة المرشَّح)")
check(confidence_of({"models": M(80, 82, 79, 81), "notes": [], "value": 49.1, "price": 23.5}) == "منخفضة",
      "١ج ورقمٌ يبعد عن السعر أكثرَ من 60٪ لا يكون «مرتفعة» ولا «متوسطة» — فيحجبه D628 (لومي +109٪)")
check(confidence_of({"models": M(10, 12.5, 8), "notes": []}) == "متوسطة",
      "٢ والمتباعدةُ (تشتّت 20٪) تبقى «متوسطة»")
check(confidence_of({"models": M(10, 10.2, 9.9, 10.1), "notes": ["خاسرةٌ في وسيط ثلاث سنوات"]}) == "منخفضة",
      "٣ والخاسرةُ تبقى «منخفضة» ولو اتّفقت نماذجُها")
check(confidence_of({"models": M(10, 10.2, 9.9), "notes": ["أحدثُ قوائم منشورة (x) أقدمُ من تسعة أشهر — الثقةُ أدنى"]})
      != "مرتفعة", "٤ والمتأخّرةُ في الإفصاح لا تبلغ «مرتفعة»")
check(confidence_of({"models": M(10, 10.1), "notes": []}) == "منخفضة", "٥ ونموذجان لا يكفيان")

# ٦ · الحذفُ بالنمط: المعتمدُ وحده، ولا يُنزل النماذجَ تحت ثلاثة
EV = {"peer_ev_ebit", "peer_ev_ebitda", "peer_ev_sales"}
check(F.ARCH_DROP == {"capital_infra": EV | {"epv"}, "consumer_defensive": EV | {"epv", "ddm_stable"},
                      "re_developer": EV},
      "٦ الحذفُ للأنماط الثلاثة التي اجتازت التحقّقَ المتقاطع وحدها — والسلعُ والدوريُّ والمصارفُ والتأمينُ لا تُمسّ")


def run(arch, keys):
    mods = [{"key": k, "family": "multiples", "name": k, "value": 10.0 + i * 0.1, "low": 9.0, "high": 11.0}
            for i, k in enumerate(keys)]
    saved = (F.base_of, F.cashflow_models, F.equity_models, F.multiple_models, F.model_set, F._tuning)
    F.base_of = lambda i: SimpleNamespace(notes=[], margin_n=0.1, ke=0.1, wacc=0.09, tax=0.02)
    F.cashflow_models = lambda i, bs: mods
    F.equity_models = lambda i, bs: []
    F.multiple_models = lambda i, bs: []
    F.model_set = lambda s, a: ("x", set(keys))
    F._tuning = lambda s: {}
    try:
        r = F.value(F.Inputs(symbol="X", price=10.0, shares=1.0, annual=[], ttm={}, balance={}, ttm_source="t",
                             archetype=arch, sector="s"))
    finally:
        F.base_of, F.cashflow_models, F.equity_models, F.multiple_models, F.model_set, F._tuning = saved
    return [m["key"] for m in r.get("models") or []]

k1 = run("capital_infra", ["epv", "peer_ev_ebit", "peer_pe", "peer_pb", "peer_ps", "dcf_gordon_5"])
check(k1 == ["peer_pe", "peer_pb", "peer_ps", "dcf_gordon_5"], "٧ السلعُ الرأسماليةُ تُقيَّم بلا EPV ولا نماذجِ قيمة المنشأة", str(k1))
k2 = run("capital_infra", ["epv", "peer_ev_ebit", "peer_pe", "peer_pb"])
check(len(k2) == 4, "٨ ولا يُحذف ما يُنزل النماذجَ تحت ثلاثة — يبقى الأصل", str(k2))
k2b = run("capital_infra", ["epv", "peer_ev_ebit", "peer_pe", "peer_pb", "peer_ps"])
check(len(k2b) == 5, "٨ب ولا ما يُبقي ثلاثةً وحدها — يبقى أربعةٌ فأكثر أو الأصل (تعديلٌ بعد البوابة)", str(k2b))
k3 = run("commodity", ["epv", "peer_ev_ebit", "peer_pe", "peer_pb"])
check(len(k3) == 4, "٩ والنمطُ الذي لم يجتز التحقّقَ (السلع) لا يُحذف منه شيء", str(k3))
src = (ROOT / "backend/app/services/fair_value_models.py").read_text(encoding="utf-8")
check('f"fvm:v40:{sym}"' in src and '"set_size": len(allowed)' in src,
      "١٠ ومفتاحُ كاش النماذج تغيّر، وحجمُ مجموعة القطاع يُحمَل مع النماذج")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
