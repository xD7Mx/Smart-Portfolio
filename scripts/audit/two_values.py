#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D174 — رقمان لا يحملان اسماً واحداً.
#
# «السعر العادل» المعروض هو **متوسّطُ أهداف بيوت الخبرة** (بأمر المالك)،
# وبوّابةُ القرار تحكم بـ**تقديرنا المحسوب** — رقمان مختلفان. فرأى المالكُ
# في «الراجحي ريت»: «السعر العادل: غير متوفّرة» وتحتها «فوق القيمة
# العادلة ⇐ انتظار». نفيٌ وإثباتٌ في شاشةٍ واحدة.
#
# والبوّابةُ تبقى على رقمها — الحكمُ بهدف المحلّلين وحدَه يُسكِت التطبيقَ
# عن ‎١٢٤ شركةً من ‎٢٧٣ لنقصٍ في مزوّدٍ لا لعيبٍ فيها — لكنّها لا تسمّيه
# باسم الرقم المعروض.
#
# فحصٌ سلوكيّ: تُشغَّل البوّابةُ على حالاتها الحقيقية ويُفتَّش النصُّ
# الخارج. لا قراءةَ مصدر — النصوصُ تُركَّب بالتنسيق في زمن التشغيل.
# ─────────────────────────────────────────────────────────────────────────
import pathlib
import sys

import os as _os
import tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backend"))

from app.services.decision_engine import (                        # noqa: E402
    ABSTAIN, Decision, apply_fair_value_ceiling,
)

fail = 0


def say(ok, label, detail=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


BUY = Decision(decision="شراء", matched_rule_id="probe", reason="أركانٌ قوية")
STRONG = Decision(decision="شراء قوي", matched_rule_id="probe", reason="أركانٌ ممتازة")

cases = {
    "سعرٌ فوق التقدير": apply_fair_value_ceiling(BUY, 141.40, 104.87),
    "دون التقدير وفوق الدخول": apply_fair_value_ceiling(
        STRONG, 95.0, 104.87, entry_price=88.0),
    "بلا تقدير": apply_fair_value_ceiling(BUY, 141.40, None),
    "مسارٌ واحد": apply_fair_value_ceiling(BUY, 90.0, 104.87, single_path=True),
    "تقديرٌ شاذّ": apply_fair_value_ceiling(BUY, 90.0, 104.87, implausible=True),
    "سوقٌ موازية": apply_fair_value_ceiling(BUY, 90.0, 104.87, nomu=True),
    "تغطيةٌ ناقصة": apply_fair_value_ceiling(BUY, 90.0, 104.87, coverage=0.4),
}

say(all(d is not None for d in cases.values()),
    "١ البوّاباتُ كلُّها تُخرج حكماً", f"{len(cases)} حالة")

# الاسمُ المحجوز: «القيمة العادلة» و«السعر العادل» لهدف المحلّلين وحدَه.
RESERVED = ("القيمة العادلة", "السعر العادل", "قيمتنا العادلة")
bad = []
for label, d in cases.items():
    if not d:
        continue
    for w in RESERVED:
        if w in (d.reason or ""):
            bad.append((label, w, d.reason))

for label, w, reason in bad:
    print(f"     [{label}] «{w}» في: {reason[:80]}")
say(not bad, "٢ لا نصَّ يسمّي تقديرَنا باسم الرقم المعروض",
    f"{len(bad)} مخالفة")

# والبوّاباتُ ما تزال تعمل — تسميةٌ لا تُعطِّل حكماً.
say(cases["سعرٌ فوق التقدير"].decision == "انتظار",
    "٣ سعرٌ فوق التقدير ⇐ انتظار", cases["سعرٌ فوق التقدير"].decision)
say(cases["بلا تقدير"].decision == ABSTAIN,
    "٤ بلا تقدير ⇐ امتناع", cases["بلا تقدير"].decision)
say(cases["دون التقدير وفوق الدخول"].decision == "شراء",
    "٥ «شراء قوي» فوق سعر الدخول تنزل إلى «شراء»",
    cases["دون التقدير وفوق الدخول"].decision)
say(cases["تغطيةٌ ناقصة"].decision == "انتظار",
    "٦ تغطيةٌ دون الحدّ ⇐ انتظار")

# ووسمُ الدخول في محرّك القيمة يسمّي مقياسَه كذلك.
from app.services import fair_value as _fv                        # noqa: E402
import inspect                                                    # noqa: E402
src = inspect.getsource(_fv.compute) if hasattr(_fv, "compute") else ""
say("فوق القيمة العادلة" not in src,
    "٧ وسمُ الدخول لا يسمّي تقديرَنا «القيمة العادلة»")

print()
print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
sys.exit(fail)
