"""‏D681: محاكاةٌ حتميّةٌ تقيس سياسةَ حفظ الأحكام في المخزن العميق الذي يقرؤه الفرز — هل يمحو امتناعُ مسحةٍ عابرٌ
(بياناتٌ تعذّر وصولُها لحظةَ المسحة) حكماً محسوماً حديثاً؟ قِيس في الإنتاج: خمسُ ريتاتٍ ثمّ اثنتان غيرُها صارت «بيانات غير
كافية» في الفرز والصفحةُ تحكم (parity_gate · run 38130632842 · run 38372206516).

تُستدعى من بوابة المحرّكات (`engines_gate_v1.py`) فتُقاس بشيفرة الإصدار نفسِه: `record_verdicts` الحقيقيّة على مخزنٍ في
الذاكرة لا يمسّ الإنتاج."""
import copy
from datetime import date, timedelta


def abstain_overwrite(record_verdicts, lastgood, engine_v: str = "ENG"):
    """← (الأحكامُ المحسومةُ الحديثةُ التي محاها الامتناع، هل استُبدل الحكمُ القديمُ (45 يوماً)، هل استبدل حكمٌ محسومٌ جديدٌ قديمَه)."""
    t = date.today()
    ago = lambda n: (t - timedelta(days=n)).isoformat()           # noqa: E731
    dec = lambda lbl: {"label": lbl, "raw": lbl, "rule_id": "buy"}   # noqa: E731
    ab = {"label": "بيانات غير كافية", "raw": "بيانات غير كافية", "rule_id": "insufficient_data"}
    store = {
        "A": {"decision": dec("شراء"), "at": ago(1), "source": "sweep", "v": engine_v},   # حكمُ مسحة الأمس
        "B": {"decision": dec("تجنب"), "at": ago(2), "v": "OLD"},                        # حكمُ صفحةٍ بمحرّكٍ سابق
        "C": {"decision": dec("انتظار"), "at": ago(3), "source": "sweep", "v": "OLD"},   # حكمُ مسحةٍ بمحرّكٍ سابق
        "D": {"decision": dec("شراء"), "at": ago(45), "source": "sweep", "v": engine_v},  # قديمٌ — يُستبدل
        "E": {"decision": dec("شراء"), "at": ago(1), "source": "sweep", "v": engine_v},   # يأتيه حكمٌ محسومٌ جديد
    }
    done = {k: {"_verdict": {"decision": ab, "evaluable": False}} for k in "ABCD"}
    done["E"] = {"_verdict": {"decision": dec("انتظار"), "evaluable": True}}
    mem = {"governance:deep": copy.deepcopy(store)}
    l0, s0 = lastgood.load, lastgood.save
    lastgood.load = lambda key, *a, **k: copy.deepcopy(mem.get(key))
    lastgood.save = lambda key, val, *a, **k: mem.__setitem__(key, copy.deepcopy(val))
    try:
        record_verdicts(done, today=t, engine_v=engine_v)
    finally:
        lastgood.load, lastgood.save = l0, s0
    out = mem["governance:deep"]
    rule = lambda k: ((out.get(k) or {}).get("decision") or {}).get("rule_id")      # noqa: E731
    label = lambda k: ((out.get(k) or {}).get("decision") or {}).get("label")       # noqa: E731
    return [k for k in "ABC" if rule(k) == "insufficient_data"], rule("D") == "insufficient_data", label("E") == "انتظار"
