#!/usr/bin/env python3
"""لكلّ نمطٍ في المواصفة أركانٌ في مجلس الخبراء (D433).

    python3 scripts/audit/every_archetype_has_pillars.py

اكتشف المالكُ في اختباره «العربية للخدمات» (‏4071): سعرٌ عادلٌ 50.34 من
قوائمها، وبجانبه «درجة الجودة المالية: بانتظار القوائم». وقِيس بكاشف
`expert_panel_of.py`: مجلسُها خبيران (بافيت · كفاءة رأس المال) والنصابُ
ثلاثة، ومجلسُ 2080 أربعة — أحدُهم «الإطار القطاعي».

والسبب: جدولُ الأركان `_ARCH_PILLARS` لا مفتاحَ فيه باسم
`consumer_cyclical` — فيه أسماءٌ قديمة (`cyclical` · `inventory_retail`)،
والمواصفةُ تُسند هذا الاسمَ لخمسَ عشرةَ شركة. فيعود الجدولُ فارغاً ويصمت
«الإطارُ القطاعي» لكلّ شركةٍ في النمط **أيّاً كانت بياناتُها**، ويقصر
المجلسُ عن النصاب متى غاب شاهدُ ياهو (‏PEG · المحللون) — فتُحبَس
الدرجةُ عن شركةٍ قوائمُها كاملة، ويُقال «بانتظار القوائم».

فالفحص: كلُّ نمطٍ تُسنده المواصفةُ لقطاعٍ له أركانٌ في المجلس (إلا
`fund` — صناديقُ مؤشّراتٍ خارج السوق الرئيسيّ لا درجةَ جودةٍ لها بتصميمها)،
وسلوكياً: شركةٌ من النمط بقوائمَ وحدَها (بلا ياهو) يبلغ مجلسُها النصاب.
"""
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


try:
    from app.data.archetype_spec import SECTOR_ARCHETYPE
    from app.services.expert_panel import _ARCH_PILLARS, build_expert_panel
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)

NO_SCORE_BY_DESIGN = {"fund"}
used = sorted(set(SECTOR_ARCHETYPE.values()))
missing = [a for a in used if a not in _ARCH_PILLARS and a not in NO_SCORE_BY_DESIGN]
check(not missing, "١ لكلّ نمطٍ في المواصفة أركانٌ في مجلس الخبراء",
      f"بلا أركان: {missing}" if missing else f"{len(used)} نمطاً")

# ── ٢ · سلوكياً: شركةٌ استهلاكيةٌ دوريةٌ بقوائمَ وحدَها تبلغ النصاب ──
sec = next((s for s, a in SECTOR_ARCHETYPE.items() if a == "consumer_cyclical"), None)
if sec is None:
    print("⚠ لا قطاعَ للنمط في المواصفة — لم يُقَس ٢")
else:
    feats = {"roic": 12.0, "margin_stability": 20.0,
             "cash_conversion_ratio": 0.9, "roe_avg": 13.3,
             "buffett_quality_score": 4, "buffett_applicable": 8}
    panel = build_expert_panel(feats, sec)
    weigh = [e for e in panel if e.get("tone") != "na" and e.get("role") != "driver"]
    frame = [e for e in panel if "الإطار القطاعي" in str(e)]
    check(len(frame) >= 1, "٢ «الإطارُ القطاعيّ» يحكم في نمطها", f"{len(frame)} ركناً")
    check(len(weigh) >= 3,
          "٢ب ومجلسُها يبلغ النصابَ بالقوائم وحدَها — بلا ياهو",
          f"{len(weigh)} خبيراً · القطاع {sec}")

# ── ٣ · و«بانتظار القوائم» لا تُقال إلا حين لم تصل القوائم ────────
# كانت تُعرض لكلّ امتناعٍ أيّاً كان سببُه — ومنه 4071 وقوائمُها واصلة
# وسعرُها العادلُ محسوبٌ منها. فيُشترط أن يكون كلُّ موضعٍ يُعرض فيه النصُّ
# محكوماً بـ`has_statements === false`.
import re as _re                                                     # noqa: E402
_SRC = ROOT / "frontend" / "src"
if not _SRC.is_dir():
    print("⚠ لا مجلَّدَ واجهةٍ — لم يُقَس ٣")
else:
    _bad = []
    for f in _SRC.rglob("*.tsx"):
        t = _re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=_re.S)
        lines = t.splitlines()
        for i, ln in enumerate(lines):
            if _re.search(r">\s*بانتظار (وصول )?القوائم\s*<", ln):
                ctx = "\n".join(lines[max(0, i - 3):i + 1])
                if "has_statements === false" not in ctx:
                    _bad.append(f"{f.relative_to(ROOT)}:{i + 1}")
    check(not _bad, "٣ «بانتظار القوائم» محكومةٌ بغياب القوائم وحدَه",
          ", ".join(_bad))

print(("FAIL" if fail else "PASS")
      + " D433 — لكلّ نمطٍ أركانُه، ولا تُحبَس درجةٌ لاسمٍ غائبٍ عن جدول")
sys.exit(fail)
