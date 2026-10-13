#!/usr/bin/env python3
"""حارسُ D693 — تحليلُ الصفحة المخزَّن يتجدّد مع كلّ مسحةٍ تغيّر رقمَ اليوم، لا مع تاريخها وحدَه.

قِيس بعد نشر 2.4 في منتصف اليوم (‏run 38394651666): مسحةُ النشر غيّرت رقمَ أنابيب الشرق 170.0 ← 171.57 (وسدافكو وجرير) في
اليوم نفسِه، والصفحةُ مفتاحُها «official:2026-10-13» فبقيت برقم المسحة الليليّة يوماً كاملاً والفرزُ يعرض الجديد.

    python3 scripts/audit/official_key_d693.py
"""
import os, pathlib, sys, tempfile
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


from app.services import analysis as A   # noqa: E402
stamp = getattr(A, "official_stamp", None)
row = {"score_asof": "2026-10-13", "fair_value": 170.0, "fair_value_conf": "منخفضة", "fair_value_low": 150.0,
       "fair_value_high": 190.0, "finance_score": 75, "stmt_asof": "2026-03-31"}
s0 = stamp(row) if stamp else None
s1 = stamp({**row, "fair_value": 171.57}) if stamp else None
s2 = stamp({**row, "fair_value_conf": "متوسطة"}) if stamp else None
s3 = stamp({**row, "finance_score": 80, "stmt_asof": "2026-06-30"}) if stamp else None
check(stamp is not None and s0 != s1 and s0 != s2,
      "١ مسحةٌ ثانيةٌ في اليوم نفسِه تغيّر الرقمَ أو ثقتَه ⇒ ختمٌ جديد فتُحسب الصفحةُ من جديد (170.0 ← 171.57)", f"{s0} · {s1} · {s2}")
check(stamp is not None and s0 == s3 and s0.startswith("2026-10-13") and stamp(None) == "live",
      "٢ وما لا تقرؤه الصفحةُ من الصفّ لا يُجدّدها — لا يُهدر الكاش؛ والتاريخُ باقٍ في الختم، وبلا مسحةٍ «live»", f"{s0} · {s3}")
src = (ROOT / "backend/app/services/analysis.py").read_text(encoding="utf-8")
check('ck += f":official:{official_stamp(official_row(symbol))}"' in src and ".get('score_asof') or 'live'}\"" not in src,
      "٣ ومفتاحُ تحليل الصفحة يحمل الختمَ لا تاريخَ المسحة وحدَه")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
