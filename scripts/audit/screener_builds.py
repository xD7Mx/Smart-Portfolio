#!/usr/bin/env python3
"""جدولُ السوق يُبنى على الخادم — لا يُخدَم من نسخةٍ قديمة (D428).

    docker exec sp_backend python /app/scripts/audit/screener_builds.py

قِيس بتشغيل اللجنة كاملةً: `_enrich_fundamentals` كانت ترفع `NameError`
في كلّ صفٍّ منذ 17 سبتمبر، فيسقط `compute_screener` كلُّه ويُخدَم آخرُ
نسخةٍ سليمةٍ قبله. فهنا يُبنى الجدولُ مرّةً واحدةً كما يبنيه الخادم،
ويُطبع: عددُ الصفوف، وكم منها يحمل سعرَنا العادل، وكم يحمل هدفَ
المحللين، وكم يحمل قيمةً نسبيةً — وهي التي كان يمرّ بها السطرُ الساقط.

وهو يكتب الجدولَ المبنيَّ في مخزن الخادم كما يفعل الخادمُ نفسُه — أي
يُحدّث نسخةً شاخت ستّةَ أيام بنسخةٍ اليوم، ولا يمسّ غيرَها.
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")


async def main() -> int:
    try:
        from app.services.market_screener import compute_screener
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0
    t0 = time.time()
    try:
        rows = await compute_screener()
    except Exception as e:                                        # noqa: BLE001
        print(f"FAIL الجدولُ لم يُبنَ — {type(e).__name__}: {e}")
        return 1
    rows = rows or []
    n = len(rows)

    def _cnt(k):
        return sum(1 for r in rows if r.get(k) is not None)

    print(f"صفوف: {n} · ثوانٍ: {time.time() - t0:.0f}")
    print(f"  سعرُنا العادل (fair_value): {_cnt('fair_value')}")
    print(f"  هدفُ المحللين (analyst_target): {_cnt('analyst_target')}")
    print(f"  قيمةٌ نسبيةٌ إلى القطاع (rel_value): {_cnt('rel_value')}")
    print(f"  فجوةُ سعرنا العادل (fair_value_upside_pct):"
          f" {_cnt('fair_value_upside_pct')}")
    ok = n >= 250
    print(("PASS" if ok else "FAIL")
          + f" D428 — جدولُ السوق يُبنى ({n} صفّاً)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
