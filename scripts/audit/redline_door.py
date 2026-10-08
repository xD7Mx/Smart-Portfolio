#!/usr/bin/env python3
"""تشخيص: الخطوطُ الحمراء للشركات ذوات درجة جودةٍ ≥ 65 — ومصدرُ قفزات السلسلة الفنّية. قارئٌ فقط."""
import asyncio, sys
sys.path.insert(0, "/app")
from app.services.analysis import analyze_company
from app.services.market_screener import get_cached_screener

rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}

async def main():
    for s in ("2380", "4050", "4240", "6012", "4250", "4018", "4071", "4265"):
        a = await analyze_company(f"{s}.SR", allow_supplement=False) or {}
        print(f"{s} {a.get('name')} · جودة {(a.get('financial') or {}).get('score')} · "
              + " | ".join(f"{x.get('id')}: {x.get('message')}" for x in a.get("red_lines") or []))
    for s in ("2030", "4160", "4140", "6040", "6050"):
        a = await analyze_company(f"{s}.SR", allow_supplement=False) or {}
        f = a.get("financial") or {}
        print(f"بلا جودة {s} {a.get('name')} · score {f.get('score')} · has_statements {f.get('has_statements')} · "
              f"reason {f.get('reason') or f.get('unavailable_reason') or (a.get('governance') or {}).get('reason')}")
asyncio.run(main())
