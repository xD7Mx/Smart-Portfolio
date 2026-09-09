#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D225 — المنحةُ ليست تخفيفاً، والزيادةُ تخفيف.
#
# صار عندنا وصولٌ إلى إجراءات الشركة في «أرقام»، وأمر المالكُ بإدخالها في
# الحوكمة. والخطرُ هنا **ماليٌّ لا برمجيّ**: عدُّ كلّ ازديادٍ في عدد الأسهم
# تخفيفاً يُنتج حكماً خاطئاً بثقةٍ عالية.
#
#   · أسهمُ المنحة والتجزئة: كلُّ مساهمٍ يأخذ بنسبته، فحصّتُه كما هي.
#     الازديادُ حسابيٌّ لا اقتصاديّ — وعدُّه تخفيفاً يعاقب شركةً على إجراءٍ
#     محايد.
#   · زيادةُ رأس المال بطرحٍ جديد وحقوقُ الأولوية: حصّةُ من لم يكتتب تصغر.
#
# وشاهدُ «أرقام» يملأ العمى ولا يغلب القياس: سلسلةُ الأسهم القائمة هي
# المقياسُ المباشر، والإجراءُ شاهدٌ على **وقوع** التخفيف لا على مقداره —
# فحكمُه متحفّظٌ لا حاسم.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

from app.services.governance_pillar import build, dilution_events  # noqa: E402

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


OWN = {"insiders": 40, "public": 55}
BONUS = [{"kind": "منحة", "date": "2026-04-20", "title": "أحقية أسهم منحة"}]
SPLIT = [{"kind": "تجزئة", "date": "2026-02-01", "title": "تجزئة السهم"}]
RAISE = [{"kind": "زيادة رأس المال", "date": "2026-03-01",
          "title": "زيادة رأس المال عن طريق طرح أسهم"}]
RIGHTS = [{"kind": "حقوق أولوية", "date": "2026-05-01", "title": "طرح حقوق أولوية"}]

base = build({}, [], OWN, None)

# ── ١ · المنحةُ لا تُصنَّف مخفِّفة ────────────────────────────────────
ev = dilution_events(BONUS)
check(not ev["مخفِّفة"] and len(ev["محايدة"]) == 1,
      "١ أسهمُ المنحة محايدةٌ لا مخفِّفة", str(ev))

# ── ٢ · ولا تُغيّر الدرجة ────────────────────────────────────────────
# الاتّجاه المعاكس: العطبُ المتوقَّع هو **خفضُ** الدرجة على إجراءٍ محايد.
b = build({}, [], OWN, BONUS)
check(b["score"] == base["score"],
      "٢ ولا تُغيّر درجةَ الحوكمة", f"{base['score']} ⇐ {b['score']}")

# ── ٣ · والتجزئةُ كذلك ──────────────────────────────────────────────
sp = build({}, [], OWN, SPLIT)
check(sp["score"] == base["score"], "٣ والتجزئةُ محايدةٌ كذلك",
      f"{base['score']} ⇐ {sp['score']}")

# ── ٤ · زيادةُ رأس المال تُخفّف ─────────────────────────────────────
r = build({}, [], OWN, RAISE)
check(r["score"] is not None and r["score"] < base["score"],
      "٤ زيادةُ رأس المال تخفض الدرجة", f"{base['score']} ⇐ {r['score']}")

# ── ٥ · وحقوقُ الأولوية كذلك ────────────────────────────────────────
g = build({}, [], OWN, RIGHTS)
check(g["score"] is not None and g["score"] < base["score"],
      "٥ وحقوقُ الأولوية تخفض الدرجة", f"{base['score']} ⇐ {g['score']}")

# ── ٦ · القياسُ المباشرُ يغلب الشاهد ────────────────────────────────
# حيث توجد سلسلةُ الأسهم القائمة لا يُقرأ الإجراءُ أصلاً: شاهدٌ لا يزاحم
# مقياساً. سلسلةٌ مستقرّةٌ + إجراءُ زيادة ⇒ الحكمُ من السلسلة.
periods = [{"shares_outstanding": 1000} for _ in range(4)]
m = build({}, periods, OWN, RAISE)
keys = [x["key"] for x in m["reads"]]
dil = next((x for x in m["reads"] if x["key"] == "share_dilution"), {})
check(dil.get("source") != "أرقام" and "٣ سنوات" in str(dil.get("label")),
      "٦ حيث توجد سلسلةُ الأسهم لا يُقرأ الشاهد", str(dil.get("label")))

# ── ٧ · والصفُّ المحايدُ يُعرض ولا يُحتسَب ─────────────────────────
# درجةٌ `None` في الجمع كانت سترفع استثناءً على كلّ شركةٍ لها منحة.
neutral = next((x for x in b["reads"] if x["key"] == "share_actions_neutral"), None)
check(neutral is not None and neutral.get("score") is None
      and b["pillars"] == base["pillars"],
      "٧ المحايدُ يُعرض ولا يدخل الحساب", f"أركان {base['pillars']} ⇐ {b['pillars']}")

# ── ٨ · وحكمُ الشاهد متحفّظٌ لا حاسم ───────────────────────────────
# وقوعُ الحدث معلومٌ ومقدارُه ليس كذلك، فلا يُنزل الركنَ إلى القاع.
rd = next((x for x in r["reads"] if x["key"] == "share_dilution"), {})
check(20 < float(rd.get("score") or 0) <= 60 and "غيرُ مقيس" in str(rd.get("verdict")),
      "٨ حكمُ الشاهد متحفّظٌ ويُعلن أن المقدارَ غيرُ مقيس",
      f"{rd.get('score')} · {rd.get('verdict')}")

print()
print("النتيجة:", "فيه ملاحظات ✘" if fail else "نظيف ✔")
raise SystemExit(fail)
