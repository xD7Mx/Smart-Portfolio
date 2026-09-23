#!/usr/bin/env python3
"""الأوراقُ المحجوبُ سعرُها العادل (D449) — مصنَّفةً بنمطها ومساراتها. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fv_withheld_causes.py
"""
import asyncio, collections, sys
sys.path.insert(0, "/app")


async def main():
    from app.services.content_engine import fund_store_load
    from app.services.analysis import analyze_company
    from app.services.statement_merge import archetype_of
    st = fund_store_load() or {}
    wh = [s for s, r in st.items() if (r or {}).get("fair_value") is None]
    print(f"محجوبةٌ أو ممتنعة: {len(wh)} من {len(st)}")
    by_arch, by_dir, by_path = collections.Counter(), collections.Counter(), collections.Counter()
    rows = []
    for s in wh:
        an = await analyze_company(f"{s}.SR", allow_supplement=False) or {}
        d = an.get("fair_value_detail") or {}
        iv, px = d.get("implausible_value"), an.get("price")
        a = archetype_of(s)
        by_arch[a] += 1
        q = (iv / px) if isinstance(iv, (int, float)) and px else None
        by_dir["دون" if q is not None and q < 1 else "فوق" if q else "ممتنع"] += 1
        ms = [(m.get("name"), m.get("value")) for m in d.get("methods") or []]
        for n, _ in ms:
            by_path[n] += 1
        rows.append((s, a, px, iv, round(q, 2) if q else None, ms, (d.get("unavailable_reason") or "")[:60]))
    print("النمط:", by_arch.most_common())
    print("الاتجاه:", by_dir.most_common())
    print("المسارات:", by_path.most_common())
    for r in sorted(rows, key=lambda x: (x[1] or "", x[4] or 0)):
        print("  ", r[:5], [(n[:18], v) for n, v in r[5]], r[6] if not r[3] else "")
    return 0

sys.exit(asyncio.run(main()))
