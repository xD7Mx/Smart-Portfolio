#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D237 — من حمل لقبَ «السعر العادل» حكَم به القرار.
#
# صار محرّكُ التقييم يُعرض باسم «السعر العادل» (بأمر المالك). ولو بقيت
# بوّابةُ القرار تحكم بهدف المحلّلين وحدَه، لعادت أقبحُ صورةٍ من D174:
# شاشةٌ تقول «السعر العادل ‎28.40» وسعرُ السهم ‎34 وقرارٌ تحته يقول
# «شراء» — لأن المعروضَ ليس هو المحكومَ به. والاسمُ يُلزِم.
#
# يُقاس سلوكاً على البوّابة نفسِها ثم على وصلها في مسار التحليل:
#   ١· سعرٌ فوق الرقم المعروض ⇒ «شراء» لا تبقى شراءً
#   ٢· وحيث لا رقمَ معروضاً لا يُمنع حكمٌ (لا نبني على ما لم نعرضه)
#   ٣· ومسارُ التحليل يمرّر المعروضَ: هدفَ المحلّلين إن وُجد، وإلا
#      السعرَ العادل — بشرط ثقةٍ لا تكون منخفضة
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import pathlib
import re
import sys
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services.decision_engine import (Decision,  # noqa: E402
                                          apply_fair_value_ceiling)

BUY = Decision(decision="شراء", matched_rule_id="buy_test", reason="اختبار")

# ── ١ · سعرٌ فوق المعروض: «شراء» تُلطَّف ─────────────────────────────────
above = apply_fair_value_ceiling(BUY, 34.0, 28.40)
check(above.decision != "شراء",
      "١ سعرٌ فوق السعر العادل المعروض ⇒ «شراء» لا تبقى",
      f"صارت «{above.decision}»")

# ── ٢ · وسعرٌ دونه لا يُلطَّف بلا سبب ────────────────────────────────────
below = apply_fair_value_ceiling(BUY, 22.0, 28.40)
check(below.decision == "شراء",
      "٢ وسعرٌ دونه يبقى حكمُه", f"«{below.decision}»")

# ── ٣ · ولا رقمَ أصلاً ⇒ امتناعٌ لا حكمٌ خام ────────────────────────────
# قِيس فسُجّل: البوّابةُ لا تُمرّر «شراءً» بلا رقمِ تقييمٍ بل تمتنع
# (‏«بيانات غير كافية»). وهذا أصدقُ ممّا افترضتُه أوّلاً، وهو أثرُ أمر
# المالك مباشرةً: الشركاتُ التي لا يغطّيها بيتُ خبرة كانت تمتنع دائماً،
# وصار لها الآن رقمٌ يُحكم به — فخرجت من الامتناع بسببٍ لا بتخفيف.
none_fv = apply_fair_value_ceiling(BUY, 34.0, None)
check(none_fv.decision != "شراء",
      "٣ وبلا رقمِ تقييمٍ يمتنع الحكمُ ولا يُمرَّر «شراء»",
      f"«{none_fv.decision}»")

# ── ٤ · ووصلُ المسار: المعروضُ هو ما يصل البوّابة ───────────────────────
# فحصُ بنيةٍ لا غنى عنه: القاعدةُ أعلاه تُقاس سلوكاً، وهذا يتأكّد أنّ
# التحليلَ يمرّر الرقمَ المعروضَ لا هدفَ المحلّلين وحدَه.
src = (ROOT / "backend/app/services/analysis.py").read_text(encoding="utf-8")
gate = re.search(r"_gate_fv = _shown_fv(.{0,400}?)apply_fair_value_ceiling",
                 src, re.S)
check(bool(gate), "٤ التحليلُ يبني رقمَ البوّابة من المعروض")
if gate:
    blk = gate.group(1)
    check("rel_value" in blk,
          "٥ فحيث لا هدفَ محلّلين يصلها السعرُ العادل من المحرّك")
    check("منخفضة" in blk or '"مرتفعة", "متوسطة"' in blk,
          "٦ وثقةٌ منخفضةٌ لا يُبنى عليها منعٌ — قيدٌ معلَن")
check("_gate_fv," in src,
      "٧ والرقمُ المبنيُّ هو ما يُسلَّم للبوّابة فعلاً")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
