#!/usr/bin/env python3
"""أين يقف المخزون: المخزَن · باب المحرّك · المحرّك (D430).

    docker exec sp_backend python /app/scripts/audit/inventory_reach.py

أُضيف «inventories» إلى خريطة «تداول» وحُصدت القوائم من جديد، وبقيت
مسحةُ التقييم «لها درجةُ جودة: 251» كما كانت. فالاسمُ وحدَه لم يصل
النتيجة — ولا يُفترَض السبب: يُقاس الحقلُ في كلّ طبقةٍ لأوراقٍ بعينها
ممّن سقطت درجتُها. قارئٌ فقط.
"""
from __future__ import annotations

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

SYMS = ("1810", "4191", "4210", "6018")


async def main() -> int:
    try:
        from app.services import tadawul_xbrl as X
        from app.services.market_data import market_service
        from app.services.analysis import analyze_company
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0
    for s in SYMS:
        print(f"═ {s} ═")
        rows = (X.for_symbol(s, "annual") or []) + (X.for_symbol(s, "quarterly") or [])
        last = max(rows, key=lambda r: str(r.get("as_of") or "")) if rows else {}
        print(f"  ١ مخزَنُ XBRL: فتراتٌ={len(rows)} · الأحدث={last.get('as_of')}"
              f" · inventory={last.get('inventory')}")
        try:
            d = await market_service.get_financials(s, allow_supplement=False)
            per = [p for p in ((d or {}).get("periods") or []) if p.get("as_of")]
            lp = max(per, key=lambda r: str(r.get("as_of"))) if per else {}
            src = (lp.get("field_sources") or {}).get("inventory")
            print(f"  ٢ بابُ المحرّك: الأحدث={lp.get('as_of')}"
                  f" · inventory={lp.get('inventory')} · مصدره={src}")
        except Exception as e:                                    # noqa: BLE001
            print(f"  ٢ بابُ المحرّك: {type(e).__name__}: {e}")
        try:
            a = await analyze_company(f"{s}.SR", allow_supplement=False)
            fin = (a or {}).get("financial") or {}
            sp = fin.get("spec") or {}
            print(f"  ٣ المحرّك: درجة={fin.get('score')} · ناقص={sp.get('missing')}")
        except Exception as e:                                    # noqa: BLE001
            print(f"  ٣ المحرّك: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
