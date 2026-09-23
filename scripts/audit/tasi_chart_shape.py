#!/usr/bin/env python3
"""شكلُ ما يردّه مولّدُ رسم «تداول» لتاريخ «تاسي» — قياسٌ قبل البناء (D438).

    docker exec sp_backend python /app/scripts/audit/tasi_chart_shape.py

كشف `tasi_history_door.py` في الصفحة الرئيسية مسارَ ChartGenerator بمعامل
`chart-parameter=tasi`. يُطلب هنا بانتحال البصمة ويُطبع: الحالة، ونوعُ
الجسم، وعددُ النقاط، وأوّلُها وآخرُها، والمفاتيح. قارئٌ فقط.
"""
from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, "/app")

BASE = "https://www.saudiexchange.sa/tadawul.eportal.charts.v2/ChartGenerator"
QS = ("methodType=parsingMethod&chart-type={t}&chart-parameter={p}"
      "&format=json&pageName=MarketStatusHomeGraph")
CASES = (("SQL_MI_MSPV", "tasi"), ("SQL_MI_MSPV", "mt30"))


def _walk(o, depth=0):
    if depth > 3:
        return
    if isinstance(o, dict):
        print("   " * depth + f"{{}} مفاتيح: {list(o)[:15]}")
        for k, v in list(o.items())[:6]:
            if isinstance(v, (list, dict)):
                print("   " * depth + f" ↳ {k}:")
                _walk(v, depth + 1)
    elif isinstance(o, list):
        print("   " * depth + f"[] {len(o)} عنصراً · أوّل: {str(o[:1])[:200]} · آخر: {str(o[-1:])[:200]}")
        if o and isinstance(o[0], (dict, list)):
            _walk(o[0], depth + 1)


async def main() -> int:
    try:
        from app.services.tadawul_http import fetch
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0
    for t, p in CASES:
        url = f"{BASE}?{QS.format(t=t, p=p)}"
        try:
            st, body = await fetch(url)
        except Exception as e:                                    # noqa: BLE001
            print(f"✘ {p} — {type(e).__name__}: {e}")
            continue
        print(f"═ {p} — HTTP {st} · {len(body or '')} حرفاً · بداية: {(body or '')[:300]!r}")
        try:
            _walk(json.loads(body))
        except Exception as e:                                    # noqa: BLE001
            print(f"   ليس JSON — {type(e).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
