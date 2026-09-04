#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D172 — نصُّ المالك عربيٌّ رسميّ، لا سطرُ تشخيص.
#
# رأى المالكُ في بطاقة الحوكمة حرفياً:
#     «القاعدة 'hold_decent' تحققت: quality=59، safety=63»
# معرّفُ قاعدةٍ بالإنجليزية وأسماءُ متغيّراتٍ داخلية في شاشةٍ يقرؤها. وقد
# نصَّ على أن يُعامَل التطبيقُ برسمية: أرقامٌ وعناوين لا شرحٌ ولا تبرير،
# فكيف بأسماءِ حقولٍ في الشيفرة.
#
# فحصٌ سلوكيّ: يُشغَّل محرّكُ القرار على أركانٍ حقيقيةٍ حتى تتحقّق قاعدة،
# ثمّ يُفتَّش **النصُّ الخارج** عن معرّفاتٍ داخلية. لا قراءةَ مصدر: نصُّ
# السبب يُركَّب في زمن التشغيل من ملفّ القواعد، فقراءةُ الشيفرة لا تراه.
# ─────────────────────────────────────────────────────────────────────────
import pathlib
import re
import sys

import os as _os
import tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backend"))

from app.services.decision_engine import evaluate_decision        # noqa: E402
from app.services.four_scores import compute_four_scores          # noqa: E402
from app.services.four_scores import build_features               # noqa: E402

fail = 0


def say(ok, label, detail=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


# معرّفاتٌ داخلية لا يجوز أن تبلغ الشاشة: أسماءُ حقول الأركان، وصيغةُ
# «اسم='قيمة'» التي تُنتجها سطورُ التشخيص، وأيُّ كلمةٍ لاتينيةٍ بشرطةٍ
# سفلية (نمطُ المعرّفات في الشيفرة).
BANNED_WORDS = ("quality=", "safety=", "valuation=", "timing=", "القاعدة '")
SNAKE = re.compile(r"[a-z]+_[a-z_]+")


def reasons_from_engine() -> list[str]:
    """أسبابٌ حقيقيةٌ من المحرّك — على أركانٍ متنوّعةٍ حتى تشتعل قواعدُ
    مختلفة، فلا يُفحص فرعٌ واحدٌ ويُظنّ الكلُّ نظيفاً."""
    out = []
    for q, s, v, t in ((80, 80, 70, 60), (59, 63, 50, 50), (30, 25, 40, 30),
                       (95, 90, 85, 75), (45, 70, 30, 55)):
        periods = [{
            "year": 2023 + i, "revenue": 1000.0 * (1.06 ** i),
            "net_income": 100 * (1.06 ** i), "operating_cash_flow": 110 * (1.06 ** i),
            "free_cash_flow": 80 * (1.06 ** i), "equity": 700, "total_assets": 1500,
            "debt_ratio": 0.4, "interest_coverage": 6, "capex": -40,
        } for i in range(3)]
        feats = build_features(periods)
        scores = compute_four_scores(feats)
        # نُزيح الأركانَ إلى القيم المطلوبة لنبلغ قواعدَ مختلفة
        for name, val in (("quality", q), ("safety", s), ("valuation", v), ("timing", t)):
            pillar = getattr(scores, name, None)
            if pillar is not None:
                try:
                    pillar.score = val
                except Exception:                                  # noqa: BLE001
                    pass
        d = evaluate_decision(scores, feats, None)
        if d and d.reason:
            out.append(d.reason)
    return out


reasons = reasons_from_engine()
say(len(reasons) >= 3, "١ أُنتجت أسبابٌ حقيقيةٌ من المحرّك", f"{len(reasons)} سبباً")

bad = []
for r in reasons:
    for w in BANNED_WORDS:
        if w in r:
            bad.append((w, r))
    for m in SNAKE.findall(r):
        bad.append((m, r))

for w, r in bad[:6]:
    print(f"     «{w}» في: {r[:90]}")
say(not bad, "٢ لا معرّفَ داخليّاً في نصٍّ يقرؤه المالك", f"{len(bad)} مخالفة")

# ولا يبقى النصُّ فارغاً: حذفُ التشخيص لا يعني حذفَ المعنى.
say(all(r.strip() for r in reasons), "٣ كلُّ سببٍ يحمل نصّاً")
print("     مثال:", reasons[0][:80] if reasons else "—")

print()
print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
sys.exit(fail)
