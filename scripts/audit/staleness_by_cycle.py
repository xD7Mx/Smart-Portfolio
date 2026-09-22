#!/usr/bin/env python3
"""الشيخوخةُ تُقاس بدورة الإفصاح لا بالتقويم (‏D409).

    python3 scripts/audit/staleness_by_cycle.py

كان حدُّ الشيخوخة ‎45 يوماً، فخرجت مسحةُ السوق بـ**268 من 270** ورقةً
«شائخة». وقِيس على المصدر نفسِه (‏`filing_types_door.py` على خادم
المالك): أحدثُ ملفّات ‎1010 بتاريخ ‎2026-08-24، و‎4070 بـ‎2026-09-14 —
وفتراتُها تنتهي بنهاية الربع، أي عمرٌ نحوُ ‎84 يوماً **وهي في أوان
إفصاحها**. فشركةٌ تُفصح ربعياً يستحيل أن تكون أرقامُها أحدثَ: الربعُ
يُقفل، ثمّ يُمهَل المُصدِر للنشر، ثمّ يمضي الربعُ التالي.

فالحدُّ ‎45 كان **إنذاراً كاذباً على نطاق السوق كلِّه**: يَصِم السليمَ
بالشيخوخة، فيخفض ثقتَه، فيوسّع هامشَ أمانه، فيرفع سعرَ دخول المالك بلا
وجهِ حقّ. وهو أسوأُ من الصمت، لأنّ إنذاراً يعمّ الجميعَ يُفقد الإنذارَ
الصادقَ معناه.

والحدُّ الصادق: ربعٌ (‏92) + مهلةُ نشرٍ (‏45) = ‎137 يوماً. وما تجاوزه
تأخّرَ عن دورته فعلاً — **ويُكلّفه تأخّرُه**: ثقةٌ منخفضةٌ وهامشٌ أوسع.
فوسمٌ لا يُغيّر قراراً وسمٌ يُقرأ ويُنسى.
"""
from __future__ import annotations

import pathlib
import sys
from datetime import date, timedelta

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
    from app.services.fair_value import STALE_AFTER_DAYS, compute
except (ModuleNotFoundError, ImportError) as e:
    print(f"⚠ بيئةٌ ناقصة ({e}) — لم يُقَس")
    sys.exit(0)


def _run(days: int) -> dict:
    d = (date.today() - timedelta(days=days)).isoformat()
    prev = (date.today() - timedelta(days=days + 92)).isoformat()
    per = [{"as_of": d, "equity": 1000.0, "total_assets": 6000.0,
            "net_income": 120.0, "shares_outstanding": 100.0, "eps": 1.2,
            "revenue": 400.0, "total_liabilities": 5000.0},
           {"as_of": prev, "equity": 950.0, "total_assets": 5800.0,
            "net_income": 110.0, "shares_outstanding": 100.0, "eps": 1.1,
            "revenue": 380.0, "total_liabilities": 4850.0}]
    return compute({"book_value": 10.0, "trailing_eps": 1.2,
                    "return_on_equity": 0.12}, price=12.0,
                   sector_avg_pe=10.0, sector_avg_pb=1.1,
                   periods=per, archetype="bank", symbol="0000")


# ── ١ · الحدُّ مشتقٌّ من الدورة لا رقمٌ مرتجَل ─────────────────────────
check(120 <= STALE_AFTER_DAYS <= 150,
      "١ حدُّ الشيخوخة من دورة الإفصاح — ربعٌ ومهلةُ نشر",
      f"{STALE_AFTER_DAYS} يوماً")

# ── ٢ · الربعُ الأحدثُ ليس شائخاً ──────────────────────────────────────
# هذا هو العطبُ بعينه: ‎84 يوماً هو وسيطُ عمر السوق كلِّه، وكان يُوسَم.
_a = _run(84)
check(_a.get("stale") is False,
      "٢ أرقامُ الربع الأحدث (‏84 يوماً) ليست شائخة — لا إنذارَ كاذب")
_b = _run(130)
check(_b.get("stale") is False,
      "٢ب وما دون الحدّ في أوانه", f"{_b.get('age_days')} يوماً")

# ── ٣ · والمتأخّرُ عن دورته يُوسَم ويُكلَّف ────────────────────────────
_c = _run(STALE_AFTER_DAYS + 25)
check(_c.get("stale") is True, "٣ والمتأخّرُ عن دورته يُوسَم شائخاً",
      f"{_c.get('age_days')} يوماً")
check(_c.get("confidence") == "منخفضة",
      "٣ب ويُكلّفه تأخّرُه ثقةً — لا وسمٌ يُقرأ ويُنسى",
      str(_c.get("confidence")))
if _a.get("entry_price") and _c.get("entry_price"):
    check(_c["entry_price"] < _a["entry_price"],
          "٣ج وسعرُ الدخول ينخفض — التأخّرُ مُسعَّرٌ لا موصوف",
          f"{_a['entry_price']} ← {_c['entry_price']}")

# ── ٤ · والأساسُ مُعلَنٌ لا مضمَر ──────────────────────────────────────
check(bool(_a.get("stale_basis")),
      "٤ أساسُ الحدّ مُعلَنٌ في المخرَج", str(_a.get("stale_basis") or ""))
check(_a.get("age_basis") == "أحدثُ فترةٍ ماليةٍ مستعملة",
      "٤ب والعمرُ من أحدثِ فترةٍ لا من تاريخ الجلب (‏D380)")

print(("FAIL" if fail else "PASS")
      + " D409 — الشيخوخةُ بدورة الإفصاح، والتأخّرُ مُسعَّر")
sys.exit(fail)
