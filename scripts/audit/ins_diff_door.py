#!/usr/bin/env python3
"""المرشَّح 2.3 · تشخيص: لماذا تراجع انحرافُ قطاع التأمين عن المحلّلين 7.1٪ ← 11.6٪؟ قارئٌ فقط.

لا يمسّ الحذفُ بالنمط التأمينَ — فالمشتبه: تسويةُ عدد الأسهم بحدّ 15٪ (‏D674)، أو حجبُ البعيد. فلكلّ مؤمِّنٍ له هدفُ
محلّلين: رقمُ الإنتاج (2.2) ورقمُ المرشَّح وملاحظاتُ الأسهم، وخطأُ كلٍّ عن الهدف.
"""
import asyncio, sys
sys.path.insert(0, "/app")
from app.services import cache as _c, lastgood as _lg
_set0 = _c.set
_c.set = lambda key, value, ttl: _set0(key, value, min(ttl, _c._PERSIST_MIN_TTL - 60))
_lg.save = lambda *a, **k: None


async def main():
    from app.data.market_universe import MARKET_UNIVERSE as MU
    from app.services.content_engine import fund_store_load
    from app.services.market_screener import get_cached_screener
    from app.services.fair_value_models import for_symbol
    from app.services.analysis import confidence_of
    store = fund_store_load()
    rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
    e22, e23 = [], []
    for s, m in sorted(MU.items()):
        if m.get("sector") != "التأمين":
            continue
        r = rows.get(s) or {}
        at, px = r.get("analyst_target"), r.get("price")
        v22 = (store.get(s) or {}).get("fair_value")
        f = await for_symbol(s) or {}
        v23 = f.get("value")
        conf = confidence_of(f) if f else None
        sh = [n for n in (f.get("notes") or []) if "عددُ الأسهم" in str(n)]
        mark = ""
        if isinstance(at, (int, float)) and at > 0:
            if isinstance(v22, (int, float)) and v22 > 0:
                e22.append(abs(v22 / at - 1))
            if isinstance(v23, (int, float)) and v23 > 0 and not (conf == "منخفضة" and px and abs(v23 / px - 1) > 0.6):
                e23.append(abs(v23 / at - 1))
            mark = f" · هدف {at}"
        if mark or sh:
            print(f"   {s} {m.get('name_ar')} · سعر {px} · 2.2: {v22} · 2.3: {v23} ({conf}){mark}"
                  + (f" · {sh[0][:90]}" if sh else ""))
    import statistics as st
    print(f"═ وسيطُ الخطأ: 2.2 {st.median(e22) if e22 else 0:.1%} (n={len(e22)}) · 2.3 {st.median(e23) if e23 else 0:.1%} (n={len(e23)})")


asyncio.run(main())
