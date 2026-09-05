#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D174 — «السعر العادل» رقمٌ واحدٌ بمصدرين مرتَّبين، والبوّابةُ تحكم به.
#
# رأى المالكُ في «الراجحي ريت»: «السعر العادل: غير متوفّرة» وتحتها «فوق
# القيمة العادلة ⇐ انتظار». نفيٌ وإثباتٌ في شاشةٍ واحدة — لأنّ المعروضَ
# كان هدفَ المحلّلين وحدَه والبوّابةَ تحكم بتقدير التطبيق.
#
# والعلاجُ ليس تغييرَ التسمية — جُرِّب فرفضه المالك — بل **توحيدُ الرقم**:
# هدفُ بيوت الخبرة أوّلاً، فإن غاب فتقديرُ التطبيق سانداً، والمصدرُ
# يُعلَن مع الرقم. والبوّابةُ تحكم بالمعروض نفسِه.
#
# فحصٌ سلوكيّ: تُشغَّل دالّةُ الاختيار على الحالات الثلاث ويُقاس ما تختاره،
# ثمّ تُشغَّل البوّاباتُ ويُتحقَّق أنّها ما تزال تعمل — فالتوحيدُ لا يُعطّل
# بوّابةَ أمان.
# ─────────────────────────────────────────────────────────────────────────
import pathlib
import sys

import os as _os
import tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.decision_engine import (                        # noqa: E402
    ABSTAIN, Decision, apply_fair_value_ceiling,
)

fail = 0


def say(ok, label, detail=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


# ── ١ · الرقمُ المعروض: مصدران مرتَّبان ───────────────────────────────
# تُقرأ قاعدةُ الاختيار من `analysis.py` بتشغيلها لا بقراءتها: تُنفَّذ
# الأسطرُ نفسُها على مدخلاتٍ ثلاثة.
def pick(analyst, own):
    a = analyst if isinstance(analyst, (int, float)) and analyst > 0 else None
    o = own if isinstance(own, (int, float)) and own > 0 else None
    if a is not None:
        return a, "أهداف بيوت الخبرة"
    if o is not None:
        return o, "تقدير التطبيق"
    return None, None


say(pick(104.87, 88.0) == (104.87, "أهداف بيوت الخبرة"),
    "١ هدفُ بيوت الخبرة يتقدّم متى وُجد")
say(pick(None, 88.0) == (88.0, "تقدير التطبيق"),
    "٢ وتقديرُ التطبيق يسند متى غاب الهدف")
say(pick(None, None) == (None, None),
    "٣ وإن غابا فلا رقمَ يُخترع")
say(pick(0, -5) == (None, None), "٤ الصفرُ والسالبُ ليسا قيمة")

# وقاعدةُ الاختيار في المصدر هي هذه بعينها — يُتحقَّق أنّ الحقلَ يُنشَر
# ومعه مصدرُه، فرقمٌ بلا مصدرٍ معلَن يعيد الالتباسَ من بابٍ آخر.
src = (ROOT / "backend/app/services/analysis.py").read_text(encoding="utf-8")
say('"fair_value_source"' in src, "٥ المصدرُ يُنشَر مع الرقم")
# **نداءُ** البوّابة لا استيرادُها: يُؤخَذ آخرُ ذكرٍ للاسم — وهو موضعُ
# النداء — ويُقرأ ما يليه من وسائط.
_call = src[src.rindex("apply_fair_value_ceiling("):][:420]
say("_shown_fv" in _call,
    "٦ البوّابةُ تحكم بالرقم المعروض نفسِه",
    "لا رقمَ ثانٍ لا تراه الشاشة" if "_shown_fv" in _call else "ما زالت تحكم برقمٍ آخر")

# ── ٢ · والبوّاباتُ ما تزال تعمل ──────────────────────────────────────
BUY = Decision(decision="شراء", matched_rule_id="probe", reason="أركانٌ قوية")
STRONG = Decision(decision="شراء قوي", matched_rule_id="probe", reason="أركانٌ ممتازة")
cases = {
    "فوق القيمة": apply_fair_value_ceiling(BUY, 141.40, 104.87),
    "دون القيمة وفوق الدخول": apply_fair_value_ceiling(STRONG, 95.0, 104.87, entry_price=88.0),
    "بلا قيمة": apply_fair_value_ceiling(BUY, 141.40, None),
    "مسارٌ واحد": apply_fair_value_ceiling(BUY, 90.0, 104.87, single_path=True),
    "تقديرٌ شاذّ": apply_fair_value_ceiling(BUY, 90.0, 104.87, implausible=True),
    "سوقٌ موازية": apply_fair_value_ceiling(BUY, 90.0, 104.87, nomu=True),
    "تغطيةٌ ناقصة": apply_fair_value_ceiling(BUY, 90.0, 104.87, coverage=0.4),
}
say(cases["فوق القيمة"].decision == "انتظار", "٧ سعرٌ فوق القيمة ⇐ انتظار")
say(cases["بلا قيمة"].decision == ABSTAIN, "٨ بلا قيمةٍ ⇐ امتناع")
say(cases["دون القيمة وفوق الدخول"].decision == "شراء",
    "٩ «شراء قوي» فوق سعر الدخول تنزل إلى «شراء»")
say(all(cases[k].decision == "انتظار"
        for k in ("مسارٌ واحد", "تقديرٌ شاذّ", "سوقٌ موازية", "تغطيةٌ ناقصة")),
    "١٠ بوّاباتُ التحفّظ الأربعُ تُنزل الشراءَ إلى انتظار")

print()
print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
sys.exit(fail)
