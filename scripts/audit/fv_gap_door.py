"""كاشفٌ للقراءة فقط: الشركاتُ بلا سعرٍ عادل في فرز السوق — وسببُ كلٍّ منها.

    docker exec sp_backend python /app/scripts/audit/fv_gap_door.py
"""
import asyncio
import sys
from collections import Counter

sys.path.insert(0, "/app")
from app.services.market_screener import get_cached_screener      # noqa: E402
from app.services.content_engine import fund_store_load           # noqa: E402
from app.data.universe import is_etf                               # noqa: E402


async def main():
    from app.services.fair_value_models import for_symbol
    rows = get_cached_screener() or []
    store = fund_store_load() or {}
    gap = [r for r in rows if not r.get("fair_value")]
    why = Counter()
    print(f"صفوف {len(rows)} · بلا سعرٍ عادل {len(gap)}")
    for r in gap:
        s = str(r["symbol"]).replace(".SR", "")
        if is_etf(s):
            why["صندوقُ مؤشّر — لا قوائم"] += 1
            continue
        st = store.get(s) or {}
        m = await for_symbol(s) or {}
        reason = st.get("fair_value_unavailable") or m.get("reason") or "—"
        n = len(m.get("models") or [])
        why[str(reason)[:70]] += 1
        print(f"   {s} {r.get('name', '')[:18]} · قطاع {r.get('sector')} · نماذج {n} · {str(reason)[:90]}")
    print("\n═ الأسباب:")
    for k, v in why.most_common():
        print(f"   {v:>3} × {k}")


asyncio.run(main())
