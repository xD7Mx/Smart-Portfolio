#!/usr/bin/env python3
"""تقريرُ المسحة يُسمّي سببَ التعذّر لا عددَه وحدَه (D424).

    python3 scripts/audit/sweep_names_failure.py

قِيس على خادم المالك: خرجت مسحةُ التقييم «تعذّرت 268 من 273 · لها سعرٌ
عادل: صفر» — والسببُ خطأٌ واحدٌ في سطرٍ واحد (`ValueError` في
`risk_flags`). لكنّ `_one` كانت تمسكه في مستوى **debug** فلا يظهر في
سجلّ الدورة، واحتاج كشفُه كاشفاً مستقلّاً ودورةً ثانيةً على الخادم.

فالشرطُ هنا: محرّكٌ يرفع في كلّ ورقة، فيخرج التقريرُ **باسمِ الخطأ
ونصِّه** — لا برقمٍ مجرّد.
"""
from __future__ import annotations

import asyncio
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
    from app.services import analysis, content_engine
    from app.services import market_valuation_sweep as M
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)


async def _boom(*_a, **_k):
    raise ValueError("not enough values to unpack (expected 3, got 2)")

# لا يُكتب شيءٌ في مخزَن المالك: الكتابةُ تُستبدَل بلا شيء
content_engine._fund_store_put_many = lambda *_a, **_k: None
analysis.analyze_company = _boom

rep = asyncio.run(M.sweep(["1010", "2222", "2010"]))

check(rep.get("تعذّرت") == 3, "١ التعذّرُ يُعَدّ", str(rep.get("تعذّرت")))
_why = rep.get("أسبابُ التعذّر") or {}
check(bool(_why), "٢ والتقريرُ يحمل أسبابَ التعذّر لا عددَها وحدَه",
      str(_why)[:120])
check(any("ValueError" in k and "unpack" in k for k in _why),
      "٢ب باسمِ الخطأ ونصِّه")
check(sum(_why.values()) == 3 if _why else False,
      "٢ج وعددُ كلِّ سببٍ يطابق ما تعذّر")

# ── ٣ · والردُّ الفارغُ يُسمّى سببُه أيضاً ─────────────────────────
async def _empty(*_a, **_k):
    return None

analysis.analyze_company = _empty
rep2 = asyncio.run(M.sweep(["1010", "2222"]))
_why2 = rep2.get("أسبابُ التعذّر") or {}
check(rep2.get("تعذّرت") == 2 and sum(_why2.values()) == 2,
      "٣ والردُّ الفارغُ بلا استثناءٍ يُسمّى سببُه لا يُعَدّ صامتاً",
      str(_why2)[:120])

print(("FAIL" if fail else "PASS")
      + " D424 — التعذّرُ الجماعيُّ يُسمّى سببُه في تقرير المسحة")
sys.exit(fail)
