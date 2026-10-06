"""كاشف (قراءةٌ فقط): لماذا نزلت ثقةُ السعر العادل للبنوك — أسبابُ الخصم كما يكتبها المحرّك.

    docker exec sp_backend python /app/scripts/audit/bank_conf_door.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services.analysis import analyze_company
    for s in ("1120", "1150", "1010", "1060"):
        a = await analyze_company(f"{s}.SR", None) or {}
        print(f"@@{s}@@ " + json.dumps({"conf": a.get("fair_value_conf"), "score": a.get("fair_value_conf_score"),
                                        "why": a.get("fair_value_conf_why"), "asof": a.get("fair_value_asof"),
                                        "age": a.get("fair_value_age_days"), "stale": a.get("fair_value_stale")},
                                       ensure_ascii=False, default=str)[:1500], flush=True)

asyncio.run(main())
