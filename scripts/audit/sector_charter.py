#!/usr/bin/env python3
"""لكلّ قطاعٍ هيكلةُ تقييمٍ معلَنةٌ تطابق محرّكَها (‏D405).

    python3 scripts/audit/sector_charter.py

قضى المالك: «يجب أن يتوفّر للجميع آليةُ عملٍ وهيكلةُ تقييمٍ واضحةٌ لكلّ
قطاع»، و«غيرُ متوفّر هو عجزُ بناءٍ من طرفك لأنّ تداول متوفّرٌ لدينا
وأرقام أيضاً». وقِيس قبل الإصلاح:

  · نمطان من اثني عشر بأوزانٍ **فارغة** وشرطِ `abstain_if: ["always"]` —
    `insurance` (‏٢٥ ورقة · ٣ قطاعات) و`fund` (الصناديقُ المتداولة).
    أي «امتناعٌ مطلق» مكتوبٌ في الميثاق.
  · والمحرّكُ **يقيّم التأمينَ فعلاً** عبر مسار `NO_DCF` بوزنَين
    متكافئَين. فالوثيقةُ تناقض محرّكَها، ومن قرأها حسب قطاعاً بلا قياس.
  · و`_spec` في `fair_value.py` يُقرأ من الوثيقة ثمّ **لا يُستعمل**:
    فرعان متطابقان. فالدعوى «أوزانُ المواصفة» كاذبة.

فالحارسُ يمنع الثلاثةَ من العودة: لا نمطَ بلا هيكلة، ولا امتناعَ
مطلقاً، ولا وثيقةً تخالف محرّكَها.
"""
from __future__ import annotations

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
    from app.data.archetype_spec import SECTOR_ARCHETYPE, VALUATION
except ModuleNotFoundError as e:                                  # فجوةُ بيئة
    print(f"⚠ لا مواصفةَ أنماطٍ في هذه البيئة ({e.name}) — لم يُقَس")
    sys.exit(0)

# ── ١ · لا نمطَ بلا هيكلةِ تقييم ───────────────────────────────────────
_empty = [k for k, v in VALUATION.items() if not (v.get("weights") or {})]
check(not _empty, "١ لا نمطَ بأوزانٍ فارغة — لكلٍّ هيكلتُه",
      "، ".join(_empty) if _empty else f"{len(VALUATION)} نمطاً")

# ── ٢ · ولا امتناعَ مطلقاً ─────────────────────────────────────────────
_always = [k for k, v in VALUATION.items()
           if "always" in (v.get("abstain_if") or [])]
check(not _always, "٢ ولا امتناعَ مطلقاً عن قطاعٍ مُلزَمٍ بالإفصاح",
      "، ".join(_always) if _always else "")

# ── ٣ · ومجموعُ الأوزان واحد ───────────────────────────────────────────
_bad_sum = [f"{k}={s:.2f}" for k, v in VALUATION.items()
            if abs((s := sum((v.get("weights") or {}).values())) - 1.0) > 0.005]
check(not _bad_sum, "٣ ومجموعُ أوزانِ كلّ نمطٍ يساوي واحداً",
      "، ".join(_bad_sum) if _bad_sum else "")

# ── ٤ · وكلُّ قطاعٍ مصنَّفٍ يجد هيكلتَه ────────────────────────────────
_orphan = sorted({a for a in SECTOR_ARCHETYPE.values() if a not in VALUATION})
check(not _orphan, "٤ وكلُّ نمطٍ يُصنَّف إليه قطاعٌ له هيكلةٌ في الوثيقة",
      "، ".join(_orphan) if _orphan else
      f"{len(set(SECTOR_ARCHETYPE.values()))} نمطاً مستعملاً")

# ── ٥ · والوثيقةُ تطابق محرّكَها في الأنماط المالية ────────────────────
# المحرّكُ يرجّح `NO_DCF` (بنك · تأمين · تمويل) بوزنَين متكافئَين ‎50/50.
# فوثيقةٌ تكتب غيرَ ذلك تكذب على قارئها، وهذا هو عطبُ D405 عينُه.
_fv = None
for _b in (ROOT / "backend" / "app" / "services" / "fair_value.py",
           pathlib.Path("/app/app/services/fair_value.py")):
    if _b.exists():
        _fv = _b
        break
if _fv is None:
    print("⚠ لا محرّكَ قيمةٍ في مسارٍ معروف — لم يُقَس التطابق")
else:
    SRC = _fv.read_text("utf-8")
    check("WEIGHTS = {_PB: 0.50, _PE: 0.50}" in SRC,
          "٥ المحرّكُ يرجّح الأنماطَ المالية متكافئاً كما تقول الوثيقة")
    _ins = (VALUATION.get("insurance") or {}).get("weights") or {}
    check(abs(_ins.get("residual_income", 0) - 0.50) < 0.005
          and abs(_ins.get("sector_pe", 0) - 0.50) < 0.005,
          "٥ب والتأمينُ في الوثيقةِ ‎50/50 لا فراغٌ")
    # و`_spec` الميّتُ لا يعود: لا قراءةَ أوزانٍ من الوثيقة يُدَّعى
    # استعمالُها ثمّ لا تُستعمل.
    check("_spec = dict(" not in SRC,
          "٥ج ولا قراءةَ أوزانٍ ميّتةً في المحرّك تُدّعى ولا تُستعمل")

# ── ٦ · والصندوقُ المتداولُ له مسطرتُه لا مسطرةُ الشركات ───────────────
_fund = VALUATION.get("fund") or {}
check((_fund.get("weights") or {}).get("nav_per_unit") == 1.00,
      "٦ الصندوقُ المتداول: سعرُه العادلُ صافي أصوله المنشور")
check(len(_fund.get("quality_axes") or []) >= 3,
      "٦ب ودرجةُ جودته من محاورَ تخصُّ الورقةَ لا منشأةً تنتج",
      f"{len(_fund.get('quality_axes') or [])} محاور")

print(("FAIL" if fail else "PASS")
      + " D405 — لكلّ قطاعٍ هيكلةٌ معلَنةٌ تطابق محرّكَها")
sys.exit(fail)
