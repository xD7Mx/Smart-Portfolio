#!/usr/bin/env python3
"""حارسُ D675 (بقرار المالك 2026-10-10: «فصلُ الثبات عن الثقة»): «ثقة X٪» كفايةُ البيانات، وثباتُ الأرباح وسمٌ بجانبها.

الحالُ قبل القرار (gov_conf_door.py · run 38071763287): الدرجةُ = 0.4 سنوات + 0.4 اكتمال + 0.2 ثبات، ووسيطُ الثبات 28 —
فلم تبلغ 90 إلا 28 شركةً من 271، و166 لا تبلغها ولو اكتملت سنواتُها ومؤشّراتُها: صفةٌ في الشركة تُقرأ ضعفاً في بياناتنا.

    python3 scripts/audit/stability_d675.py
"""
import inspect, os, pathlib, sys, tempfile
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


from app.services.confidence import compute_confidence, _CORE_FEATURES   # noqa: E402
full = {k: {"value": 1.0} for k in _CORE_FEATURES}
c = compute_confidence({**full, "years_available": {"value": 6}, "consistency_index": {"value": 10.0}})
check(c.score >= 90, "١ بياناتٌ كاملةٌ لست سنوات تبلغ «ثقة» 90 فأكثر ولو تذبذبت الأرباح — الثقةُ في البيانات لا في الشركة",
      str(c.score))
check(c.stability_label == "متذبذبة" and c.stability == 10.0, "٢ والتذبذبُ لا يضيع: وسمٌ مستقلٌّ بقيمته", f"{c.stability_label} · {c.stability}")
c2 = compute_confidence({**full, "years_available": {"value": 6}, "consistency_index": {"value": 75.0}})
check(c2.score == c.score and c2.stability_label == "مستقرّة", "٣ والثباتُ لا يرفع الثقةَ ولا يخفضها — يغيّر وسمَه وحده",
      f"{c.score} · {c2.score} · {c2.stability_label}")
c3 = compute_confidence({**full, "years_available": {"value": 2}, "consistency_index": {"value": 10.0}})
check(c3.score < 90, "٤ وقِصَرُ السجلّ (سنتان) يخفضها دون 90", str(c3.score))
thin = {k: ({"value": 1.0} if i < 9 else {"value": None}) for i, k in enumerate(_CORE_FEATURES)}
c4 = compute_confidence({**thin, "years_available": {"value": 1}, "consistency_index": {"value": 10.0}})
check(c4.score < 60 and c4.warning and "سنة" in c4.warning and "تذبذب" not in c4.warning,
      "٤ب وتحت 60 يُحذَّر بأسباب البيانات وحدها — لا بتذبذب الأرباح", str(c4.warning)[:90])
from app.services import analysis, governance_engine, decision_engine   # noqa: E402
src_a = inspect.getsource(analysis)
check('"stability_label": conf.stability_label' in src_a and '"stability_label": confidence.stability_label'
      in inspect.getsource(governance_engine), "٥ والوسمُ يصل الصفحةَ ونافذةَ الحوكمة من المنتِج الواحد")
check("conf.score" not in inspect.getsource(decision_engine),
      "٦ والقرارُ لا يقرأ درجةَ الثقة (سنواتُ القوائم وحدها) — فالفصلُ لا يغيّر قراراً")
fe = (ROOT / "frontend/src/components/governance/GovernanceV2Modal.tsx").read_text(encoding="utf-8")
check("stability_label" in fe and "ثباتُ الأرباح" in fe and "var(--warn-ink)" in fe and "flex-wrap" in fe,
      "٧ والنافذةُ تعرض «ثباتُ الأرباح» بجانب «ثقة X٪» بألوان الرموز، وتلتفّ على الجوال")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
