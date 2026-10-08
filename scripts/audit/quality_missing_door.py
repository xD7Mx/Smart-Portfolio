#!/usr/bin/env python3
"""تشخيص: لماذا تغيب درجةُ الجودة بلا سبب (صالح الراشد · دي بي اس · أرماح) — المخزنُ والفرزُ والكاش والتحليل. قارئٌ فقط."""
import asyncio, sys
sys.path.insert(0, "/app")
from app.services import cache
from app.services.analysis import analyze_company
from app.services.content_engine import fund_store_load
from app.services.market_screener import get_cached_screener
st = fund_store_load()
rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}

async def main():
    for s in ("1324", "7205", "6022"):
        a = await analyze_company(f"{s}.SR", allow_supplement=False) or {}
        f = a.get("financial") or {}
        print(s, "· مخزن:", {k: (st.get(s) or {}).get(k) for k in ("finance_score", "finance_score_unavailable", "stmt_asof", "score_asof")},
              "· فرز:", (rows.get(s) or {}).get("finance_score"), "· كاش:", cache.get(f"screener:gov:{s}.SR"),
              "· تحليل:", {"score": f.get("score"), "verdict": (f.get("verdict") or "")[:90]},
              "· حوكمة:", (a.get("governance") or {}).get("score") if isinstance(a.get("governance"), dict) else None)
asyncio.run(main())
