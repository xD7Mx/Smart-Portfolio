#!/usr/bin/env python3
"""كاشفُ D842 على الخادم — لماذا لا يظهر رسمُ العقد في بطاقة المركز المفتوح: شموعُ عقد NIO المفتوح وسهمِه بكلّ إطار. قراءةٌ فقط."""
import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in (ROOT / "backend", pathlib.Path("/app")):
    if p.exists():
        sys.path.insert(0, str(p))

from app.services.market_data import market_service as M   # noqa: E402
from app.services import saqr_trader as TR                 # noqa: E402


async def main():
    st = TR.load("us")
    cs = [p.get("contract") or p.get("symbol") for p in st.get("positions") or []]
    print("المراكز:", cs)
    for c in cs + ["NIO"]:
        for tf in ("15m", "1h", "4h", "1d"):
            try:
                b = await asyncio.wait_for(M.get_bars(c, tf), 40) or []
            except Exception as e:                       # noqa: BLE001
                print(f"  {c} {tf}: خطأ {type(e).__name__}: {str(e)[:120]}")
                continue
            print(f"  {c} {tf}: {len(b)} شمعة" + (f" · أوّلها {b[0].get('time')} · آخرُها {b[-1].get('time')} إغلاق {b[-1].get('close')}" if b else ""))
asyncio.run(main())
